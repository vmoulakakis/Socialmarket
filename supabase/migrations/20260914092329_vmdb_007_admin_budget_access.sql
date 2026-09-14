grant select on public.agent_budget_policies to authenticated;
grant select,insert,update on public.agent_usage_ledger to authenticated;
create policy agent_budget_policies_admin_select on public.agent_budget_policies for select to authenticated using (public.is_admin());
create policy agent_usage_ledger_admin_select on public.agent_usage_ledger for select to authenticated using (public.is_admin());
create policy agent_usage_ledger_admin_insert on public.agent_usage_ledger for insert to authenticated with check (public.is_admin());
create policy agent_usage_ledger_admin_update on public.agent_usage_ledger for update to authenticated using (public.is_admin()) with check (public.is_admin());

grant execute on function public.reserve_agent_budget(text,numeric,text,text,text,text,jsonb) to authenticated,service_role;
grant execute on function public.finalize_agent_budget(bigint,numeric,jsonb) to authenticated,service_role;
grant execute on function public.release_agent_budget(bigint) to authenticated,service_role;
