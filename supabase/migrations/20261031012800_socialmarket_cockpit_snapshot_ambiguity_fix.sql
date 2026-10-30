-- Fix PL/pgSQL local variable shadowing of audit.result, preserve tight access controls.
create or replace function public.socialmarket_cockpit_snapshot()
returns jsonb language plpgsql stable security definer set search_path='' as $$
declare snapshot_payload jsonb;
begin
 if auth.uid() is null or not private.is_admin() then
   raise exception 'admin_access_required' using errcode='42501';
 end if;
 select jsonb_build_object(
 'version','sm-cockpit-1.0', 'generated_at',now(),
 'scope','sm_intel', 'market','GR',
 'health',(select to_jsonb(h) from sm_intel.orchestrator_objective_health h),
 'agent_roles',coalesce((select jsonb_agg(to_jsonb(x) order by x.agent_role,x.state)
  from (select agent_role,state,count(*)::int n from sm_intel.agent_tasks
        group by agent_role,state) x),'[]'::jsonb),
 'objectives',coalesce((select jsonb_agg(jsonb_build_object('key',objective_key,
  'purpose',purpose,'status',status,'version',version,'criteria',success_criteria)
  order by objective_key) from sm_intel.agent_objectives),'[]'::jsonb),
 'merchants',coalesce((select jsonb_agg(to_jsonb(x) order by x.n desc)
 from (select case when program_status='mapped' then 'mapped · unverified' else program_status end status,
      count(*)::int n from sm_intel.merchant_program_directory group by 1) x),'[]'::jsonb),
 'categories',coalesce((select jsonb_agg(to_jsonb(x) order by x.n desc)
 from (select left(coalesce(nullif(category_raw,''),'Unclassified'),44) label,
  count(*)::int n from sm_intel.raw_products group by 1 order by 2 desc limit 9) x),'[]'::jsonb),
 'embedding',coalesce((select jsonb_agg(to_jsonb(x) order by x.n desc)
 from (select embedding_status status,count(*)::int n from sm_intel.search_documents group by 1) x),'[]'::jsonb),
 'research',coalesce((select jsonb_agg(to_jsonb(x) order by x.n desc)
 from (select next_research_action status,count(*)::int n from sm_intel.gap_research_queue group by 1) x),'[]'::jsonb),
 'feeds',coalesce((select jsonb_agg(to_jsonb(x) order by x.started_at desc)
 from (select id,source_key,state,scanned,stored,admitted,rejected,
    started_at,finished_at,error_code, checkpoint->>'mode' as mode
  from sm_intel.feed_runs order by created_at desc limit 12) x),'[]'::jsonb),
 'agent_runs',coalesce((select jsonb_agg(to_jsonb(x) order by x.started_at desc)
 from (select id,runtime_mode,state,processed_tasks,model_calls,
    started_at,finished_at
  from sm_intel.agent_runs order by started_at desc limit 12) x),'[]'::jsonb),
 'budgets',coalesce((select jsonb_agg(to_jsonb(x) order by x.metric)
 from (select p.metric,p.enabled,p.daily_limit,p.monthly_limit,p.soft_threshold,
  (select coalesce(sum(l.quantity),0) from public.agent_usage_ledger l
   where l.metric=p.metric and l.status in ('reserved','committed')
     and l.created_at>=date_trunc('day',now())) as used_today,
  (select coalesce(sum(l.quantity),0) from public.agent_usage_ledger l
   where l.metric=p.metric and l.status in ('reserved','committed')
     and l.created_at>=date_trunc('month',now())) as used_month
 from public.agent_budget_policies p) x),'[]'::jsonb),
 'configuration',jsonb_build_object(
  'min_commission_eur',10,
  'feed_source','encrypted Supabase Vault; URL never displayed',
  'feed_import_policy','full-stream scan / insert-new-only / manual commit',
  'commercial_gate','verified terms + conservative >=€10',
  'vector_model','intfloat/multilingual-e5-small',
  'vector_dimensions',384,
  'paid_ai','explicit escalation only; no automatic paid requests',
  'agent_max_concurrency',3,
  'feed_live_import_enabled',false,
  'schema_is_private',true,
  'verified_offer_policy','fail-closed'),
 'audit',coalesce((select jsonb_agg(to_jsonb(x) order by x.created_at desc)
   from (select id,action,target,result,created_at from sm_intel.cockpit_audit
     order by created_at desc limit 30) x),'[]'::jsonb),
 'alerts',jsonb_build_array(
   jsonb_build_object('level','critical','title','No current qualified offers',
    'detail','Commission terms must be verified before product admission',
    'active',(select count(*)=0 from sm_intel.qualified_offers)),
   jsonb_build_object('level','warning','title','Embedding pipeline not yet active',
    'detail','Vector index exists but production vectors are pending',
    'active',(select count(*)=0 from sm_intel.search_documents where embedding_status='ready')),
   jsonb_build_object('level','warning','title','Program IDs missing',
    'detail','Source records need authoritative program identity',
    'active',(select count(*)>0 from sm_intel.merchant_program_directory where linkwise_program_id is null)),
   jsonb_build_object('level','warning','title','Old catalog',
    'detail','No recent fresh imported product snapshots',
    'active',(select count(*)=0 from sm_intel.raw_products where last_seen_at>now()-interval '7 days')),
   jsonb_build_object('level','info','title','Full live ingestion disabled',
    'detail','User-requested: no full feed import until approval',
    'active',true)
 )
 ) into snapshot_payload;
 return snapshot_payload;
end $$;
