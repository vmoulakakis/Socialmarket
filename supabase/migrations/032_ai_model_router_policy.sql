-- Canonical SocialMarket AI model-routing policy.
-- Additive only: does not modify merchant/product intelligence ownership.

create table if not exists ops.ai_model_policy (
  task_type text primary key,
  deterministic_first boolean not null default true,
  local_open_weight_enabled boolean not null default false,
  local_endpoint text,
  local_model text,
  github_models_enabled boolean not null default true,
  deepseek_enabled boolean not null default true,
  deepseek_model text not null default 'deepseek-v4-pro',
  deepseek_thinking boolean not null default true,
  openai_fallback_enabled boolean not null default false,
  openai_model text,
  openai_reasoning_effort text not null default 'low' check (openai_reasoning_effort in ('none','minimal','low','medium','high','xhigh')),
  openai_max_output_tokens integer not null default 1000 check (openai_max_output_tokens between 100 and 4000),
  min_paid_complexity numeric(5,4) not null default 0.9200 check (min_paid_complexity between 0 and 1),
  monthly_paid_call_cap integer not null default 100 check (monthly_paid_call_cap between 0 and 10000),
  openai_daily_call_cap integer not null default 10 check (openai_daily_call_cap between 0 and 1000),
  notes text,
  updated_at timestamptz not null default now()
);

create table if not exists ops.ai_usage_daily (
  usage_day date not null default current_date,
  provider text not null,
  model_name text not null,
  task_type text not null,
  calls integer not null default 0,
  input_tokens bigint not null default 0,
  output_tokens bigint not null default 0,
  estimated_cost_usd numeric(14,6) not null default 0,
  updated_at timestamptz not null default now(),
  primary key (usage_day,provider,model_name,task_type)
);

create table if not exists ops.ai_remote_request_log (
  id uuid primary key default gen_random_uuid(),
  task_id text,
  task_type text not null,
  provider text not null check (provider in ('deepseek','openai')),
  model_name text not null,
  complexity_score numeric(5,4) not null,
  escalation_reason text not null,
  status text not null default 'reserved' check (status in ('reserved','completed','failed','cancelled')),
  input_tokens bigint not null default 0,
  output_tokens bigint not null default 0,
  estimated_cost_usd numeric(14,6) not null default 0,
  created_at timestamptz not null default now(),
  completed_at timestamptz
);

create index if not exists ai_remote_request_log_created_idx
  on ops.ai_remote_request_log(created_at desc,provider,task_type);

insert into ops.ai_model_policy(
  task_type,deterministic_first,local_open_weight_enabled,github_models_enabled,
  deepseek_enabled,deepseek_model,deepseek_thinking,openai_fallback_enabled,
  openai_model,openai_reasoning_effort,openai_max_output_tokens,min_paid_complexity,
  monthly_paid_call_cap,openai_daily_call_cap,notes
) values
  ('product_research',true,false,true,true,'deepseek-v4-pro',true,false,null,'low',1000,0.92,100,10,
   'Deterministic/RAG first. Free/open-weight may preclassify. DeepSeek is paid reasoning tier. OpenAI is disabled until explicitly configured.'),
  ('product_audit',true,false,true,true,'deepseek-v4-pro',true,false,null,'low',1000,0.92,100,10,
   'Independent skeptic audit. Never allow a cheaper model to fabricate evidence or bypass deterministic gates.'),
  ('merchant_research',true,false,true,true,'deepseek-v4-pro',true,false,null,'low',1000,0.92,100,10,
   'Preserve existing merchant evidence pipeline; model routing is additive.'),
  ('generic_semantic',true,false,true,false,'deepseek-v4-pro',true,false,null,'low',800,0.95,100,5,
   'Prefer deterministic/vector/free model path; no paid call by default.')
on conflict(task_type) do nothing;

alter table ops.ai_model_policy enable row level security;
alter table ops.ai_usage_daily enable row level security;
alter table ops.ai_remote_request_log enable row level security;

revoke all on ops.ai_model_policy from anon, authenticated;
revoke all on ops.ai_usage_daily from anon, authenticated;
revoke all on ops.ai_remote_request_log from anon, authenticated;

grant select,insert,update on ops.ai_model_policy to service_role;
grant select,insert,update on ops.ai_usage_daily to service_role;
grant select,insert,update on ops.ai_remote_request_log to service_role;

