-- Harden the single-admin surface without changing the authenticated admin UX.
-- Browser admin calls continue through guarded RPCs; service integrations keep service_role access.

begin;

-- Admin RPCs are intentionally callable by authenticated users because each function
-- performs the single-admin JWT/email/provider guard internally. Anonymous execution
-- is never required and must not be available.
revoke all on function public.socialmarket_is_admin() from public, anon;
revoke all on function public.admin_log_action(text,text,text,jsonb) from public, anon;
revoke all on function public.admin_ai_log(text,text,text,text,bigint,bigint,jsonb) from public, anon;
revoke all on function public.admin_dashboard_snapshot() from public, anon;

grant execute on function public.socialmarket_is_admin() to authenticated, service_role;
grant execute on function public.admin_log_action(text,text,text,jsonb) to authenticated, service_role;
grant execute on function public.admin_ai_log(text,text,text,text,bigint,bigint,jsonb) to authenticated, service_role;
grant execute on function public.admin_dashboard_snapshot() to authenticated, service_role;

-- Compatibility views are internal integration surfaces, not public GraphQL endpoints.
-- security_invoker avoids privilege escalation through the view owner.
alter view public.socialmarket_publishing_outbox set (security_invoker = true);
alter view public.socialmarket_content_items set (security_invoker = true);
alter view public.merchant_gap_rankings set (security_invoker = true);
alter view public.validated_pain_clusters set (security_invoker = true);

revoke all on public.socialmarket_publishing_outbox from public, anon, authenticated;
revoke all on public.socialmarket_content_items from public, anon, authenticated;
revoke all on public.merchant_gap_rankings from public, anon, authenticated;
revoke all on public.validated_pain_clusters from public, anon, authenticated;

grant select on public.socialmarket_publishing_outbox to service_role;
grant select on public.socialmarket_content_items to service_role;
grant select on public.merchant_gap_rankings to service_role;
grant select on public.validated_pain_clusters to service_role;

commit;
