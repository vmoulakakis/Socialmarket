-- SocialMarket V2 owns approved content/publishing intent.
-- SocialScheduler is execution-only and may only claim/ack through the OIDC gateway.

create schema if not exists content;
create schema if not exists publish;
revoke all on schema content,publish from anon,authenticated;

create table if not exists content.brand_sites (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  name text not null,
  site_url text,
  positioning text,
  target_audience text,
  primary_cta text,
  content_pillars jsonb not null default '[]'::jsonb,
  active boolean not null default true,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists content.items (
  id uuid primary key default gen_random_uuid(),
  source_key text unique,
  brand_site_id uuid not null references content.brand_sites(id) on delete restrict,
  merchant_id uuid references catalog.merchants(id) on delete set null,
  title text not null,
  angle text,
  core_copy text,
  cta text,
  tracking_url text,
  media_url text,
  status text not null default 'draft' check (status in ('draft','approved','rejected','queued','completed','cancelled')),
  scheduled_from timestamptz,
  approved_at timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists publish.outbox (
  id uuid primary key default gen_random_uuid(),
  content_item_id uuid not null references content.items(id) on delete cascade,
  platform text not null check (platform in ('facebook','instagram','tiktok')),
  caption text not null,
  hashtags text[] not null default '{}'::text[],
  format text not null default 'post',
  media_url text,
  tracking_url text,
  scheduled_for timestamptz not null,
  priority smallint not null default 50,
  status text not null default 'approved' check (status in ('approved','leased','scheduled','published','failed','cancelled')),
  claimed_by text,
  claimed_at timestamptz,
  lease_expires_at timestamptz,
  external_post_id text,
  external_permalink text,
  published_at timestamptz,
  attempt_count integer not null default 0,
  last_error text,
  executor_metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(content_item_id,platform)
);

create index if not exists content_items_brand_status_idx on content.items(brand_site_id,status,created_at desc);
create index if not exists content_items_merchant_idx on content.items(merchant_id,created_at desc) where merchant_id is not null;
create index if not exists publish_outbox_claim_idx on publish.outbox(status,scheduled_for,priority desc,created_at);
create index if not exists publish_outbox_external_idx on publish.outbox(external_post_id) where external_post_id is not null;

create table if not exists ops.executor_controls (
  executor_key text primary key,
  enabled boolean not null default false,
  reason text,
  updated_at timestamptz not null default now(),
  metadata jsonb not null default '{}'::jsonb
);

insert into ops.executor_controls(executor_key,enabled,reason)
values('socialscheduler',false,'awaiting_v2_outbox_import_and_dry_run')
on conflict(executor_key) do update set enabled=excluded.enabled,reason=excluded.reason,updated_at=now();

insert into content.brand_sites(slug,name,site_url,positioning,primary_cta,content_pillars,metadata) values
('coffeego-ai','CoffeeGo AI','https://coffeego-ai.vmoulakakis.chatgpt.site/','AI guide for portable espresso and coffee setup selection','Smart Match / ask Elena','["portable espresso education","setup comparison","coffee economics","AI advisor","honest buying guidance"]'::jsonb,'{"legacy_scheduler_brand":"CoffeeGo AI"}'::jsonb),
('cabinpilot-travel','CabinPilot Travel','https://cabinpilot-travel.vmoulakakis.chatgpt.site/','Cabin luggage and airline-rule decision support','Check cabin fit before travel','["airline rules","luggage dimensions","packing","fee avoidance","travel stress reduction"]'::jsonb,'{"legacy_scheduler_brand":"CabinPilot Travel"}'::jsonb),
('cabinpilot-smart-savings','CabinPilot Smart Savings',null,'Crew and frequent-traveller savings/value stream','Compare real annual travel benefit','["crew benefits","travel savings","benefit calculators","frequent traveller value"]'::jsonb,'{"legacy_scheduler_brand":"CabinPilot Smart Savings"}'::jsonb),
('lyseis-pou-axizoun','Λύσεις που Αξίζουν / Biz Box Solver','https://lyseis-pou-axizoun.vmoulakakis.chatgpt.site/','Practical value solutions, tools and offers without hype','See if the solution is worth it','["practical savings","business tools","ecommerce","pain-point solving","worth-it analysis"]'::jsonb,'{"legacy_scheduler_brand":"Lyseis / Biz Box Solver"}'::jsonb),
('travel-ai','Travel AI / GreekVibes','https://travel-ai-navy-eight.vercel.app/','Greek AI travel discovery and advisor','Find the next Greek escape','["destination discovery","seasonal Greece","weekend escapes","travel preferences","offers and ideas"]'::jsonb,'{"legacy_scheduler_brand":"Travel AI / GreekVibes"}'::jsonb),
('red-raven-eyewear','Red Raven Eyewear','https://red-raven-eyewear-handcrafted-sunglasses-122630476133.europe-west1.run.app/','Eyewear and handcrafted sunglasses brand stream','Explore verified eyewear','["eyewear education","style","verified product features","seasonal sun protection"]'::jsonb,'{"legacy_scheduler_brand":"Red Raven Eyewear"}'::jsonb)
on conflict(slug) do update set name=excluded.name,site_url=excluded.site_url,positioning=excluded.positioning,primary_cta=excluded.primary_cta,content_pillars=excluded.content_pillars,metadata=content.brand_sites.metadata||excluded.metadata,active=true,updated_at=now();

-- Core queue/claim/ack/import functions are applied in Supabase migration
-- `publishing_source_of_truth_v2` and are intentionally service-role only.
-- See MIGRATION_MANIFEST.md for the authoritative applied migration chain.
