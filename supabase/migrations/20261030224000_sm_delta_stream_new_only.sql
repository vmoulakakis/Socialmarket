-- SocialMarket CD104 delta-by-new-product only. Existing rows never updated.
-- No live feed is requested or executed in this migration.
alter table sm_intel.feed_runs
 add column if not exists skipped_existing bigint not null default 0 check(skipped_existing>=0),
 add column if not exists ambiguous_identity bigint not null default 0 check(ambiguous_identity>=0);
create index if not exists sm_delta_source_identity
 on sm_intel.raw_products(source_key,program_id,source_product_id)
 where source_product_id is not null;
create index if not exists sm_delta_legacy_unknown
 on sm_intel.raw_products(source_key,source_product_id)
 where program_id='unknown' and source_product_id is not null;
create table if not exists sm_intel.delta_identity_conflicts(
 id uuid primary key default gen_random_uuid(),
 run_id uuid not null references sm_intel.feed_runs(id) on delete cascade,
 source_product_id text,
 incoming_program_id text,
 incoming_record_key text,
 reason_code text not null check(reason_code in ('legacy_unresolved_merchant','invalid_identity','oversized_record')),
 first_seen_at timestamptz not null default now(),
 unique(run_id,incoming_record_key,reason_code)
);
alter table sm_intel.delta_identity_conflicts enable row level security;
revoke all on sm_intel.delta_identity_conflicts from public,anon,authenticated;
grant select,insert,update,delete on sm_intel.delta_identity_conflicts to service_role;

create or replace function sm_intel.ingest_new_only_batch(p_run_id uuid,p_rows jsonb)
 returns jsonb language plpgsql volatile security invoker set search_path='' as $$
declare v_scanned integer; v_distinct integer; v_new integer; v_qualified integer;
 v_ambiguous integer; v_skipped integer; v_state text; v_mode text;
