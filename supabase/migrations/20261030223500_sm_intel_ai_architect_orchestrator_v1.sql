-- SocialMarket AI Architect Orchestrator v1: merchant-program reconciliation + auditable bounded learning agents.
-- No updates to public merchants, legacy ingestion, approval flags or scheduled marketing.
create table if not exists sm_intel.merchant_program_directory (
 id uuid primary key default gen_random_uuid(),
 source text not null default 'linkwise',
 publisher_key text not null default 'CD104',
 source_record_key text not null,
 program_name text not null,
 linkwise_program_id text,
 merchant_profile_id uuid references public.merchant_profiles(id) on delete set null,
 source_imported_at timestamptz,
 source_active_since date,
 terms_valid_from timestamptz,
 terms_valid_to timestamptz,
 approved_for_publisher boolean,
 program_status text not null default 'unresolved'
  check(program_status in ('unresolved','mapped','approved','rejected','expired','suspended')),
 identity_confidence numeric(5,4) not null default 0 check(identity_confidence between 0 and 1),
 mapping_evidence jsonb not null default '{}'::jsonb,
 raw_commission_record jsonb not null default '{}'::jsonb,
 last_verified_at timestamptz,
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now(),
 unique(source,publisher_key,source_record_key),
 check (terms_valid_to is null or (terms_valid_from is not null and terms_valid_to>terms_valid_from)),
 check(program_status<>'approved' or (approved_for_publisher is true and last_verified_at is not null and linkwise_program_id is not null))
);
create index if not exists sm_program_status_idx on sm_intel.merchant_program_directory(program_status,linkwise_program_id);
create index if not exists sm_program_id_idx on sm_intel.merchant_program_directory(linkwise_program_id) where linkwise_program_id is not null;

create table if not exists sm_intel.agent_objectives (
 id uuid primary key default gen_random_uuid(),
 objective_key text not null unique,
 purpose text not null,
 success_criteria jsonb not null default '{}'::jsonb,
 hard_constraints jsonb not null default '{}'::jsonb,
 status text not null default 'active' check(status in ('active','paused','retired')),
 version text not null default 'v1',
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now()
);
create table if not exists sm_intel.agent_tasks (
 id uuid primary key default gen_random_uuid(),
 objective_key text not null references sm_intel.agent_objectives(objective_key) on delete restrict,
 agent_role text not null check(agent_role in ('merchant_identity','commission_verifier','market_research','product_analyst','graphrag_librarian','commercial_skeptic','ai_architect')),
 subject_kind text not null check(subject_kind in ('program','product','pain_gap','merchant','graph','portfolio')),
 subject_key text not null,
 market_code text not null default 'GR' check(market_code='GR'),
 priority integer not null default 50 check(priority between 0 and 100),
 state text not null default 'queued' check(state in ('queued','claimed','candidate','needs_evidence','reviewed','blocked','failed')),
 attempts integer not null default 0 check(attempts>=0),
 claimed_by text,
 claimed_at timestamptz,
 next_attempt_at timestamptz not null default now(),
 input_refs jsonb not null default '{}'::jsonb,
 findings jsonb not null default '{}'::jsonb,
 evidence_refs jsonb not null default '[]'::jsonb,
 uncertainty jsonb not null default '{}'::jsonb,
 output_version text not null default 'v1',
 last_run_id uuid,
 last_evaluated_at timestamptz,
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now(),
 unique(objective_key,agent_role,subject_kind,subject_key,output_version),
 check(state not in ('candidate','reviewed') or jsonb_typeof(findings)='object')
);
create index if not exists sm_agent_tasks_dispatch on sm_intel.agent_tasks(state,next_attempt_at,priority desc,created_at) where state in ('queued','claimed','needs_evidence');
create index if not exists sm_agent_tasks_subject on sm_intel.agent_tasks(subject_kind,subject_key);
create table if not exists sm_intel.agent_runs (
 id uuid primary key default gen_random_uuid(),
 objective_key text references sm_intel.agent_objectives(objective_key),
 requested_by text not null,
 runtime_mode text not null check(runtime_mode in ('deterministic','hybrid_ai','research_agent')),
 state text not null default 'running' check(state in ('running','completed','partial','failed','stopped')),
 max_tasks integer not null default 3 check(max_tasks between 1 and 20),
 max_model_calls integer not null default 3 check(max_model_calls between 0 and 10),
 model_calls integer not null default 0 check(model_calls>=0),
 processed_tasks integer not null default 0 check(processed_tasks>=0),
 outcome jsonb not null default '{}'::jsonb,
 started_at timestamptz not null default now(),
 finished_at timestamptz
);
alter table sm_intel.agent_tasks add constraint sm_agent_tasks_last_run_id_fkey
 foreign key (last_run_id) references sm_intel.agent_runs(id) on delete set null;
