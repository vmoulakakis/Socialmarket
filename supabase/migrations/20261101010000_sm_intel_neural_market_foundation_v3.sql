-- SocialMarket 3.0 P0/P1: source-grounded market intelligence, versioned product features.
-- No feed fetch, paid LLM execution, merchant approval, promotion or cross-project writes.
create table if not exists sm_intel.market_signals_v3(
 id uuid primary key default gen_random_uuid(),
 problem_cluster_id uuid not null references public.market_problem_clusters(id) on delete restrict,
 market_code text not null default 'GR' check (market_code='GR'),
 region_code text not null default 'GR',
 signal_type text not null check(signal_type in
  ('demand','supply','competition','buyer_intent','seasonality','price','buyer_objection')),
 metric_name text not null,
 metric_value numeric,
 metric_unit text,
 qualitative_finding text,
 source_family text not null,
 source_record_id text,
 source_url text,
 independent_source_key text,
 observed_at timestamptz not null,
 expires_at timestamptz,
 sample_size integer check(sample_size is null or sample_size>=0),
 raw_payload jsonb not null default '{}'::jsonb,
 evidence_status text not null default 'candidate'
  check(evidence_status in ('candidate','verified','rejected','expired')),
 verified_by text,
 verified_at timestamptz,
 source_fingerprint text,
 created_at timestamptz not null default now(),
 unique(source_family,source_record_id,signal_type,problem_cluster_id),
 check (expires_at is null or expires_at>observed_at),
 check (metric_value is null or metric_unit is not null),
 check (evidence_status<>'verified' or (
   verified_by is not null and verified_at is not null
   and independent_source_key is not null
   and (source_url is not null or source_family='first_party_analytics')
 )),
 check (signal_type<>'buyer_intent' or
   not (raw_payload ? 'email' or raw_payload ? 'phone' or raw_payload ? 'ip_address'))
);
create index if not exists sm_v3_signals_problem_type
 on sm_intel.market_signals_v3(problem_cluster_id,region_code,signal_type,observed_at desc);
create index if not exists sm_v3_signals_review
 on sm_intel.market_signals_v3(evidence_status,expires_at);
create index if not exists sm_v3_signals_source
 on sm_intel.market_signals_v3(source_family,independent_source_key);

create table if not exists sm_intel.product_feature_snapshots_v3(
 id uuid primary key default gen_random_uuid(),
 raw_product_id uuid not null references sm_intel.raw_products(id) on delete restrict,
 feature_version text not null default 'p3.0',
 source_content_hash text not null,
 features jsonb not null,
 observed_at timestamptz not null,
 built_at timestamptz not null default now(),
 unique(raw_product_id,feature_version,source_content_hash)
);
create index if not exists sm_v3_feature_raw on sm_intel.product_feature_snapshots_v3(raw_product_id,built_at desc);

create table if not exists sm_intel.product_problem_hypotheses_v3(
 id uuid primary key default gen_random_uuid(),
 problem_cluster_id uuid not null references public.market_problem_clusters(id) on delete restrict,
 raw_product_id uuid not null references sm_intel.raw_products(id) on delete restrict,
 model_version text not null,
 retrieval_method text not null check(retrieval_method in
  ('lexical','dense_e5','hybrid_rrf','neural_reranker','human_review')),
 relevance_score numeric check(relevance_score between 0 and 1),
 customer_fit_score numeric check(customer_fit_score between 0 and 1),
 evidence_refs jsonb not null default '[]'::jsonb,
 counterevidence jsonb not null default '[]'::jsonb,
 status text not null default 'candidate'
   check(status in ('candidate','needs_evidence','verified','rejected')),
 reviewer text,
 reviewed_at timestamptz,
 reasoning jsonb not null default '{}'::jsonb,
 created_at timestamptz not null default now(),
 unique(problem_cluster_id,raw_product_id,model_version),
 check (jsonb_typeof(evidence_refs)='array'),
 check (status<>'verified' or (
   reviewer is not null and reviewed_at is not null and
   jsonb_array_length(evidence_refs)>0
 ))
);
create index if not exists sm_v3_product_hypotheses_problem
 on sm_intel.product_problem_hypotheses_v3(problem_cluster_id,status,relevance_score desc);

