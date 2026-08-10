create extension if not exists vector;
create extension if not exists pgcrypto;

create table if not exists public.sources (
  id uuid primary key default gen_random_uuid(), name text not null, source_type text not null default 'json_feed',
  source_url text, country_code text not null default 'GR', active boolean not null default true,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create table if not exists public.import_jobs (
  id uuid primary key default gen_random_uuid(), source_id uuid references public.sources(id) on delete set null,
  status text not null default 'queued', file_name text, file_size_bytes bigint, records_seen bigint not null default 0,
  records_inserted bigint not null default 0, records_updated bigint not null default 0, records_skipped bigint not null default 0,
  checkpoint jsonb not null default '{}'::jsonb, error_summary text, started_at timestamptz, finished_at timestamptz,
  created_at timestamptz not null default now()
);
create table if not exists public.products (
  id uuid primary key default gen_random_uuid(), source_id uuid references public.sources(id) on delete set null,
  external_product_id text not null, model_name text, product_name text not null, description text, category_raw text,
  brand_name text, merchant_name text, program_name text, tracking_url text, thumb_url text, image_url text,
  extra_images jsonb not null default '[]'::jsonb, in_stock boolean, availability text, valid_from timestamptz,
  valid_to timestamptz, on_sale boolean, currency text not null default 'EUR', price numeric(14,2), full_price numeric(14,2),
  discount_pct numeric(7,2), times_bought bigint, city text, longitude numeric, latitude numeric, address text, size text,
  colour text, extra_json jsonb not null default '{}'::jsonb, is_active boolean not null default true,
  hard_gate_pass boolean not null default false, purchase_friction numeric(5,4), purchase_friction_reason text,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now(), unique(source_id, external_product_id)
);
create index if not exists idx_products_price on public.products(price);
create index if not exists idx_products_active_gate on public.products(is_active, hard_gate_pass);
create index if not exists idx_products_category_raw on public.products(category_raw);
create index if not exists idx_products_brand on public.products(brand_name);
create index if not exists idx_products_program on public.products(program_name);

create table if not exists public.product_media (
  id uuid primary key default gen_random_uuid(), product_id uuid not null references public.products(id) on delete cascade,
  media_type text not null default 'main', source_url text not null, storage_path text, width integer, height integer,
  quality_score numeric(5,2), visual_commercial_score numeric(5,2), background_type text, contains_text boolean,
  is_primary boolean not null default false, analysis jsonb not null default '{}'::jsonb, created_at timestamptz not null default now()
);
create index if not exists idx_product_media_product on public.product_media(product_id);

create table if not exists public.taxonomy (
  id uuid primary key default gen_random_uuid(), parent_id uuid references public.taxonomy(id) on delete cascade,
  level smallint not null, name text not null, slug text not null unique, taxonomy_type text not null,
  country_code text not null default 'GR', active boolean not null default true, created_at timestamptz not null default now()
);
create table if not exists public.product_classifications (
  id uuid primary key default gen_random_uuid(), product_id uuid not null references public.products(id) on delete cascade,
  taxonomy_id uuid not null references public.taxonomy(id) on delete cascade, source text not null default 'ai', confidence numeric(5,4),
  is_primary boolean not null default false, rationale text, created_at timestamptz not null default now(), unique(product_id, taxonomy_id)
);
create index if not exists idx_product_class_taxonomy on public.product_classifications(taxonomy_id);

create table if not exists public.product_embeddings (
  id uuid primary key default gen_random_uuid(), product_id uuid not null references public.products(id) on delete cascade,
  embedding_type text not null default 'text', embedding vector(1024) not null, model_name text not null default 'BAAI/bge-m3',
  content_hash text, created_at timestamptz not null default now(), unique(product_id, embedding_type)
);
create index if not exists idx_product_embeddings_hnsw on public.product_embeddings using hnsw (embedding vector_cosine_ops);

create or replace function public.match_products(query_embedding vector(1024), match_count integer default 20, min_price numeric default 150, min_similarity double precision default 0.35)
returns table(product_id uuid, similarity double precision) language sql stable as $$
  select pe.product_id, 1 - (pe.embedding <=> query_embedding) as similarity
  from public.product_embeddings pe join public.products p on p.id = pe.product_id
  where p.is_active = true and p.hard_gate_pass = true and coalesce(p.price,0) >= min_price
    and 1 - (pe.embedding <=> query_embedding) >= min_similarity
  order by pe.embedding <=> query_embedding limit match_count;
$$;

create table if not exists public.market_research_runs (
  id uuid primary key default gen_random_uuid(), scope_type text not null, scope_key text not null, country_code text not null default 'GR',
  query_plan jsonb not null default '{}'::jsonb, status text not null default 'queued', model_route text,
  started_at timestamptz, finished_at timestamptz, error text, created_at timestamptz not null default now()
);
create table if not exists public.market_signals (
  id uuid primary key default gen_random_uuid(), research_run_id uuid references public.market_research_runs(id) on delete cascade,
  product_id uuid references public.products(id) on delete cascade, taxonomy_id uuid references public.taxonomy(id) on delete cascade,
  signal_type text not null, source_name text not null, source_url text, observed_at timestamptz not null default now(), raw_value numeric,
  normalized_score numeric(5,2), direction text, evidence jsonb not null default '{}'::jsonb, confidence numeric(5,4),
  created_at timestamptz not null default now()
);
create index if not exists idx_market_signals_product on public.market_signals(product_id, observed_at desc);
create index if not exists idx_market_signals_taxonomy on public.market_signals(taxonomy_id, observed_at desc);
create index if not exists idx_market_signals_type on public.market_signals(signal_type, observed_at desc);

create table if not exists public.forecast_runs (
  id uuid primary key default gen_random_uuid(), model_name text not null, horizon_days integer not null, training_window_days integer,
  parameters jsonb not null default '{}'::jsonb, status text not null default 'queued', started_at timestamptz, finished_at timestamptz,
  created_at timestamptz not null default now()
);
create table if not exists public.forecasts (
  id uuid primary key default gen_random_uuid(), forecast_run_id uuid not null references public.forecast_runs(id) on delete cascade,
  scope_type text not null, scope_key text not null, taxonomy_id uuid references public.taxonomy(id) on delete cascade,
  product_id uuid references public.products(id) on delete cascade, forecast_date date not null, point_forecast numeric,
  lower_bound numeric, upper_bound numeric, growth_pct numeric, direction text, confidence numeric(5,4), created_at timestamptz not null default now()
);
create index if not exists idx_forecasts_scope on public.forecasts(scope_type, scope_key, forecast_date desc);

create table if not exists public.opportunity_scores (
  id uuid primary key default gen_random_uuid(), product_id uuid not null references public.products(id) on delete cascade,
  demand_score numeric(5,2) not null default 0, forecast_momentum_score numeric(5,2) not null default 0,
  attention_gap_score numeric(5,2) not null default 0, purchase_ease_score numeric(5,2) not null default 0,
  offer_score numeric(5,2) not null default 0, evidence_quality_score numeric(5,2) not null default 0,
  merchant_reliability_score numeric(5,2) not null default 0, creative_potential_score numeric(5,2) not null default 0,
  higo_raw numeric(5,2) not null default 0, confidence numeric(5,4) not null default 0, higo_adjusted numeric(5,2) not null default 0,
  decision text not null default 'ignore', skeptic_status text not null default 'pending', explanation jsonb not null default '{}'::jsonb,
  calculated_at timestamptz not null default now()
);
create index if not exists idx_opportunity_rank on public.opportunity_scores(higo_adjusted desc, confidence desc);
create index if not exists idx_opportunity_product on public.opportunity_scores(product_id, calculated_at desc);

create table if not exists public.evidence_audits (
  id uuid primary key default gen_random_uuid(), opportunity_score_id uuid not null references public.opportunity_scores(id) on delete cascade,
  verdict text not null, risk_score numeric(5,2), risks jsonb not null default '[]'::jsonb, counter_evidence jsonb not null default '[]'::jsonb,
  notes text, model_route text, created_at timestamptz not null default now()
);
create table if not exists public.creative_jobs (
  id uuid primary key default gen_random_uuid(), product_id uuid not null references public.products(id) on delete cascade,
  opportunity_score_id uuid references public.opportunity_scores(id) on delete set null, status text not null default 'queued', concept_type text,
  platform_target text, tracking_url text not null, brief jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(),
  started_at timestamptz, finished_at timestamptz
);
create table if not exists public.creative_assets (
  id uuid primary key default gen_random_uuid(), creative_job_id uuid not null references public.creative_jobs(id) on delete cascade,
  asset_type text not null, storage_path text not null, width integer, height integer, copy jsonb not null default '{}'::jsonb,
  qr_payload text, quality_score numeric(5,2), visual_audit jsonb not null default '{}'::jsonb, created_at timestamptz not null default now()
);
create table if not exists public.approvals (
  id uuid primary key default gen_random_uuid(), creative_asset_id uuid not null references public.creative_assets(id) on delete cascade,
  action text not null, notes text, reviewed_by uuid references auth.users(id) on delete set null, reviewed_at timestamptz not null default now()
);
create table if not exists public.agent_runs (
  id uuid primary key default gen_random_uuid(), agent_name text not null, task_type text not null, entity_type text, entity_id uuid,
  status text not null default 'queued', model_route text, input_summary jsonb not null default '{}'::jsonb,
  output_summary jsonb not null default '{}'::jsonb, token_usage jsonb not null default '{}'::jsonb, error text,
  started_at timestamptz, finished_at timestamptz, created_at timestamptz not null default now()
);
create table if not exists public.app_settings (key text primary key, value jsonb not null, updated_at timestamptz not null default now());
insert into public.app_settings(key,value) values
('selection_rules','{"min_price_eur":150,"base_max_purchase_friction":0.40,"large_discount_pct":30,"large_discount_max_friction":0.60,"exceptional_discount_pct":45,"exceptional_discount_max_friction":0.75,"min_higo_create":85,"min_higo_priority":92,"min_confidence_create":0.70}'::jsonb)
on conflict (key) do nothing;

insert into storage.buckets(id,name,public,file_size_limit,allowed_mime_types) values
('product-media','product-media',false,52428800,array['image/jpeg','image/png','image/webp']),
('creatives','creatives',false,52428800,array['image/jpeg','image/png','image/webp','image/svg+xml'])
on conflict (id) do nothing;

alter table public.sources enable row level security; alter table public.import_jobs enable row level security;
alter table public.products enable row level security; alter table public.product_media enable row level security;
alter table public.taxonomy enable row level security; alter table public.product_classifications enable row level security;
alter table public.product_embeddings enable row level security; alter table public.market_research_runs enable row level security;
alter table public.market_signals enable row level security; alter table public.forecast_runs enable row level security;
alter table public.forecasts enable row level security; alter table public.opportunity_scores enable row level security;
alter table public.evidence_audits enable row level security; alter table public.creative_jobs enable row level security;
alter table public.creative_assets enable row level security; alter table public.approvals enable row level security;
alter table public.agent_runs enable row level security; alter table public.app_settings enable row level security;

do $$ declare t text; begin
  foreach t in array array['sources','import_jobs','products','product_media','taxonomy','product_classifications','product_embeddings','market_research_runs','market_signals','forecast_runs','forecasts','opportunity_scores','evidence_audits','creative_jobs','creative_assets','approvals','agent_runs','app_settings'] loop
    execute format('drop policy if exists admin_authenticated_all on public.%I', t);
    execute format('create policy admin_authenticated_all on public.%I for all to authenticated using (true) with check (true)', t);
  end loop;
end $$;

drop policy if exists admin_product_media on storage.objects;
create policy admin_product_media on storage.objects for all to authenticated using (bucket_id in ('product-media','creatives')) with check (bucket_id in ('product-media','creatives'));
