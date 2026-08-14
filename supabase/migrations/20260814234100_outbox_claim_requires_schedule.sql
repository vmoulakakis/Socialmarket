-- The executor must never invent a publishing time. Only explicitly dated jobs are claimable.
create or replace function public.claim_publishing_jobs(
  p_executor text,
  p_limit integer default 10,
  p_lease_minutes integer default 30
) returns table(
  id uuid,
  content_item_id uuid,
  platform text,
  caption text,
  hashtags text[],
  format text,
  media_url text,
  tracking_url text,
  scheduled_for timestamptz,
  priority smallint,
  brand_slug text,
  brand_name text,
  title text
)
language plpgsql
security definer
set search_path = public
as $$
begin
  return query
  with picked as (
    select o.id
    from public.publishing_outbox o
    where o.scheduled_for is not null
      and (o.status='approved'
       or (o.status='leased' and coalesce(o.lease_expires_at,now()-interval '1 second') < now()))
    order by o.scheduled_for, o.priority desc, o.created_at
    for update skip locked
    limit greatest(1,least(coalesce(p_limit,10),50))
  ), leased as (
    update public.publishing_outbox o
       set status='leased', claimed_by=p_executor, claimed_at=now(),
           lease_expires_at=now()+make_interval(mins => greatest(5,least(coalesce(p_lease_minutes,30),120))),
           attempt_count=o.attempt_count+1, updated_at=now()
     where o.id in (select picked.id from picked)
     returning o.*
  )
  select l.id,l.content_item_id,l.platform,l.caption,l.hashtags,l.format,l.media_url,l.tracking_url,
         l.scheduled_for,l.priority,b.slug,b.name,c.title
    from leased l
    join public.content_items c on c.id=l.content_item_id
    join public.brand_sites b on b.id=c.brand_site_id
   order by l.scheduled_for,l.priority desc,l.created_at;
end;
$$;

revoke all on function public.claim_publishing_jobs(text,integer,integer) from public, anon, authenticated;
grant execute on function public.claim_publishing_jobs(text,integer,integer) to service_role;
