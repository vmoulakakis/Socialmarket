-- Qualify already-imported Linkwise products *only* after dated publisher terms
-- have been independently verified. Raw source rows are immutable.
create or replace function sm_intel.reconcile_existing_eligible_offers_v4(p_limit integer default 5000)
returns jsonb language plpgsql volatile security invoker set search_path='' as $$
declare admitted integer:=0;
begin
 if p_limit is null or p_limit<1 or p_limit>10000 then
   raise exception 'invalid_reconcile_limit';
 end if;
 with candidates as (
  select r.id raw_product_id, r.program_id,r.price price_eur,r.tracking_url,
   r.stock_available,r.valid_to,
   t.id commission_terms_id,t.rate_type,
   sm_intel.calculate_commission_eur(r.price,t.rate_type,t.rate_value) amount
  from sm_intel.raw_products r
  join lateral (
   select c.id,c.rate_type,c.rate_value from sm_intel.commission_terms c
   where c.program_id=r.program_id and c.publisher_key='CD104'
     and c.currency='EUR' and c.review_status='verified'
     and c.effective_from<=now()
     and (c.effective_until>now() or
       (c.effective_until is null and c.evidence->>'explicit_open_ended_verified'='true'))
   order by c.effective_from desc,c.id desc limit 1
  ) t on true
  where r.source_key='linkwise_cd104'
   and r.program_id ~ '^[0-9]+$' and r.source_product_id is not null
   and r.price>0 and r.currency='EUR'
   and r.valid_to is not null and r.valid_to>now()
   and (r.valid_to at time zone 'Europe/Athens')::date >= (now() at time zone 'Europe/Athens')::date
   and r.tracking_url like 'https://go.linkwi.se/z/'||r.program_id||'-%/CD104/%'
   and r.quarantine_reason is null
   and not exists(select 1 from sm_intel.qualified_offers q where q.raw_product_id=r.id)
  order by r.id limit p_limit
 ), inserted as (
  insert into sm_intel.qualified_offers
   (raw_product_id,commission_terms_id,program_id,price_eur,calculated_commission_eur,
    calculation_method,tracking_url,stock_available,valid_to)
  select c.raw_product_id,c.commission_terms_id,c.program_id,c.price_eur,c.amount,
    c.rate_type,c.tracking_url,c.stock_available,c.valid_to from candidates c
  where c.amount>10
  on conflict(raw_product_id) do nothing
  returning id
 )
 select count(*) into admitted from inserted;
 return jsonb_build_object('new_qualified_offers',admitted,
  'commission_strictly_greater_than_eur',10,'valid_to_after_now',true,
  'existing_raw_products_updated',0,'public_promotion_approved',false);
end $$;
revoke all on function sm_intel.reconcile_existing_eligible_offers_v4(integer) from public,anon,authenticated;
grant execute on function sm_intel.reconcile_existing_eligible_offers_v4(integer) to service_role;
