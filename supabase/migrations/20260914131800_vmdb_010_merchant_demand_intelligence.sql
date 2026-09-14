-- VMDB 010: canonical Merchant 360 + Greek demand + product-admission control plane.
-- Live on canonical VMDB gqpbskssrvpfjtujwezc.

create table if not exists public.merchant_profiles (
  id uuid primary key default gen_random_uuid(),
  legacy_merchant_id text unique,
  affiliate_program_id uuid references public.affiliate_programs(id) on delete set null,
  merchant_name text not null,
  canonical_domain text,
  country_code text,
  currency text not null default 'EUR',
  primary_category text,
  primary_subcategory text,
  active boolean not null default true,
  program_approved boolean not null default false,
  tracking_verified boolean not null default false,
  median_conversion_rate numeric,
  median_epc_eur numeric,
  median_approval_pct numeric,
  median_approval_days numeric,
  flat_commission_min_eur numeric,
  flat_commission_max_eur numeric,
  percent_commission_min numeric,
  percent_commission_max numeric,
  expected_aov_eur numeric,
  expected_commission_eur numeric,
  active_since date,
  source_files jsonb not null default '[]'::jsonb,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint merchant_profiles_expected_commission_nonnegative check (expected_commission_eur is null or expected_commission_eur >= 0)
);
create unique index if not exists merchant_profiles_name_lower_uq on public.merchant_profiles (lower(merchant_name));
create index if not exists merchant_profiles_category_idx on public.merchant_profiles (primary_category, primary_subcategory);
create index if not exists merchant_profiles_import_gate_idx on public.merchant_profiles (active, program_approved, tracking_verified, expected_commission_eur desc);

create table if not exists public.merchant_category_memberships (
  id uuid primary key default gen_random_uuid(),
  merchant_id uuid not null references public.merchant_profiles(id) on delete cascade,
  category_key text,
  category text not null,
  subcategory text,
  is_primary boolean not null default false,
  source_file text,
  source_row integer,
  conversion_rate numeric,
  epc_eur numeric,
  approval_pct numeric,
  approval_days numeric,
  flat_commission_min_eur numeric,
  flat_commission_max_eur numeric,
  percent_commission_min numeric,
  percent_commission_max numeric,
  active_since date,
  created_at timestamptz not null default now(),
  unique (merchant_id, category, subcategory, source_file)
);
create index if not exists merchant_category_memberships_cat_idx on public.merchant_category_memberships (category, subcategory, merchant_id);

create table if not exists public.merchant_research_runs (
  id uuid primary key default gen_random_uuid(),
  merchant_id uuid references public.merchant_profiles(id) on delete cascade,
  run_scope text not null default 'merchant_360',
  methodology_version text not null default 'merchant_360_v1',
  market_code text not null default 'GR',
  status text not null default 'queued' check (status in ('queued','running','succeeded','failed','cancelled')),
  model_provider text,
  model_name text,
  prompt_version text,
  evidence_count integer not null default 0,
  confidence numeric not null default 0 check (confidence between 0 and 1),
  started_at timestamptz,
  completed_at timestamptz,
  summary jsonb not null default '{}'::jsonb,
  error text,
  created_at timestamptz not null default now()
);
create index if not exists merchant_research_runs_merchant_idx on public.merchant_research_runs (merchant_id, created_at desc);
create index if not exists merchant_research_runs_status_idx on public.merchant_research_runs (status, created_at);

