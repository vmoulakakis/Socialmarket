alter table publish.affiliate_short_links
  drop constraint if exists affiliate_short_links_destination_url_check;
alter table publish.affiliate_short_links
  add constraint affiliate_short_links_destination_url_check
  check (destination_url ~ '^https://go[.]linkwi[.]se/');

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
  if v_destination is null or v_destination !~ '^https://go[.]linkwi[.]se/' then return null; end if;
  insert into public.socialscheduler_affiliate_clicks(seed_key,platform,campaign,user_agent,destination_host)
  values(p_seed_key,v_platform,nullif(left(coalesce(p_campaign,''),120),''),nullif(left(coalesce(p_user_agent,''),500),''),'go.linkwi.se');
  return v_destination;
end $$;
revoke all on function public.socialscheduler_track_affiliate_click(text,text,text,text) from public,anon,authenticated;
grant execute on function public.socialscheduler_track_affiliate_click(text,text,text,text) to service_role;
