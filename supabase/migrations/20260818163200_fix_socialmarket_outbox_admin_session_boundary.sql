-- Keep browser/PostgREST access admin-only while allowing trusted server-side
-- Edge Functions to read the publishing outbox through their direct DB session.
create or replace function api.socialmarket_admin_publishing_outbox_rows()
returns table(
  id uuid,
  content_item_id uuid,
  platform text,
  title text,
  brand_slug text,
  brand_name text,
  caption text,
  hashtags text[],
  format text,
  media_url text,
  tracking_url text,
  scheduled_for timestamptz,
  priority smallint,
  status text,
  claimed_by text,
  claimed_at timestamptz,
  lease_expires_at timestamptz,
  external_post_id text,
  external_permalink text,
  published_at timestamptz,
  attempt_count integer,
  last_error text,
  created_at timestamptz,
  updated_at timestamptz
)
language plpgsql
stable
security definer
set search_path = ''
as $$
begin
  if session_user = 'authenticator' and not public.socialmarket_is_admin() then
    raise exception 'admin_only';
  end if;

  return query
  select
    x.id,
    x.content_item_id,
    x.platform,
    x.title,
    x.brand_slug,
    x.brand_name,
    x.caption,
    x.hashtags,
    x.format,
    x.media_url,
    x.tracking_url,
    x.scheduled_for,
    x.priority,
    x.status,
    x.claimed_by,
    x.claimed_at,
    x.lease_expires_at,
    x.external_post_id,
    x.external_permalink,
    x.published_at,
    x.attempt_count,
    x.last_error,
    x.created_at,
    x.updated_at
  from api.publishing_outbox x;
end;
$$;

revoke all on function api.socialmarket_admin_publishing_outbox_rows() from public;
revoke all on function api.socialmarket_admin_publishing_outbox_rows() from anon;
grant execute on function api.socialmarket_admin_publishing_outbox_rows() to authenticated, service_role;

grant select on public.socialmarket_publishing_outbox to authenticated, service_role;
revoke all on public.socialmarket_publishing_outbox from anon;
