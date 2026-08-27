-- Lock provider-routing RPCs to the service role.
-- Supabase projects can retain explicit anon/authenticated function grants even
-- after PUBLIC is revoked, so every affected signature is revoked explicitly.

revoke all on function public.socialscheduler_provider_assignment_ready(text,text)
  from public, anon, authenticated;
grant execute on function public.socialscheduler_provider_assignment_ready(text,text)
  to service_role;

revoke all on function public.socialscheduler_choose_provider(text)
  from public, anon, authenticated;
grant execute on function public.socialscheduler_choose_provider(text)
  to service_role;

revoke all on function public.socialscheduler_rebalance_approved_jobs()
  from public, anon, authenticated;
grant execute on function public.socialscheduler_rebalance_approved_jobs()
  to service_role;
