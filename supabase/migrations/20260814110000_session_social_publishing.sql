create extension if not exists pgcrypto;

create table if not exists public.social_session_accounts (
  id uuid primary key default gen_random_uuid(),
  platform text not null check (platform in ('instagram','tiktok','facebook','linkedin')),
  account_label text not null,
  account_handle text,
  status text not null default 'disconnected' check (status in ('disconnected','paired','connected','challenge','error','disabled')),
  publish_mode text not null default 'browser_session' check (publish_mode in ('browser_session','private_session','assisted','existing_api')),
  auto_publish boolean not null default false,
  capabilities jsonb not null default '{}'::jsonb,
  worker_last_seen_at timestamptz,
  last_verified_at timestamptz,
  last_error text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(platform, account_label)
);

create table if not exists public.social_session_vault (
  account_id uuid primary key references public.social_session_accounts(id) on delete cascade,
  cipher_version text not null default 'fernet-v1',
  encrypted_state text not null,
  state_fingerprint text,
  updated_at timestamptz not null default now()
);

create table if not exists public.social_publish_jobs (
  id uuid primary key default gen_random_uuid(),
  post_id uuid,
  account_id uuid references public.social_session_accounts(id) on delete set null,
  platform text not null check (platform in ('instagram','tiktok','facebook','linkedin')),
  publish_mode text not null default 'browser_session' check (publish_mode in ('browser_session','private_session','assisted','existing_api')),
  status text not null default 'queued' check (status in ('queued','claimed','publishing','assisted','published','failed','blocked','cancelled')),
  scheduled_at timestamptz not null default now(),
  payload jsonb not null default '{}'::jsonb,
  idempotency_key text not null,
  attempts integer not null default 0,
  claimed_by text,
  claimed_at timestamptz,
  lease_until timestamptz,
  published_at timestamptz,
  external_permalink text,
  last_error text,
  result jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(idempotency_key)
);

create index if not exists idx_social_publish_jobs_due
  on public.social_publish_jobs(status, scheduled_at)
  where status in ('queued','claimed');
create index if not exists idx_social_publish_jobs_platform on public.social_publish_jobs(platform, created_at desc);
create index if not exists idx_social_session_accounts_status on public.social_session_accounts(platform, status);

-- Add the foreign key only when the existing scheduler table is present.
do $$
begin
  if to_regclass('public.social_posts') is not null and not exists (
    select 1 from pg_constraint where conname='social_publish_jobs_post_id_fkey'
  ) then
    alter table public.social_publish_jobs
      add constraint social_publish_jobs_post_id_fkey
      foreign key (post_id) references public.social_posts(id) on delete set null;
  end if;
end $$;

alter table public.social_session_accounts enable row level security;
alter table public.social_session_vault enable row level security;
alter table public.social_publish_jobs enable row level security;

drop policy if exists social_session_accounts_admin on public.social_session_accounts;
create policy social_session_accounts_admin on public.social_session_accounts
  for all to authenticated using (true) with check (true);

drop policy if exists social_publish_jobs_admin on public.social_publish_jobs;
create policy social_publish_jobs_admin on public.social_publish_jobs
  for all to authenticated using (true) with check (true);

-- Raw encrypted session material is never readable by normal authenticated clients.
-- The service-role worker bypasses RLS.

create or replace function public.claim_social_publish_jobs(
  p_worker_id text,
  p_limit integer default 5,
  p_lease_seconds integer default 300
)
returns setof public.social_publish_jobs
language plpgsql
security definer
set search_path = public
as $$
begin
  return query
  with candidates as (
    select j.id
    from public.social_publish_jobs j
    where (
      j.status='queued'
      or (j.status='claimed' and coalesce(j.lease_until, now() - interval '1 second') < now())
    )
      and j.scheduled_at <= now()
    order by j.scheduled_at asc, j.created_at asc
    for update skip locked
    limit greatest(1, least(coalesce(p_limit,5),20))
  )
  update public.social_publish_jobs j
  set status='claimed',
      claimed_by=p_worker_id,
      claimed_at=now(),
      lease_until=now() + make_interval(secs => greatest(60, least(coalesce(p_lease_seconds,300),1800))),
      attempts=j.attempts+1,
      updated_at=now()
  from candidates c
  where j.id=c.id
  returning j.*;
end;
$$;

revoke all on function public.claim_social_publish_jobs(text,integer,integer) from public, anon, authenticated;
grant execute on function public.claim_social_publish_jobs(text,integer,integer) to service_role;

create or replace function public.social_session_worker_heartbeat(
  p_account_id uuid,
  p_status text default 'connected',
  p_error text default null
)
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  update public.social_session_accounts
     set worker_last_seen_at=now(),
         status=case when p_status in ('paired','connected','challenge','error','disabled','disconnected') then p_status else status end,
         last_error=p_error,
         updated_at=now()
   where id=p_account_id;
end;
$$;

revoke all on function public.social_session_worker_heartbeat(uuid,text,text) from public, anon, authenticated;
grant execute on function public.social_session_worker_heartbeat(uuid,text,text) to service_role;
