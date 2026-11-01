-- Linkwise CD104 strict v4: dated 2026-11-01 requested eligibility,
-- requires explicit valid_to still unexpired AT runtime and conservative commission > EUR10.
-- Never trust price-only, stale terms or open-ended product validity.
alter table sm_intel.delta_feed_batches
 add column if not exists missing_valid_to integer not null default 0 check(missing_valid_to>=0),
 add column if not exists expired_valid_to integer not null default 0 check(expired_valid_to>=0),
 add column if not exists unverified_terms integer not null default 0 check(unverified_terms>=0),
 add column if not exists commission_not_over_10 integer not null default 0 check(commission_not_over_10>=0);

CREATE OR REPLACE FUNCTION sm_intel.ingest_new_only_batch(p_run_id uuid, p_batch_offset bigint, p_rows jsonb, p_source_fingerprint text)
 RETURNS jsonb
 LANGUAGE plpgsql
 SET search_path TO ''
AS $function$
declare
 n integer; old_offset bigint; state text; original_fingerprint text;
 payload_hash text; replay sm_intel.delta_feed_batches%rowtype;
 inserted_n integer := 0; existing_n integer := 0; unresolved_n integer := 0; unqualified_n integer := 0;
 missing_expiry_n integer:=0; expired_n integer:=0; unverified_terms_n integer:=0; low_commission_n integer:=0;
