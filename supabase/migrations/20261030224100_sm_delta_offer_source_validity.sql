-- SocialMarket delta feed: start/end validity are source facts, never inferred.
create or replace function sm_intel.source_offer_valid_now(p_raw jsonb,p_valid_to timestamptz)
returns boolean language plpgsql stable security invoker set search_path='' as $$
declare v_from text;v_to text;start_at timestamptz;
begin
 v_from:=nullif(trim(p_raw->>'valid_from'),'');
 v_to:=nullif(trim(p_raw->>'valid_to'),'');
 if v_from is not null then
  begin
   start_at:=v_from::timestamptz;
  exception when invalid_datetime_format or datetime_field_overflow then
   return false;
  end;
  if start_at>now() then return false; end if;
 end if;
 if v_to is not null then
  if p_valid_to is null or p_valid_to<=now() then return false; end if;
 end if;
 return true;
end $$;
revoke all on function sm_intel.source_offer_valid_now(jsonb,timestamptz) from public,anon,authenticated;
grant execute on function sm_intel.source_offer_valid_now(jsonb,timestamptz) to service_role;

create or replace view sm_intel.promotion_ready_offers with (security_invoker=true) as
select q.id as qualified_offer_id,q.raw_product_id,q.merchant_profile_id,
       r.product_title,r.category_raw,r.source_product_id,
       q.price_eur,q.calculated_commission_eur,q.tracking_url,q.valid_to
from sm_intel.qualified_offers q
join sm_intel.raw_products r on r.id=q.raw_product_id
join sm_intel.commission_terms t on t.id=q.commission_terms_id
join sm_intel.feed_runs f on f.id=r.last_run_id
where q.review_status='approved'
  and q.merchant_approval='approved'
  and q.tracking_verification='verified'
  and q.stock_available is true and r.stock_available is true
  and q.price_eur=r.price and q.tracking_url=r.tracking_url
  and q.valid_to is not distinct from r.valid_to
  and t.review_status='verified'
  and t.program_id=r.program_id
  and t.effective_from<=now()
  and (t.effective_until is null or t.effective_until>now())
  and (q.valid_to is null or q.valid_to>now())
  and sm_intel.source_offer_valid_now(r.raw_json,r.valid_to)
  and r.source_state='identified'
  and f.state='completed'
  and f.finished_at>now()-interval '7 days'
  and q.calculated_commission_eur>=10;
revoke all on sm_intel.promotion_ready_offers from public,anon,authenticated;
grant select on sm_intel.promotion_ready_offers to service_role;
