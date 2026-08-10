create schema if not exists private;

create or replace function private.is_admin()
returns boolean
language sql
stable
security definer
set search_path = public, private
as $$
  select exists (
    select 1 from public.admin_emails a
    where lower(a.email) = lower(coalesce(auth.jwt() ->> 'email',''))
  );
$$;

revoke all on function private.is_admin() from public;
revoke all on function private.is_admin() from anon;
grant usage on schema private to authenticated;
grant execute on function private.is_admin() to authenticated;

do $$
declare t text;
begin
  foreach t in array array['sources','import_jobs','products','product_media','taxonomy','product_classifications','product_embeddings','market_research_runs','market_signals','forecast_runs','forecasts','opportunity_scores','evidence_audits','creative_jobs','creative_assets','approvals','agent_runs','app_settings'] loop
    execute format('drop policy if exists single_admin_all on public.%I', t);
    execute format('create policy single_admin_all on public.%I for all to authenticated using (private.is_admin()) with check (private.is_admin())', t);
  end loop;
end $$;

drop policy if exists admin_emails_deny_direct_access on public.admin_emails;
create policy admin_emails_deny_direct_access on public.admin_emails for all using (false) with check (false);

drop policy if exists single_admin_storage on storage.objects;
create policy single_admin_storage on storage.objects for all to authenticated
using (bucket_id in ('product-media','creatives') and private.is_admin())
with check (bucket_id in ('product-media','creatives') and private.is_admin());

drop function if exists public.is_admin();