create table if not exists sm_intel.agent_learning_observations (
 id uuid primary key default gen_random_uuid(),
 source_family text not null check(source_family in ('affiliate_conversion','merchant_terms','user_feedback','market_research','retrieval_eval','agent_quality')),
 source_event_id text not null,
 subject_kind text not null,
 subject_key text not null,
 event_at timestamptz not null,
 facts jsonb not null,
 confidence numeric(5,4) not null default 0 check(confidence between 0 and 1),
 observed_effect numeric,
 counterevidence jsonb not null default '[]'::jsonb,
 review_state text not null default 'candidate' check(review_state in ('candidate','verified','rejected')),
 attributed_agent_role text,
 created_at timestamptz not null default now(),
 unique(source_family,source_event_id)
);
create index if not exists sm_learning_subject on sm_intel.agent_learning_observations(subject_kind,subject_key,event_at desc);
create table if not exists sm_intel.agent_change_proposals (
 id uuid primary key default gen_random_uuid(),
 proposed_by_role text not null,
 objective_key text not null references sm_intel.agent_objectives(objective_key),
 target_kind text not null check(target_kind in ('ranking_weights','research_priority','mapping','model_prompt','retriever_config','source_selection')),
 target_key text not null,
 change_proposal jsonb not null,
 evidence_refs jsonb not null default '[]'::jsonb,
 expected_kpi_change jsonb not null default '{}'::jsonb,
 offline_evaluation jsonb not null default '{}'::jsonb,
 status text not null default 'proposed' check(status in ('proposed','testing','approved','rejected','applied','rolled_back')),
 reviewed_by text,
 reviewed_at timestamptz,
 created_at timestamptz not null default now(),
 check(status not in ('approved','applied') or (reviewed_by is not null and reviewed_at is not null))
);

create or replace function sm_intel.queue_architect_work(p_cap integer default 5000)
returns jsonb language plpgsql security invoker set search_path='' as $$
declare programs_n integer; products_n integer; gaps_n integer;
begin
 with x as (
 insert into sm_intel.agent_tasks(objective_key,agent_role,subject_kind,subject_key,priority,input_refs)
 select 'trustworthy_merchant_coverage','merchant_identity','program',p.id::text,
 case when p.linkwise_program_id is not null then 85 else 60 end,
 jsonb_build_object('program_name',p.program_name,'linkwise_program_id',p.linkwise_program_id,
                    'source','sm_intel.merchant_program_directory','valid_to_known',p.terms_valid_to is not null)
 from sm_intel.merchant_program_directory p
 order by case when p.linkwise_program_id is not null then 0 else 1 end,p.program_name
 limit least(greatest(coalesce(p_cap,5000),1),10000)
 on conflict(objective_key,agent_role,subject_kind,subject_key,output_version) do nothing returning id)
 select count(*) into programs_n from x;

 with x as (
 insert into sm_intel.agent_tasks(objective_key,agent_role,subject_kind,subject_key,priority,input_refs)
 select 'evidence_first_solution_discovery','product_analyst','product',r.id::text,
 case when r.source_state='identified' then 70 else 35 end,
 jsonb_build_object('source','sm_intel.raw_products','program_id',r.program_id,
                    'stale',r.last_seen_at<now()-interval '7 days',
                    'required_research',jsonb_build_array('greek_demand','greek_supply','alternatives','commission','merchant','time','geography','counter_evidence'))
 from sm_intel.raw_products r where r.source_key='linkwise_cd104'
 order by r.last_seen_at desc,r.id
 limit least(greatest(coalesce(p_cap,5000),1),10000)
 on conflict(objective_key,agent_role,subject_kind,subject_key,output_version) do nothing returning id)
 select count(*) into products_n from x;

 with x as (
 insert into sm_intel.agent_tasks(objective_key,agent_role,subject_kind,subject_key,priority,input_refs)
 select 'greek_high_demand_low_supply','market_research','pain_gap',p.id::text,90,
 jsonb_build_object('source','public.market_problem_clusters','category',p.category)
 from public.market_problem_clusters p where p.market_code='GR'
 on conflict(objective_key,agent_role,subject_kind,subject_key,output_version) do nothing returning id)
 select count(*) into gaps_n from x;
 return jsonb_build_object('program_tasks',programs_n,'product_tasks',products_n,'gap_tasks',gaps_n);
end $$;
create or replace function sm_intel.claim_architect_tasks(p_agent text,p_limit integer default 3)
returns setof sm_intel.agent_tasks language sql volatile security invoker set search_path='' as $$
 with selected as (
  select id from sm_intel.agent_tasks
  where ((state in ('queued','needs_evidence') and next_attempt_at<=now())
   or (state='claimed' and claimed_at<now()-interval '20 minutes'))
  and attempts<4
  order by priority desc,created_at asc,id
  for update skip locked
  limit least(greatest(coalesce(p_limit,3),1),3)
 )
 update sm_intel.agent_tasks t set state='claimed',claimed_by=left(p_agent,120),
  claimed_at=now(),attempts=t.attempts+1,updated_at=now()
 from selected s where t.id=s.id returning t.*
$$;

-- Private only; no browser data grants, no autonomous production publishing.
do $$
declare x record;
begin
 for x in select table_name from information_schema.tables where table_schema='sm_intel' and table_type='BASE TABLE'
 loop
  execute format('alter table sm_intel.%I enable row level security',x.table_name);
  execute format('revoke all on sm_intel.%I from public,anon,authenticated',x.table_name);
 end loop;
end $$;
revoke all on function sm_intel.queue_architect_work(integer) from public,anon,authenticated;
revoke all on function sm_intel.claim_architect_tasks(text,integer) from public,anon,authenticated;
grant usage on schema sm_intel to service_role;
grant select,insert,update,delete on all tables in schema sm_intel to service_role;
grant execute on function sm_intel.queue_architect_work(integer) to service_role;
grant execute on function sm_intel.claim_architect_tasks(text,integer) to service_role;
