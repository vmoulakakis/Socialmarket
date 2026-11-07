-- SocialMarket AI Shopping Assistant: rate limits and ring-fenced LLM budget.
-- No modification to existing catalog, merchant identity, network links or AI pipelines.
create table if not exists public.shopper_ai_daily_gate (
  actor_hash text not null check(actor_hash ~ '^[0-9a-f]{64}$'),
  day date not null default (now() at time zone 'UTC')::date,
  calls integer not null default 0 check(calls >= 0),
  updated_at timestamptz not null default now(),
  primary key (actor_hash, day)
);
alter table public.shopper_ai_daily_gate enable row level security;
revoke all on public.shopper_ai_daily_gate from public, anon, authenticated;
grant select, insert, update on public.shopper_ai_daily_gate to service_role;

create or replace function public.shopper_take_daily_slot(
  p_actor_hash text, p_limit integer default 3
) returns boolean language plpgsql security invoker
set search_path = public, pg_temp
as $$
declare v_hits integer;
begin
  if p_actor_hash is null or p_actor_hash !~ '^[0-9a-f]{64}$' or
     p_limit is null or p_limit < 1 or p_limit > 5 then
    return false;
  end if;

  insert into public.shopper_ai_daily_gate(actor_hash,day,calls)
  values (p_actor_hash,(now() at time zone 'UTC')::date,1)
  on conflict(actor_hash,day) do update
    set calls=public.shopper_ai_daily_gate.calls+1,updated_at=now()
    where public.shopper_ai_daily_gate.calls < p_limit
  returning calls into v_hits;
  return v_hits is not null;
end;
$$;
revoke all on function public.shopper_take_daily_slot(text,integer) from PUBLIC, anon, authenticated;
grant execute on function public.shopper_take_daily_slot(text,integer) to service_role;

insert into public.agent_budget_policies
(metric,daily_limit,monthly_limit,soft_threshold,enabled,notes)
values
('shopper_llm_calls',12,240,0.75,true,'Ring-fenced max AI model calls for shopper runtime; requires owner feature gate, strict source evidence and existing global budget')
on conflict (metric) do nothing;
