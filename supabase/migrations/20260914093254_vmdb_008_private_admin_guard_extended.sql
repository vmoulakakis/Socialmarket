create schema if not exists private;
create or replace function private.is_admin() returns boolean language sql stable security definer set search_path=public,private as $$ select exists(select 1 from public.admin_emails a where lower(a.email)=lower(coalesce(auth.jwt()->>'email',''))) $$;
revoke all on function private.is_admin() from public,anon;
grant usage on schema private to authenticated;
grant execute on function private.is_admin() to authenticated;

do $$ declare t text; begin
 foreach t in array array['sources','import_jobs','products','product_media','taxonomy','product_classifications','product_embeddings','market_research_runs','market_signals','forecast_runs','forecasts','opportunity_scores','evidence_audits','creative_jobs','creative_assets','approvals','agent_runs','app_settings'] loop
  execute format('drop policy if exists single_admin_all on public.%I',t);
  execute format('create policy single_admin_all on public.%I for all to authenticated using (private.is_admin()) with check (private.is_admin())',t);
 end loop;
end $$;

drop policy if exists orchestrator_runs_admin_all on public.orchestrator_runs;
create policy orchestrator_runs_admin_all on public.orchestrator_runs for all to authenticated using (private.is_admin()) with check (private.is_admin());
drop policy if exists orchestrator_steps_admin_all on public.orchestrator_steps;
create policy orchestrator_steps_admin_all on public.orchestrator_steps for all to authenticated using (private.is_admin()) with check (private.is_admin());
drop policy if exists site_registry_admin_select on public.site_registry;
create policy site_registry_admin_select on public.site_registry for select to authenticated using (private.is_admin());

drop policy if exists agent_tool_tasks_admin_select on public.agent_tool_tasks;
drop policy if exists agent_tool_tasks_admin_insert on public.agent_tool_tasks;
drop policy if exists agent_tool_tasks_admin_update on public.agent_tool_tasks;
create policy agent_tool_tasks_admin_select on public.agent_tool_tasks for select to authenticated using (private.is_admin());
create policy agent_tool_tasks_admin_insert on public.agent_tool_tasks for insert to authenticated with check (private.is_admin());
create policy agent_tool_tasks_admin_update on public.agent_tool_tasks for update to authenticated using (private.is_admin()) with check (private.is_admin());

drop policy if exists agent_budget_policies_admin_select on public.agent_budget_policies;
create policy agent_budget_policies_admin_select on public.agent_budget_policies for select to authenticated using (private.is_admin());
drop policy if exists agent_usage_ledger_admin_select on public.agent_usage_ledger;
drop policy if exists agent_usage_ledger_admin_insert on public.agent_usage_ledger;
drop policy if exists agent_usage_ledger_admin_update on public.agent_usage_ledger;
create policy agent_usage_ledger_admin_select on public.agent_usage_ledger for select to authenticated using (private.is_admin());
create policy agent_usage_ledger_admin_insert on public.agent_usage_ledger for insert to authenticated with check (private.is_admin());
create policy agent_usage_ledger_admin_update on public.agent_usage_ledger for update to authenticated using (private.is_admin()) with check (private.is_admin());

drop policy if exists single_admin_storage on storage.objects;
create policy single_admin_storage on storage.objects for all to authenticated using (bucket_id in ('product-media','creatives') and private.is_admin()) with check (bucket_id in ('product-media','creatives') and private.is_admin());

drop function if exists public.is_admin();