create table if not exists public.merchant_evidence (
  id uuid primary key default gen_random_uuid(),
  merchant_id uuid not null references public.merchant_profiles(id) on delete cascade,
  research_run_id uuid references public.merchant_research_runs(id) on delete set null,
  evidence_type text not null,
  source_name text not null,
  source_url text,
  source_tier smallint not null default 3 check (source_tier between 1 and 5),
  observed_at timestamptz not null default now(),
  confidence numeric not null default 0.5 check (confidence between 0 and 1),
  raw_value numeric,
  normalized_score numeric check (normalized_score is null or normalized_score between 0 and 100),
  evidence jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists merchant_evidence_lookup_idx on public.merchant_evidence (merchant_id, evidence_type, observed_at desc);

create table if not exists public.merchant_demand_assessments (
  id uuid primary key default gen_random_uuid(),
  merchant_id uuid not null references public.merchant_profiles(id) on delete cascade,
  research_run_id uuid references public.merchant_research_runs(id) on delete set null,
  market_code text not null default 'GR',
  category text,
  subcategory text,
  problem_cluster text,
  demand_score numeric not null default 0 check (demand_score between 0 and 100),
  commercial_intent_score numeric not null default 0 check (commercial_intent_score between 0 and 100),
  competition_score numeric not null default 100 check (competition_score between 0 and 100),
  supply_gap_score numeric not null default 0 check (supply_gap_score between 0 and 100),
  greek_scarcity_score numeric not null default 0 check (greek_scarcity_score between 0 and 100),
  problem_solving_score numeric not null default 0 check (problem_solving_score between 0 and 100),
  price_value_score numeric not null default 0 check (price_value_score between 0 and 100),
  trust_score numeric not null default 0 check (trust_score between 0 and 100),
  warranty_returns_score numeric not null default 0 check (warranty_returns_score between 0 and 100),
  greek_fulfilment_score numeric not null default 0 check (greek_fulfilment_score between 0 and 100),
  affiliate_performance_score numeric not null default 0 check (affiliate_performance_score between 0 and 100),
  conversion_potential_score numeric not null default 0 check (conversion_potential_score between 0 and 100),
  expected_revenue_score numeric not null default 0 check (expected_revenue_score between 0 and 100),
  confidence numeric not null default 0 check (confidence between 0 and 1),
  verdict text,
  why_selected text,
  why_rejected text,
  evidence_summary jsonb not null default '{}'::jsonb,
  assessed_at timestamptz not null default now()
);
create index if not exists merchant_demand_assessments_latest_idx on public.merchant_demand_assessments (merchant_id, market_code, assessed_at desc);
create index if not exists merchant_demand_assessments_opportunity_idx on public.merchant_demand_assessments (demand_score desc, competition_score, supply_gap_score desc, confidence desc);

create table if not exists public.merchant_rankings (
  id uuid primary key default gen_random_uuid(),
  merchant_id uuid not null references public.merchant_profiles(id) on delete cascade,
  demand_assessment_id uuid references public.merchant_demand_assessments(id) on delete set null,
  methodology_version text not null default 'merchant_360_v1',
  category_snapshot text,
  subcategory_snapshot text,
  raw_360_score numeric not null check (raw_360_score between 0 and 100),
  confidence_adjusted_score numeric not null check (confidence_adjusted_score between 0 and 100),
  confidence numeric not null check (confidence between 0 and 1),
  hard_gate_pass boolean not null default false,
  hard_gate_reasons jsonb not null default '[]'::jsonb,
  grade text,
  raw_rank integer,
  diversified_rank integer,
  eligible_for_product_discovery boolean not null default false,
  ai_verdict text,
  ranked_at timestamptz not null default now(),
  created_at timestamptz not null default now()
);
create index if not exists merchant_rankings_latest_idx on public.merchant_rankings (merchant_id, ranked_at desc);
create index if not exists merchant_rankings_selection_idx on public.merchant_rankings (eligible_for_product_discovery, confidence_adjusted_score desc, category_snapshot, subcategory_snapshot);

create table if not exists public.merchant_selection_policies (
  policy_key text primary key,
  enabled boolean not null default true,
  market_code text not null default 'GR',
  min_expected_commission_eur numeric not null default 15,
  min_demand_score numeric not null default 70,
  max_competition_score numeric not null default 45,
  min_supply_gap_score numeric not null default 60,
  min_problem_solving_score numeric not null default 70,
  min_trust_score numeric not null default 65,
  min_price_value_score numeric not null default 55,
  min_greek_fulfilment_score numeric not null default 60,
  min_confidence numeric not null default 0.65,
  min_confidence_adjusted_score numeric not null default 72,
  max_merchants_per_subcategory integer not null default 3 check (max_merchants_per_subcategory between 1 and 10),
  weights jsonb not null default '{"affiliate_performance":0.15,"expected_commission":0.15,"problem_solving":0.14,"demand_supply_gap":0.14,"trust":0.12,"price_value":0.10,"greek_fulfilment":0.08,"scarcity":0.05,"conversion_potential":0.04,"operational":0.03}'::jsonb,
  notes text,
  updated_at timestamptz not null default now()
);
insert into public.merchant_selection_policies (policy_key, notes)
values ('greece_problem_solver_v1','High-demand, under-served Greek-market merchants only; expected commission >= 15 EUR; final portfolio capped at 3 merchants per subcategory.')
on conflict (policy_key) do nothing;

create table if not exists public.product_discovery_runs (
  id uuid primary key default gen_random_uuid(),
  merchant_id uuid not null references public.merchant_profiles(id) on delete cascade,
  merchant_ranking_id uuid references public.merchant_rankings(id) on delete set null,
  policy_key text not null references public.merchant_selection_policies(policy_key),
  status text not null default 'queued' check (status in ('queued','running','succeeded','failed','cancelled')),
  checkpoint jsonb not null default '{}'::jsonb,
  source_cursor text,
  scanned_count bigint not null default 0,
  candidate_count bigint not null default 0,
  admitted_count bigint not null default 0,
  rejected_count bigint not null default 0,
  started_at timestamptz,
  completed_at timestamptz,
  error text,
  created_at timestamptz not null default now()
);
create index if not exists product_discovery_runs_merchant_idx on public.product_discovery_runs (merchant_id, created_at desc);

create table if not exists public.merchant_product_candidates (
  id uuid primary key default gen_random_uuid(),
  discovery_run_id uuid not null references public.product_discovery_runs(id) on delete cascade,
  merchant_id uuid not null references public.merchant_profiles(id) on delete cascade,
  source_product_id text,
  canonical_key text,
  product_name text not null,
  product_url text,
  tracking_url text,
  category text,
  subcategory text,
  problem_cluster text,
  price_eur numeric,
  expected_commission_eur numeric,
  demand_score numeric not null default 0 check (demand_score between 0 and 100),
  competition_score numeric not null default 100 check (competition_score between 0 and 100),
  supply_gap_score numeric not null default 0 check (supply_gap_score between 0 and 100),
  problem_solving_score numeric not null default 0 check (problem_solving_score between 0 and 100),
  greek_scarcity_score numeric not null default 0 check (greek_scarcity_score between 0 and 100),
  price_value_score numeric not null default 0 check (price_value_score between 0 and 100),
  trust_score numeric not null default 0 check (trust_score between 0 and 100),
  conversion_potential_score numeric not null default 0 check (conversion_potential_score between 0 and 100),
  confidence numeric not null default 0 check (confidence between 0 and 1),
  final_opportunity_score numeric not null default 0 check (final_opportunity_score between 0 and 100),
  admission_status text not null default 'pending' check (admission_status in ('pending','admit','reject','hold')),
  rejection_reasons jsonb not null default '[]'::jsonb,
  evidence jsonb not null default '{}'::jsonb,
  evaluated_at timestamptz,
  created_at timestamptz not null default now(),
  unique (merchant_id, canonical_key)
);
create index if not exists merchant_product_candidates_rank_idx on public.merchant_product_candidates (admission_status, final_opportunity_score desc, demand_score desc, competition_score);

alter table public.products add column if not exists merchant_profile_id uuid references public.merchant_profiles(id) on delete set null;
alter table public.product_feed_items add column if not exists merchant_profile_id uuid references public.merchant_profiles(id) on delete set null;
create index if not exists products_merchant_profile_idx on public.products (merchant_profile_id);
create index if not exists product_feed_items_merchant_profile_idx on public.product_feed_items (merchant_profile_id);

create or replace view public.merchant_latest_360 with (security_invoker=true) as
with latest_assessment as (
  select distinct on (merchant_id) * from public.merchant_demand_assessments where market_code='GR' order by merchant_id,assessed_at desc
), latest_ranking as (
  select distinct on (merchant_id) * from public.merchant_rankings order by merchant_id,ranked_at desc
)
select m.*,a.id as latest_assessment_id,a.demand_score,a.commercial_intent_score,a.competition_score,a.supply_gap_score,a.greek_scarcity_score,a.problem_solving_score,a.price_value_score,a.trust_score,a.warranty_returns_score,a.greek_fulfilment_score,a.affiliate_performance_score,a.conversion_potential_score,a.expected_revenue_score,a.confidence as assessment_confidence,r.id as latest_ranking_id,r.raw_360_score,r.confidence_adjusted_score,r.confidence as ranking_confidence,r.hard_gate_pass,r.grade,r.raw_rank,r.diversified_rank,r.eligible_for_product_discovery,r.ai_verdict,r.ranked_at
from public.merchant_profiles m left join latest_assessment a on a.merchant_id=m.id left join latest_ranking r on r.merchant_id=m.id;

create or replace view public.merchant_product_discovery_eligible with (security_invoker=true) as
with policy as (
  select * from public.merchant_selection_policies where policy_key='greece_problem_solver_v1' and enabled
), candidates as (
  select v.*,coalesce(nullif(v.primary_subcategory,''),nullif(v.primary_category,''),'uncategorized') as diversity_bucket,
         row_number() over (partition by coalesce(nullif(v.primary_subcategory,''),nullif(v.primary_category,''),'uncategorized') order by v.confidence_adjusted_score desc nulls last,v.expected_revenue_score desc nulls last,v.merchant_name) as subcategory_rank
  from public.merchant_latest_360 v cross join policy p
  where v.active and v.hard_gate_pass and v.eligible_for_product_discovery
    and coalesce(v.expected_commission_eur,0)>=p.min_expected_commission_eur
    and coalesce(v.demand_score,0)>=p.min_demand_score
    and coalesce(v.competition_score,100)<=p.max_competition_score
    and coalesce(v.supply_gap_score,0)>=p.min_supply_gap_score
    and coalesce(v.problem_solving_score,0)>=p.min_problem_solving_score
    and coalesce(v.trust_score,0)>=p.min_trust_score
    and coalesce(v.price_value_score,0)>=p.min_price_value_score
    and coalesce(v.greek_fulfilment_score,0)>=p.min_greek_fulfilment_score
    and coalesce(v.ranking_confidence,0)>=p.min_confidence
    and coalesce(v.confidence_adjusted_score,0)>=p.min_confidence_adjusted_score
)
select c.* from candidates c cross join policy p where c.subcategory_rank<=p.max_merchants_per_subcategory;

alter table public.merchant_profiles enable row level security;
alter table public.merchant_category_memberships enable row level security;
alter table public.merchant_research_runs enable row level security;
alter table public.merchant_evidence enable row level security;
alter table public.merchant_demand_assessments enable row level security;
alter table public.merchant_rankings enable row level security;
alter table public.merchant_selection_policies enable row level security;
alter table public.product_discovery_runs enable row level security;
alter table public.merchant_product_candidates enable row level security;

revoke all on public.merchant_profiles,public.merchant_category_memberships,public.merchant_research_runs,public.merchant_evidence,public.merchant_demand_assessments,public.merchant_rankings,public.merchant_selection_policies,public.product_discovery_runs,public.merchant_product_candidates from anon;
grant select,insert,update,delete on public.merchant_profiles,public.merchant_category_memberships,public.merchant_research_runs,public.merchant_evidence,public.merchant_demand_assessments,public.merchant_rankings,public.merchant_selection_policies,public.product_discovery_runs,public.merchant_product_candidates to authenticated;
grant select on public.merchant_latest_360,public.merchant_product_discovery_eligible to authenticated;

do $$ declare t text; begin
  foreach t in array array['merchant_profiles','merchant_category_memberships','merchant_research_runs','merchant_evidence','merchant_demand_assessments','merchant_rankings','merchant_selection_policies','product_discovery_runs','merchant_product_candidates'] loop
    execute format('drop policy if exists admin_all on public.%I',t);
    execute format('create policy admin_all on public.%I for all to authenticated using (private.is_admin()) with check (private.is_admin())',t);
  end loop;
end $$;
