-- SocialMarket private full-feed batch adapter and fail-closed promotion view.
-- Only trusted server-side DB roles can execute. No public RPC and no automatic cron changes.
create or replace function sm_intel.ingest_full_feed_batch(p_run_id uuid,p_rows jsonb)
returns jsonb language plpgsql security invoker set search_path='' as $$
declare v_seen integer; v_written integer; v_qualified integer; v_state text;
begin
 if p_run_id is null or p_rows is null or jsonb_typeof(p_rows)<>'array' then
   raise exception 'invalid_batch_contract';
 end if;
 v_seen := jsonb_array_length(p_rows);
 if v_seen<1 or v_seen>500 then raise exception 'batch_size_out_of_range'; end if;
 select state into v_state from sm_intel.feed_runs where id=p_run_id and source_key='linkwise_cd104' for update;
 if v_state is distinct from 'running' then raise exception 'feed_run_not_running'; end if;
 with incoming as (
  select distinct on (x.record_key)
   x.record_key,x.source_product_id,x.program_id,x.product_title,x.category_raw,
   x.currency,x.price,x.tracking_url,x.stock_available,x.valid_to,
   x.raw_json,x.content_sha256,x.quarantine_reason
  from jsonb_to_recordset(p_rows) as x(
   record_key text,source_product_id text,program_id text,product_title text,category_raw text,
   currency text,price numeric,tracking_url text,stock_available boolean,valid_to timestamptz,
   raw_json jsonb,content_sha256 text,quarantine_reason text)
  where x.record_key is not null and x.record_key<>'' and length(x.content_sha256)=64 and x.raw_json is not null
  order by x.record_key
 ), written as (
  insert into sm_intel.raw_products(
   source_key,record_key,source_product_id,program_id,product_title,category_raw,
   currency,price,tracking_url,stock_available,valid_to,raw_json,content_sha256,
   last_run_id,source_state,quarantine_reason,last_seen_at)
  select 'linkwise_cd104',record_key,source_product_id,program_id,product_title,category_raw,
   currency,price,tracking_url,stock_available,valid_to,raw_json,content_sha256,
   p_run_id,
   case when quarantine_reason is null and source_product_id is not null and program_id is not null
       and currency='EUR' and price>0 and tracking_url ~ '^https://' then 'identified'
       else 'quarantined' end,quarantine_reason,now()
  from incoming
  on conflict(source_key,record_key) do update set
   source_product_id=excluded.source_product_id,program_id=excluded.program_id,
   product_title=excluded.product_title,category_raw=excluded.category_raw,
   currency=excluded.currency,price=excluded.price,tracking_url=excluded.tracking_url,
   stock_available=excluded.stock_available,valid_to=excluded.valid_to,
   raw_json=case when sm_intel.raw_products.content_sha256 is distinct from excluded.content_sha256
                 then excluded.raw_json else sm_intel.raw_products.raw_json end,
   content_sha256=excluded.content_sha256,last_run_id=p_run_id,
   source_state=excluded.source_state,quarantine_reason=excluded.quarantine_reason,last_seen_at=now()
  returning id
 )
 select count(*) into v_written from written;
 with incoming as (
  select distinct on (x.record_key) x.record_key
  from jsonb_to_recordset(p_rows) as x(record_key text)
  where x.record_key is not null and x.record_key<>''
  order by x.record_key
 ), candidates as (
  select r.id,r.program_id,r.price,r.tracking_url,r.stock_available,r.valid_to,
         t.id as terms_id,t.rate_type,
         sm_intel.calculate_commission_eur(r.price,t.rate_type,t.rate_value) as estimate
  from incoming i
  join sm_intel.raw_products r on r.source_key='linkwise_cd104' and r.record_key=i.record_key
  join lateral (
    select terms.id,terms.rate_type,terms.rate_value from sm_intel.commission_terms terms
    where terms.publisher_key='CD104' and terms.program_id=r.program_id
      and terms.review_status='verified'
      and terms.effective_from<=now()
      and (terms.effective_until is null or terms.effective_until>now())
    order by terms.effective_from desc,terms.id desc limit 1
  ) t on true
  where r.source_state='identified' and r.currency='EUR' and r.price>0
    and r.tracking_url ~ '^https://'
 ), admitted as (
  insert into sm_intel.qualified_offers(raw_product_id,commission_terms_id,program_id,
   price_eur,calculated_commission_eur,calculation_method,tracking_url,stock_available,valid_to)
  select id,terms_id,program_id,price,estimate,rate_type,tracking_url,stock_available,valid_to
  from candidates where estimate>=10
  on conflict(raw_product_id) do update set
   commission_terms_id=excluded.commission_terms_id,program_id=excluded.program_id,
   price_eur=excluded.price_eur,calculated_commission_eur=excluded.calculated_commission_eur,
   calculation_method=excluded.calculation_method,tracking_url=excluded.tracking_url,
   stock_available=excluded.stock_available,valid_to=excluded.valid_to,evaluated_at=now(),
   review_status=case when sm_intel.qualified_offers.price_eur is distinct from excluded.price_eur
                   or sm_intel.qualified_offers.tracking_url is distinct from excluded.tracking_url
                   or sm_intel.qualified_offers.commission_terms_id is distinct from excluded.commission_terms_id
               then 'candidate' else sm_intel.qualified_offers.review_status end,
   tracking_verification=case when sm_intel.qualified_offers.tracking_url is distinct from excluded.tracking_url
                then 'unknown' else sm_intel.qualified_offers.tracking_verification end
  returning id
 )
 select count(*) into v_qualified from admitted;
 update sm_intel.feed_runs set scanned=scanned+v_seen,stored=stored+v_written,
   admitted=admitted+v_qualified,rejected=rejected+greatest(0,v_seen-v_qualified)
 where id=p_run_id;
 return jsonb_build_object('scanned',v_seen,'stored',v_written,'admitted',v_qualified);
end $$;
revoke all on function sm_intel.ingest_full_feed_batch(uuid,jsonb) from public,anon,authenticated;
grant execute on function sm_intel.ingest_full_feed_batch(uuid,jsonb) to service_role;

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
  and (t.effective_until is null or t.effective_until>now())
  and (q.valid_to is null or q.valid_to>now())
  and r.source_state='identified'
  and f.state='completed'
  and f.finished_at>now()-interval '7 days'
  and q.calculated_commission_eur>=10;
revoke all on sm_intel.promotion_ready_offers from public,anon,authenticated;
