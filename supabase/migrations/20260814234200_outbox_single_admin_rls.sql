-- Match SocialMarket's existing single-admin security model on the new content tables.
do $$
declare t text;
begin
  foreach t in array array['brand_sites','content_items','publishing_outbox'] loop
    execute format('drop policy if exists admin_authenticated_all on public.%I', t);
    execute format('drop policy if exists single_admin_all on public.%I', t);
    execute format(
      'create policy single_admin_all on public.%I for all to authenticated using (private.is_admin()) with check (private.is_admin())',
      t
    );
  end loop;
end $$;
