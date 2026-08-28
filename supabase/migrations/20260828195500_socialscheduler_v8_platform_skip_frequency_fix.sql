-- SocialScheduler v8 hotfix: platform skip instead of run-killing no_safe_frequency_slot.
-- Scope: safe no-paid-spend frequency caps, brand-aware next slot, and nonfatal platform skip.

update public.socialscheduler_frequency_policy
set base_target = v.base_target,
    min_target = v.min_target,
    hard_cap = v.hard_cap,
    min_gap_minutes = v.min_gap_minutes,
    effective_target = v.effective_target,
    last_adjustment = 'v8_safe_recovery_after_no_safe_frequency_slot',
    updated_at = now()
from (values
  ('facebook'::text, 1, 1, 2, 360, 1),
  ('instagram'::text, 1, 1, 2, 360, 1),
  ('tiktok'::text, 2, 1, 3, 360, 2),
  ('linkedin'::text, 1, 1, 1, 480, 1)
) as v(platform, base_target, min_target, hard_cap, min_gap_minutes, effective_target)
where public.socialscheduler_frequency_policy.platform = v.platform;

create or replace function public.socialscheduler_frequency_guard_v8(
  p_platform text,
  p_at timestamptz,
  p_brand_site_id uuid default null
)
returns boolean
language plpgsql
volatile
set search_path=''
as $$
declare
  p record;
  day_local date := (p_at at time zone 'Europe/Athens')::date;
  n int := 0;
  near_n int := 0;
  brand_n int := 0;
begin
  select * into p
  from public.socialscheduler_frequency_policy
  where platform = lower(p_platform);

  if not found or p_at is null then
    return false;
  end if;

  with live_posts as (
    select o.id as logical_id, o.content_item_id, o.scheduled_for
    from publish.outbox o
    where lower(o.platform) = lower(p_platform)
      and o.scheduled_for is not null
      and o.status in ('approved','leased','scheduled','published')
      and not exists (
        select 1
        from publish.delivery_history h
        where h.original_outbox_id = o.id
          and h.delivery_status in ('scheduled','published','sent')
      )
    union all
    select coalesce(h.original_outbox_id, h.id) as logical_id, h.content_item_id, h.scheduled_for
    from publish.delivery_history h
    where lower(h.platform) = lower(p_platform)
      and h.scheduled_for is not null
      and h.delivery_status in ('scheduled','published','sent')
  )
  select count(*)::int,
         count(*) filter (where abs(extract(epoch from (scheduled_for - p_at))) < p.min_gap_minutes * 60)::int
    into n, near_n
  from live_posts
  where (scheduled_for at time zone 'Europe/Athens')::date = day_local;

  if n >= p.hard_cap or near_n > 0 then
    return false;
  end if;

  if p_brand_site_id is not null then
    with live_posts as (
      select o.id as logical_id, o.content_item_id, o.scheduled_for
      from publish.outbox o
      where lower(o.platform) = lower(p_platform)
        and o.scheduled_for is not null
        and o.status in ('approved','leased','scheduled','published')
        and not exists (
          select 1
          from publish.delivery_history h
          where h.original_outbox_id = o.id
            and h.delivery_status in ('scheduled','published','sent')
        )
      union all
      select coalesce(h.original_outbox_id, h.id) as logical_id, h.content_item_id, h.scheduled_for
      from publish.delivery_history h
      where lower(h.platform) = lower(p_platform)
        and h.scheduled_for is not null
        and h.delivery_status in ('scheduled','published','sent')
    )
    select count(*)::int
      into brand_n
    from live_posts lp
    join content.items ci on ci.id = lp.content_item_id
    where ci.brand_site_id = p_brand_site_id
      and (lp.scheduled_for at time zone 'Europe/Athens')::date = day_local;

    if brand_n >= 1 then
      return false;
    end if;
  end if;

  return true;
end $$;

create or replace function public.socialscheduler_next_slot_v8(
  p_platform text,
  p_after timestamptz default now(),
  p_brand_site_id uuid default null
)
returns timestamptz
language plpgsql
volatile
set search_path=''
as $$
declare
  ts timestamptz;
  day_local date;
  d int;
  h int;
  hours int[];
  minute_part int;
begin
  select s.scheduled_for
    into ts
  from publish.generate_slots_v6(p_after, 168) s
  where s.platform = lower(p_platform)
    and s.scheduled_for > p_after + interval '15 minutes'
    and public.socialscheduler_frequency_guard_v8(lower(p_platform), s.scheduled_for, p_brand_site_id)
  order by s.scheduled_for
  limit 1;

  if ts is not null then
    return ts;
  end if;

  for d in 1..42 loop
    day_local := (p_after at time zone 'Europe/Athens')::date + d;
    hours := case lower(p_platform)
      when 'facebook' then array[9,14,19]
      when 'instagram' then array[10,15,20]
      when 'tiktok' then array[11,16,21]
      when 'linkedin' then case when extract(isodow from day_local)::int >= 6 then array[10] else array[9,16] end
      else array[]::int[]
    end;

    foreach h in array hours loop
      minute_part := 5 + mod(abs(hashtext(lower(p_platform) || day_local::text || h::text)::bigint), 14)::int;
      ts := ((day_local + make_time(h, minute_part, 0)) at time zone 'Europe/Athens');
      if public.socialscheduler_frequency_guard_v8(lower(p_platform), ts, p_brand_site_id) then
        return ts;
      end if;
    end loop;
  end loop;

  return null;