create table if not exists sm_intel.model_registry_v3(
 model_key text primary key,
 purpose text not null,
 provider text not null,
 model_id text not null,
 embedding_dim integer,
 runtime_class text not null check(runtime_class in ('cpu','gpu','api','sql')),
 deployment_state text not null default 'candidate'
   check(deployment_state in ('candidate','ready','disabled','retired')),
 risk_level text not null check(risk_level in ('low','medium','high')),
 requires_evaluation boolean not null default true,
 evaluation_thresholds jsonb not null default '{}'::jsonb,
 approved_evaluation_id uuid,
 last_reviewed_at timestamptz,
 created_at timestamptz not null default now(),
 check (deployment_state<>'ready' or
   (last_reviewed_at is not null and
    (requires_evaluation is false or approved_evaluation_id is not null)))
);
create table if not exists sm_intel.model_evaluations_v3(
 id uuid primary key default gen_random_uuid(),
 model_key text not null references sm_intel.model_registry_v3(model_key),
 dataset_version text not null,
 sample_count integer not null check(sample_count>=1),
 metrics jsonb not null default '{}'::jsonb,
 comparison_model_key text,
 p50_latency_ms numeric,
 p95_latency_ms numeric,
 cost_per_1000_eur numeric,
 evaluation_status text not null default 'pending'
   check (evaluation_status in ('pending','passed','failed','invalid')),
 evaluated_at timestamptz not null default now(),
 reviewer text,
 evidence_digest text
);
alter table sm_intel.model_registry_v3
 add constraint sm_v3_registry_evaluation_fk
 foreign key(approved_evaluation_id) references sm_intel.model_evaluations_v3(id) deferrable initially deferred;

create table if not exists sm_intel.market_assessments_v3(
 id uuid primary key default gen_random_uuid(),
 problem_cluster_id uuid not null references public.market_problem_clusters(id) on delete restrict,
 region_code text not null default 'GR',
 period_start date not null,
 period_end date not null,
 assessment_version text not null,
 demand_estimate numeric,
 local_supply_estimate numeric,
 buyer_intent_estimate numeric,
 uncertainty jsonb not null default '{}'::jsonb,
 methodology jsonb not null default '{}'::jsonb,
 evidence_ids uuid[] not null default '{}'::uuid[],
 counterevidence_ids uuid[] not null default '{}'::uuid[],
 judgment text not null default 'research_needed'
   check(judgment in ('research_needed','candidate','verified_opportunity','rejected')),
 reviewer text,
 reviewed_at timestamptz,
 created_at timestamptz not null default now(),
 unique(problem_cluster_id,region_code,period_start,period_end,assessment_version),
 check (period_end>=period_start),
 check (judgment<>'verified_opportunity' or (
   reviewer is not null and reviewed_at is not null
   and cardinality(evidence_ids)>=2
   and demand_estimate is not null and local_supply_estimate is not null
 ))
);
create index if not exists sm_v3_assessment_problem on sm_intel.market_assessments_v3(problem_cluster_id,region_code,period_end desc);

-- Prevent a generated score from becoming a market fact without independent recent demand/supply proof.
create or replace function sm_intel.guard_verified_assessment_v3()
returns trigger language plpgsql security invoker set search_path='' as $$
declare n_demand integer; n_supply integer; groups_count integer; unknown integer;
begin
 if new.judgment='verified_opportunity' then
  select count(*) filter(where signal_type='demand'),
         count(*) filter(where signal_type='supply'),
         count(distinct independent_source_key),
         count(*) filter(where evidence_status<>'verified'
            or (expires_at is not null and expires_at<=now())
            or observed_at<now()-interval '180 days')
   into n_demand,n_supply,groups_count,unknown
  from sm_intel.market_signals_v3
  where id=any(new.evidence_ids) and problem_cluster_id=new.problem_cluster_id
    and region_code=new.region_code;
  if n_demand<1 or n_supply<1 or groups_count<2 or unknown>0 or
     (n_demand+n_supply)<cardinality(new.evidence_ids)
  then raise exception 'verified_market_assessment_requires_independent_fresh_demand_and_supply';
  end if;
 end if;
 return new;
