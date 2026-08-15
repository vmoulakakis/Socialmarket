-- Demand Intelligence V3
-- Non-destructive analytical layer. Existing demand / competition / pain scores remain authoritative.

create index if not exists evidence_observations_fts_simple_idx
on evidence.observations
using gin (to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(body,'')));

create index if not exists evidence_observations_title_trgm_idx
on evidence.observations
using gin (title extensions.gin_trgm_ops);

create table if not exists intel.demand_external_source_registry (
  source_key text primary key,
  source_name text not null,
  source_domain text not null,
  source_class text not null check (source_class in ('official_statistics','public_institution','industry_primary','marketplace','social','other')),
  geography text not null default 'GR',
  authority_weight numeric not null check (authority_weight between 0 and 1),
  cadence text,
  measures jsonb not null default '[]'::jsonb,
  notes text,
  enabled boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

insert into intel.demand_external_source_registry(source_key,source_name,source_domain,source_class,geography,authority_weight,cadence,measures,notes)
values
 ('elstat_retail','ELSTAT Retail Trade','statistics.gr','official_statistics','GR',1.0,'monthly','["retail_turnover_index","retail_volume_index"]'::jsonb,'Macro/category context only; never treated as product search demand.'),
 ('elstat_hbs','ELSTAT Household Budget Survey','statistics.gr','official_statistics','GR',1.0,'annual','["household_expenditure_mix"]'::jsonb,'Household expenditure context.'),
 ('elstat_ict','ELSTAT ICT Households & Individuals','statistics.gr','official_statistics','GR',1.0,'annual','["online_purchase_behavior","digital_usage"]'::jsonb,'Digital commerce adoption context.'),
 ('eurostat_digital','Eurostat Digital Economy & Society','ec.europa.eu','public_institution','GR',1.0,'annual','["online_shopping","enterprise_esales","digital_behavior"]'::jsonb,'EU-comparable digital commerce context.'),
 ('greca_research','Greek eCommerce Association Research','greekecommerce.gr','industry_primary','GR',0.82,'periodic','["ecommerce_operations","payments","fulfilment","industry_benchmarks"]'::jsonb,'Industry evidence; not official statistics.')
on conflict (source_key) do update set
 source_name=excluded.source_name,
 source_domain=excluded.source_domain,
 source_class=excluded.source_class,
 authority_weight=excluded.authority_weight,
 cadence=excluded.cadence,
 measures=excluded.measures,
 notes=excluded.notes,
 updated_at=now();

create table if not exists intel.demand_analysis_runs (
  id uuid primary key default gen_random_uuid(),
  taxonomy_id uuid not null,
  analysis_mode text not null default 'autonomous',
  status text not null default 'completed' check (status in ('running','completed','failed','withheld')),
  generated_at timestamptz not null default now(),
  market_observed_at timestamptz,
  retrieval_version text not null default 'hybrid_rag_v3',
  fuzzy_version text not null default 'fuzzy_uncertainty_v1',
  forecast_version text not null default 'shadow_ensemble_v1',
  presentation_version text not null default 'narrative_story_v1',
  data_contract jsonb not null default '{}'::jsonb,
  analysis jsonb not null default '{}'::jsonb,
  evidence_ids uuid[] not null default '{}'::uuid[],
  created_by text,
  error text
);

create index if not exists demand_analysis_runs_taxonomy_idx
on intel.demand_analysis_runs(taxonomy_id, generated_at desc);

create or replace function public.admin_demand_deep_context(
  p_taxonomy_id uuid,
  p_query text default null,
  p_limit integer default 50
) returns jsonb
language plpgsql
security definer
set search_path=''
as $$
declare
  market_row jsonb;
  aliases jsonb := '[]'::jsonb;
  history jsonb := '[]'::jsonb;
  evidence_rows jsonb := '[]'::jsonb;
  supply_rows jsonb := '[]'::jsonb;
  source_mix jsonb := '[]'::jsonb;
  query_text text := '';
  category_name text;
  subcategory_name text;
begin
  if not public.socialmarket_is_admin() then
    raise exception 'admin_only';
  end if;

  select to_jsonb(x), coalesce(x.query_aliases,'[]'::jsonb), x.category_name, x.subcategory_name
  into market_row, aliases, category_name, subcategory_name
  from api.semantic_category_market_v2 x
  where x.taxonomy_id=p_taxonomy_id
  limit 1;

  if market_row is null then
    return jsonb_build_object('error','taxonomy_not_found','taxonomy_id',p_taxonomy_id);
  end if;

  query_text := trim(coalesce(p_query,''));
  if query_text='' then
    select string_agg(v,' ') into query_text
    from jsonb_array_elements_text(aliases) a(v);
  end if;
  query_text := coalesce(query_text, category_name || ' ' || coalesce(subcategory_name,''));

  select coalesce(jsonb_agg(to_jsonb(h) order by h.observed_at desc),'[]'::jsonb)
  into history
  from (
    select observed_at,demand_score,competition_score,pain_gap_score,satisfaction_score,opportunity_score,confidence,methodology_version
    from intel.category_market_snapshots
    where taxonomy_id=p_taxonomy_id
    order by observed_at desc
    limit 180
  ) h;

  with candidates as (
    select o.*,
      case when o.entity_type='taxonomy' and o.entity_id=p_taxonomy_id then 1.0 else 0.0 end as direct_match,
      ts_rank_cd(
        to_tsvector('simple',coalesce(o.title,'') || ' ' || coalesce(o.body,'')),
        websearch_to_tsquery('simple',query_text)
      ) as fts_rank,
      greatest(
        extensions.word_similarity(lower(query_text),lower(coalesce(o.title,''))),
        extensions.word_similarity(lower(query_text),lower(left(coalesce(o.body,''),800)))
      ) as fuzzy_rank,
      greatest(0.0, 1.0 - least(1.0, extract(epoch from (now()-coalesce(o.published_at,o.collected_at)))/(86400.0*180.0))) as recency_rank,
      case
        when lower(coalesce(o.source_domain,'')) like '%statistics.gr%' then 1.0
        when lower(coalesce(o.source_domain,'')) like '%ec.europa.eu%' then 1.0
        when lower(coalesce(o.source_domain,'')) like '%eurostat%' then 1.0
        when lower(coalesce(o.source_domain,'')) like '%greekecommerce.gr%' then 0.82
        else 0.58
      end as authority_rank
    from evidence.observations o
    where
      (o.entity_type='taxonomy' and o.entity_id=p_taxonomy_id)
      or to_tsvector('simple',coalesce(o.title,'') || ' ' || coalesce(o.body,'')) @@ websearch_to_tsquery('simple',query_text)
      or extensions.word_similarity(lower(query_text),lower(coalesce(o.title,''))) >= 0.22
  ), ranked as (
    select c.*,
      (c.direct_match*0.35 + least(1.0,c.fts_rank*4.0)*0.20 + c.fuzzy_rank*0.15 + coalesce(c.confidence,0.5)*0.10 + c.recency_rank*0.10 + c.authority_rank*0.10) as retrieval_score
    from candidates c
  )
  select coalesce(jsonb_agg(jsonb_build_object(
    'id',r.id,
    'entity_type',r.entity_type,
    'source_kind',r.source_kind,
    'platform',r.platform,
    'source_url',r.source_url,
    'source_domain',r.source_domain,
    'title',r.title,
    'body',left(r.body,1600),
    'published_at',r.published_at,
    'collected_at',r.collected_at,
    'confidence',r.confidence,
    'validation_status',r.validation_status,
    'retrieval',jsonb_build_object('score',round(r.retrieval_score::numeric,4),'direct',r.direct_match,'fts',r.fts_rank,'fuzzy',r.fuzzy_rank,'recency',r.recency_rank,'authority',r.authority_rank),
    'metrics',r.metrics,
    'metadata',r.metadata
  ) order by r.retrieval_score desc),'[]'::jsonb)
  into evidence_rows
  from (
    select * from ranked
    order by retrieval_score desc, coalesce(published_at,collected_at) desc
    limit greatest(10,least(coalesce(p_limit,50),120))
  ) r;

  select coalesce(jsonb_agg(to_jsonb(s) order by s.opportunity_score desc nulls last, s.trust_score desc nulls last),'[]'::jsonb)
  into supply_rows
  from (
    select g.merchant_id,g.canonical_name,g.taxonomy_id,g.taxonomy_name,g.primary_category,g.primary_subcategory,
           g.opportunity_score,g.trust_score,g.complaint_risk_score,g.confidence,g.observed_at,
           mr.program_id,mr.program_name,mr.commercial_score,mr.commercial_confidence,
           mr.competition_intensity_score,mr.greek_market_fit_score,mr.deep_research_score,mr.research_confidence,
           mr.risk_flag,mr.risk_reason,mr.evidence_count,mr.researched_at
    from api.merchant_gap_rankings g
    left join api.merchant_rankings mr on mr.merchant_id=g.merchant_id
    where g.taxonomy_id=p_taxonomy_id
    order by g.opportunity_score desc nulls last, g.trust_score desc nulls last
    limit 40
  ) s;

  with e as (
    select value as x from jsonb_array_elements(evidence_rows)
  )
  select coalesce(jsonb_agg(to_jsonb(q) order by q.observations desc),'[]'::jsonb)
  into source_mix
  from (
    select x->>'source_domain' source_domain,
           count(*)::int observations,
           round(avg(coalesce((x->>'confidence')::numeric,0.5)),3) avg_confidence,
           round(avg(coalesce((x->'retrieval'->>'authority')::numeric,0.58)),3) avg_authority
    from e
    group by 1
  ) q;

  return jsonb_build_object(
    'taxonomy_id',p_taxonomy_id,
    'query',query_text,
    'market',market_row,
    'history',history,
    'retrieved_evidence',evidence_rows,
    'source_mix',source_mix,
    'supply_context',supply_rows,
    'validated_pains',coalesce((select jsonb_agg(to_jsonb(v)) from public.validated_pain_clusters v where v.category=category_name and (subcategory_name is null or v.subcategory=subcategory_name)),'[]'::jsonb),
    'retrieval_semantics',jsonb_build_object(
      'method','hybrid direct + PostgreSQL FTS + pg_trgm fuzzy + confidence + recency + source authority',
      'purpose','evidence retrieval and context ranking only',
      'does_not_modify_scores',true,
      'missing_remains_missing',true
    ),
    'forecast_gate',jsonb_build_object(
      'history_points',jsonb_array_length(history),
      'neural_status',case when jsonb_array_length(history)>=90 then 'eligible_for_shadow_backtest' else 'withheld_insufficient_history' end,
      'minimum_history_points',90,
      'production_forecast_requires_backtest',true
    )
  );
end;
$$;

revoke all on function public.admin_demand_deep_context(uuid,text,integer) from public;
grant execute on function public.admin_demand_deep_context(uuid,text,integer) to authenticated;

create or replace function public.admin_save_demand_analysis_v3(
  p_taxonomy_id uuid,
  p_market_observed_at timestamptz,
  p_data_contract jsonb,
  p_analysis jsonb,
  p_evidence_ids uuid[] default '{}'::uuid[],
  p_status text default 'completed'
) returns uuid
language plpgsql
security definer
set search_path=''
as $$
declare out_id uuid;
begin
  if not public.socialmarket_is_admin() then raise exception 'admin_only'; end if;
  insert into intel.demand_analysis_runs(taxonomy_id,status,market_observed_at,data_contract,analysis,evidence_ids,created_by)
  values(p_taxonomy_id,p_status,p_market_observed_at,coalesce(p_data_contract,'{}'::jsonb),coalesce(p_analysis,'{}'::jsonb),coalesce(p_evidence_ids,'{}'::uuid[]),lower(coalesce(auth.jwt()->>'email','')))
  returning id into out_id;
  return out_id;
end;
$$;

revoke all on function public.admin_save_demand_analysis_v3(uuid,timestamptz,jsonb,jsonb,uuid[],text) from public;
grant execute on function public.admin_save_demand_analysis_v3(uuid,timestamptz,jsonb,jsonb,uuid[],text) to authenticated;
