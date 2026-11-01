-- SocialMarket AI 3.0, P0: traceable evidence + opportunity research, additive/private only.
-- IMPORTANT: a high demand / low supply claim is NEVER created from corpus size,
-- affiliate feed coverage, model output, or lexical similarity alone.
create table if not exists sm_intel.opportunity_research_v3 (
 id uuid primary key default gen_random_uuid(),
 problem_cluster_id uuid not null references public.market_problem_clusters(id) on delete restrict,
 region_code text not null default 'GR' check(region_code='GR'),
 assessed_at timestamptz not null default now(),
 demand_sources integer not null default 0,
 supply_sources integer not null default 0,
 counter_sources integer not null default 0,
 verified_demand_sources integer not null default 0,
 verified_supply_sources integer not null default 0,
 distinct_verified_demand_domains integer not null default 0,
 distinct_verified_supply_domains integer not null default 0,
 evidence_status text not null default 'research_needed'
   check(evidence_status in ('research_needed','partial_evidence','ready_for_independent_review')),
 market_demand_estimate numeric,
 market_supply_gap_estimate numeric,
 estimate_unit text,
 research_gaps jsonb not null default '[]'::jsonb check (jsonb_typeof(research_gaps)='array'),
 source_snapshot jsonb not null default '{}'::jsonb,
 methodology_version text not null default 'source_provenance_v3',
 unique(problem_cluster_id,region_code,methodology_version),
 check (demand_sources>=verified_demand_sources and supply_sources>=verified_supply_sources),
 check(market_demand_estimate is null and market_supply_gap_estimate is null)
);
create index if not exists sm_v3_research_queue on sm_intel.opportunity_research_v3(evidence_status,assessed_at);

create table if not exists sm_intel.opportunity_product_candidates_v3 (
 problem_cluster_id uuid not null references public.market_problem_clusters(id) on delete restrict,
 document_id uuid not null references sm_intel.search_documents(id) on delete cascade,
 retrieval_version text not null default 'fts_rrf_v3',
 retrieval_rank integer not null check(retrieval_rank between 1 and 30),
 rrf_score double precision not null check(rrf_score>=0),
 relevance_review text not null default 'unverified'
   check(relevance_review in ('unverified','rejected','needs_product_research')),
 evidence_statement text not null default 'lexical or semantic proximity; not evidence of solution efficacy, stock or merchant approval',
 evaluated_at timestamptz not null default now(),
 primary key(problem_cluster_id,document_id,retrieval_version)
);
create index if not exists sm_v3_matches_by_problem on sm_intel.opportunity_product_candidates_v3(problem_cluster_id,retrieval_rank);

alter table sm_intel.opportunity_research_v3 enable row level security;
alter table sm_intel.opportunity_product_candidates_v3 enable row level security;
revoke all on sm_intel.opportunity_research_v3,sm_intel.opportunity_product_candidates_v3 from public,anon,authenticated;
grant select,insert,update on sm_intel.opportunity_research_v3,sm_intel.opportunity_product_candidates_v3 to service_role;

