-- VMDB 021 — AliExpress Gap Solver V2
--
-- Additive, backend-only and fail-closed. This migration does not alter the
-- legacy Linkwise pipeline. V2 accepts only source_key = 'aliexpress'.
-- Numeric opportunity decisions are deterministic; model output may propose
-- queries or summarize evidence but cannot override these gates.

create extension if not exists pgcrypto;

create table if not exists public.ai_gap_solver_policies (
  policy_key text primary key,
  enabled boolean not null default true,
  market_code text not null default 'GR',
  source_key text not null default 'aliexpress' check (source_key = 'aliexpress'),
  discovery_min_commission_eur numeric not null default 10 check (discovery_min_commission_eur >= 0),
  organic_min_commission_eur numeric not null default 15 check (organic_min_commission_eur >= discovery_min_commission_eur),
  paid_static_min_commission_eur numeric not null default 35 check (paid_static_min_commission_eur >= organic_min_commission_eur),
  min_demand_score numeric not null default 65 check (min_demand_score between 0 and 100),
  min_paid_demand_score numeric not null default 72 check (min_paid_demand_score between 0 and 100),
  min_gap_score numeric not null default 70 check (min_gap_score between 0 and 100),
  min_strong_gap_score numeric not null default 85 check (min_strong_gap_score between 0 and 100),
  min_problem_fit_score numeric not null default 72 check (min_problem_fit_score between 0 and 100),
  min_paid_problem_fit_score numeric not null default 80 check (min_paid_problem_fit_score between 0 and 100),
  min_organic_trust_score numeric not null default 50 check (min_organic_trust_score between 0 and 100),
  min_trust_score numeric not null default 68 check (min_trust_score between 0 and 100),
  min_evidence_score numeric not null default 65 check (min_evidence_score between 0 and 100),
  min_paid_evidence_score numeric not null default 75 check (min_paid_evidence_score between 0 and 100),
  min_problem_confidence numeric not null default 0.60 check (min_problem_confidence between 0 and 1),
  min_evidence_items integer not null default 8 check (min_evidence_items >= 1),
  min_source_families integer not null default 2 check (min_source_families >= 1),
  min_competitors_audited integer not null default 3 check (min_competitors_audited >= 1),
  max_contradiction_ratio numeric not null default 0.35 check (max_contradiction_ratio between 0 and 1),
  max_evidence_age_days integer not null default 120 check (max_evidence_age_days >= 1),
  max_product_age_hours integer not null default 168 check (max_product_age_hours >= 1),
  paid_unit_economics_assumptions jsonb not null default '{"cpc_eur":0.35,"click_to_order_rate":0.015,"approval_rate":0.80,"creative_cost_per_approved_order_eur":5,"target_margin_rate":0.25,"provenance":"policy_assumption"}'::jsonb,
  score_weights jsonb not null default '{"problem_fit":0.25,"gap":0.20,"demand":0.18,"economics":0.12,"trust":0.10,"evidence":0.10,"competition_inverse":0.05}'::jsonb,
  notes text null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

insert into public.ai_gap_solver_policies (
  policy_key,
  enabled,
  market_code,
  source_key,
  notes
) values (
  'aliexpress_gap_solver_v2',
  true,
  'GR',
  'aliexpress',
  'Problem-first AliExpress-only policy. Linkwise is intentionally excluded. Discovery >= EUR10; organic >= EUR15; paid test >= max(EUR35, modeled break-even with safety margin).'
)
on conflict (policy_key) do update set
  enabled = excluded.enabled,
  market_code = excluded.market_code,
  source_key = excluded.source_key,
  notes = excluded.notes,
  updated_at = now();

create table if not exists public.ai_gap_solver_runs (
  id uuid primary key default gen_random_uuid(),
  policy_key text not null references public.ai_gap_solver_policies(policy_key),
  market_code text not null default 'GR',
  source_key text not null default 'aliexpress' check (source_key = 'aliexpress'),
  run_mode text not null default 'dry_run' check (run_mode in ('dry_run','live')),
  status text not null default 'running' check (status in ('running','completed','failed','withheld')),
  config_snapshot jsonb not null default '{}'::jsonb,
  counters jsonb not null default '{}'::jsonb,
  error_summary text null,
  requested_by text null,
  started_at timestamptz not null default now(),
  completed_at timestamptz null
);

create table if not exists public.ai_gap_solver_evidence (
  id uuid primary key default gen_random_uuid(),
  market_code text not null default 'GR',
  problem_cluster_id uuid not null references public.market_problem_clusters(id) on delete cascade,
  source_family text not null,
  source_name text not null,
  source_domain text not null,
  source_url text not null,
  source_independence_key text not null,
  claim_type text not null check (claim_type in (
    'pain','purchase_intent','search_interest','first_party_behavior',
    'exact_solution','substitute','competitor','price_friction',
    'availability_gap','market_gap','contradiction'
  )),
  polarity text not null default 'supports' check (polarity in ('supports','contradicts','neutral')),
  evidence_tier text not null check (evidence_tier in ('structured_metric','full_text','snippet','metadata')),
  provenance_class text not null check (provenance_class in ('observed','user_provided','calculated','inferred','unavailable')),
  raw_excerpt text null,
  extracted_claim text null,
  relevance_score numeric null check (relevance_score between 0 and 100),
  strength_score numeric null check (strength_score between 0 and 100),
  confidence numeric null check (confidence between 0 and 1),
  facts jsonb not null default '{}'::jsonb,
  content_hash text not null,
  observed_at timestamptz not null,
  stale_after timestamptz null,
  collected_at timestamptz not null default now(),
  unique (problem_cluster_id, content_hash, claim_type)
);

create table if not exists public.ai_gap_solver_problem_assessments (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references public.ai_gap_solver_runs(id) on delete cascade,
  problem_cluster_id uuid not null references public.market_problem_clusters(id) on delete cascade,
  market_code text not null default 'GR',
  demand_score numeric not null check (demand_score between 0 and 100),
  pain_score numeric not null check (pain_score between 0 and 100),
  buyer_intent_score numeric not null check (buyer_intent_score between 0 and 100),
  competition_score numeric not null check (competition_score between 0 and 100),
  gap_score numeric not null check (gap_score between 0 and 100),
  evidence_count integer not null default 0,
  source_family_count integer not null default 0,
  independent_source_count integer not null default 0,
  competitors_audited integer not null default 0,
  contradiction_ratio numeric not null default 0 check (contradiction_ratio between 0 and 1),
  confidence numeric not null default 0 check (confidence between 0 and 1),
  evidence_score numeric not null default 0 check (evidence_score between 0 and 100),
  solution_requirements jsonb not null default '[]'::jsonb,
  evidence_ids jsonb not null default '[]'::jsonb,
  gate_results jsonb not null default '{}'::jsonb,
  score_provenance jsonb not null default '{}'::jsonb,
  eligible_to_source boolean not null default false,
  strong_gap boolean not null default false,
  thesis text null,
  counter_thesis text null,
  assessment_version text not null default 'gap-solver-v2',
  assessed_at timestamptz not null default now(),
  unique (run_id, problem_cluster_id)
);

create table if not exists public.ai_gap_solver_queries (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references public.ai_gap_solver_runs(id) on delete cascade,
  problem_cluster_id uuid not null references public.market_problem_clusters(id) on delete cascade,
  problem_assessment_id uuid not null references public.ai_gap_solver_problem_assessments(id) on delete cascade,
  query_text text not null,
  mechanism text not null,
  requirement_ids jsonb not null default '[]'::jsonb,
  retrieval_modes jsonb not null default '["relevance","volume"]'::jsonb,
  priority numeric not null default 0,
  status text not null default 'active' check (status in ('active','completed','withheld','failed')),
  hypothesis jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  last_run_at timestamptz null,
  unique (run_id, problem_cluster_id, query_text)
);

create table if not exists public.ai_gap_solver_discoveries (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references public.ai_gap_solver_runs(id) on delete cascade,
  problem_cluster_id uuid not null references public.market_problem_clusters(id) on delete cascade,
  query_id uuid not null references public.ai_gap_solver_queries(id) on delete cascade,
  product_candidate_id uuid not null references public.ai_product_candidates(id) on delete cascade,
  offer_id uuid not null references public.ai_product_offers(id) on delete cascade,
  retrieval_mode text not null check (retrieval_mode in ('relevance','volume','hot_product')),
  result_rank integer null check (result_rank is null or result_rank >= 1),
  query_text text not null,
  metadata jsonb not null default '{}'::jsonb,
  discovered_at timestamptz not null default now(),
  unique (run_id, problem_cluster_id, query_id, product_candidate_id, offer_id, retrieval_mode)
);

create table if not exists public.ai_gap_solver_product_assessments (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references public.ai_gap_solver_runs(id) on delete cascade,
  problem_cluster_id uuid not null references public.market_problem_clusters(id) on delete cascade,
  problem_assessment_id uuid not null references public.ai_gap_solver_problem_assessments(id) on delete cascade,
  product_candidate_id uuid not null references public.ai_product_candidates(id) on delete cascade,
  offer_id uuid not null references public.ai_product_offers(id) on delete cascade,
  source_key text not null check (source_key = 'aliexpress'),
  expected_commission_eur numeric null,
  paid_required_commission_eur numeric null,
  identity_score numeric not null check (identity_score between 0 and 100),
  problem_fit_score numeric not null check (problem_fit_score between 0 and 100),
  trust_score numeric not null check (trust_score between 0 and 100),
  economics_score numeric not null check (economics_score between 0 and 100),
  evidence_score numeric not null check (evidence_score between 0 and 100),
  opportunity_score numeric not null check (opportunity_score between 0 and 100),
  risk_penalty numeric not null default 0 check (risk_penalty between 0 and 100),
  lane text not null check (lane in ('REJECT','WATCH','ORGANIC_TEST','PAID_TEST','B2B_SEARCH')),
  verdict text not null check (verdict in ('REJECTED','WITHHELD','ELIGIBLE')),
  confidence numeric not null default 0 check (confidence between 0 and 1),
  gate_results jsonb not null default '{}'::jsonb,
  requirement_matches jsonb not null default '[]'::jsonb,
  unit_economics jsonb not null default '{}'::jsonb,
  evidence_refs jsonb not null default '[]'::jsonb,
  reason_codes jsonb not null default '[]'::jsonb,
  score_provenance jsonb not null default '{}'::jsonb,
  assessment_version text not null default 'gap-solver-v2',
  assessed_at timestamptz not null default now(),
  unique (run_id, problem_cluster_id, product_candidate_id, offer_id)
);

create index if not exists ai_gap_solver_runs_started_idx
  on public.ai_gap_solver_runs(started_at desc);
create index if not exists ai_gap_solver_evidence_problem_idx
  on public.ai_gap_solver_evidence(problem_cluster_id, observed_at desc);
create index if not exists ai_gap_solver_evidence_claim_idx
  on public.ai_gap_solver_evidence(claim_type, source_family, observed_at desc);
create index if not exists ai_gap_solver_problem_ready_idx
  on public.ai_gap_solver_problem_assessments(eligible_to_source, gap_score desc, demand_score desc);
create index if not exists ai_gap_solver_queries_active_idx
  on public.ai_gap_solver_queries(status, priority desc, created_at);
create index if not exists ai_gap_solver_discoveries_product_idx
  on public.ai_gap_solver_discoveries(product_candidate_id, discovered_at desc);
create index if not exists ai_gap_solver_products_lane_idx
  on public.ai_gap_solver_product_assessments(lane, opportunity_score desc, assessed_at desc);

create or replace view public.ai_gap_solver_candidate_inputs_v
with (security_invoker = true) as
select distinct on (d.run_id, d.problem_cluster_id, d.product_candidate_id, d.offer_id)
  d.run_id,
  d.problem_cluster_id,
  d.query_id,
  d.query_text,
  d.retrieval_mode,
  d.result_rank,
  d.discovered_at,
  pc.problem_title,
  pc.problem_description,
  pc.target_customer,
  a.id as problem_assessment_id,
  a.demand_score,
  a.pain_score,
  a.buyer_intent_score,
  a.competition_score,
  a.gap_score,
  a.evidence_score as problem_evidence_score,
  a.confidence as problem_confidence,
  a.contradiction_ratio,
  a.evidence_ids as problem_evidence_ids,
  a.eligible_to_source,
  a.strong_gap,
  a.solution_requirements,
  p.id as product_candidate_id,
  p.source_key,
  p.source_product_id,
  p.title,
  p.product_url,
  p.image_url,
  p.category,
  p.raw_payload as product_raw_payload,
  p.observed_at as product_observed_at,
  o.id as offer_id,
  o.price_eur,
  o.original_price_eur,
  o.shipping_eur,
  o.commission_rate,
  o.expected_commission_eur,
  o.promotion_url,
  o.warehouse_country,
  o.seller_source_id,
  o.seller_name,
  o.seller_evidence,
  o.logistics_evidence,
  o.review_evidence,
  o.raw_payload as offer_raw_payload,
  o.observed_at as offer_observed_at
from public.ai_gap_solver_discoveries d
join public.ai_gap_solver_problem_assessments a
  on a.run_id = d.run_id and a.problem_cluster_id = d.problem_cluster_id
join public.market_problem_clusters pc on pc.id = d.problem_cluster_id
join public.ai_product_candidates p on p.id = d.product_candidate_id
join public.ai_product_offers o on o.id = d.offer_id
where p.source_key = 'aliexpress'
order by d.run_id, d.problem_cluster_id, d.product_candidate_id, d.offer_id,
  d.discovered_at desc, d.result_rank asc nulls last;

create or replace view public.ai_gap_solver_ready_candidates_v
with (security_invoker = true) as
with latest_problem_run as (
  select distinct on (a.problem_cluster_id)
    a.problem_cluster_id,
    a.run_id
  from public.ai_gap_solver_problem_assessments a
  join public.ai_gap_solver_runs r on r.id = a.run_id
  where r.status = 'completed'
  order by a.problem_cluster_id, a.assessed_at desc
), latest as (
  select distinct on (pa.problem_cluster_id, pa.product_candidate_id, pa.offer_id)
    pa.*
  from public.ai_gap_solver_product_assessments pa
  join latest_problem_run lpr
    on lpr.problem_cluster_id = pa.problem_cluster_id and lpr.run_id = pa.run_id
  order by pa.problem_cluster_id, pa.product_candidate_id, pa.offer_id, pa.assessed_at desc
)
select
  pa.*,
  p.source_product_id,
  p.title,
  p.product_url,
  p.image_url,
  p.category,
  o.price_eur,
  o.promotion_url,
  o.seller_source_id,
  o.warehouse_country
from latest pa
join public.ai_product_candidates p on p.id = pa.product_candidate_id
join public.ai_product_offers o on o.id = pa.offer_id
where pa.verdict = 'ELIGIBLE'
  and pa.lane in ('ORGANIC_TEST','PAID_TEST','B2B_SEARCH')
  and pa.source_key = 'aliexpress';

create or replace function public.vmdb_aliexpress_gap_solver_health()
returns jsonb
language sql
stable
security invoker
set search_path = public, pg_temp
as $$
  select jsonb_build_object(
    'policy', (
      select to_jsonb(p) - 'paid_unit_economics_assumptions' - 'score_weights'
      from public.ai_gap_solver_policies p
      where p.policy_key = 'aliexpress_gap_solver_v2'
    ),
    'latest_run', (
      select to_jsonb(r)
      from public.ai_gap_solver_runs r
      order by r.started_at desc
      limit 1
    ),
    'evidence_items', (select count(*) from public.ai_gap_solver_evidence),
    'validated_problems', (
      select count(*) from public.ai_gap_solver_problem_assessments where eligible_to_source
    ),
    'eligible_products', (select count(*) from public.ai_gap_solver_ready_candidates_v),
    'paid_test_products', (
      select count(*) from public.ai_gap_solver_ready_candidates_v where lane = 'PAID_TEST'
    ),
    'source_scope', 'aliexpress_only',
    'linkwise_included', false,
    'checked_at', now()
  );
$$;

comment on table public.ai_gap_solver_evidence is
'Auditable claim-level evidence. Snippets are stored but cannot independently prove pain or a market gap.';
comment on table public.ai_gap_solver_problem_assessments is
'Deterministic demand/gap scorecard. AI may summarize evidence but cannot set numeric gates.';
comment on table public.ai_gap_solver_product_assessments is
'AliExpress-only deterministic lane decision: WATCH, ORGANIC_TEST, PAID_TEST, B2B_SEARCH or REJECT.';
comment on view public.ai_gap_solver_ready_candidates_v is
'Only evidence-gated AliExpress products; Linkwise and all other sources are excluded by construction.';

alter table public.ai_gap_solver_policies enable row level security;
alter table public.ai_gap_solver_runs enable row level security;
alter table public.ai_gap_solver_evidence enable row level security;
alter table public.ai_gap_solver_problem_assessments enable row level security;
alter table public.ai_gap_solver_queries enable row level security;
alter table public.ai_gap_solver_discoveries enable row level security;
alter table public.ai_gap_solver_product_assessments enable row level security;

revoke all on public.ai_gap_solver_policies from anon, authenticated;
revoke all on public.ai_gap_solver_runs from anon, authenticated;
revoke all on public.ai_gap_solver_evidence from anon, authenticated;
revoke all on public.ai_gap_solver_problem_assessments from anon, authenticated;
revoke all on public.ai_gap_solver_queries from anon, authenticated;
revoke all on public.ai_gap_solver_discoveries from anon, authenticated;
revoke all on public.ai_gap_solver_product_assessments from anon, authenticated;
revoke all on public.ai_gap_solver_candidate_inputs_v from anon, authenticated;
revoke all on public.ai_gap_solver_ready_candidates_v from anon, authenticated;
revoke all on function public.vmdb_aliexpress_gap_solver_health() from public, anon, authenticated;

grant select, insert, update, delete on public.ai_gap_solver_policies to service_role;
grant select, insert, update, delete on public.ai_gap_solver_runs to service_role;
grant select, insert, update, delete on public.ai_gap_solver_evidence to service_role;
grant select, insert, update, delete on public.ai_gap_solver_problem_assessments to service_role;
grant select, insert, update, delete on public.ai_gap_solver_queries to service_role;
grant select, insert, update, delete on public.ai_gap_solver_discoveries to service_role;
grant select, insert, update, delete on public.ai_gap_solver_product_assessments to service_role;
grant select on public.ai_gap_solver_candidate_inputs_v to service_role;
grant select on public.ai_gap_solver_ready_candidates_v to service_role;
grant execute on function public.vmdb_aliexpress_gap_solver_health() to service_role;
