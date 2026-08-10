create table if not exists public.admin_emails (
  email text primary key,
  created_at timestamptz not null default now()
);
alter table public.admin_emails enable row level security;

create or replace function public.is_admin()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from public.admin_emails a
    where lower(a.email) = lower(coalesce(auth.jwt() ->> 'email',''))
  );
$$;
revoke all on function public.is_admin() from public;
grant execute on function public.is_admin() to authenticated;

do $$
declare t text;
begin
  foreach t in array array['sources','import_jobs','products','product_media','taxonomy','product_classifications','product_embeddings','market_research_runs','market_signals','forecast_runs','forecasts','opportunity_scores','evidence_audits','creative_jobs','creative_assets','approvals','agent_runs','app_settings'] loop
    execute format('drop policy if exists admin_authenticated_all on public.%I', t);
    execute format('drop policy if exists single_admin_all on public.%I', t);
    execute format('create policy single_admin_all on public.%I for all to authenticated using (public.is_admin()) with check (public.is_admin())', t);
  end loop;
end $$;

drop policy if exists admin_product_media on storage.objects;
drop policy if exists single_admin_storage on storage.objects;
create policy single_admin_storage on storage.objects for all to authenticated
using (bucket_id in ('product-media','creatives') and public.is_admin())
with check (bucket_id in ('product-media','creatives') and public.is_admin());

-- Add the single admin email directly in the target Supabase project, not in source control.
