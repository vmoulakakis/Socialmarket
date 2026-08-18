-- SocialScheduler v6: opportunity calendar with psychology/fatigue hard limits
-- Generated from production-tested Supabase state on 2026-08-19.

create table if not exists public.socialscheduler_frequency_policy (
  platform text primary key,
  base_target integer not null,
  min_target integer not null,
  hard_cap integer not null,
  min_gap_minutes integer not null,
  effective_target integer not null,
  last_week_score numeric,
  prior_week_score numeric,
  last_adjustment text,
  updated_at timestamptz not null default now(),
  constraint socialscheduler_frequency_policy_bounds check (
    min_target >= 1 and base_target >= min_target and hard_cap >= base_target
    and effective_target between min_target and hard_cap
  )
);

insert into public.socialscheduler_frequency_policy(platform,base_target,min_target,hard_cap,min_gap_minutes,effective_target,last_adjustment)
values
 ('facebook',2,1,3,240,2,'safe_baseline_v6'),
 ('instagram',2,1,3,240,2,'safe_baseline_v6'),
 ('tiktok',2,1,3,240,2,'safe_baseline_v6'),
 ('linkedin',1,1,2,360,1,'safe_baseline_v6')
on conflict(platform) do update set
 base_target=excluded.base_target,
 min_target=excluded.min_target,
 hard_cap=excluded.hard_cap,
 min_gap_minutes=excluded.min_gap_minutes,
 effective_target=least(excluded.hard_cap,greatest(excluded.min_target,public.socialscheduler_frequency_policy.effective_target)),
 updated_at=now();

create table if not exists public.socialscheduler_weekly_feedback (
  week_start date not null,
  platform text not null,
  provider_key text not null,
  posts integer not null default 0,
  views numeric not null default 0,
  reach numeric not null default 0,
  impressions numeric not null default 0,
  clicks numeric not null default 0,
  reactions numeric not null default 0,
  comments numeric not null default 0,
  shares numeric not null default 0,
  saves numeric not null default 0,
  avg_weighted_score numeric not null default 0,
  engagement_per_1000 numeric not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key(week_start,platform,provider_key)
);

alter table public.socialscheduler_frequency_policy enable row level security;
alter table public.socialscheduler_weekly_feedback enable row level security;
revoke all on public.socialscheduler_frequency_policy from anon, authenticated;
revoke all on public.socialscheduler_weekly_feedback from anon, authenticated;

create or replace function public.socialscheduler_weekly_feedback_v6()
returns jsonb
language plpgsql
security definer
set search_path=''
as $$
declare
  v_week_start date := ((date_trunc('week', now() at time zone 'Europe/Athens') - interval '7 days')::date);
  v_week_end date := ((date_trunc('week', now() at time zone 'Europe/Athens'))::date);
  r record;
  v_prev numeric;
  v_curr numeric;
  v_posts integer;
  v_old_target integer;
  v_new_target integer;
  v_action text;
