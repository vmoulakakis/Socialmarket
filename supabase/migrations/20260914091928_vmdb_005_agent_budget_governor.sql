create table if not exists public.agent_budget_policies (
  metric text primary key,
  daily_limit numeric not null check (daily_limit > 0),
  monthly_limit numeric,
  soft_threshold numeric not null default 0.80 check (soft_threshold > 0 and soft_threshold <= 1),
  enabled boolean not null default true,
  notes text,
  updated_at timestamptz not null default now()
);
create table if not exists public.agent_usage_ledger (
  id bigint generated always as identity primary key,
  run_id text,
  actor text not null default 'unknown', provider text, model text,
  metric text not null references public.agent_budget_policies(metric),
  quantity numeric not null check (quantity >= 0),
  status text not null default 'committed' check (status in ('reserved','committed','released')),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists agent_usage_metric_created_idx on public.agent_usage_ledger(metric,created_at desc);
create index if not exists agent_usage_run_idx on public.agent_usage_ledger(run_id) where run_id is not null;
alter table public.agent_budget_policies enable row level security;
alter table public.agent_usage_ledger enable row level security;
revoke all on public.agent_budget_policies from public,anon,authenticated;
revoke all on public.agent_usage_ledger from public,anon,authenticated;
grant select,insert,update,delete on public.agent_budget_policies to service_role;
grant select,insert,update on public.agent_usage_ledger to service_role;
grant usage,select on sequence public.agent_usage_ledger_id_seq to service_role;
insert into public.agent_budget_policies(metric,daily_limit,monthly_limit,soft_threshold,notes) values
 ('llm_output_tokens',150000,2500000,0.80,'Internal safety budget; deliberately below provider ceilings and adjustable.'),
 ('remote_llm_calls',120,2500,0.80,'All paid/free remote LLM calls combined.'),
 ('premium_llm_calls',5,100,0.60,'Explicit premium escalations only.'),
 ('github_worker_runs',24,500,0.80,'Bounded autonomous worker executions.'),
 ('web_research_queries',250,5000,0.80,'Bounded discovery/research calls.'),
 ('orchestrator_runs',500,10000,0.80,'Protects Vercel/API runtime from runaway loops.')
on conflict(metric) do update set daily_limit=excluded.daily_limit,monthly_limit=excluded.monthly_limit,soft_threshold=excluded.soft_threshold,notes=excluded.notes,updated_at=now();

create or replace function public.reserve_agent_budget(p_metric text,p_quantity numeric,p_run_id text default null,p_actor text default 'unknown',p_provider text default null,p_model text default null,p_metadata jsonb default '{}'::jsonb) returns jsonb language plpgsql security definer set search_path=public,pg_temp as $$ declare pol public.agent_budget_policies%rowtype; used_day numeric; used_month numeric; reservation_id bigint; begin if p_quantity is null or p_quantity<=0 then raise exception 'quantity_must_be_positive'; end if; perform pg_advisory_xact_lock(hashtext('agent-budget:'||p_metric)); select * into pol from public.agent_budget_policies where metric=p_metric and enabled=true; if not found then raise exception 'budget_metric_not_enabled:%',p_metric; end if; select coalesce(sum(quantity),0) into used_day from public.agent_usage_ledger where metric=p_metric and status in ('reserved','committed') and created_at>=date_trunc('day',now()); select coalesce(sum(quantity),0) into used_month from public.agent_usage_ledger where metric=p_metric and status in ('reserved','committed') and created_at>=date_trunc('month',now()); if used_day+p_quantity>pol.daily_limit then return jsonb_build_object('allowed',false,'reason','daily_limit','used',used_day,'limit',pol.daily_limit); end if; if pol.monthly_limit is not null and used_month+p_quantity>pol.monthly_limit then return jsonb_build_object('allowed',false,'reason','monthly_limit','used',used_month,'limit',pol.monthly_limit); end if; insert into public.agent_usage_ledger(run_id,actor,provider,model,metric,quantity,status,metadata) values(p_run_id,coalesce(p_actor,'unknown'),p_provider,p_model,p_metric,p_quantity,'reserved',coalesce(p_metadata,'{}'::jsonb)) returning id into reservation_id; return jsonb_build_object('allowed',true,'reservation_id',reservation_id,'used_day_before',used_day,'daily_limit',pol.daily_limit,'soft',used_day+p_quantity>=pol.daily_limit*pol.soft_threshold); end $$;
create or replace function public.finalize_agent_budget(p_reservation_id bigint,p_actual_quantity numeric,p_metadata jsonb default '{}'::jsonb) returns boolean language plpgsql security definer set search_path=public,pg_temp as $$ begin update public.agent_usage_ledger set quantity=greatest(coalesce(p_actual_quantity,0),0),status='committed',metadata=metadata||coalesce(p_metadata,'{}'::jsonb) where id=p_reservation_id and status='reserved'; return found; end $$;
create or replace function public.release_agent_budget(p_reservation_id bigint) returns boolean language plpgsql security definer set search_path=public,pg_temp as $$ begin update public.agent_usage_ledger set status='released' where id=p_reservation_id and status='reserved'; return found; end $$;
revoke all on function public.reserve_agent_budget(text,numeric,text,text,text,text,jsonb) from public,anon,authenticated;
revoke all on function public.finalize_agent_budget(bigint,numeric,jsonb) from public,anon,authenticated;
revoke all on function public.release_agent_budget(bigint) from public,anon,authenticated;
grant execute on function public.reserve_agent_budget(text,numeric,text,text,text,text,jsonb) to service_role;
grant execute on function public.finalize_agent_budget(bigint,numeric,jsonb) to service_role;
grant execute on function public.release_agent_budget(bigint) to service_role;
