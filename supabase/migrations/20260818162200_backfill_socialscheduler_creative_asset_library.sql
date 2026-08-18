-- Backfill the new SocialScheduler Admin asset library from existing canonical content media.

insert into public.socialscheduler_creative_assets(
  asset_key,file_name,public_url,mime_type,post_id_hint,source,status,metadata,created_by_email,created_at,updated_at
)
select
  'content:'||ci.id::text,
  regexp_replace(coalesce(ci.source_key,ci.id::text),'[^a-zA-Z0-9._-]+','-','g')||case when lower(ci.media_url) like '%.webp%' then '.webp' when lower(ci.media_url) like '%.jpg%' or lower(ci.media_url) like '%.jpeg%' then '.jpg' else '.png' end,
  ci.media_url,
  case when lower(ci.media_url) like '%.webp%' then 'image/webp' when lower(ci.media_url) like '%.jpg%' or lower(ci.media_url) like '%.jpeg%' then 'image/jpeg' else 'image/png' end,
  ci.source_key,
  'content_backfill',
  'ready',
  jsonb_strip_nulls(jsonb_build_object(
    'content_item_id',ci.id,
    'title',ci.title,
    'planned_platform',ci.metadata->>'planned_platform',
    'campaign',ci.metadata->>'campaign',
    'creative_key',ci.metadata->>'creative_key',
    'original_source',ci.metadata->>'source'
  )),
  'vmoulakakis@gmail.com',
  ci.created_at,
  now()
from content.items ci
where ci.media_url like 'https://%'
on conflict(asset_key) do update set
  public_url=excluded.public_url,
  mime_type=excluded.mime_type,
  post_id_hint=excluded.post_id_hint,
  metadata=excluded.metadata,
  status='ready',
  updated_at=now();
