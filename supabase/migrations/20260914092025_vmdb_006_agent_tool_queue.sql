create table if not exists public.agent_tool_tasks (
  id uuid primary key default gen_random_uuid(), run_id text not null, step_id text not null,
  capability text not null, target_site_id text, target_repo text,
  payload jsonb not null default '{}'::jsonb,
  state text not null default 'queued' check (state in ('queued','running','succeeded','failed','cancelled')),
  priority smallint not null default 50 check (priority between 0 and 100),
  attempt_count integer not null default 0, max_attempts integer not null default 2 check (max_attempts between 1 and 5),
  worker_id text, output jsonb, error text,
  created_at timestamptz not null default now(), claimed_at timestamptz, completed_at timestamptz, updated_at timestamptz not null default now(),
  unique(run_id,step_id)
);
create index if not exists agent_tool_tasks_queue_idx on public.agent_tool_tasks(state,priority desc,created_at) where state='queued';
create index if not exists agent_tool_tasks_run_idx on public.agent_tool_tasks(run_id,created_at);
alter table public.agent_tool_tasks enable row level security;
revoke all on public.agent_tool_tasks from public,anon,authenticated;
grant select,insert,update on public.agent_tool_tasks to authenticated;
grant select,insert,update,delete on public.agent_tool_tasks to service_role;
create policy agent_tool_tasks_admin_select on public.agent_tool_tasks for select to authenticated using (public.is_admin());
create policy agent_tool_tasks_admin_insert on public.agent_tool_tasks for insert to authenticated with check (public.is_admin());
create policy agent_tool_tasks_admin_update on public.agent_tool_tasks for update to authenticated using (public.is_admin()) with check (public.is_admin());

grant select,insert,update on public.orchestrator_runs to authenticated;
grant select,insert,update on public.orchestrator_steps to authenticated;
grant select on public.site_registry to authenticated;
create policy orchestrator_runs_admin_all on public.orchestrator_runs for all to authenticated using (public.is_admin()) with check (public.is_admin());
create policy orchestrator_steps_admin_all on public.orchestrator_steps for all to authenticated using (public.is_admin()) with check (public.is_admin());
create policy site_registry_admin_select on public.site_registry for select to authenticated using (public.is_admin());

create or replace function public.claim_agent_tool_task(p_worker_id text) returns jsonb language plpgsql security definer set search_path=public,pg_temp as $$ declare t public.agent_tool_tasks%rowtype; begin select * into t from public.agent_tool_tasks where state='queued' and attempt_count<max_attempts order by priority desc,created_at for update skip locked limit 1; if not found then return null; end if; update public.agent_tool_tasks set state='running',worker_id=p_worker_id,attempt_count=attempt_count+1,claimed_at=now(),updated_at=now() where id=t.id returning * into t; return to_jsonb(t); end $$;
create or replace function public.finish_agent_tool_task(p_task_id uuid,p_output jsonb default '{}'::jsonb) returns boolean language plpgsql security definer set search_path=public,pg_temp as $$ begin update public.agent_tool_tasks set state='succeeded',output=coalesce(p_output,'{}'::jsonb),error=null,completed_at=now(),updated_at=now() where id=p_task_id and state='running'; return found; end $$;
create or replace function public.fail_agent_tool_task(p_task_id uuid,p_error text,p_retry boolean default false) returns boolean language plpgsql security definer set search_path=public,pg_temp as $$ declare attempts int; maxa int; begin select attempt_count,max_attempts into attempts,maxa from public.agent_tool_tasks where id=p_task_id for update; if not found then return false; end if; update public.agent_tool_tasks set state=case when p_retry and attempts<maxa then 'queued' else 'failed' end,error=left(coalesce(p_error,'unknown'),4000),worker_id=case when p_retry and attempts<maxa then null else worker_id end,claimed_at=case when p_retry and attempts<maxa then null else claimed_at end,completed_at=case when p_retry and attempts<maxa then null else now() end,updated_at=now() where id=p_task_id; return true; end $$;
revoke all on function public.claim_agent_tool_task(text) from public,anon,authenticated;
revoke all on function public.finish_agent_tool_task(uuid,jsonb) from public,anon,authenticated;
revoke all on function public.fail_agent_tool_task(uuid,text,boolean) from public,anon,authenticated;
grant execute on function public.claim_agent_tool_task(text) to service_role;
grant execute on function public.finish_agent_tool_task(uuid,jsonb) to service_role;
grant execute on function public.fail_agent_tool_task(uuid,text,boolean) to service_role;