create or replace function sm_intel.refresh_opportunity_research_v3(p_limit int default 100)
returns jsonb language plpgsql volatile security invoker set search_path='' as $$
declare researched int := 0; matches int := 0;
begin
 if p_limit is null or p_limit<1 or p_limit>100 then raise exception 'limit_out_of_range'; end if;
 with problems as (
  select id,problem_title,category from public.market_problem_clusters
  where market_code='GR' order by id limit p_limit
 ),
 signals as (
  select p.id as problem_id,
  count(e.id) filter(where e.signal_kind='demand' and e.observed_at>now()-interval '90 days' and
       (e.expires_at is null or e.expires_at>now()))::integer as demand_n,
  count(e.id) filter(where e.signal_kind='supply' and e.observed_at>now()-interval '90 days' and
       (e.expires_at is null or e.expires_at>now()))::integer as supply_n,
  count(e.id) filter(where e.signal_kind in ('counter_evidence','competition') and
       e.observed_at>now()-interval '90 days' and (e.expires_at is null or e.expires_at>now()))::integer as counters_n,
  count(e.id) filter(where e.signal_kind='demand' and e.audit_status='verified' and
       e.observed_at>now()-interval '90 days' and (e.expires_at is null or e.expires_at>now()))::integer as verified_d_n,
  count(e.id) filter(where e.signal_kind='supply' and e.audit_status='verified' and
       e.observed_at>now()-interval '90 days' and (e.expires_at is null or e.expires_at>now()))::integer as verified_s_n,
  count(distinct nullif(lower(split_part(e.source_url,'/',3)),'')) filter(
       where e.signal_kind='demand' and e.audit_status='verified' and
       e.observed_at>now()-interval '90 days' and (e.expires_at is null or e.expires_at>now()))::integer as verified_d_domains,
  count(distinct nullif(lower(split_part(e.source_url,'/',3)),'')) filter(
       where e.signal_kind='supply' and e.audit_status='verified' and
       e.observed_at>now()-interval '90 days' and (e.expires_at is null or e.expires_at>now()))::integer as verified_s_domains,
  coalesce(jsonb_agg(jsonb_build_object('id',e.id,'kind',e.signal_kind,
     'status',e.audit_status,'source_url',e.source_url,'observed_at',e.observed_at,
     'confidence',e.confidence) order by e.observed_at desc)
     filter(where e.id is not null),'[]'::jsonb) as audit_snapshot
  from problems p left join sm_intel.research_evidence e on e.problem_cluster_id=p.id
       and e.market_code='GR' and e.region_code='GR'
  group by p.id
 ), proposed as (
 select s.*,
  case when s.verified_d_domains>=2 and s.verified_s_domains>=2
        then 'ready_for_independent_review'
       when s.demand_n>0 or s.supply_n>0 or s.counters_n>0 then 'partial_evidence'
       else 'research_needed' end as next_status,
  (case when s.verified_d_domains<2 then jsonb_build_array('need_two_verified_demand_source_domains')
     else '[]'::jsonb end) ||
  (case when s.verified_s_domains<2 then jsonb_build_array('need_two_verified_supply_source_domains')
     else '[]'::jsonb end) ||
  (case when s.counters_n=0 then jsonb_build_array('need_counterevidence_or_competitor_research')
     else '[]'::jsonb end) as gaps
 from signals s
 ), written as (
  insert into sm_intel.opportunity_research_v3 (
    problem_cluster_id,demand_sources,supply_sources,counter_sources,
    verified_demand_sources,verified_supply_sources,distinct_verified_demand_domains,
    distinct_verified_supply_domains,evidence_status,research_gaps,source_snapshot,assessed_at
  ) select problem_id,demand_n,supply_n,counters_n,verified_d_n,verified_s_n,
           verified_d_domains,verified_s_domains,next_status,gaps,
           jsonb_build_object('observed_90_day_signals',audit_snapshot,
            'review_note','Distinct domains are not proof of source independence',
            'source_policy','Only verified source evidence can unlock independent review'),
           now()
    from proposed
  on conflict(problem_cluster_id,region_code,methodology_version)
  do update set demand_sources=excluded.demand_sources,
    supply_sources=excluded.supply_sources,counter_sources=excluded.counter_sources,
    verified_demand_sources=excluded.verified_demand_sources,
    verified_supply_sources=excluded.verified_supply_sources,
    distinct_verified_demand_domains=excluded.distinct_verified_demand_domains,
    distinct_verified_supply_domains=excluded.distinct_verified_supply_domains,
    evidence_status=excluded.evidence_status,
    research_gaps=excluded.research_gaps,source_snapshot=excluded.source_snapshot,
    assessed_at=now()
  returning id
 )
 select count(*) into researched from written;
 -- Search returns *candidate* product relevance only. Never creates promotion-ready offers.
 with problems as (
  select id,problem_title from public.market_problem_clusters
  where market_code='GR' order by id limit p_limit
 ), retrieved as (
  select p.id problem_id,h.doc_id,h.rrf_score,
   row_number() over(partition by p.id order by h.rrf_score desc,h.doc_id) as rank
  from problems p cross join lateral sm_intel.hybrid_retrieve(
       p.problem_title,null,8,array['product']::text[],true) h
  where h.entity_type='product'
 ), ins as (
  insert into sm_intel.opportunity_product_candidates_v3
     (problem_cluster_id,document_id,retrieval_rank,rrf_score)
  select problem_id,doc_id,rank::integer,rrf_score from retrieved
  on conflict(problem_cluster_id,document_id,retrieval_version)
  do update set retrieval_rank=excluded.retrieval_rank,rrf_score=excluded.rrf_score,
                evaluated_at=now()
  returning 1
 )
 select count(*) into matches from ins;
 return jsonb_build_object('problems_assessed',researched,
    'candidate_matches_scored',matches,
    'promotions_created',0,'market_demand_estimates_created',0,
    'mode','evidence_gated_and_unverified_match_only');
end $$;
revoke all on function sm_intel.refresh_opportunity_research_v3(integer) from public,anon,authenticated;
grant execute on function sm_intel.refresh_opportunity_research_v3(integer) to service_role;

create or replace function sm_intel.opportunity_brief_v3(p_problem_id uuid)
returns jsonb language sql stable security invoker set search_path='' as $$
select jsonb_build_object(
 'problem_id',p.id,'problem',p.problem_title,'category',p.category,
 'research',coalesce((select to_jsonb(r) from sm_intel.opportunity_research_v3 r
   where r.problem_cluster_id=p.id and r.region_code='GR'),'{}'::jsonb),
 'product_candidates',coalesce((select jsonb_agg(jsonb_build_object(
  'title',d.title,'source_state',d.source_state,'rrf_score',m.rrf_score,
  'relevance_review',m.relevance_review,'model_status',
    case when d.embedding_status='ready' then 'real_embedding' else 'fts_only' end)
  order by m.retrieval_rank)
  from sm_intel.opportunity_product_candidates_v3 m
  join sm_intel.search_documents d on d.id=m.document_id
  where m.problem_cluster_id=p.id),'[]'::jsonb),
 'commercially_approved_products',0,
 'assessment_status','research_only_not_purchase_advice'
)
from public.market_problem_clusters p where p.market_code='GR' and p.id=p_problem_id
$$;
revoke all on function sm_intel.opportunity_brief_v3(uuid) from public,anon,authenticated;
grant execute on function sm_intel.opportunity_brief_v3(uuid) to service_role;