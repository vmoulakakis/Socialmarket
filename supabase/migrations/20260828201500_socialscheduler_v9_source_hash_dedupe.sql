-- SocialScheduler v9: source_record_hash dedupe and cleanup of duplicate active rows inserted during recovery.

create or replace function publish.refill_verified_affiliate_outbox_v8(p_hours integer default 168)
returns jsonb
language plpgsql
security definer
set search_path=''
as $$
declare
  s record;
  c record;
  n int := 0;
  skipped_no_provider int := 0;
  tags text[];
  caption_text text;
  asset_url text;
  provider text;
begin
  for s in
    select *
    from publish.generate_slots_v6(now(), least(greatest(p_hours, 24), 168))
    order by scheduled_for, platform
  loop
    if not public.socialscheduler_frequency_guard_v8(s.platform, s.scheduled_for, null) then
      continue;
    end if;

    select ci.* into c
    from content.items ci
    where ci.status in ('approved','queued')
      and ci.metadata->>'origin' = 'ranked_product_creative'
      and ci.metadata#>>'{creative_audit,verdict}' = 'READY'
      and ci.metadata#>>'{asset_validation,status}' = 'ready'
      and ci.metadata->>'image_provenance' in ('merchant_feed','merchant_og','merchant_product_page')
      and coalesce((ci.metadata->>'affiliate_disclosure')::boolean, false)
      and jsonb_array_length(coalesce(ci.metadata->'risk_flags','[]')) = 0
      and ci.tracking_url like 'https://%'
      and coalesce(ci.metadata#>>'{tracking_validation,status}', 'structurally_valid') in ('structurally_valid','verified')
      and ci.metadata->'platform_assets' ? s.platform
      and ci.metadata->'platform_copy' ? s.platform
      and not exists (
        select 1 from publish.outbox o
        where o.content_item_id = ci.id
          and o.platform = s.platform
          and o.status not in ('cancelled','failed','failed_permanent','rejected','superseded')
      )
      and not exists (
        select 1
        from publish.outbox o
        join content.items oi on oi.id = o.content_item_id
        where o.platform = s.platform
          and o.status not in ('cancelled','failed','failed_permanent','rejected','superseded')
          and coalesce(oi.metadata->>'source_record_hash', oi.id::text) = coalesce(ci.metadata->>'source_record_hash', ci.id::text)
      )
      and not exists (
        select 1 from publish.delivery_history h
        where h.content_item_id = ci.id
          and h.platform = s.platform
          and h.delivery_status not in ('rebalanced_cancelled','deleted_before_publish','failed','cancelled','cancelled_before_publish')
      )
      and not exists (
        select 1
        from publish.delivery_history h
        join content.items hi on hi.id = h.content_item_id
        where h.platform = s.platform
          and h.delivery_status not in ('rebalanced_cancelled','deleted_before_publish','failed','cancelled','cancelled_before_publish')
          and coalesce(hi.metadata->>'source_record_hash', hi.id::text) = coalesce(ci.metadata->>'source_record_hash', ci.id::text)
      )
      and public.socialscheduler_frequency_guard_v8(s.platform, s.scheduled_for, ci.brand_site_id)
      and (
        (
          ci.metadata ? 'audited_conversion'
          and ci.metadata#>>'{audited_conversion,decision}' in ('SOCIAL_READY','PRIORITY_SOCIAL','HIGH_TICKET_TEST','VIRAL_TEST')
          and coalesce((ci.metadata#>>'{audited_conversion,final_ai_conversion_score}')::numeric, 0) >= 70
          and coalesce(ci.metadata#>>'{audited_conversion,logistics,status}', '') <> 'LOGISTICS_REJECTED'
        )
        or
        (
          ci.metadata->>'scheduler_version' = 'v8-conversion-first'
          and coalesce((ci.metadata->>'expected_commission_eur')::numeric, 0) >= 15
          and coalesce((ci.metadata->>'ranking_score')::numeric, 0) >= 35
          and (coalesce(ci.title,'') || ' ' || coalesce(ci.metadata->>'category','')) ~* '(cctv|camera|κάμερα|security|ασφαλ|robot|πισίνα|office|γραφείο|καρέκλ|car|auto|αυτοκιν|inverter|led|power|εργαλ|tool|school|σχολ|φοιτητ|travel|ταξιδ|pet|σκυλ|γατ|σκούπα)'
        )
      )
    order by
      case when ci.metadata ? 'audited_conversion' then 0 else 1 end,
      coalesce((ci.metadata#>>'{audited_conversion,final_ai_conversion_score}')::numeric, 0) desc,
      coalesce((ci.metadata->>'ranking_score')::numeric, 0) desc,
      coalesce((ci.metadata->>'expected_commission_eur')::numeric, 0) desc,
      ci.updated_at desc
    limit 1;

    if not found then
      continue;
    end if;

    provider := public.socialscheduler_choose_provider(s.platform);
    if provider is null then
      skipped_no_provider := skipped_no_provider + 1;
      continue;
    end if;

    caption_text := c.metadata #>> array['platform_copy', s.platform, 'caption'];
    asset_url := c.metadata #>> array['platform_assets', s.platform];

    select coalesce(array_agg(value order by ord), '{}'::text[])
      into tags
    from jsonb_array_elements_text(coalesce(c.metadata #> array['platform_copy', s.platform, 'hashtags'], '[]'::jsonb))
         with ordinality a(value, ord)
    where ord <= case when s.platform = 'tiktok' then 5 else 10 end;

    insert into publish.outbox(
      content_item_id, platform, caption, hashtags, format, media_url, tracking_url,
      scheduled_for, priority, status, executor_metadata, updated_at
    )
    values(
      c.id,
      s.platform,
      caption_text,
      tags,
      case when s.platform = 'tiktok' then 'photo' else 'post' end,
      asset_url,
      c.tracking_url,
      s.scheduled_for,
      case when c.metadata ? 'audited_conversion' then 90 else 75 end,
      'approved',
      jsonb_build_object(
        'scheduler_version', 'v9-source-hash-dedupe',
        'verified_seed', true,
        'audited_conversion_required_for_new_runs', true,
        'legacy_safe_bridge', not (c.metadata ? 'audited_conversion'),
        'source_record_hash', c.metadata->>'source_record_hash',
        'creative_json', true,
        'exact_qr', true,
        'orchestrator', jsonb_build_object(
          'provider_key', provider,
          'assigned_at', now(),
          'policy', 'explicit-route-v9-source-hash-dedupe'
        )
      ),
      now()
    )
    on conflict(content_item_id, platform, format) do nothing;

    if found then
      n := n + 1;
    end if;
  end loop;

  return jsonb_build_object(
    'ok', true,
    'version', 'v9-source-hash-dedupe',
    'inserted', n,
    'skipped_no_provider', skipped_no_provider,
    'horizon_hours', least(p_hours, 168)
  );
end $$;

with ranked as (
  select o.id,
         row_number() over (
           partition by lower(o.platform), coalesce(ci.metadata->>'source_record_hash', ci.id::text)
           order by o.scheduled_for asc, o.created_at asc
         ) rn
  from publish.outbox o
  join content.items ci on ci.id = o.content_item_id
  where o.status in ('approved','leased','scheduled')
)
update publish.outbox o
set status = 'cancelled',
    last_error = 'cancelled_by_v9_source_hash_dedupe',
    executor_metadata = coalesce(o.executor_metadata, '{}'::jsonb) || jsonb_build_object('dedupe_cancelled_by', 'v9_source_hash_dedupe', 'dedupe_cancelled_at', now()),
    updated_at = now()
from ranked r
where o.id = r.id
  and r.rn > 1;

update ops.socialscheduler_config
set config = config || jsonb_build_object(
      'refill_policy', 'v9-source-hash-dedupe',
      'source_record_hash_dedupe', true,
      'refill_policy_updated_at', to_jsonb(now())
    ),
    version = version + 1,
    updated_by = 'socialscheduler_v9_source_hash_dedupe_fix',
    updated_at = now()
where id = 1;
