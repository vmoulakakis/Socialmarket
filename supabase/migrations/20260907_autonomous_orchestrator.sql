create table if not exists public.orchestrator_runs (
  id text primary key,
  prompt text not null,
  state text not null,
  intent text,
  plan jsonb,
  result jsonb,
  error jsonb,
  history jsonb not null default '[]'::jsonb,
  approval_required boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.orchestrator_steps (
  run_id text not null references public.orchestrator_runs(id) on delete cascade,
  step_id text not null,
  capability text not null,
  state text not null,
  input jsonb,
  output jsonb,
  error text,
  requires_approval boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (run_id, step_id)
);

create table if not exists public.site_registry (
  id text primary key,
  project text not null,
  production_url text,
  repo text,
  role text,
  managed boolean not null default false,
  index_policy text,
  known_issues jsonb not null default '[]'::jsonb,
  health jsonb,
  last_audit_at timestamptz,
  updated_at timestamptz not null default now()
);

create index if not exists orchestrator_runs_state_idx on public.orchestrator_runs(state);
create index if not exists orchestrator_steps_capability_idx on public.orchestrator_steps(capability);
create index if not exists site_registry_managed_idx on public.site_registry(managed);

alter table public.orchestrator_runs enable row level security;
alter table public.orchestrator_steps enable row level security;
alter table public.site_registry enable row level security;

-- Runtime access is intentionally service-role only. No public RLS policies are created here.
