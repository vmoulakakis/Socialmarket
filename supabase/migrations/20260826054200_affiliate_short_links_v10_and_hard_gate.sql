-- SocialMarket v10: private short-link registry and emergency scheduling hard gate.
create table if not exists publish.affiliate_short_links (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique check (slug ~ '^[a-z0-9][a-z0-9-]{7,31}$'),
  run_id uuid references intel.product_ranking_runs(id) on delete set null,
  source_record_hash text not null,
  destination_url text not null check (destination_url ~ '^https://go\\.linkwi\\.se/'),
  active boolean not null default true,
  valid_from timestamptz not null default now(),
  valid_to timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(source_record_hash,destination_url)
);
alter table publish.affiliate_short_links enable row level security;
revoke all on publish.affiliate_short_links from public,anon,authenticated;

create table if not exists ops.product_exclusion_rules (
  rule_key text primary key,
  field text not null check(field in ('merchant','category','subcategory','product')),
  pattern text not null,
  reason text not null,
  active boolean not null default true,
  created_at timestamptz not null default now()
);
alter table ops.product_exclusion_rules enable row level security;
revoke all on ops.product_exclusion_rules from public,anon,authenticated;

insert into ops.product_exclusion_rules(rule_key,field,pattern,reason) values
 ('lodging_merchant','merchant','(hotel|hostel|resort|accommodation|booking\\.com|expedia|airbnb|ξενοδοχ|κατάλυμ|διαμον)','excluded_hotel_accommodation'),
 ('lodging_category','category','(hotel|hostel|resort|accommodation|lodging|ξενοδοχ|κατάλυμ|διαμον)','excluded_hotel_accommodation'),
 ('travel_package_product','product','(travel package|holiday package|flight[ +]hotel|πακέτο διακοπών|τουριστικό πακέτο)','excluded_travel_package')
on conflict(rule_key) do update set pattern=excluded.pattern,reason=excluded.reason,active=true;

create or replace function public.socialscheduler_track_affiliate_click(
  p_seed_key text,p_platform text default 'unknown',p_campaign text default null,p_user_agent text default null
) returns text language plpgsql security definer set search_path='' as $$
declare v_destination text; v_platform text;
begin
  if p_seed_key !~ '^[a-z0-9][a-z0-9-]{1,63}$' then return null; end if;
  v_platform := case when lower(coalesce(p_platform,'')) in ('facebook','instagram','tiktok','linkedin') then lower(p_platform) else 'unknown' end;
  select l.destination_url into v_destination from publish.affiliate_short_links l
   where l.slug=p_seed_key and l.active and now()>=l.valid_from and (l.valid_to is null or now()<=l.valid_to) limit 1;
  if v_destination is null then
    select s.tracking_url into v_destination from ops.pain_solver_campaign_seeds s
     where s.seed_key=p_seed_key and s.status='active' and s.tracking_url is not null
       and (s.season_start is null or current_date>=s.season_start)
       and (s.season_end is null or current_date<=s.season_end) limit 1;
  end if;
  if v_destination is null or v_destination !~ '^https://go\\.linkwi\\.se/' then return null; end if;
  insert into public.socialscheduler_affiliate_clicks(seed_key,platform,campaign,user_agent,destination_host)
  values(p_seed_key,v_platform,nullif(left(coalesce(p_campaign,''),120),''),nullif(left(coalesce(p_user_agent,''),500),''),'go.linkwi.se');
  return v_destination;
end $$;
revoke all on function public.socialscheduler_track_affiliate_click(text,text,text,text) from public,anon,authenticated;
grant execute on function public.socialscheduler_track_affiliate_click(text,text,text,text) to service_role;
revoke execute on function public.socialscheduler_audit_worker_v9() from public,anon,authenticated;
revoke execute on function public.worker_v9_poster_outbox_refill(integer,boolean) from public,anon,authenticated;
