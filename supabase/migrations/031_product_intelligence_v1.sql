-- Product Intelligence V1 — additive layer over the existing merchant/evidence foundation.
-- Raw 3.8 GB feeds are NOT stored here. Only commission-eligible canonical products/offers survive into these tables.

create table if not exists catalog.merchant_promotion_policy (
  merchant_id uuid primary key references catalog.merchants(id) on delete cascade,
  promotion_mode text not null default 'eligible' check (promotion_mode in ('eligible','demand_beacon_only','blocked')),
  dominant_market boolean not null default false,
  reason text,
  methodology_version text not null default 'merchant-promotion-policy-v1',
  metadata jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);
alter table catalog.merchant_promotion_policy enable row level security;

insert into catalog.merchant_promotion_policy(merchant_id,promotion_mode,dominant_market,reason,metadata)
select id,'demand_beacon_only',true,
       'Dominant/high-saturation retailer or marketplace: keep as demand/evidence beacon, exclude its offers from Solution Whitespace promotion.',
       jsonb_build_object('source','product-intelligence-v1-seed','canonical_name',canonical_name)
from catalog.merchants
where normalized_name in ('public','kotsovolos','shein','aliexpress','e-shop-gr')
on conflict (merchant_id) do update
set promotion_mode=excluded.promotion_mode,
    dominant_market=excluded.dominant_market,
    reason=excluded.reason,
    metadata=catalog.merchant_promotion_policy.metadata || excluded.metadata,
    updated_at=now();

