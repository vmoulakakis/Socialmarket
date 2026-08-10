alter table public.merchant_profiles add column if not exists internal_trust_score numeric;
alter table public.merchant_profiles add column if not exists external_reputation_confidence numeric default 0;
alter table public.merchant_profiles add column if not exists official_domain text;
alter table public.merchant_profiles add column if not exists domain_age_years numeric;
alter table public.merchant_profiles add column if not exists business_identity_score numeric;
alter table public.merchant_profiles add column if not exists review_footprint_score numeric;
alter table public.merchant_profiles add column if not exists complaint_risk_score numeric;
alter table public.merchant_profiles add column if not exists external_risk_flag boolean default false;
alter table public.merchant_profiles add column if not exists external_risk_reason text;
alter table public.merchant_profiles add column if not exists evidence_count integer default 0;
alter table public.merchant_profiles add column if not exists last_researched_at timestamptz;

create table if not exists public.merchant_research_runs (
  id uuid primary key default gen_random_uuid(),
  status text not null default 'queued',
  merchant_count integer default 0,
  evidence_count integer default 0,
  config jsonb not null default '{}'::jsonb,
  started_at timestamptz,
  finished_at timestamptz,
  error text,
  created_at timestamptz not null default now()
);

create table if not exists public.merchant_reputation_evidence (
  id uuid primary key default gen_random_uuid(),
  run_id uuid references public.merchant_research_runs(id) on delete cascade,
  merchant_profile_id uuid references public.merchant_profiles(id) on delete cascade,
  merchant_name text not null,
  evidence_type text not null,
  source_name text,
  source_url text,
  source_domain text,
  title text,
  snippet text,
  credibility_tier smallint not null default 3,
  signal_score numeric,
  confidence numeric not null default 0,
  review_rating numeric,
  review_count integer,
  observed_at timestamptz not null default now(),
  metadata jsonb not null default '{}'::jsonb
);

create index if not exists idx_merchant_evidence_profile on public.merchant_reputation_evidence(merchant_profile_id, observed_at desc);
create index if not exists idx_merchant_evidence_type on public.merchant_reputation_evidence(evidence_type, observed_at desc);
create index if not exists idx_merchant_research_runs_status on public.merchant_research_runs(status, created_at desc);

alter table public.merchant_research_runs enable row level security;
alter table public.merchant_reputation_evidence enable row level security;

do $$ begin
  if not exists (select 1 from pg_policies where schemaname='public' and tablename='merchant_research_runs' and policyname='merchant_research_runs_admin_all') then
    create policy merchant_research_runs_admin_all on public.merchant_research_runs for all using (private.is_admin()) with check (private.is_admin());
  end if;
  if not exists (select 1 from pg_policies where schemaname='public' and tablename='merchant_reputation_evidence' and policyname='merchant_reputation_evidence_admin_all') then
    create policy merchant_reputation_evidence_admin_all on public.merchant_reputation_evidence for all using (private.is_admin()) with check (private.is_admin());
  end if;
end $$;