begin
 if p_run_id is null or p_rows is null or jsonb_typeof(p_rows)<>'array'
  then raise exception 'invalid_delta_input'; end if;
 v_scanned:=jsonb_array_length(p_rows);
 if v_scanned<1 or v_scanned>250 then raise exception 'batch_size_1_to_250_required'; end if;
 select state,checkpoint->>'mode' into v_state,v_mode
 from sm_intel.feed_runs
 where id=p_run_id and source_key='linkwise_cd104' for update;
 if v_state is distinct from 'running' or v_mode is distinct from 'new_only'
  then raise exception 'delta_run_must_be_running_new_only'; end if;
 -- Per-batch parse once; stable canonical identity remains program_id|product_id,
 -- compatible with 3921 legacy rows (including program_id='unknown').
 create temporary table if not exists pg_temp.sm_delta_stage(
  record_key text,source_product_id text,program_id text,product_title text,
  category_raw text,currency text,price numeric,tracking_url text,
  stock_available boolean,valid_to timestamptz,raw_json jsonb,
  content_sha256 text,quarantine_reason text
 ) on commit drop;
 truncate table pg_temp.sm_delta_stage;
 insert into pg_temp.sm_delta_stage
 select distinct on (x.record_key)
 x.record_key,x.source_product_id,x.program_id,x.product_title,x.category_raw,
 x.currency,x.price,x.tracking_url,x.stock_available,x.valid_to,x.raw_json,
 x.content_sha256,x.quarantine_reason
 from jsonb_to_recordset(p_rows) as x(
  record_key text,source_product_id text,program_id text,product_title text,
  category_raw text,currency text,price numeric,tracking_url text,
  stock_available boolean,valid_to timestamptz,raw_json jsonb,
  content_sha256 text,quarantine_reason text)
 where x.record_key is not null and x.record_key <> ''
  and x.raw_json is not null and x.content_sha256 ~ '^[0-9a-f]{64}$'
  and x.source_product_id is not null and x.source_product_id <> ''
  and length(x.record_key)<=500
 order by x.record_key;
 select count(*) into v_distinct from pg_temp.sm_delta_stage;

 -- A legacy unresolved merchant ID cannot prove a new offer is distinct.
 -- Its source ID stays quarantined for manual mapping, never silently duplicated.
 insert into sm_intel.delta_identity_conflicts(run_id,source_product_id,incoming_program_id,incoming_record_key,reason_code)
 select p_run_id,s.source_product_id,s.program_id,s.record_key,'legacy_unresolved_merchant'
 from pg_temp.sm_delta_stage s
 where s.program_id <> 'unknown'
 and exists(
  select 1 from sm_intel.raw_products x
  where x.source_key='linkwise_cd104' and x.source_product_id=s.source_product_id
   and x.program_id='unknown')
 and not exists(
  select 1 from sm_intel.raw_products x
  where x.source_key='linkwise_cd104' and x.source_product_id=s.source_product_id
   and x.program_id=s.program_id)
 on conflict(run_id,incoming_record_key,reason_code) do nothing;

 select count(*) into v_ambiguous from sm_intel.delta_identity_conflicts
  where run_id=p_run_id and reason_code='legacy_unresolved_merchant'
   and incoming_record_key in (select record_key from pg_temp.sm_delta_stage);

 -- Only insert source IDs not already in legacy or new catalog.
 -- No UPDATE clause. No current product mutates even if price or stock changed.
 with new_rows as (
 insert into sm_intel.raw_products(
  source_key,record_key,source_product_id,program_id,product_title,category_raw,
  currency,price,tracking_url,stock_available,valid_to,
  raw_json,content_sha256,last_run_id,source_state,quarantine_reason)
 select 'linkwise_cd104',s.record_key,s.source_product_id,s.program_id,s.product_title,s.category_raw,
  s.currency,s.price,s.tracking_url,s.stock_available,s.valid_to,s.raw_json,
  s.content_sha256,p_run_id,
  case when s.quarantine_reason is not null or s.program_id='unknown'
             or s.currency<>'EUR' or s.price is null or s.price<=0
             or s.tracking_url !~ '^https://' then 'quarantined'
       else 'identified' end,
  s.quarantine_reason
 from pg_temp.sm_delta_stage s
 where not exists(
  select 1 from sm_intel.raw_products x
  where x.source_key='linkwise_cd104'
   and (x.record_key=s.record_key or
     (x.program_id=s.program_id and x.source_product_id=s.source_product_id)))
 and not exists(
   select 1 from sm_intel.delta_identity_conflicts c
   where c.run_id=p_run_id and c.incoming_record_key=s.record_key
      and c.reason_code='legacy_unresolved_merchant')
 on conflict(source_key,record_key) do nothing
 returning id,record_key,source_product_id,program_id,product_title,category_raw,
  currency,price,tracking_url,stock_available,valid_to,source_state
 ), qualified as (
 insert into sm_intel.qualified_offers(
  raw_product_id,commission_terms_id,program_id,price_eur,
  calculated_commission_eur,calculation_method,tracking_url,stock_available,valid_to)
 select n.id,t.id,n.program_id,n.price,
  sm_intel.calculate_commission_eur(n.price,t.rate_type,t.rate_value),
  t.rate_type,n.tracking_url,n.stock_available,n.valid_to
 from new_rows n
 join lateral (
  select c.* from sm_intel.commission_terms c
  where c.publisher_key='CD104' and c.program_id=n.program_id
   and c.review_status='verified' and c.currency='EUR'
   and c.effective_from<=now()
   and (c.effective_until is null or c.effective_until>now())
  order by c.effective_from desc,c.id desc limit 1
 ) t on true
 where n.source_state='identified' and n.currency='EUR' and n.price>0
  and n.tracking_url ~ '^https://'
  and sm_intel.calculate_commission_eur(n.price,t.rate_type,t.rate_value)>=10
 on conflict(raw_product_id) do nothing returning id
 ), totals as (
 select (select count(*) from new_rows) new_count,
        (select count(*) from qualified) qualified_count
 )
 select new_count,qualified_count into v_new,v_qualified from totals;

 -- Deferred derived indexes only for new rows, without reprocessing the full corpus.
 insert into sm_intel.search_documents(
  entity_pk,source_table,entity_type,title,content,source_state,metadata,content_sha256)
 select r.id::text,'sm_intel.raw_products','product',
  coalesce(nullif(r.product_title,''),r.source_product_id),
  left(concat_ws(' ',r.product_title,r.category_raw,r.raw_json->>'description',
    r.raw_json->>'brand_name',r.raw_json->>'model_name'),1600),
  r.source_state,
  jsonb_build_object('program_id',r.program_id,'source_product_id',r.source_product_id,
   'source_key',r.source_key,'stock_available',r.stock_available,'price_eur',r.price),
  encode(sha256(convert_to(concat_ws('|',coalesce(nullif(r.product_title,''),r.source_product_id),
   left(concat_ws(' ',r.product_title,r.category_raw,r.raw_json->>'description',
    r.raw_json->>'brand_name',r.raw_json->>'model_name'),1600)),'UTF8')),'hex')
 from sm_intel.raw_products r
 where r.last_run_id=p_run_id
 and r.record_key in (select record_key from pg_temp.sm_delta_stage)
 on conflict(tenant_key,source_table,entity_pk) do nothing;

 insert into sm_intel.graph_nodes(node_type,source_table,source_pk,display_label,metadata)
 select 'product','sm_intel.raw_products',r.id::text,
  coalesce(nullif(r.product_title,''),r.source_product_id),
  jsonb_build_object('source_key',r.source_key,'program_id',r.program_id,'source_state',r.source_state)
 from sm_intel.raw_products r where r.last_run_id=p_run_id
 and r.record_key in (select record_key from pg_temp.sm_delta_stage)
 on conflict(tenant_key,node_type,source_table,source_pk) do nothing;

 insert into sm_intel.agent_tasks(
  objective_key,agent_role,subject_kind,subject_key,priority,input_refs)
 select 'evidence_first_solution_discovery','product_analyst','product',r.id::text,
  case when r.source_state='identified' then 70 else 30 end,
  jsonb_build_object('source','sm_intel.raw_products','program_id',r.program_id,
   'required_research',jsonb_build_array('Greek demand','Greek local supply','merchant','terms','pain gap','contradictions'))
 from sm_intel.raw_products r where r.last_run_id=p_run_id
 and r.record_key in (select record_key from pg_temp.sm_delta_stage)
 on conflict(objective_key,agent_role,subject_kind,subject_key,output_version) do nothing;

 v_skipped:=greatest(0,v_scanned-v_new-v_ambiguous);
 update sm_intel.feed_runs
 set scanned=scanned+v_scanned,
  stored=stored+v_new,admitted=admitted+v_qualified,
  skipped_existing=skipped_existing+v_skipped,
  ambiguous_identity=ambiguous_identity+v_ambiguous
 where id=p_run_id;
 return jsonb_build_object('scanned',v_scanned,'new_products',v_new,
  'commercially_admitted',v_qualified,'existing_or_duplicate',v_skipped,
  'identity_conflicts',v_ambiguous,'strategy','new_only');
end $$;
revoke all on function sm_intel.ingest_new_only_batch(uuid,jsonb) from public,anon,authenticated;
grant execute on function sm_intel.ingest_new_only_batch(uuid,jsonb) to service_role;
