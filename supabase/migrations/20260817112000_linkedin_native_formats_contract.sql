begin;

alter table publish.outbox drop constraint if exists outbox_platform_check;
alter table publish.outbox add constraint outbox_platform_check
  check (platform = any(array['facebook'::text,'instagram'::text,'tiktok'::text,'linkedin'::text]));

alter table publish.delivery_history drop constraint if exists delivery_history_platform_check;
alter table publish.delivery_history add constraint delivery_history_platform_check
  check (platform = any(array['facebook'::text,'instagram'::text,'tiktok'::text,'linkedin'::text]));

alter table publish.outbox drop constraint if exists outbox_content_item_id_platform_key;
alter table publish.outbox add constraint outbox_content_item_platform_format_key
  unique(content_item_id,platform,format);

create or replace function publish.native_format_for_slot_v1(p_platform text,p_slot_no integer)
returns text language sql immutable set search_path='' as $$
  select case
    when lower(coalesce(p_platform,''))='instagram' and mod(greatest(coalesce(p_slot_no,1),1),5)=0 then 'story'
    when lower(coalesce(p_platform,''))='instagram' and mod(greatest(coalesce(p_slot_no,1),1),3)=0 then 'reel'
    when lower(coalesce(p_platform,''))='tiktok' then 'photo'
    else 'post'
  end
$$;

create or replace function publish.queue_content_item_v2(p_content_item_id uuid,p_platform_payloads jsonb,p_default_scheduled_for timestamptz default null)
returns setof publish.outbox language plpgsql security definer set search_path='' as $$
declare v_platform text;v_payload jsonb;v_item content.items%rowtype;v_when timestamptz;v_format text;
begin
  select * into v_item from content.items where id=p_content_item_id for update;
  if not found then raise exception 'content_item_not_found'; end if;
  if v_item.status<>'approved' then raise exception 'content_item_not_approved'; end if;
  for v_platform,v_payload in select key,value from jsonb_each(coalesce(p_platform_payloads,'{}'::jsonb)) loop
    if v_platform not in ('facebook','instagram','tiktok','linkedin') then raise exception 'unsupported_platform:%',v_platform; end if;
    if coalesce(trim(v_payload->>'caption'),'')='' then raise exception 'caption_required:%',v_platform; end if;
    v_when=coalesce(nullif(v_payload->>'scheduled_for','')::timestamptz,p_default_scheduled_for,v_item.scheduled_from);
    if v_when is null then raise exception 'scheduled_for_required:%',v_platform; end if;
    v_format=lower(coalesce(nullif(v_payload->>'format',''),'post'));
    if v_platform='tiktok' and v_format like '%story%' then raise exception 'unsupported_format:tiktok_story'; end if;
    insert into publish.outbox(content_item_id,platform,caption,hashtags,format,media_url,tracking_url,scheduled_for,priority,status,updated_at)
    values(p_content_item_id,v_platform,v_payload->>'caption',coalesce(array(select jsonb_array_elements_text(coalesce(v_payload->'hashtags','[]'::jsonb))),'{}'::text[]),v_format,coalesce(nullif(v_payload->>'media_url',''),v_item.media_url),coalesce(nullif(v_payload->>'tracking_url',''),v_item.tracking_url),v_when,coalesce((v_payload->>'priority')::smallint,50),'approved',now())
    on conflict(content_item_id,platform,format) do update set caption=excluded.caption,hashtags=excluded.hashtags,media_url=excluded.media_url,tracking_url=excluded.tracking_url,scheduled_for=excluded.scheduled_for,priority=excluded.priority,status=case when publish.outbox.status in('scheduled','published') then publish.outbox.status else 'approved' end,last_error=null,updated_at=now();
  end loop;
  update content.items set status='queued',updated_at=now() where id=p_content_item_id;
  return query select * from publish.outbox where content_item_id=p_content_item_id order by platform,format;
end $$;

