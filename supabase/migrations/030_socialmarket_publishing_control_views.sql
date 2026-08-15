-- Read-only admin projections over the single shared publishing/content source of truth.
-- Applied to Supabase project rpfadpdnnxequgvdcfoq.

create or replace view public.socialmarket_publishing_outbox as
select
  id, content_item_id, platform, title, brand_slug, brand_name,
  caption, hashtags, format, media_url, tracking_url, scheduled_for,
  priority, status, claimed_by, claimed_at, lease_expires_at,
  external_post_id, external_permalink, published_at, attempt_count,
  last_error, created_at, updated_at
from api.publishing_outbox;

create or replace view public.socialmarket_content_items as
select
  i.id, i.source_key, i.brand_site_id,
  bs.slug as brand_slug,
  bs.name as brand_name,
  i.merchant_id, i.title, i.angle, i.core_copy, i.cta,
  i.tracking_url, i.media_url, i.status, i.scheduled_from,
  i.approved_at, i.created_at, i.updated_at
from content.items i
left join content.brand_sites bs on bs.id = i.brand_site_id;

revoke all on public.socialmarket_publishing_outbox from anon;
revoke all on public.socialmarket_content_items from anon;
revoke all on public.socialmarket_publishing_outbox from authenticated;
revoke all on public.socialmarket_content_items from authenticated;
grant select on public.socialmarket_publishing_outbox to authenticated;
grant select on public.socialmarket_content_items to authenticated;
