create table if not exists intel.marketplace_source_state (
  source_network text not null,
  source_partition text not null,
  baseline_completed boolean not null default false,
  source_fingerprint text,
  etag text,
  last_modified text,
  content_length bigint,
  last_checked_at timestamptz,
  last_changed_at timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  primary key (source_network, source_partition)
);

create table if not exists intel.marketplace_product_ledger (
  source_network text not null,
  source_product_id text not null,
  source_record_hash text,
  product_fingerprint text not null,
  merchant_id uuid,
  merchant_program_id uuid,
  external_program_id text,
  seller_id text,
  product_name text,
  price_eur numeric,
  expected_commission_eur numeric,
  first_seen_at timestamptz not null default now(),
  last_seen_at timestamptz not null default now(),
  last_changed_at timestamptz not null default now(),
  last_evaluated_at timestamptz,
  last_quality_decision text,
  metadata jsonb not null default '{}'::jsonb,
  primary key (source_network, source_product_id)
);

create index if not exists marketplace_product_ledger_merchant_idx on intel.marketplace_product_ledger(merchant_id, last_seen_at desc);
create index if not exists marketplace_product_ledger_program_idx on intel.marketplace_product_ledger(external_program_id, last_seen_at desc);
create index if not exists marketplace_product_ledger_seller_idx on intel.marketplace_product_ledger(seller_id, last_seen_at desc);

create table if not exists intel.marketplace_seller_registry (
  source_network text not null default 'aliexpress_affiliate_api',
  seller_id text not null,
  seller_name text,
  seller_url text,
  trust_state text not null default 'discovery' check (trust_state in ('trusted','discovery','blocked')),
  evidence_score numeric not null default 0,
  confidence numeric not null default 0,
  validated_products integer not null default 0,
  rejected_products integer not null default 0,
  seen_products integer not null default 0,
  tracking_successes integer not null default 0,
  last_seen_at timestamptz,
  last_validated_at timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  primary key (source_network, seller_id)
);

comment on table intel.marketplace_source_state is 'Persistent source checkpoints: full baseline once, then delta/merchant-scoped retrieval.';
comment on table intel.marketplace_product_ledger is 'Product fingerprints used to send only new or materially changed products through AFFINITY research/QA.';
comment on table intel.marketplace_seller_registry is 'Evidence-based seller trust; AliExpress product evaluate_rate is not treated as seller trust.';