create or replace function publish.claim_jobs_capacity_v3(p_executor text,p_capacity jsonb,p_lease_minutes integer default 30)
returns table(id uuid,content_item_id uuid,platform text,caption text,hashtags text[],format text,media_url text,tracking_url text,scheduled_for timestamptz,priority smallint,brand_slug text,brand_name text,title text)
language plpgsql security definer set search_path='' as $$
declare v_enabled boolean;
begin
  select enabled into v_enabled from ops.executor_controls where executor_key=p_executor;
  if coalesce(v_enabled,false)=false then raise exception 'executor_disabled:%',p_executor; end if;
  return query
  with caps(platform,capacity) as (
    values
      ('facebook'::text,greatest(0,least(10,coalesce((p_capacity->>'facebook')::int,0)))),
      ('instagram'::text,greatest(0,least(10,coalesce((p_capacity->>'instagram')::int,0)))),
      ('tiktok'::text,greatest(0,least(10,coalesce((p_capacity->>'tiktok')::int,0)))),
      ('linkedin'::text,greatest(0,least(10,coalesce((p_capacity->>'linkedin')::int,0))))
  ), picked as (
    select x.id picked_id from caps c cross join lateral (
      select o.id from publish.outbox o where o.platform=c.platform and (o.status='approved' or (o.status='leased' and coalesce(o.lease_expires_at,now()-interval '1 second')<now())) order by o.scheduled_for,o.priority desc,o.created_at for update skip locked limit c.capacity
    ) x where c.capacity>0
  ), leased as (
    update publish.outbox o set status='leased',claimed_by=p_executor,claimed_at=now(),lease_expires_at=now()+make_interval(mins=>greatest(5,least(coalesce(p_lease_minutes,30),120))),attempt_count=o.attempt_count+1,updated_at=now()
    where exists(select 1 from picked p where p.picked_id=o.id) returning o.*
  )
  select l.id,l.content_item_id,l.platform,l.caption,l.hashtags,l.format,l.media_url,l.tracking_url,l.scheduled_for,l.priority,b.slug,b.name,c.title
  from leased l join content.items c on c.id=l.content_item_id join content.brand_sites b on b.id=c.brand_site_id
  order by l.scheduled_for,l.priority desc,l.created_at;
end $$;

create or replace function publish.generate_slots_v3(p_from timestamptz default now(),p_hours integer default 72)
returns table(platform text,scheduled_for timestamptz,slot_no integer,local_day date)
language sql stable set search_path='' as $$
with days as (
  select d::date local_day,extract(isodow from d)::int dow
  from generate_series((p_from at time zone 'Europe/Athens')::date,((p_from+make_interval(hours=>greatest(12,least(coalesce(p_hours,72),168)))) at time zone 'Europe/Athens')::date,interval '1 day') d
), targets as (
  select local_day,dow,'facebook'::text platform,(case when dow<=5 then 16 else 15 end)::int n,time '08:30' start_time,900::numeric window_min from days
  union all select local_day,dow,'instagram',(case when dow<=6 then 13 else 12 end),time '09:00',840::numeric from days
  union all select local_day,dow,'tiktok',10,time '10:00',810::numeric from days
  union all select local_day,dow,'linkedin',(case when dow<=5 then 5 when dow=6 then 3 else 2 end),time '08:45',600::numeric from days
), slots as (
  select t.platform,t.local_day,g.i,((t.local_day+t.start_time+make_interval(mins=>floor(((g.i-0.5)*t.window_min/t.n))::int)) at time zone 'Europe/Athens') scheduled_for
  from targets t cross join lateral generate_series(1,t.n) g(i)
)
select platform,scheduled_for,i,local_day from slots
where scheduled_for>p_from+interval '5 minutes' and scheduled_for<=p_from+make_interval(hours=>greatest(12,least(coalesce(p_hours,72),168)))
order by scheduled_for,platform
$$;

update ops.socialscheduler_config
set config=jsonb_set(jsonb_set(config,'{weekly_target}','300'::jsonb,true),'{channel_weekly}','{"facebook":110,"instagram":90,"tiktok":70,"linkedin":30}'::jsonb,true),version=version+1,updated_by='linkedin_native_formats_v1',updated_at=now()
where id=1;

commit;
