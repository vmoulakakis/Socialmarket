-- Dealora P0 security hardening.
-- Admin SECURITY DEFINER RPCs remain reachable only by authenticated users
-- (and then enforce socialmarket_is_admin()) plus service_role.
-- Autonomous/mutation RPCs are backend-only.

do $$
declare r record;
begin
  for r in
    select n.nspname,p.proname,pg_get_function_identity_arguments(p.oid) args
    from pg_proc p
    join pg_namespace n on n.oid=p.pronamespace
    where n.nspname='public'
      and p.prosecdef
      and p.proname like 'admin\_%' escape '\'
  loop
    execute format(
      'revoke all on function %I.%I(%s) from public, anon',
      r.nspname,r.proname,r.args
    );
    execute format(
      'grant execute on function %I.%I(%s) to authenticated, service_role',
      r.nspname,r.proname,r.args
    );
  end loop;

  for r in
    select n.nspname,p.proname,pg_get_function_identity_arguments(p.oid) args
    from pg_proc p
    join pg_namespace n on n.oid=p.pronamespace
    where n.nspname='public'
      and p.proname in (
        'dealora_refresh_growth_v1',
        'dealora_refresh_public_pages_v1',
        'dealora_seed_creatives_v1',
        'dealora_seed_pages_v1',
        'socialmarket_reconcile_revenue_v1',
        'socialmarket_refresh_winner_lifecycle_v1',
        'socialmarket_revenue_feedback_v1',
        'socialscheduler_rebalance_frequency_v6',
        'socialscheduler_refresh_dynamic_kpi_v1',
        'socialscheduler_weekly_feedback_v6',
        'worker_v3_outbox_ack'
      )
  loop
    execute format(
      'revoke all on function %I.%I(%s) from public, anon, authenticated',
      r.nspname,r.proname,r.args
    );
    execute format(
      'grant execute on function %I.%I(%s) to service_role',
      r.nspname,r.proname,r.args
    );
  end loop;
end $$;