begin
  perform public.socialscheduler_sync_feedback_v4();
  insert into public.socialscheduler_weekly_feedback(
    week_start,platform,provider_key,posts,views,reach,impressions,clicks,reactions,comments,shares,saves,
    avg_weighted_score,engagement_per_1000,updated_at
  )
  select v_week_start,lower(f.platform),coalesce(nullif(f.provider_key,''),'unknown'),count(*)::int,
         coalesce(sum(f.views),0),coalesce(sum(f.reach),0),coalesce(sum(f.impressions),0),coalesce(sum(f.clicks),0),
         coalesce(sum(f.reactions),0),coalesce(sum(f.comments),0),coalesce(sum(f.shares),0),coalesce(sum(f.saves),0),
         coalesce(avg(f.weighted_score),0),
         round((1000.0*(coalesce(sum(f.clicks),0)+coalesce(sum(f.reactions),0)+coalesce(sum(f.comments),0)+coalesce(sum(f.shares),0)+coalesce(sum(f.saves),0)) /
           greatest(1,coalesce(nullif(sum(f.reach),0),nullif(sum(f.impressions),0),nullif(sum(f.views),0),count(*)::numeric)))::numeric,4),now()
  from public.socialscheduler_post_feedback f
  where (f.scheduled_for at time zone 'Europe/Athens')::date >= v_week_start
    and (f.scheduled_for at time zone 'Europe/Athens')::date < v_week_end
  group by lower(f.platform),coalesce(nullif(f.provider_key,''),'unknown')
  on conflict(week_start,platform,provider_key) do update set
    posts=excluded.posts,views=excluded.views,reach=excluded.reach,impressions=excluded.impressions,
    clicks=excluded.clicks,reactions=excluded.reactions,comments=excluded.comments,shares=excluded.shares,saves=excluded.saves,
    avg_weighted_score=excluded.avg_weighted_score,engagement_per_1000=excluded.engagement_per_1000,updated_at=now();

  for r in select * from public.socialscheduler_frequency_policy order by platform loop
    select coalesce(sum(posts),0)::int,
           case when sum(posts)>0 then sum(avg_weighted_score*posts)/sum(posts) else 0 end
      into v_posts,v_curr
    from public.socialscheduler_weekly_feedback
    where week_start=v_week_start and platform=r.platform;

    select case when sum(posts)>0 then sum(avg_weighted_score*posts)/sum(posts) else null end
      into v_prev
    from public.socialscheduler_weekly_feedback
    where week_start=v_week_start-7 and platform=r.platform;

    v_old_target:=r.effective_target;
    v_new_target:=v_old_target;
    v_action:='hold_sample_or_signal';
    if v_posts>=7 and v_prev is not null and v_prev>0 then
      if v_curr>=v_prev*1.15 then
        v_new_target:=least(r.hard_cap,v_old_target+1);
        v_action:=case when v_new_target>v_old_target then 'increase_one_strong_week' else 'hold_at_hard_cap' end;
      elsif v_curr<=v_prev*0.82 then
        v_new_target:=greatest(r.min_target,v_old_target-1);
        v_action:=case when v_new_target<v_old_target then 'decrease_one_fatigue_guard' else 'hold_at_minimum' end;
      else
        v_action:='hold_stable_week';
      end if;
    elsif v_posts>=14 and v_prev is null then
      v_action:='hold_first_evidence_week';
    end if;

    update public.socialscheduler_frequency_policy
       set prior_week_score=v_prev,last_week_score=v_curr,effective_target=v_new_target,
           last_adjustment=v_action,updated_at=now()
     where platform=r.platform;
  end loop;
  return jsonb_build_object('ok',true,'week_start',v_week_start,'week_end',v_week_end,
    'policy',(select jsonb_agg(to_jsonb(p) order by p.platform) from public.socialscheduler_frequency_policy p));
end $$;

create or replace function public.socialscheduler_frequency_guard_v6(p_platform text,p_at timestamptz,p_brand_site_id uuid default null)
returns boolean
language plpgsql
volatile
set search_path=''
as $$
declare
  p record;
  v_day date := (p_at at time zone 'Europe/Athens')::date;
  v_total integer:=0;
  v_brand integer:=0;
  v_near integer:=0;
begin
  select * into p from public.socialscheduler_frequency_policy where platform=lower(p_platform);
  if not found then return false; end if;
  select count(*)::int into v_total from (
    select 1 from publish.outbox o where lower(o.platform)=lower(p_platform)
      and (o.scheduled_for at time zone 'Europe/Athens')::date=v_day and o.status in('approved','leased','scheduled')
    union all
    select 1 from publish.delivery_history h where lower(h.platform)=lower(p_platform)
      and (h.scheduled_for at time zone 'Europe/Athens')::date=v_day and h.delivery_status in('scheduled','published','sent')
  ) x;
  if v_total>=p.hard_cap then return false; end if;
  select count(*)::int into v_near from (
    select o.scheduled_for from publish.outbox o where lower(o.platform)=lower(p_platform) and o.status in('approved','leased','scheduled')
    union all
    select h.scheduled_for from publish.delivery_history h where lower(h.platform)=lower(p_platform) and h.delivery_status in('scheduled','published','sent')
  ) q where abs(extract(epoch from(q.scheduled_for-p_at))) < p.min_gap_minutes*60;
  if v_near>0 then return false; end if;
  if p_brand_site_id is not null then
    select count(*)::int into v_brand from (
      select 1 from publish.outbox o join content.items ci on ci.id=o.content_item_id
       where ci.brand_site_id=p_brand_site_id and lower(o.platform)=lower(p_platform)
         and (o.scheduled_for at time zone 'Europe/Athens')::date=v_day and o.status in('approved','leased','scheduled')
      union all
      select 1 from publish.delivery_history h join content.items ci on ci.id=h.content_item_id
       where ci.brand_site_id=p_brand_site_id and lower(h.platform)=lower(p_platform)
         and (h.scheduled_for at time zone 'Europe/Athens')::date=v_day and h.delivery_status in('scheduled','published','sent')
    ) b;
    if v_brand>=1 then return false; end if;
  end if;
  return true;