create table if not exists catalog.products (
  id uuid primary key default gen_random_uuid(),
  canonical_key text not null unique,
  canonical_title text not null,
  brand_name text,
  model_name text,
  gtin text,
  mpn text,
  category text,
  subcategory text,
  status text not null default 'candidate' check (status in ('candidate','validated','needs_review','rejected','inactive')),
  semantic_text text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
alter table catalog.products enable row level security;
create index if not exists products_brand_model_idx on catalog.products(lower(coalesce(brand_name,'')), lower(coalesce(model_name,'')));
create index if not exists products_category_idx on catalog.products(category,subcategory);

create table if not exists catalog.product_offers (
  id uuid primary key default gen_random_uuid(),
  product_id uuid not null references catalog.products(id) on delete cascade,
  merchant_id uuid not null references catalog.merchants(id) on delete restrict,
  merchant_program_id uuid references catalog.merchant_programs(id) on delete set null,
  source_feed text not null default 'linkwise-products.json',
  external_product_id text,
  source_record_hash text not null,
  program_name_raw text,
  product_name_raw text,
  description_raw text,
  category_raw text,
  effective_price numeric(14,4) not null,
  full_price numeric(14,4),
  discount_pct numeric(8,3),
  currency text not null default 'EUR',
  commission_rate_pct numeric(8,4),
  flat_commission_eur numeric(14,4),
  expected_commission_eur numeric(14,4) not null,
  commission_rule text not null,
  commission_confidence numeric(6,5) not null default 1,
  tracking_url text not null,
  image_url text,
  thumb_url text,
  in_stock boolean,
  availability text,
  times_bought bigint,
  valid_from timestamptz,
  valid_to timestamptz,
  dominant_market_excluded boolean not null default false,
  eligible boolean not null default true,
  eligibility_reason text,
  raw_metadata jsonb not null default '{}'::jsonb,
  first_seen_at timestamptz not null default now(),
  last_seen_at timestamptz not null default now(),
  unique(source_feed,source_record_hash)
);
alter table catalog.product_offers enable row level security;
create index if not exists product_offers_product_idx on catalog.product_offers(product_id);
create index if not exists product_offers_merchant_idx on catalog.product_offers(merchant_id);
create index if not exists product_offers_commission_idx on catalog.product_offers(expected_commission_eur desc) where eligible;

create table if not exists intel.demand_themes (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  name text not null,
  parent_id uuid references intel.demand_themes(id) on delete cascade,
  theme_type text not null default 'seasonal',
  market text not null default 'GR',
  active_from date,
  peak_date date,
  active_to date,
  semantic_brief text not null,
  base_demand_score numeric(6,2),
  confidence numeric(6,5),
  status text not null default 'active',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
alter table intel.demand_themes enable row level security;

insert into intel.demand_themes(slug,name,theme_type,active_from,peak_date,active_to,semantic_brief,metadata)
values
('back-to-school-2026','Back to School 2026','seasonal','2026-07-15','2026-09-01','2026-10-15','Greek Back-to-School demand: students, parents and teachers seeking ergonomic, organizational, concentration, technology, transport, lunch and study-space solutions.',jsonb_build_object('version','theme-v1'))
on conflict(slug) do update set semantic_brief=excluded.semantic_brief,updated_at=now();

with root as (select id from intel.demand_themes where slug='back-to-school-2026')
insert into intel.demand_themes(slug,name,parent_id,theme_type,active_from,peak_date,active_to,semantic_brief,metadata)
select x.slug,x.name,root.id,'seasonal_subtheme','2026-07-15','2026-09-01','2026-10-15',x.brief,jsonb_build_object('version','theme-v1')
from root cross join (values
 ('bts-ergonomics','Ergonomics','Backpacks, chairs, desk setup, posture and carrying comfort for students.'),
 ('bts-study-organization','Study Organization','Storage, planners, desk organization and time-management solutions.'),
 ('bts-concentration','Concentration','Noise, focus, distraction and sensory-friendly study solutions.'),
 ('bts-technology','Student Technology','Devices and accessories that solve real school/study workflow pains.'),
 ('bts-meal-lunch','Meal & Lunch','Practical lunch, hydration and food-transport solutions for school days.'),
 ('bts-transport','School Transport','Daily carrying, commuting, visibility, safety and mobility solutions.'),
 ('bts-university','University','Dorm, commuting, study, organization and technology pains for university students.'),
 ('bts-teachers','Teachers','Classroom organization, teaching aids, ergonomics and productivity solutions for teachers.')
) as x(slug,name,brief)
on conflict(slug) do update set semantic_brief=excluded.semantic_brief,updated_at=now();

create table if not exists intel.product_pain_matches (
  product_id uuid not null references catalog.products(id) on delete cascade,
  pain_cluster_id uuid not null references evidence.semantic_clusters(id) on delete cascade,
  match_score numeric(6,2) not null,
  evidence_confidence numeric(6,5),
  rationale text,
  methodology_version text not null default 'product-pain-rag-v1',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key(product_id,pain_cluster_id)
);
alter table intel.product_pain_matches enable row level security;
create index if not exists product_pain_match_score_idx on intel.product_pain_matches(match_score desc);

create table if not exists intel.product_theme_matches (
  product_id uuid not null references catalog.products(id) on delete cascade,
  theme_id uuid not null references intel.demand_themes(id) on delete cascade,
  relevance_score numeric(6,2) not null,
  seasonal_score numeric(6,2),
  rationale text,
  methodology_version text not null default 'product-theme-rag-v1',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key(product_id,theme_id)
);
alter table intel.product_theme_matches enable row level security;

create table if not exists intel.product_intelligence_snapshots (
  id uuid primary key default gen_random_uuid(),
  product_id uuid not null references catalog.products(id) on delete cascade,
  offer_id uuid not null references catalog.product_offers(id) on delete cascade,
  merchant_id uuid not null references catalog.merchants(id) on delete restrict,
  observed_at timestamptz not null default now(),
  pain_gap_fit_score numeric(6,2),
  merchant_opportunity_score numeric(6,2),
  greek_demand_score numeric(6,2),
  competition_score numeric(6,2),
  seasonal_theme_score numeric(6,2),
  merchant_trust_score numeric(6,2),
  commission_score numeric(6,2),
  discount_score numeric(6,2),
  product_evidence_confidence numeric(6,2),
  dominant_market_penalty numeric(6,2) not null default 0,
  final_opportunity_score numeric(6,2),
  validation_status text not null default 'needs_review' check(validation_status in ('validated','needs_review','rejected')),
  audit_summary text,
  evidence_count integer not null default 0,
  methodology_version text not null default 'product-opportunity-v1',
  metadata jsonb not null default '{}'::jsonb
);
alter table intel.product_intelligence_snapshots enable row level security;
create index if not exists product_intel_product_time_idx on intel.product_intelligence_snapshots(product_id,observed_at desc);
create index if not exists product_intel_rank_idx on intel.product_intelligence_snapshots(final_opportunity_score desc) where validation_status='validated';

create or replace view api.product_opportunities as
with latest as (
  select distinct on (s.product_id) s.*
  from intel.product_intelligence_snapshots s
  order by s.product_id,s.observed_at desc
)
select
  p.id as product_id,p.canonical_title,p.brand_name,p.model_name,p.category,p.subcategory,p.status as product_status,
  o.id as offer_id,o.merchant_id,m.canonical_name as merchant_name,o.effective_price,o.full_price,o.discount_pct,
  o.expected_commission_eur,o.commission_rate_pct,o.flat_commission_eur,o.tracking_url,o.image_url,o.times_bought,
  coalesce(pol.promotion_mode,'eligible') as merchant_promotion_mode,coalesce(pol.dominant_market,false) as dominant_market,
  l.pain_gap_fit_score,l.merchant_opportunity_score,l.greek_demand_score,l.competition_score,l.seasonal_theme_score,
  l.merchant_trust_score,l.commission_score,l.discount_score,l.product_evidence_confidence,l.final_opportunity_score,
  l.validation_status,l.audit_summary,l.evidence_count,l.observed_at,l.methodology_version
from latest l
join catalog.products p on p.id=l.product_id
join catalog.product_offers o on o.id=l.offer_id
join catalog.merchants m on m.id=l.merchant_id
left join catalog.merchant_promotion_policy pol on pol.merchant_id=m.id;

comment on view api.product_opportunities is 'Latest merchant-aware product opportunity ranking. Raw feed records are never exposed/imported wholesale.';