end $$;
drop trigger if exists sm_v3_assessment_guard on sm_intel.market_assessments_v3;
create trigger sm_v3_assessment_guard before insert or update on sm_intel.market_assessments_v3
 for each row execute function sm_intel.guard_verified_assessment_v3();

create or replace view sm_intel.market_evidence_coverage_v3 with (security_invoker=true) as
select p.id problem_cluster_id,p.problem_title,p.category,p.subcategory,'GR'::text region_code,
 count(s.id) total_observations,
 count(s.id) filter(where s.signal_type='demand' and s.evidence_status='verified'
    and (s.expires_at is null or s.expires_at>now())) verified_demand,
 count(s.id) filter(where s.signal_type='supply' and s.evidence_status='verified'
    and (s.expires_at is null or s.expires_at>now())) verified_supply,
 count(distinct s.independent_source_key) filter(where s.evidence_status='verified'
    and (s.expires_at is null or s.expires_at>now())) independent_sources,
 count(s.id) filter(where s.evidence_status='candidate') candidate_observations,
 max(s.observed_at) latest_observation,
 case when count(s.id) filter(where s.signal_type='demand' and s.evidence_status='verified')=0
     then 'verify_demand'
      when count(s.id) filter(where s.signal_type='supply' and s.evidence_status='verified')=0
     then 'verify_supply'
      when count(distinct s.independent_source_key) filter(where s.evidence_status='verified')<2
     then 'verify_independent_source'
      else 'ready_for_assessment' end next_action
from public.market_problem_clusters p left join sm_intel.market_signals_v3 s
 on s.problem_cluster_id=p.id and s.region_code='GR'
where p.market_code='GR'
group by p.id,p.problem_title,p.category,p.subcategory;

create or replace view sm_intel.market_brain_health_v3 with (security_invoker=true) as
select
 (select count(*) from sm_intel.raw_products) imported_products,
 (select count(distinct program_id) from sm_intel.raw_products) imported_program_ids,
 (select count(*) from sm_intel.product_feature_snapshots_v3) feature_snapshots,
 (select count(*) from sm_intel.product_problem_hypotheses_v3) product_problem_hypotheses,
 (select count(*) from sm_intel.product_problem_hypotheses_v3 where status='verified') verified_product_problem_pairs,
 (select count(*) from sm_intel.market_signals_v3) observed_market_signals,
 (select count(*) from sm_intel.market_signals_v3 where evidence_status='verified') verified_market_signals,
 (select count(*) from sm_intel.market_assessments_v3 where judgment='verified_opportunity') verified_market_opportunities,
 (select count(*) from sm_intel.market_evidence_coverage_v3 where next_action<>'ready_for_assessment') research_gaps,
 (select count(*) from sm_intel.search_documents where embedding_status='ready') active_embeddings,
 (select count(*) from sm_intel.graph_edges where review_status='verified') verified_graph_relations,
 (select count(*) from sm_intel.model_evaluations_v3 where evaluation_status='passed') passed_model_evaluations,
 now() audited_at;