begin
 if p_run_id is null or p_rows is null or jsonb_typeof(p_rows)<>'array'
    or p_batch_offset is null or p_batch_offset<0 then
   raise exception 'invalid_delta_batch_contract';
 end if;
 n:=jsonb_array_length(p_rows);
 if n<1 or n>250 then raise exception 'delta_batch_must_contain_1_to_250_records'; end if;
 payload_hash:=encode(sha256(convert_to(p_rows::text,'UTF8')),'hex');
 select * into replay from sm_intel.delta_feed_batches b
 where b.run_id=p_run_id and b.batch_offset=p_batch_offset;
 if found then
  if replay.batch_hash<>payload_hash or replay.batch_size<>n then
   raise exception 'delta_batch_replay_payload_mismatch';
  end if;
  return jsonb_build_object('scanned',n,'new',replay.inserted_new,
    'existing',replay.existing_skipped,'unqualified',replay.unqualified_skipped,
    'unresolved',replay.unresolved_skipped,
    'missing_valid_to',replay.missing_valid_to,
    'expired_valid_to',replay.expired_valid_to,
    'unverified_terms',replay.unverified_terms,
    'commission_not_over_10',replay.commission_not_over_10,
    'replayed',true);
 end if;
 select f.scanned,f.state,f.source_fingerprint into old_offset,state,original_fingerprint
 from sm_intel.feed_runs f where f.id=p_run_id and f.source_key='linkwise_cd104' for update;
 if not found or state<>'running' or old_offset<>p_batch_offset then
   raise exception 'run_not_running_or_noncontiguous_offset';
 end if;
 if original_fingerprint is distinct from p_source_fingerprint then
   raise exception 'feed_snapshot_fingerprint_changed';
 end if;
 -- Reject duplicate identity within one batch from ambiguous program/product IDs.
 -- Quarantine those identities at audit level instead of guessing a single winner.
 with incoming as (
  select x.*,count(*) over(partition by x.program_id,x.source_product_id) collisions
  from jsonb_to_recordset(p_rows) as x(
    record_key text,source_product_id text,program_id text,product_title text,category_raw text,
    currency text,price numeric,tracking_url text,stock_available boolean,valid_to timestamptz,
    raw_json jsonb,content_sha256 text,quarantine_reason text
  )
 ),
 normalized as (
  select i.*,
   (i.collisions=1
    and i.program_id ~ '^[0-9]+$'
    and i.source_product_id is not null and i.source_product_id<>''
    and i.record_key=i.program_id||'|'||i.source_product_id
    and i.tracking_url like 'https://go.linkwi.se/z/'||i.program_id||'-%/CD104/%'
    and i.currency='EUR' and i.price>0 and i.price<10000000000
    and (i.valid_to is not null and i.valid_to>now() and (i.valid_to at time zone 'Europe/Athens')::date >= (now() at time zone 'Europe/Athens')::date)
    and i.quarantine_reason is null
    and i.raw_json is not null and jsonb_typeof(i.raw_json)='object'
    and i.content_sha256 ~ '^[a-f0-9]{64}$') as structurally_valid
  from incoming i
 ), classified as (
  select i.*,
  exists(
    select 1 from sm_intel.raw_products r
    where r.source_key='linkwise_cd104' and r.program_id=i.program_id
      and r.source_product_id=i.source_product_id
   ) as already_exists,
   t.id terms_id,t.rate_type,
   sm_intel.calculate_commission_eur(i.price,t.rate_type,t.rate_value) as commission
  from normalized i
  left join lateral(
   select c.id,c.rate_type,c.rate_value
   from sm_intel.commission_terms c
   where c.program_id=i.program_id and c.publisher_key='CD104'
     and c.review_status='verified' and c.currency='EUR'
     and c.effective_from<=now()
     and (c.effective_until>now() or
       (c.effective_until is null and c.evidence->>'explicit_open_ended_verified'='true'))
   order by c.effective_from desc,c.id desc limit 1
  ) t on true
 ), eligibility as (
  select * from classified
  where structurally_valid and not already_exists
    and commission>10
 ), inserted as (
  insert into sm_intel.raw_products(
    source_key,record_key,source_product_id,program_id,product_title,category_raw,
    currency,price,tracking_url,stock_available,valid_to,raw_json,content_sha256,
    last_run_id,source_state,first_seen_at,last_seen_at)
  select 'linkwise_cd104',e.record_key,e.source_product_id,e.program_id,e.product_title,
    e.category_raw,e.currency,e.price,e.tracking_url,e.stock_available,e.valid_to,
    e.raw_json,e.content_sha256,p_run_id,'identified',now(),now()
  from eligibility e
  on conflict(source_key,record_key) do nothing
  returning id,record_key
 ), commercial as (
  insert into sm_intel.qualified_offers(
    raw_product_id,commission_terms_id,program_id,price_eur,calculated_commission_eur,
    calculation_method,tracking_url,stock_available,valid_to)
  select i.id,e.terms_id,e.program_id,e.price,e.commission,e.rate_type,
    e.tracking_url,e.stock_available,e.valid_to
  from inserted i join eligibility e on e.record_key=i.record_key
  on conflict(raw_product_id) do nothing
  returning id
 ), counts as (
  select
   (select count(*)::int from commercial) new_n,
   (select count(*)::int from classified c where c.already_exists) existing_n,
   (select count(*)::int from classified c where c.program_id is null or c.program_id !~ '^[0-9]+
 )
 select c.new_n,c.existing_n,c.unknown_n,c.missing_expiry_n,c.expired_n,c.no_terms_n,c.low_commission_n
 into inserted_n,existing_n,unresolved_n,missing_expiry_n,expired_n,unverified_terms_n,low_commission_n
 from counts c;

 unqualified_n:=n-inserted_n-existing_n;
 if unqualified_n<0 then raise exception 'bad_ingest_delta_counts'; end if;
 insert into sm_intel.delta_feed_batches(run_id,batch_offset,batch_size,batch_hash,
   inserted_new,existing_skipped,unresolved_skipped,unqualified_skipped,
   missing_valid_to,expired_valid_to,unverified_terms,commission_not_over_10)
 values(p_run_id,p_batch_offset,n,payload_hash,inserted_n,existing_n,unresolved_n,unqualified_n,
   missing_expiry_n,expired_n,unverified_terms_n,low_commission_n);
 update sm_intel.feed_runs
 set scanned=p_batch_offset+n,stored=stored+inserted_n,admitted=admitted+inserted_n,
  rejected=rejected+unqualified_n,
  checkpoint=jsonb_build_object('offset',p_batch_offset+n,'mode','insert_new_only','source_fingerprint',p_source_fingerprint)
 where id=p_run_id;
 return jsonb_build_object('scanned',n,'new',inserted_n,'existing',existing_n,
  'unqualified',unqualified_n,'unresolved',unresolved_n,
  'missing_valid_to',missing_expiry_n,'expired_valid_to',expired_n,
  'unverified_terms',unverified_terms_n,'commission_not_over_10',low_commission_n,
  'replayed',false);
end $function$
) unknown_n,
   (select count(*)::int from classified c where c.valid_to is null and not c.already_exists) missing_expiry_n,
   (select count(*)::int from classified c where c.valid_to<=now() and not c.already_exists) expired_n,
   (select count(*)::int from classified c where c.terms_id is null and not c.already_exists and c.structurally_valid) no_terms_n,
   (select count(*)::int from classified c where c.terms_id is not null and c.commission<=10
      and not c.already_exists and c.structurally_valid) low_commission_n
 )
 select c.new_n,c.existing_n,c.unknown_n into inserted_n,existing_n,unresolved_n from counts c;

 unqualified_n:=n-inserted_n-existing_n;
 if unqualified_n<0 then raise exception 'bad_ingest_delta_counts'; end if;
 insert into sm_intel.delta_feed_batches(run_id,batch_offset,batch_size,batch_hash,
   inserted_new,existing_skipped,unresolved_skipped,unqualified_skipped)
 values(p_run_id,p_batch_offset,n,payload_hash,inserted_n,existing_n,unresolved_n,unqualified_n);
 update sm_intel.feed_runs
 set scanned=p_batch_offset+n,stored=stored+inserted_n,admitted=admitted+inserted_n,
  rejected=rejected+unqualified_n,
  checkpoint=jsonb_build_object('offset',p_batch_offset+n,'mode','insert_new_only','source_fingerprint',p_source_fingerprint)
 where id=p_run_id;
 return jsonb_build_object('scanned',n,'new',inserted_n,'existing',existing_n,
  'unqualified',unqualified_n,'unresolved',unresolved_n,'replayed',false);
