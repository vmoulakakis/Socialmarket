-- VMDB 020: unified SocialMarket admin control center.
-- Live canonical migration applied to VMDB gqpbskssrvpfjtujwezc on 2026-09-18.
-- Provides admin-only snapshot/update RPCs plus an immutable configuration audit trail.

create table if not exists public.admin_configuration_audit (
  id bigint generated always as identity primary key,
  actor_email text not null,
  domain text not null,
  config_key text not null,
  before_value jsonb,
  after_value jsonb,
  created_at timestamptz not null default now()
);
create index if not exists admin_configuration_audit_created_idx on public.admin_configuration_audit(created_at desc);
alter table public.admin_configuration_audit enable row level security;
revoke all on public.admin_configuration_audit from public,anon,authenticated;
grant select on public.admin_configuration_audit to authenticated;
create policy admin_configuration_audit_admin_select on public.admin_configuration_audit
for select to authenticated using (private.is_admin());

-- Canonical DDL for the RPC bodies is maintained in the live VMDB migration ledger.
-- Git history intentionally records the contract and security boundary here; use
-- Supabase migration history/version 020 for the exact applied function definitions.
