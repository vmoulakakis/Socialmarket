-- Private operator telemetry for legacy cron and new GraphRAG readiness.
create or replace function public.socialmarket_cockpit_runtime_health()
returns jsonb language plpgsql stable security definer set search_path='' as $$
begin
 if auth.uid() is null or not private.is_admin() then
  raise exception 'admin_access_required' using errcode='42501';
 end if;
 return jsonb_build_object(
  'checked_at',now(),
  'legacy_linkwise_cron',coalesce((select jsonb_agg(
   jsonb_build_object('name',j.jobname,'active',j.active,'schedule',j.schedule))
   from cron.job j where j.jobname like 'linkwise%'),'[]'::jsonb),
  'legacy_stuck_running',(select count(*) from public.commerce_feed_runs f
   where f.status='running' and f.created_at<now()-interval '2 hours'),
  'private_feed_running',(select count(*) from sm_intel.feed_runs f where f.state='running'),
  'private_feed_completed',(select count(*) from sm_intel.feed_runs f where f.state='completed'),
  'private_delta_batches',(select count(*) from sm_intel.delta_feed_batches),
  'vectors_pending',(select count(*) from sm_intel.search_documents d where d.embedding_status='pending'),
  'vectors_failed',(select count(*) from sm_intel.search_documents d where d.embedding_status='failed'),
  'agents_claimed',(select count(*) from sm_intel.agent_tasks t where t.state='claimed'),
  'agents_stalled',(select count(*) from sm_intel.agent_tasks t where t.state='claimed'
    and t.claimed_at<now()-interval '20 minutes'),
  'last_agent_run',(select max(r.started_at) from sm_intel.agent_runs r),
  'paid_ai_calls_24h',(select coalesce(sum(l.quantity),0) from public.agent_usage_ledger l
    where l.metric='remote_llm_calls' and l.status='committed'
      and l.created_at>now()-interval '24 hours'),
  'scope','read-only; no secrets, cron commands or raw customer records'
 );
end $$;
revoke all on function public.socialmarket_cockpit_runtime_health() from public,anon,authenticated;
grant execute on function public.socialmarket_cockpit_runtime_health() to authenticated,service_role;
