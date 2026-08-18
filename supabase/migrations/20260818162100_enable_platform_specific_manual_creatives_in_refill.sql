-- SocialScheduler refill hotfix: prefer platform-specific manual creatives for IG/TikTok/LinkedIn
-- while preserving dedupe against active outbox rows and delivery history.

create or replace function publish.refill_conversion_outbox_v3(p_hours integer default 72)
returns jsonb
language plpgsql
security definer
set search_path to ''
as $function$
declare
  s record;
  c record;
  v_inserted int:=0;
  v_products int:=0;
  v_sites int:=0;
  v_pain int:=0;
  v_manual int:=0;
  v_prefer_site boolean;
  v_candidate_found boolean:=false;
  v_hashtags text[];
  v_format text;
  v_desired_format text;
  v_site_share numeric:=0.25;
  v_site_pool jsonb;
  v_week_slot integer;
begin
  select coalesce((config->>'facebook_site_share')::numeric,0.25)
    into v_site_share
  from ops.socialscheduler_config
  where id=1;

  v_site_share:=greatest(0.125,least(0.50,coalesce(v_site_share,0.25)));
  select content.ensure_weekly_site_pool_v3(null) into v_site_pool;

  for s in select * from publish.generate_slots_v3(now(),p_hours) loop
    v_desired_format:=publish.native_format_for_slot_v1(s.platform,s.slot_no);

    if exists(
         select 1 from publish.outbox o
         where o.platform=s.platform
           and o.status in('approved','leased','scheduled')
           and abs(extract(epoch from(o.scheduled_for-s.scheduled_for)))<60
       ) or exists(
         select 1 from publish.delivery_history h
         where h.platform=s.platform
           and h.delivery_status in('scheduled','published','sent')
           and abs(extract(epoch from(h.scheduled_for-s.scheduled_for)))<60
       ) then
      continue;
    end if;

    if s.platform='facebook' then
      v_week_slot:=case
        when extract(isodow from s.local_day)::int<=6
          then (extract(isodow from s.local_day)::int-1)*16+s.slot_no
        else 95+s.slot_no
      end;
      v_prefer_site:=floor(v_week_slot*v_site_share)>floor((v_week_slot-1)*v_site_share);
    else
      v_prefer_site:=false;
    end if;

    v_candidate_found:=false;

    if v_prefer_site then
      select ci.id,ci.core_copy,ci.media_url,ci.tracking_url,ci.metadata,ci.created_at,
             80::smallint as priority
        into c
      from content.items ci
      where ci.status in('approved','queued')
        and ci.metadata->>'source'='chatgpt_site_promo'
        and coalesce(ci.metadata->>'platform','facebook')='facebook'
        and coalesce(trim(ci.core_copy),'')<>''
        and coalesce(trim(ci.tracking_url),'')<>''
        and not exists(
          select 1 from publish.outbox o
          where o.content_item_id=ci.id
            and o.platform='facebook'
            and o.format='post'
            and o.status not in('cancelled','failed')
        )
        and not exists(
          select 1 from publish.delivery_history h
          where h.content_item_id=ci.id
            and h.platform='facebook'
            and coalesce(h.format,'post')='post'
            and h.delivery_status not in('rebalanced_cancelled','deleted_before_publish','failed')
        )
      order by ci.created_at asc
      limit 1;
      v_candidate_found:=found;
    else
      if s.platform in ('instagram','tiktok','linkedin') then
        select ci.id,ci.core_copy,ci.media_url,ci.tracking_url,ci.metadata,ci.created_at,
               98::smallint as priority
          into c
        from content.items ci
        where ci.status in('approved','queued')
          and lower(coalesce(ci.metadata->>'planned_platform',''))=s.platform
          and coalesce(trim(ci.core_copy),'')<>''
          and ci.media_url like 'https://%'
          and ci.tracking_url like 'http%'
          and not exists(
            select 1 from publish.outbox o
            where o.content_item_id=ci.id
              and o.platform=s.platform
              and o.status not in('cancelled','failed')
          )
          and not exists(
            select 1 from publish.delivery_history h
            where h.content_item_id=ci.id
              and h.platform=s.platform
              and h.delivery_status not in('rebalanced_cancelled','deleted_before_publish','failed')
          )
        order by ci.created_at asc,ci.id
        limit 1;
        v_candidate_found:=found;
      end if;

      if not v_candidate_found and v_desired_format='post' then
        select ci.id,ci.core_copy,ci.media_url,ci.tracking_url,ci.metadata,ci.created_at,
               95::smallint as priority
          into c
        from content.items ci
        where ci.status in('approved','queued')
          and ci.metadata->>'campaign_type'='pain_solver'
          and coalesce(trim(ci.core_copy),'')<>''
          and ci.media_url like 'https://%'
          and ci.tracking_url like 'http%'
          and (ci.scheduled_from is null or ci.scheduled_from between s.scheduled_for-interval '18 hours' and s.scheduled_for+interval '36 hours')
          and not exists(
            select 1 from publish.outbox o
            where o.content_item_id=ci.id
              and o.platform=s.platform
              and o.format=v_desired_format
              and o.status not in('cancelled','failed')
          )
          and not exists(
            select 1 from publish.delivery_history h
            where h.content_item_id=ci.id
              and h.platform=s.platform
              and coalesce(h.format,'post')=v_desired_format
              and h.delivery_status not in('rebalanced_cancelled','deleted_before_publish','failed')
          )
        order by abs(extract(epoch from(coalesce(ci.scheduled_from,s.scheduled_for)-s.scheduled_for))),ci.created_at desc,ci.id
        limit 1;
        v_candidate_found:=found;
      end if;

      if not v_candidate_found then
        select ci.id,ci.core_copy,ci.media_url,ci.tracking_url,ci.metadata,ci.created_at,
               greatest(50,least(100,101-coalesce(nullif(ci.metadata->>'global_rank','')::int,50)))::smallint as priority
          into c
        from content.items ci
        where ci.status in('approved','queued')
          and ci.metadata->>'origin'='ranked_product_creative'
          and coalesce(trim(ci.core_copy),'')<>''
          and ci.media_url like 'https://%'
          and ci.tracking_url like 'http%'
          and exists(
            select 1
            from jsonb_array_elements_text(coalesce(ci.metadata->'platforms','[]'::jsonb)) p
            where p.value=s.platform
          )
          and (
            (s.platform='instagram' and v_desired_format in('reel','story') and ci.metadata->>'variant_id'='reel_9x16')
            or (s.platform='instagram' and v_desired_format='post' and ci.metadata->>'variant_id' in('feed_4x5','square_1x1'))
            or (s.platform='tiktok' and ci.metadata->>'variant_id'='reel_9x16')
            or (s.platform='linkedin' and ci.metadata->>'variant_id' in('feed_4x5','square_1x1'))
            or (s.platform='facebook')
          )
          and not exists(
            select 1 from publish.outbox o
            where o.content_item_id=ci.id
              and o.platform=s.platform
              and o.format=v_desired_format
              and o.status not in('cancelled','failed')
          )
          and not exists(
            select 1 from publish.delivery_history h
            where h.content_item_id=ci.id
              and h.platform=s.platform
              and coalesce(h.format,'post')=v_desired_format
              and h.delivery_status not in('rebalanced_cancelled','deleted_before_publish','failed')
          )
          and not exists(
            select 1
            from publish.outbox o2
            join content.items ci2 on ci2.id=o2.content_item_id
            where o2.status in('approved','leased','scheduled')
              and ci2.metadata->>'source_record_hash'=ci.metadata->>'source_record_hash'
              and o2.scheduled_for>s.scheduled_for-interval '4 hours'
              and o2.scheduled_for<s.scheduled_for
          )
          and not exists(
            select 1
            from publish.delivery_history h2
            join content.items ci2 on ci2.id=h2.content_item_id
            where h2.delivery_status in('scheduled','published','sent')
              and ci2.metadata->>'source_record_hash'=ci.metadata->>'source_record_hash'
              and h2.scheduled_for>s.scheduled_for-interval '4 hours'
              and h2.scheduled_for<s.scheduled_for
          )
        order by coalesce(nullif(ci.metadata->>'global_rank','')::int,9999),ci.created_at desc,ci.id
        limit 1;
        v_candidate_found:=found;
      end if;
    end if;

    if not v_candidate_found then
      continue;
    end if;

    if c.metadata->>'origin'='ranked_product_creative' then
      select coalesce(array_agg(x order by ord),'{}'::text[])
        into v_hashtags
      from (
        select value x,ord
        from jsonb_array_elements_text(coalesce(c.metadata->'hashtags','[]'::jsonb))
             with ordinality a(value,ord)
        where ord<=case when s.platform='tiktok' then 5 else 10 end
      ) q;
      v_format:=v_desired_format;
    elsif c.metadata ? 'planned_platform' then
      select coalesce(array_agg(x order by ord),'{}'::text[])
        into v_hashtags
      from (
        select value x,ord
        from jsonb_array_elements_text(coalesce(c.metadata->'hashtags','[]'::jsonb))
             with ordinality a(value,ord)
        where ord<=case when s.platform='tiktok' then 5 else 10 end
      ) q;
      v_format:=v_desired_format;
    else
      v_hashtags:=coalesce(array(
        select jsonb_array_elements_text(coalesce(c.metadata->'hashtags','[]'::jsonb))
        limit case when s.platform='tiktok' then 5 else 10 end
      ),'{}'::text[]);
      v_format:='post';
    end if;

    insert into publish.outbox(
      content_item_id,platform,caption,hashtags,format,media_url,tracking_url,
      scheduled_for,priority,status,executor_metadata,updated_at
    ) values(
      c.id,s.platform,
      c.core_copy||case when position(c.tracking_url in c.core_copy)>0 then '' else E'\n\n'||c.tracking_url end,
      coalesce(v_hashtags,'{}'::text[]),v_format,c.media_url,c.tracking_url,
      s.scheduled_for,c.priority,'approved',
      jsonb_build_object(
        'scheduler_version','v3-native-formats','weekly_target',300,
        'facebook_site_share',v_site_share,'refilled_at',now(),
        'campaign_type',c.metadata->>'campaign_type','native_format',v_format,
        'source_mode',case when c.metadata ? 'planned_platform' then 'platform_specific_manual' else 'native' end
      ),now()
    )
    on conflict(content_item_id,platform,format) do nothing;

    if found then
      v_inserted:=v_inserted+1;
      if c.metadata ? 'planned_platform' then
        v_manual:=v_manual+1;
      elsif c.metadata->>'origin'='ranked_product_creative' then
        v_products:=v_products+1;
      elsif c.metadata->>'campaign_type'='pain_solver' then
        v_pain:=v_pain+1;
      else
        v_sites:=v_sites+1;
      end if;
      update content.items
      set status='queued',updated_at=now()
      where id=c.id and status='approved';
    end if;
  end loop;

  return jsonb_build_object(
    'ok',true,
    'inserted',v_inserted,
    'manual_platform_posts',v_manual,
    'product_posts',v_products,
    'pain_solver_posts',v_pain,
    'site_posts',v_sites,
    'horizon_hours',p_hours,
    'weekly_target',300,
    'channel_weekly',jsonb_build_object('facebook',110,'instagram',90,'tiktok',70,'linkedin',30),
    'instagram_formats',jsonb_build_array('post','reel','story'),
    'tiktok_formats',jsonb_build_array('photo','video'),
    'facebook_site_share',v_site_share,
    'site_pool',v_site_pool
  );
end $function$;