end $$;

create or replace function publish.generate_slots_v6(p_from timestamptz default now(),p_hours integer default 72)
returns table(platform text,scheduled_for timestamptz,slot_no integer,local_day date)
language sql
stable
set search_path=''
as $$
with days as (
  select d::date local_day,extract(isodow from d)::int dow
  from generate_series((p_from at time zone 'Europe/Athens')::date,
    ((p_from+make_interval(hours=>greatest(12,least(coalesce(p_hours,72),168)))) at time zone 'Europe/Athens')::date,interval '1 day') d
), candidate_hours(platform,hr,ord) as (
  values ('facebook',9,1),('facebook',14,2),('facebook',19,3),
         ('instagram',10,1),('instagram',15,2),('instagram',20,3),
         ('tiktok',11,1),('tiktok',16,2),('tiktok',21,3),
         ('linkedin',9,1),('linkedin',16,2)
), hist as (
  select lower(platform) platform,extract(isodow from scheduled_for at time zone 'Europe/Athens')::int dow,
         extract(hour from scheduled_for at time zone 'Europe/Athens')::int hr,count(*)::int evidence_posts,avg(weighted_score)::numeric avg_score
  from public.socialscheduler_post_feedback where scheduled_for>=now()-interval '120 days' group by 1,2,3
), scored as (
  select d.local_day,d.dow,c.platform,c.hr,c.ord,
         least(case when c.platform='linkedin' and d.dow>=6 then 1 else p.effective_target end,p.hard_cap)::int target_n,
         (case c.platform when 'facebook' then case c.hr when 19 then 92 when 14 then 82 else 76 end
                          when 'instagram' then case c.hr when 20 then 94 when 15 then 84 else 78 end
                          when 'tiktok' then case c.hr when 21 then 96 when 16 then 84 else 74 end
                          when 'linkedin' then case c.hr when 9 then 94 else 80 end else 50 end
          + least(45,ln(1+greatest(0,coalesce(h.avg_score,0)))*10)
          + least(15,coalesce(h.evidence_posts,0)*1.5))::numeric score,
         (5+mod(abs(hashtext(c.platform||d.local_day::text||c.hr::text)::bigint),14)::int)::int minute_of_hour
  from days d cross join candidate_hours c join public.socialscheduler_frequency_policy p on p.platform=c.platform
  left join hist h on h.platform=c.platform and h.dow=d.dow and h.hr=c.hr
), ranked as (
  select s.*,row_number() over(partition by platform,local_day order by score desc,ord asc)::int rn from scored s
), chosen as (
  select platform,local_day,hr,minute_of_hour,row_number() over(partition by platform,local_day order by hr)::int slot_no
  from ranked where rn<=target_n
), final as (
  select platform,((local_day+make_time(hr,minute_of_hour,0)) at time zone 'Europe/Athens') scheduled_for,slot_no,local_day from chosen
)
select platform,scheduled_for,slot_no,local_day from final
where scheduled_for>p_from+interval '5 minutes'
  and scheduled_for<=p_from+make_interval(hours=>greatest(12,least(coalesce(p_hours,72),168)))
order by scheduled_for,platform
$$;

create or replace function public.socialscheduler_next_slot(p_platform text,p_after timestamptz default now())
returns timestamptz
language plpgsql
volatile
set search_path=''
as $$
declare v_ts timestamptz;v_day date;d integer;h integer;v_hours integer[];v_minute integer;
begin
  select s.scheduled_for into v_ts from publish.generate_slots_v6(p_after,168) s
  where s.platform=lower(p_platform) and s.scheduled_for>p_after+interval '15 minutes'
    and public.socialscheduler_frequency_guard_v6(lower(p_platform),s.scheduled_for,null)
  order by s.scheduled_for asc limit 1;
  if v_ts is not null then return v_ts; end if;
  for d in 1..28 loop
    v_day:=(p_after at time zone 'Europe/Athens')::date+d;
    v_hours:=case lower(p_platform)
      when 'facebook' then array[9,14,19] when 'instagram' then array[10,15,20]
      when 'tiktok' then array[11,16,21]
      when 'linkedin' then case when extract(isodow from v_day)::int>=6 then array[10] else array[9,16] end
      else array[]::integer[] end;
    if cardinality(v_hours)=0 then return null; end if;
    foreach h in array v_hours loop
      v_minute:=5+mod(abs(hashtext(lower(p_platform)||v_day::text||h::text)::bigint),14)::int;
      v_ts:=((v_day+make_time(h,v_minute,0)) at time zone 'Europe/Athens');
      if public.socialscheduler_frequency_guard_v6(lower(p_platform),v_ts,null) then return v_ts; end if;
    end loop;
  end loop;
  return null;
