-- Ranked product creatives become durable public media + canonical SocialMarket content.
-- SocialScheduler never owns/copies these records; it only claims publish.outbox.

insert into storage.buckets(id,name,public,file_size_limit,allowed_mime_types)
values('socialmarket-creatives','socialmarket-creatives',true,8388608,array['image/png','image/jpeg','image/webp'])
on conflict(id) do update set public=true,file_size_limit=excluded.file_size_limit,allowed_mime_types=excluded.allowed_mime_types;

alter table intel.product_rankings
  add column if not exists creative_content_count smallint not null default 0;

do $$ begin
  alter table intel.product_rankings
    add constraint product_rankings_creative_content_count_check
    check(creative_content_count between 0 and 3);
exception when duplicate_object then null; end $$;

create index if not exists content_items_ranked_creative_run_idx
  on content.items ((metadata->>'creative_run_id'), (metadata->>'source_record_hash'))
  where metadata->>'origin'='ranked_product_creative';

create or replace function public.admin_creative_content_items()
returns jsonb
language plpgsql
security definer
set search_path=''
as $$
declare result jsonb;
begin
  if not public.socialmarket_is_admin() then raise exception 'admin_only'; end if;
  select coalesce(jsonb_agg(to_jsonb(x) order by x.created_at desc),'[]'::jsonb)
  into result
  from (
    select i.id,i.source_key,i.title,i.angle,i.core_copy,i.cta,i.tracking_url,i.media_url,i.status,i.scheduled_from,i.approved_at,i.metadata,i.created_at,
           b.slug brand_slug,b.name brand_name
    from content.items i
    join content.brand_sites b on b.id=i.brand_site_id
    where i.metadata->>'origin'='ranked_product_creative'
    order by i.created_at desc
    limit 240
  ) x;
  return result;
end $$;

revoke all on function public.admin_creative_content_items() from public;
grant execute on function public.admin_creative_content_items() to authenticated;