create or replace function ops.reserve_remote_model_request(
  p_task_id text,
  p_task_type text,
  p_provider text,
  p_model_name text,
  p_complexity_score numeric,
  p_escalation_reason text
) returns uuid
language plpgsql
security definer
set search_path=''
as $$
declare
  pol ops.ai_model_policy;
  used_month integer;
  used_openai_today integer;
  rid uuid;
begin
  if p_provider not in ('deepseek','openai') then
    raise exception 'unsupported paid provider';
  end if;
  if nullif(btrim(p_escalation_reason),'') is null then
    raise exception 'escalation reason required';
  end if;

  select * into pol from ops.ai_model_policy where task_type=p_task_type;
  if not found then raise exception 'unknown task type'; end if;
  if p_complexity_score < pol.min_paid_complexity then raise exception 'complexity below paid threshold'; end if;
  if p_provider='deepseek' and not pol.deepseek_enabled then raise exception 'deepseek disabled for task'; end if;
  if p_provider='openai' and not pol.openai_fallback_enabled then raise exception 'openai fallback disabled for task'; end if;

  select count(*) into used_month
    from ops.ai_remote_request_log
   where created_at >= date_trunc('month',now())
     and status in ('reserved','completed');
  if used_month >= pol.monthly_paid_call_cap then raise exception 'monthly paid model cap reached'; end if;

  if p_provider='openai' then
    select count(*) into used_openai_today
      from ops.ai_remote_request_log
     where provider='openai' and created_at >= current_date
       and status in ('reserved','completed');
    if used_openai_today >= pol.openai_daily_call_cap then raise exception 'openai daily cap reached'; end if;
  end if;

  insert into ops.ai_remote_request_log(task_id,task_type,provider,model_name,complexity_score,escalation_reason)
  values(p_task_id,p_task_type,p_provider,p_model_name,p_complexity_score,p_escalation_reason)
  returning id into rid;
  return rid;
end;
$$;

create or replace function ops.complete_remote_model_request(
  p_request_id uuid,
  p_status text,
  p_input_tokens bigint default 0,
  p_output_tokens bigint default 0,
  p_estimated_cost_usd numeric default 0
) returns void
language plpgsql
security definer
set search_path=''
as $$
declare r ops.ai_remote_request_log;
begin
  if p_status not in ('completed','failed','cancelled') then raise exception 'invalid completion status'; end if;
  update ops.ai_remote_request_log
     set status=p_status,input_tokens=greatest(0,p_input_tokens),output_tokens=greatest(0,p_output_tokens),
         estimated_cost_usd=greatest(0,p_estimated_cost_usd),completed_at=now()
   where id=p_request_id returning * into r;
  if not found then raise exception 'request not found'; end if;

  insert into ops.ai_usage_daily(usage_day,provider,model_name,task_type,calls,input_tokens,output_tokens,estimated_cost_usd)
  values(current_date,r.provider,r.model_name,r.task_type,1,greatest(0,p_input_tokens),greatest(0,p_output_tokens),greatest(0,p_estimated_cost_usd))
  on conflict(usage_day,provider,model_name,task_type) do update set
    calls=ops.ai_usage_daily.calls+1,
    input_tokens=ops.ai_usage_daily.input_tokens+excluded.input_tokens,
    output_tokens=ops.ai_usage_daily.output_tokens+excluded.output_tokens,
    estimated_cost_usd=ops.ai_usage_daily.estimated_cost_usd+excluded.estimated_cost_usd,
    updated_at=now();
end;
$$;

-- Compatibility wrapper for the pre-existing Python model_router.py REST RPC contract.
create or replace function public.reserve_remote_model_request(
  p_task_id text default null,
  p_provider text default null,
  p_model_name text default null,
  p_complexity_score numeric default null,
  p_escalation_reason text default null,
  p_task_type text default 'generic_semantic'
) returns uuid
language sql
security definer
set search_path=''
as $$
  select ops.reserve_remote_model_request(p_task_id,p_task_type,p_provider,p_model_name,p_complexity_score,p_escalation_reason);
$$;

revoke all on function public.reserve_remote_model_request(text,text,text,numeric,text,text) from public, anon, authenticated;
grant execute on function public.reserve_remote_model_request(text,text,text,numeric,text,text) to service_role;
