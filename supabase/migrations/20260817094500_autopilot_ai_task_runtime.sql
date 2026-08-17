begin;

create table if not exists ops.ai_task_cache (
  cache_key text primary key,
  task_type text not null,
  input_hash text not null,
  contract_hash text not null,
  output jsonb not null,
  output_hash text not null,
  executor text not null,
  tier smallint not null check (tier >= 0 and tier <= 9),
  route text,
  model text,
  created_at timestamptz not null default now(),
  last_used_at timestamptz not null default now(),
  hit_count bigint not null default 0 check (hit_count >= 0)
);

create index if not exists ai_task_cache_task_type_idx
  on ops.ai_task_cache (task_type, created_at desc);

create index if not exists ai_task_cache_input_contract_idx
  on ops.ai_task_cache (input_hash, contract_hash);

create table if not exists ops.ai_task_attempts (
  id bigint generated always as identity primary key,
  task_type text not null,
  input_hash text not null,
  contract_hash text not null,
  executor text not null,
  tier smallint not null check (tier >= 0 and tier <= 9),
  status text not null check (status in ('ok','not_applicable','invalid','unavailable','error','safe_hold','cache_hit')),
  route text,
  model text,
  latency_ms integer not null default 0 check (latency_ms >= 0),
  output_hash text,
  error text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists ai_task_attempts_task_time_idx
  on ops.ai_task_attempts (task_type, created_at desc);

create index if not exists ai_task_attempts_status_time_idx
  on ops.ai_task_attempts (status, created_at desc);

create index if not exists ai_task_attempts_input_contract_idx
  on ops.ai_task_attempts (input_hash, contract_hash, created_at desc);

comment on table ops.ai_task_cache is
  'Immutable-hash AI task result cache. Stores bounded structured outputs only; raw evidence payloads are intentionally excluded.';

comment on table ops.ai_task_attempts is
  'Provider-neutral AI task execution telemetry. Stores hashes, routing, latency and validation outcomes; never raw prompt/evidence payloads.';

revoke all on table ops.ai_task_cache from anon, authenticated;
revoke all on table ops.ai_task_attempts from anon, authenticated;

grant select, insert, update, delete on table ops.ai_task_cache to service_role;
grant select, insert on table ops.ai_task_attempts to service_role;
grant usage, select on sequence ops.ai_task_attempts_id_seq to service_role;

commit;