end $function$
;

create or replace view sm_intel.product_expiry_commission_audit_v4
with (security_invoker=true) as
select r.id,r.program_id,r.source_product_id,r.product_title,r.price,
 r.currency,r.valid_to,
 t.review_status as terms_review_status,t.rate_type,t.rate_value,
 sm_intel.calculate_commission_eur(r.price,t.rate_type,t.rate_value)
   as verified_calculated_commission_eur,
 case when r.valid_to is null then 'missing_valid_to'
      when r.valid_to <= now() then 'expired'
      when r.program_id is null or r.program_id !~ '^[0-9]+$' then 'invalid_program_id'
      when r.currency<>'EUR' or r.price is null or r.price<=0 then 'invalid_price_or_currency'
      when t.id is null then 'unverified_or_expired_commission_terms'
      when sm_intel.calculate_commission_eur(r.price,t.rate_type,t.rate_value)<=10 then 'commission_not_over_10'
      else 'catalog_candidate_not_promotion_approved' end eligibility_status
from sm_intel.raw_products r
left join lateral (
 select c.* from sm_intel.commission_terms c
 where c.program_id=r.program_id and c.publisher_key='CD104'
   and c.review_status='verified' and c.currency='EUR'
   and c.effective_from<=now()
   and (c.effective_until>now() or (c.effective_until is null and c.evidence->>'explicit_open_ended_verified'='true'))
 order by c.effective_from desc,c.id desc limit 1
) t on true
where r.source_key='linkwise_cd104';
revoke all on sm_intel.product_expiry_commission_audit_v4 from public,anon,authenticated;
grant select on sm_intel.product_expiry_commission_audit_v4 to service_role;
