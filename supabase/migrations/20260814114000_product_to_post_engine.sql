create table if not exists public.product_to_post_runs (
  id uuid primary key default gen_random_uuid(),
  mode text not null default 'manual' check (mode in ('manual','auto')),
  product_id uuid references public.products(id) on delete set null,
  requested_count integer not null default 1 check (requested_count between 1 and 100),
  platforms text[] not null default array['facebook','instagram','tiktok','linkedin']::text[],
  horizon_days integer not null default 30 check (horizon_days between 1 and 90),
  strategy text not null default 'conversion',
  audience_context jsonb not null default '{}'::jsonb,
  status text not null default 'queued' check (status in ('queued','processing','generated','needs_approval','scheduled','completed','failed','cancelled')),
  priority integer not null default 0,
  worker_id text,
  model_route text,
  summary jsonb not null default '{}'::jsonb,
  error text,
  started_at timestamptz,
  finished_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists idx_product_to_post_runs_queue on public.product_to_post_runs(status, priority desc, created_at);

create table if not exists public.product_to_post_items (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references public.product_to_post_runs(id) on delete cascade,
  product_id uuid not null references public.products(id) on delete cascade,
  selection_rank integer,
  selection_reason jsonb not null default '{}'::jsonb,
  status text not null default 'selected' check (status in ('selected','enriched','strategized','rendered','planned','failed')),
  error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(run_id, product_id)
);
create index if not exists idx_product_to_post_items_run on public.product_to_post_items(run_id, selection_rank);

create table if not exists public.product_enrichment_evidence (
  id uuid primary key default gen_random_uuid(),
  item_id uuid not null references public.product_to_post_items(id) on delete cascade,
  source_url text not null,
  resolved_url text,
  http_status integer,
  facts jsonb not null default '{}'::jsonb,
  source_meta jsonb not null default '{}'::jsonb,
  content_hash text,
  fetched_at timestamptz not null default now()
);
create index if not exists idx_product_enrichment_item on public.product_enrichment_evidence(item_id, fetched_at desc);

create table if not exists public.marketing_angles (
  id uuid primary key default gen_random_uuid(),
  item_id uuid not null references public.product_to_post_items(id) on delete cascade,
  angle_key text not null,
  framework text not null,
  persona text,
  hook text not null,
  promise text,
  proof_points jsonb not null default '[]'::jsonb,
  objections jsonb not null default '[]'::jsonb,
  cta text,
  score numeric(5,2) not null default 0,
  rationale text,
  selected boolean not null default false,
  model_route jsonb not null default '{}'::jsonb,
  prompt_version text not null default 'p2p-v1',
  created_at timestamptz not null default now(),
  unique(item_id, angle_key)
);
create index if not exists idx_marketing_angles_item_score on public.marketing_angles(item_id, score desc);

create table if not exists public.social_post_variants (
  id uuid primary key default gen_random_uuid(),
  item_id uuid not null references public.product_to_post_items(id) on delete cascade,
  angle_id uuid references public.marketing_angles(id) on delete set null,
  platform text not null check (platform in ('facebook','instagram','tiktok','linkedin')),
  variant_key text not null,
  headline text,
  hook text,
  caption text not null,
  hashtags text[] not null default '{}'::text[],
  cta text,
  disclosure text,
  media_format text,
  creative_direction jsonb not null default '{}'::jsonb,
  selected boolean not null default false,
  status text not null default 'draft' check (status in ('draft','needs_creative','needs_approval','approved','rejected','scheduled','published')),
  model_route jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique(item_id, platform, variant_key)
);
create index if not exists idx_social_post_variants_item on public.social_post_variants(item_id, platform, selected desc);

create table if not exists public.social_content_calendar (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references public.product_to_post_runs(id) on delete cascade,
  item_id uuid not null references public.product_to_post_items(id) on delete cascade,
  variant_id uuid not null references public.social_post_variants(id) on delete cascade,
  platform text not null check (platform in ('facebook','instagram','tiktok','linkedin')),
  scheduled_at timestamptz not null,
  objective text not null default 'conversion',
  status text not null default 'needs_approval' check (status in ('needs_approval','approved','scheduled','published','skipped','failed')),
  tracking_url text not null,
  creative_asset_id uuid references public.creative_assets(id) on delete set null,
  social_post_id uuid,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(run_id, variant_id, scheduled_at)
);
create index if not exists idx_social_content_calendar_schedule on public.social_content_calendar(status, scheduled_at);
create index if not exists idx_social_content_calendar_run on public.social_content_calendar(run_id, scheduled_at);

create table if not exists public.social_performance_observations (
  id uuid primary key default gen_random_uuid(),
  calendar_item_id uuid not null references public.social_content_calendar(id) on delete cascade,
  source text not null default 'manual',
  impressions bigint,
  engagements bigint,
  clicks bigint,
  outbound_clicks bigint,
  conversions numeric,
  revenue numeric(14,2),
  metadata jsonb not null default '{}'::jsonb,
  observed_at timestamptz not null default now()
);
create index if not exists idx_social_performance_calendar on public.social_performance_observations(calendar_item_id, observed_at desc);

alter table public.product_to_post_runs enable row level security;
alter table public.product_to_post_items enable row level security;
alter table public.product_enrichment_evidence enable row level security;
alter table public.marketing_angles enable row level security;
alter table public.social_post_variants enable row level security;
alter table public.social_content_calendar enable row level security;
alter table public.social_performance_observations enable row level security;

do $$ declare t text; begin
  foreach t in array array['product_to_post_runs','product_to_post_items','product_enrichment_evidence','marketing_angles','social_post_variants','social_content_calendar','social_performance_observations'] loop
    execute format('drop policy if exists admin_authenticated_all on public.%I', t);
    execute format('create policy admin_authenticated_all on public.%I for all to authenticated using (true) with check (true)', t);
  end loop;
end $$;

create or replace function public.claim_product_to_post_runs(p_worker_id text, p_limit integer default 2)
returns setof public.product_to_post_runs
language plpgsql
security definer
set search_path = public
as $$
begin
  return query
  with picked as (
    select id
    from public.product_to_post_runs
    where status = 'queued'
    order by priority desc, created_at
    for update skip locked
    limit greatest(1, least(coalesce(p_limit,2),10))
  )
  update public.product_to_post_runs r
  set status='processing', worker_id=p_worker_id, started_at=coalesce(r.started_at,now()), updated_at=now(), error=null
  where r.id in (select id from picked)
  returning r.*;
end;
$$;

revoke all on function public.claim_product_to_post_runs(text, integer) from public, anon, authenticated;
grant execute on function public.claim_product_to_post_runs(text, integer) to service_role;
