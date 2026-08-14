create schema if not exists evidence;

create table if not exists evidence.source_links (
  id uuid primary key default gen_random_uuid(),
  entity_type text not null,
  entity_id uuid not null,
  url text not null,
  normalized_domain text,
  source_kind text not null,
  source_name text,
  is_authoritative boolean not null default false,
  confidence numeric not null default 0 check (confidence >= 0 and confidence <= 1),
  validation_status text not null default 'pending' check (validation_status in ('pending','validated','contradicted','rejected','stale')),
  evidence jsonb not null default '{}'::jsonb,
  first_seen_at timestamptz not null default now(),
  last_verified_at timestamptz,
  unique(entity_type, entity_id, url, source_kind)
);

create table if not exists evidence.observations (
  id uuid primary key default gen_random_uuid(),
  entity_type text not null,
  entity_id uuid not null,
  source_kind text not null,
  platform text,
  source_url text,
  source_domain text,
  collector text not null,
  collected_at timestamptz not null default now(),
  title text,
  body text,
  author_label text,
  published_at timestamptz,
  metrics jsonb not null default '{}'::jsonb,
  metadata jsonb not null default '{}'::jsonb,
  confidence numeric not null default 0 check (confidence >= 0 and confidence <= 1),
  validation_status text not null default 'pending' check (validation_status in ('pending','validated','contradicted','rejected','stale')),
  content_hash text not null,
  unique(entity_type, entity_id, source_kind, content_hash)
);

create index if not exists evidence_observations_entity_idx on evidence.observations(entity_type, entity_id, collected_at desc);
create index if not exists evidence_observations_source_idx on evidence.observations(source_kind, platform, collected_at desc);

create table if not exists evidence.semantic_clusters (
  id uuid primary key default gen_random_uuid(),
  entity_type text not null,
  entity_id uuid not null,
  cluster_type text not null check (cluster_type in ('pain','desire','complaint','unmet_need','alternative_request','positive_signal','risk','topic')),
  canonical_text text not null,
  language text not null default 'el+en',
  category text,
  subcategory text,
  evidence_ids uuid[] not null default '{}',
  evidence_count integer not null default 0,
  source_diversity integer not null default 0,
  frequency_score numeric,
  engagement_score numeric,
  demand_score numeric,
  competition_score numeric,
  pain_severity numeric,
  commercial_intent numeric,
  audit_score numeric,
  confidence numeric not null default 0 check (confidence >= 0 and confidence <= 1),
  validation_status text not null default 'pending' check (validation_status in ('pending','validated','contradicted','rejected','stale')),
  embedding vector(1024),
  embedding_model text default 'BAAI/bge-m3',
  methodology_version text not null default 'semantic_cluster_v1',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists semantic_clusters_entity_idx on evidence.semantic_clusters(entity_type, entity_id, cluster_type, validation_status);

create table if not exists evidence.audit_results (
  id uuid primary key default gen_random_uuid(),
  entity_type text not null,
  entity_id uuid not null,
  target_type text not null,
  target_id uuid,
  audited_at timestamptz not null default now(),
  audit_agent text not null default 'skeptic_v1',
  identity_score numeric,
  source_quality_score numeric,
  source_diversity_score numeric,
  contradiction_score numeric,
  taxonomy_score numeric,
  demand_validation_score numeric,
  competition_validation_score numeric,
  pain_validation_score numeric,
  social_validation_score numeric,
  overall_score numeric,
  verdict text not null check (verdict in ('validated','needs_review','rejected')),
  reasons jsonb not null default '[]'::jsonb,
  contradictions jsonb not null default '[]'::jsonb,
  supporting_evidence_ids uuid[] not null default '{}',
  methodology_version text not null default 'audit_skeptic_v1',
  metadata jsonb not null default '{}'::jsonb
);

create table if not exists ops.collection_jobs (
  id uuid primary key default gen_random_uuid(),
  entity_type text not null,
  entity_id uuid not null,
  collection_type text not null,
  status text not null default 'queued' check (status in ('queued','running','completed','failed','cancelled')),
  priority integer not null default 50,
  reason text,
  collector_policy jsonb not null default '{}'::jsonb,
  requested_at timestamptz not null default now(),
  not_before timestamptz not null default now(),
  lease_owner text,
  lease_expires_at timestamptz,
  attempt_count integer not null default 0,
  last_error text,
  completed_at timestamptz,
  dedupe_key text unique,
  payload jsonb not null default '{}'::jsonb
);

alter table evidence.source_links enable row level security;
alter table evidence.observations enable row level security;
alter table evidence.semantic_clusters enable row level security;
alter table evidence.audit_results enable row level security;
alter table ops.collection_jobs enable row level security;

create or replace view public.validated_pain_clusters as
select id, entity_type, entity_id, cluster_type, canonical_text, category, subcategory,
       evidence_count, source_diversity, frequency_score, engagement_score, demand_score,
       competition_score, pain_severity, commercial_intent, audit_score, confidence, updated_at
from evidence.semantic_clusters
where validation_status='validated'
  and cluster_type in ('pain','unmet_need','alternative_request','complaint');