end $$;

create or replace function public.socialscheduler_frequency_guard_v7(
  p_platform text,
  p_at timestamptz,
  p_brand_site_id uuid default null
)
returns boolean
language sql
volatile
set search_path=''
as $$
  select public.socialscheduler_frequency_guard_v8(p_platform, p_at, p_brand_site_id)
$$;

create or replace function public.socialscheduler_next_slot(
  p_platform text,
  p_after timestamptz default now()
)
returns timestamptz
language sql
volatile
set search_path=''
as $$
  select public.socialscheduler_next_slot_v8(p_platform, p_after, null)
$$;

create or replace function public.socialscheduler_assign_provider_trigger()
returns trigger
language plpgsql
set search_path=''
as $$
declare
  v_provider text;
  v_ts timestamptz;
  v_brand uuid;
begin
  if new.status = 'approved' then
    select ci.brand_site_id into v_brand
    from content.items ci
    where ci.id = new.content_item_id;

    if new.scheduled_for is null
       or not public.socialscheduler_frequency_guard_v8(new.platform, new.scheduled_for, v_brand) then
      v_ts := public.socialscheduler_next_slot_v8(new.platform, now(), v_brand);

      if v_ts is null then
        -- Critical change: a saturated platform is skipped, not allowed to abort the whole Night Brain finalize.
        new.status := 'cancelled';
        new.scheduled_for := coalesce(new.scheduled_for, now() + interval '365 days');
        new.last_error := 'platform_skip_no_safe_frequency_slot:' || lower(new.platform);
        new.executor_metadata := coalesce(new.executor_metadata, '{}'::jsonb) || jsonb_build_object(
          'schedule_optimizer', coalesce(new.executor_metadata->'schedule_optimizer', '{}'::jsonb) || jsonb_build_object(
            'optimized', false,
            'skipped', true,
            'skip_reason', 'no_safe_frequency_slot',
            'platform', lower(new.platform),
            'policy', 'v8-platform-skip-not-run-failure',
            'frequency_guard', true,
            'fatigue_guard', true,
            'optimized_at', now()
          )
        );
      else
        new.scheduled_for := v_ts;
        new.executor_metadata := coalesce(new.executor_metadata, '{}'::jsonb) || jsonb_build_object(
          'schedule_optimizer', coalesce(new.executor_metadata->'schedule_optimizer', '{}'::jsonb) || jsonb_build_object(
            'optimized', true,
            'policy', 'v8-brand-aware-platform-skip-safe',
            'frequency_guard', true,
            'fatigue_guard', true,
            'optimized_at', now()
          )
        );
      end if;
    else
      new.executor_metadata := coalesce(new.executor_metadata, '{}'::jsonb) || jsonb_build_object(
        'schedule_optimizer', coalesce(new.executor_metadata->'schedule_optimizer', '{}'::jsonb) || jsonb_build_object(
          'optimized', true,
          'policy', 'v8-existing-slot-validated',
          'frequency_guard', true,
          'fatigue_guard', true,
          'optimized_at', now()
        )
      );
    end if;
  end if;

  if new.status in ('approved','leased','scheduled')
     and coalesce(new.executor_metadata #>> '{orchestrator,provider_key}', '') = '' then
    v_provider := public.socialscheduler_choose_provider(new.platform);
    if v_provider is not null then
      new.executor_metadata := coalesce(new.executor_metadata, '{}'::jsonb) || jsonb_build_object(
        'orchestrator', coalesce(new.executor_metadata->'orchestrator', '{}'::jsonb) || jsonb_build_object(
          'provider_key', v_provider,
          'assigned_at', now(),
          'policy', 'dynamic-performance-v8-platform-safe'
        )
      );
    end if;
  end if;

  return new;
end $$;

update ops.socialscheduler_config
set config = jsonb_set(
               jsonb_set(
                 jsonb_set(config, '{weekly_target}', '38'::jsonb, true),
                 '{channel_weekly}', '{"facebook":10,"instagram":10,"tiktok":14,"linkedin":4}'::jsonb, true
               ),
               '{handoff_contract,facebook_slot_failure_mode}', '"platform_skip_not_run_failure"'::jsonb, true
             ) || jsonb_build_object(
               'safe_recovery_mode', 'v8-platform-skip-no-paid-spend',
               'recovery_updated_at', to_jsonb(now())
             ),
    version = version + 1,
    updated_by = 'socialscheduler_v8_platform_skip_fix',
    updated_at = now()
where id = 1;
