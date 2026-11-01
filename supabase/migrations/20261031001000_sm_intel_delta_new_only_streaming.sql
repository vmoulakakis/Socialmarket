-- SocialMarket CD104 full-stream / delta-only commercial ingestion v2.
-- Full JSON stream is scanned externally, but ONLY genuinely new products with verified
-- conservative commission >= EUR10 enter raw_products + qualified_offers.
-- Existing raw JSON, price, stock, and source timestamps are NEVER overwritten.
-- Nonqualified/unknowns are counted, not imported as misleading approved offers.
create index if not exists sm_raw_identity_lookup_idx
  on sm_intel.raw_products(source_key,program_id,source_product_id)
  where program_id is not null and source_product_id is not null;

create table if not exists sm_intel.delta_feed_batches(
 id uuid primary key default gen_random_uuid(),
 run_id uuid not null references sm_intel.feed_runs(id) on delete restrict,
 batch_offset bigint not null check(batch_offset>=0),
 batch_size integer not null check(batch_size between 1 and 250),
 batch_hash text not null check(length(batch_hash)=64),
 inserted_new integer not null default 0 check(inserted_new>=0),
 existing_skipped integer not null default 0 check(existing_skipped>=0),
 unresolved_skipped integer not null default 0 check(unresolved_skipped>=0),
 unqualified_skipped integer not null default 0 check(unqualified_skipped>=0),
 created_at timestamptz not null default now(),
 unique(run_id,batch_offset),
 check(inserted_new+existing_skipped+unqualified_skipped=batch_size)
);
create index if not exists sm_delta_audit_run_idx on sm_intel.delta_feed_batches(run_id,batch_offset);
alter table sm_intel.delta_feed_batches enable row level security;
revoke all on sm_intel.delta_feed_batches from public,anon,authenticated;
grant select,insert on sm_intel.delta_feed_batches to service_role;

create or replace function sm_intel.ingest_new_only_batch(
 p_run_id uuid,p_batch_offset bigint,p_rows jsonb,p_source_fingerprint text
) returns jsonb language plpgsql volatile security invoker set search_path='' as $$
declare
 n integer; old_offset bigint; state text; original_fingerprint text;
 payload_hash text; replay sm_intel.delta_feed_batches%rowtype;
 inserted_n integer := 0; existing_n integer := 0; unresolved_n integer := 0; unqualified_n integer := 0;
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
    'unresolved',replay.unresolved_skipped,'replayed',true);
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
    and (i.valid_to is null or i.valid_to>now())
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
    and commission>=10
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
   (select count(*)::int from classified c where c.program_id is null or c.program_id !~ '^[0-9]+$') unknown_n
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
end $$;
revoke all on function sm_intel.ingest_new_only_batch(uuid,bigint,jsonb,text) from public,anon,authenticated;
grant execute on function sm_intel.ingest_new_only_batch(uuid,bigint,jsonb,text) to service_role;