-- Deterministic product features: data quality/provenance, not customer-demand claims.
create or replace function sm_intel.refresh_product_features_v3(p_limit integer default 10000)
returns jsonb language plpgsql security invoker set search_path='' as $$
declare inserted_count integer;
begin
 with sources as (
   select r.id,r.content_sha256,r.last_seen_at,
     jsonb_build_object(
       'source_key',r.source_key,'program_id',r.program_id,
       'has_product_id',r.source_product_id is not null,
       'title_present',r.product_title is not null and trim(r.product_title)<>'',
       'description_present',coalesce(length(trim(r.raw_json->>'description')),0)>0,
       'category_present',r.category_raw is not null,
       'brand_present',coalesce(length(trim(r.raw_json->>'brand_name')),0)>0,
       'image_present',coalesce(length(trim(r.raw_json->>'image_url')),0)>0,
       'currency',r.currency,'price_eur',case when r.currency='EUR' then r.price else null end,
       'stock_observed',r.stock_available,'offer_expires_at',r.valid_to,
       'last_observed_at',r.last_seen_at,
       'data_fresh_7d',r.last_seen_at>now()-interval '7 days',
       'merchant_program_identity_known',r.program_id is not null and r.program_id<>'unknown',
       'verified_terms_exist',exists(select 1 from sm_intel.commission_terms c
         where c.program_id=r.program_id and c.review_status='verified'
          and c.effective_from<=now()
          and (c.effective_until>now() or
          (c.effective_until is null and c.evidence->>'explicit_open_ended_verified'='true')))
     ) features
   from sm_intel.raw_products r
   order by r.id limit greatest(1,least(coalesce(p_limit,10000),200000))
 ), changed as (
  insert into sm_intel.product_feature_snapshots_v3(raw_product_id,feature_version,source_content_hash,features,observed_at)
  select id,'p3.0',content_sha256,features,last_seen_at from sources
  on conflict(raw_product_id,feature_version,source_content_hash) do nothing
  returning id
 )
 select count(*) into inserted_count from changed;
 return jsonb_build_object('inserted_feature_snapshots',inserted_count,'model_version','p3.0');
end $$;

-- Registration is informational: no pretend-ready embeddings or untested neural models.
insert into sm_intel.model_registry_v3(model_key,purpose,provider,model_id,embedding_dim,runtime_class,risk_level,evaluation_thresholds)
values
 ('e5small_384','greek/english dense embeddings','huggingface','intfloat/multilingual-e5-small',384,'cpu','low','{"recall_at_20":0.85,"ndcg_at_10":0.70}'::jsonb),
 ('bgem3_candidate','multilingual candidate retrieval benchmark','huggingface','BAAI/bge-m3',1024,'cpu','medium','{"must_beat_baseline":true}'::jsonb),
 ('qwen_reranker_candidate','neural cross-encoder rerank','huggingface','Qwen/Qwen3-Reranker-0.6B',null,'cpu','medium','{"must_beat_baseline":true}'::jsonb),
 ('market_forecaster_candidate','uncertainty-calibrated demand regression','local','gradient_boosting_baseline',null,'cpu','high','{"holdout_required":true}'::jsonb),
 ('graph_nn_candidate','heterogeneous graph recommendation','local','heterogeneous_gnn',null,'gpu','high','{"sufficient_verified_edges_required":true}'::jsonb)
on conflict(model_key) do nothing;

do $$
declare t text;
begin
 foreach t in array array['market_signals_v3','product_feature_snapshots_v3','product_problem_hypotheses_v3','model_registry_v3','model_evaluations_v3','market_assessments_v3']
 loop
  execute format('alter table sm_intel.%I enable row level security',t);
  execute format('revoke all on sm_intel.%I from public,anon,authenticated',t);
 end loop;
end $$;
revoke all on function sm_intel.guard_verified_assessment_v3() from public,anon,authenticated;
revoke all on function sm_intel.refresh_product_features_v3(integer) from public,anon,authenticated;
revoke all on sm_intel.market_evidence_coverage_v3,sm_intel.market_brain_health_v3 from public,anon,authenticated;
grant select,insert,update on sm_intel.market_signals_v3,sm_intel.product_feature_snapshots_v3,sm_intel.product_problem_hypotheses_v3,
 sm_intel.model_registry_v3,sm_intel.model_evaluations_v3,sm_intel.market_assessments_v3 to service_role;
grant select on sm_intel.market_evidence_coverage_v3,sm_intel.market_brain_health_v3 to service_role;
grant execute on function sm_intel.refresh_product_features_v3(integer) to service_role;
