-- Least-privilege hardening for SocialMarket production.
-- Preserve intended read contracts while removing accidental DML/RPC exposure.

revoke all on public.category_market_dashboard from public, anon, authenticated, service_role;
grant select on public.category_market_dashboard to authenticated, service_role;

revoke all on public.niche_candidates from public, anon, authenticated, service_role;
grant select on public.niche_candidates to authenticated, service_role;

revoke all on public.socialscheduler_provider_scores_v from public, anon, authenticated, service_role;
grant select on public.socialscheduler_provider_scores_v to authenticated, service_role;

revoke all on public.socialscheduler_feedback_stats_v from public, anon, authenticated, service_role;
grant select on public.socialscheduler_feedback_stats_v to authenticated, service_role;

revoke all on public.socialmarket_revenue_daily_v from public, anon, authenticated, service_role;
grant select on public.socialmarket_revenue_daily_v to authenticated, service_role;

revoke all on public.dealora_public_deals_v from public, anon, authenticated, service_role;
grant select on public.dealora_public_deals_v to anon, authenticated, service_role;

revoke all on public.socialmarket_top100_publication_state_v from public, anon, authenticated, service_role;
grant select on public.socialmarket_top100_publication_state_v to authenticated, service_role;

revoke all on public.socialmarket_top100_current_v from public, anon, authenticated, service_role;
grant select on public.socialmarket_top100_current_v to authenticated, service_role;

revoke all on public.socialmarket_top100_history_v from public, anon, authenticated, service_role;
grant select on public.socialmarket_top100_history_v to authenticated, service_role;

revoke all on public.socialmarket_marketplace200_public_v from public, anon, authenticated, service_role;
grant select on public.socialmarket_marketplace200_public_v to anon, authenticated, service_role;

revoke all on public.socialmarket_marketplace200_admin_v from public, anon, authenticated, service_role;
grant select on public.socialmarket_marketplace200_admin_v to authenticated, service_role;

do $$
declare r record;
begin
  for r in
    select unnest(array[
      'public."User"',
      'public."Lead"',
      'public."Click"',
      'public."Follow"',
      'public."Wishlist"',
      'public."Share"',
      'public.dealora_amplification_queue',
      'public.dealora_creative_experiments',
      'public.dealora_email_events',
      'public.dealora_paid_decisions',
      'public.dealora_subscribers',
      'public.socialmarket_affiliate_revenue_events',
      'public.socialmarket_affiliate_revenue_imports',
      'public.socialmarket_winner_state',
      'public.socialscheduler_orchestration_decisions_archive'
    ]) as fqname
  loop
    if to_regclass(r.fqname) is not null then
      execute format('revoke select on table %s from anon', r.fqname);
    end if;
  end loop;
end $$;

do $$
declare p record;
begin
  for p in
    select x.oid::regprocedure as fn
    from pg_proc x
    join pg_namespace n on n.oid=x.pronamespace
    where n.nspname='public'
      and x.proname in (
        'optimization_daily_prepare',
        'socialscheduler_archive_stale_orchestration_decisions',
        'socialscheduler_audit_worker_v8',
        'socialscheduler_log_delivery_event',
        'socialscheduler_log_outbox_event',
        'socialscheduler_mark_overdue_delivery_unknown',
        'socialscheduler_reclaim_for_night_brain_v1'
      )
  loop
    execute format('revoke execute on function %s from public, anon, authenticated', p.fn);
    execute format('grant execute on function %s to service_role', p.fn);
  end loop;
end $$;

alter function public.product_intelligence_default_config() security invoker;
alter function public.validate_product_intelligence_config(jsonb) security invoker;

alter function ops.socialmarket_revenue_goal_snapshot_v1()
  set search_path = pg_catalog, public, ops;