end $$;

create or replace function public.socialscheduler_assign_provider_trigger()
returns trigger
language plpgsql
set search_path=''
as $$
declare v_provider text;v_ts timestamptz;v_brand uuid;v_try integer:=0;
begin
  if tg_op='INSERT' and new.status='approved' then
    select ci.brand_site_id into v_brand from content.items ci where ci.id=new.content_item_id;
    if new.scheduled_for is null or not public.socialscheduler_frequency_guard_v6(new.platform,new.scheduled_for,v_brand) then
      v_ts:=public.socialscheduler_next_slot(new.platform,now());
      while v_ts is not null and v_try<8 loop
        exit when public.socialscheduler_frequency_guard_v6(new.platform,v_ts,v_brand);
        v_ts:=public.socialscheduler_next_slot(new.platform,v_ts+interval '5 minutes');v_try:=v_try+1;
      end loop;
      if v_ts is null or not public.socialscheduler_frequency_guard_v6(new.platform,v_ts,v_brand) then
        raise exception 'no_safe_frequency_slot:%',new.platform;
      end if;
      new.scheduled_for:=v_ts;
    end if;
    new.executor_metadata:=coalesce(new.executor_metadata,'{}'::jsonb)||jsonb_build_object(
      'schedule_optimizer',coalesce(new.executor_metadata->'schedule_optimizer','{}'::jsonb)||jsonb_build_object(
        'optimized',true,'policy','v6-psychology-bounded','frequency_guard',true,'fatigue_guard',true,'optimized_at',now()));
  end if;
  if coalesce(new.executor_metadata #>> '{orchestrator,provider_key}','')='' then
    v_provider:=public.socialscheduler_choose_provider(new.platform);
    if v_provider is not null then
      new.executor_metadata:=coalesce(new.executor_metadata,'{}'::jsonb)||jsonb_build_object(
        'orchestrator',coalesce(new.executor_metadata->'orchestrator','{}'::jsonb)||jsonb_build_object(
          'provider_key',v_provider,'assigned_at',now(),'policy','dynamic-performance-v3'));
    end if;
  end if;
  return new;
end $$;

-- Existing publish.refill_opportunity_outbox_v6 remains the opportunity selector.
-- Compatibility bridge guarantees older publishing gateways cannot bypass v6.
create or replace function public.worker_v3_outbox_refill(p_hours integer default 72)
returns jsonb language sql set search_path='' as $$ select public.worker_v6_outbox_refill(p_hours) $$;

revoke execute on function public.socialscheduler_weekly_feedback_v6() from anon,authenticated;
revoke execute on function public.socialscheduler_frequency_guard_v6(text,timestamptz,uuid) from anon,authenticated;

DO $$
declare r record;
begin
  for r in select jobid from cron.job where jobname in(
    'socialscheduler-outbox-refill','socialscheduler-morning-horizon-refill',
    'socialscheduler-feedback-sync-v6','socialscheduler-weekly-feedback-v6'
  ) loop perform cron.unschedule(r.jobid); end loop;
  perform cron.schedule('socialscheduler-outbox-refill','*/30 * * * *','select public.worker_v6_outbox_refill(72);');
  perform cron.schedule('socialscheduler-morning-horizon-refill','20 4 * * *','select public.worker_v6_outbox_refill(168); select public.socialscheduler_rebalance_approved_jobs();');
  perform cron.schedule('socialscheduler-feedback-sync-v6','17,47 * * * *','select public.socialscheduler_sync_feedback_v4();');
  perform cron.schedule('socialscheduler-weekly-feedback-v6','15 3 * * 1','select public.socialscheduler_weekly_feedback_v6();');
end $$;
