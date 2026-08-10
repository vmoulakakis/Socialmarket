create extension if not exists vector;
create extension if not exists pgcrypto;

create type opportunity_decision as enum ('drop','monitor','watchlist','create_creative','priority');
create type evidence_direction as enum ('positive','negative','neutral');

create table if not exists sources (id uuid primary key default gen_random_uuid(),name text not null,source_type text not null,source_url text,is_active boolean not null default true,created_at timestamptz not null default now());

create table if not exists products (
  id uuid primary key default gen_random_uuid(),source_id uuid references sources(id) on delete set null,external_product_id text,product_name text not null,model_name text,description text,brand_name text,program_name text,category_raw text,subcategory_raw text,price numeric(12,2),full_price numeric(12,2),discount_percent numeric(7,2),currency text default 'EUR',in_stock boolean,availability text,valid_from timestamptz,valid_to timestamptz,times_bought numeric,tracking_url text,image_url text,thumb_url text,extra_images jsonb not null default '[]'::jsonb,merchant_name text,city text,colour text,size text,raw jsonb,is_active boolean not null default true,created_at timestamptz not null default now(),updated_at timestamptz not null default now(),unique(source_id,external_product_id)
);
create index if not exists products_price_idx on products(price);
create index if not exists products_category_idx on products(category_raw);
create index if not exists products_active_idx on products(is_active,in_stock);

create table if not exists taxonomy_nodes (id uuid primary key default gen_random_uuid(),parent_id uuid references taxonomy_nodes(id) on delete cascade,level smallint not null,name text not null,slug text not null,node_type text not null check(node_type in ('category','subcategory','intent_cluster','product_type','theme')),unique(parent_id,slug));
create table if not exists product_taxonomy (product_id uuid references products(id) on delete cascade,taxonomy_id uuid references taxonomy_nodes(id) on delete cascade,confidence numeric(5,4),source text not null default 'agent',is_primary boolean not null default false,primary key(product_id,taxonomy_id));
create table if not exists product_embeddings (product_id uuid primary key references products(id) on delete cascade,embedding vector(1024),model text not null default 'BAAI/bge-m3',updated_at timestamptz not null default now());

create table if not exists market_signals (id uuid primary key default gen_random_uuid(),taxonomy_id uuid references taxonomy_nodes(id) on delete cascade,product_id uuid references products(id) on delete cascade,signal_type text not null,source_name text not null,source_url text,observed_at timestamptz not null default now(),raw_value numeric,normalized_score numeric(6,2),direction evidence_direction,evidence jsonb not null default '{}'::jsonb,confidence numeric(5,4));
create index if not exists market_signals_lookup_idx on market_signals(taxonomy_id,product_id,observed_at desc);

create table if not exists forecasts (id uuid primary key default gen_random_uuid(),taxonomy_id uuid references taxonomy_nodes(id) on delete cascade,product_id uuid references products(id) on delete cascade,horizon_days integer not null,model_name text not null,generated_at timestamptz not null default now(),direction text,growth_low numeric,growth_mid numeric,growth_high numeric,confidence numeric(5,4),payload jsonb not null default '{}'::jsonb);

create table if not exists opportunity_scores (id uuid primary key default gen_random_uuid(),product_id uuid references products(id) on delete cascade,current_demand numeric(6,2) not null,forecast_momentum numeric(6,2) not null,attention_gap numeric(6,2) not null,purchase_ease numeric(6,2) not null,price_discount numeric(6,2) not null,evidence_quality numeric(6,2) not null,offer_reliability numeric(6,2) not null,creative_potential numeric(6,2) not null,purchase_friction numeric(5,4) not null,raw_higo numeric(6,2) not null,confidence numeric(6,2) not null,final_higo numeric(6,2) not null,decision opportunity_decision not null,hard_gate_pass boolean not null,rationale jsonb not null default '{}'::jsonb,generated_at timestamptz not null default now());
create index if not exists opportunity_rank_idx on opportunity_scores(final_higo desc,confidence desc);

create table if not exists research_runs (id uuid primary key default gen_random_uuid(),scope_type text not null,scope_id uuid,agent_name text not null,provider text,status text not null,input jsonb not null default '{}'::jsonb,output jsonb not null default '{}'::jsonb,evidence_count integer not null default 0,started_at timestamptz not null default now(),finished_at timestamptz);
create table if not exists creative_jobs (id uuid primary key default gen_random_uuid(),product_id uuid references products(id) on delete cascade,opportunity_score_id uuid references opportunity_scores(id) on delete set null,status text not null default 'queued',creative_brief jsonb not null default '{}'::jsonb,tracking_url text not null,created_at timestamptz not null default now());

alter table sources enable row level security;alter table products enable row level security;alter table taxonomy_nodes enable row level security;alter table product_taxonomy enable row level security;alter table product_embeddings enable row level security;alter table market_signals enable row level security;alter table forecasts enable row level security;alter table opportunity_scores enable row level security;alter table research_runs enable row level security;alter table creative_jobs enable row level security;
-- Single-admin policies are intentionally added only after the admin identity is configured.
