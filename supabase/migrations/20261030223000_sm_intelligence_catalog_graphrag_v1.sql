-- SocialMarket AI v1.0 isolated catalog, commercial eligibility, demand intelligence and GraphRAG.
-- Non-destructive: does not change legacy public tables, functions, cron or Edge Functions.
create schema if not exists sm_intel;
revoke all on schema sm_intel from public, anon, authenticated;
comment on schema sm_intel is 'SocialMarket AI only; non-exposed private data plane; never cross-project VMDB joins';

create table if not exists sm_intel.feed_runs (
 id uuid primary key default gen_random_uuid(),
 source_key text not null default 'linkwise_cd104',
 source_fingerprint text,
 state text not null default 'queued' check(state in ('queued','running','completed','failed','partial')),
 checkpoint jsonb not null default '{}'::jsonb,
 scanned bigint not null default 0 check(scanned>=0),
 stored bigint not null default 0 check(stored>=0),
 admitted bigint not null default 0 check(admitted>=0),
 rejected bigint not null default 0 check(rejected>=0),
 bytes_read bigint not null default 0 check(bytes_read>=0),
 error_code text,
 started_at timestamptz not null default now(),
 finished_at timestamptz,
 created_at timestamptz not null default now()
);
create index if not exists sm_feed_runs_status_idx on sm_intel.feed_runs(source_key,state,created_at desc);

create table if not exists sm_intel.raw_products (
 id uuid primary key default gen_random_uuid(),
 source_key text not null default 'linkwise_cd104',
 record_key text not null,
 source_product_id text,
 program_id text,
 product_title text,
 category_raw text,
 region_code text not null default 'GR' check(region_code='GR'),
 currency text,
 price numeric(14,4),
 tracking_url text,
 stock_available boolean,
 valid_to timestamptz,
 raw_json jsonb not null,
 content_sha256 text not null check(length(content_sha256)=64),
 first_seen_at timestamptz not null default now(),
 last_seen_at timestamptz not null default now(),
 last_run_id uuid references sm_intel.feed_runs(id) on delete set null,
 source_state text not null default 'candidate' check(source_state in ('candidate','identified','quarantined','removed')),
 quarantine_reason text,
 unique(source_key,record_key),
 check(price is null or price >= 0),
 check(record_key <> '')
);
create index if not exists sm_raw_program_idx on sm_intel.raw_products(program_id,source_product_id);
create index if not exists sm_raw_lastseen_idx on sm_intel.raw_products(last_seen_at desc);
create index if not exists sm_raw_sha_idx on sm_intel.raw_products(content_sha256);

create table if not exists sm_intel.commission_terms (
 id uuid primary key default gen_random_uuid(),
 program_id text not null,
 program_name text,
 publisher_key text not null default 'CD104',
 rate_type text not null check(rate_type in ('percent_min','flat_min')),
 rate_value numeric(14,6) not null check(rate_value > 0),
 currency text not null default 'EUR' check(currency='EUR'),
 effective_from timestamptz not null default now(),
 effective_until timestamptz,
 source_record text not null,
 source_observed_at timestamptz,
 evidence jsonb not null default '{}'::jsonb,
 review_status text not null default 'unverified' check(review_status in ('unverified','verified','rejected','stale')),
 version_key text not null,
 reviewed_at timestamptz,
 created_at timestamptz not null default now(),
 unique(publisher_key,program_id,version_key),
 check(effective_until is null or effective_until > effective_from)
);
create index if not exists sm_terms_program_idx on sm_intel.commission_terms(publisher_key,program_id,review_status);

create or replace function sm_intel.calculate_commission_eur(
 p_price_eur numeric, p_rate_type text, p_rate_value numeric
) returns numeric language sql immutable strict set search_path='' as $$
 select case
   when p_price_eur<=0 or p_rate_value<=0 then null::numeric
   when p_rate_type='percent_min' and p_rate_value<=100 then round(p_price_eur*p_rate_value/100,4)
   when p_rate_type='flat_min' then round(p_rate_value,4)
   else null::numeric end
$$;
revoke all on function sm_intel.calculate_commission_eur(numeric,text,numeric) from public,anon,authenticated;

create table if not exists sm_intel.qualified_offers (
 id uuid primary key default gen_random_uuid(),
 raw_product_id uuid not null unique references sm_intel.raw_products(id) on delete restrict,
 commission_terms_id uuid not null references sm_intel.commission_terms(id) on delete restrict,
 program_id text not null,
 price_eur numeric(14,4) not null check(price_eur>0),
 calculated_commission_eur numeric(14,4) not null check(calculated_commission_eur>=10),
 calculation_method text not null,
 tracking_url text not null check(tracking_url ~ '^https://'),
 stock_available boolean,
 valid_to timestamptz,
 merchant_profile_id uuid references public.merchant_profiles(id) on delete set null,
 merchant_approval text not null default 'unknown' check(merchant_approval in ('unknown','approved','rejected')),
 tracking_verification text not null default 'unknown' check(tracking_verification in ('unknown','verified','invalid')),
 review_status text not null default 'candidate' check(review_status in ('candidate','approved','rejected','paused')),
 evaluated_at timestamptz not null default now(),
 updated_at timestamptz not null default now()
);
create index if not exists sm_qualified_comm_idx on sm_intel.qualified_offers(calculated_commission_eur desc);
create index if not exists sm_qualified_merchant_idx on sm_intel.qualified_offers(merchant_profile_id,review_status);

create or replace function sm_intel.validate_qualified_offer()
returns trigger language plpgsql security invoker set search_path='' as $$
declare x sm_intel.commission_terms%rowtype; r sm_intel.raw_products%rowtype; v numeric;
begin
 select * into x from sm_intel.commission_terms where id=new.commission_terms_id;
 select * into r from sm_intel.raw_products where id=new.raw_product_id;
 if x.id is null or r.id is null then raise exception 'source_row_missing'; end if;
 if x.review_status <> 'verified' or x.publisher_key <> 'CD104'
    or x.program_id<>r.program_id or new.program_id<>r.program_id
    or x.effective_from>now() or (x.effective_until is not null and x.effective_until<=now())
    or x.currency<>'EUR' or r.currency<>'EUR' then
   raise exception 'unverified_or_inapplicable_commission_terms'; end if;
 v:=sm_intel.calculate_commission_eur(r.price,x.rate_type,x.rate_value);
 if v is null or v<10 or new.calculated_commission_eur is distinct from v
    or new.price_eur is distinct from r.price
    or new.tracking_url is distinct from r.tracking_url
    or r.tracking_url !~ '^https://' or r.source_state='quarantined'
    or new.stock_available is distinct from r.stock_available
    or new.valid_to is distinct from r.valid_to then
    raise exception 'offer_admission_policy_violation'; end if;
 new.calculation_method:=x.rate_type;
 new.updated_at:=now();
 return new;
end $$;
create trigger sm_qualified_offer_gate before insert or update on sm_intel.qualified_offers
for each row execute function sm_intel.validate_qualified_offer();
revoke all on function sm_intel.validate_qualified_offer() from public,anon,authenticated;

create table if not exists sm_intel.research_evidence (
 id uuid primary key default gen_random_uuid(),
 source_family text not null,
 source_record_id text,
 source_url text,
 source_sha256 text,
 market_code text not null default 'GR' check(market_code='GR'),
 region_code text not null default 'GR',
 location_precision text not null default 'country' check(location_precision in ('country','region','city','other')),
 problem_cluster_id uuid references public.market_problem_clusters(id) on delete set null,
 signal_kind text not null check(signal_kind in ('demand','supply','competition','intent','seasonality','fulfillment','merchant_trust','incentive','counter_evidence')),
 signal_value jsonb not null default '{}'::jsonb,
 sample_size integer check(sample_size is null or sample_size>=0),
 confidence numeric(5,4) not null default 0 check(confidence between 0 and 1),
 observed_at timestamptz not null,
 expires_at timestamptz,
 audit_status text not null default 'candidate' check(audit_status in ('candidate','verified','rejected','stale')),
 collected_at timestamptz not null default now(),
 check(source_url is not null or source_record_id is not null),
 check(expires_at is null or expires_at>observed_at)
);
create index if not exists sm_research_pain_idx on sm_intel.research_evidence(problem_cluster_id,signal_kind,observed_at desc);
create index if not exists sm_research_market_idx on sm_intel.research_evidence(market_code,region_code,signal_kind,observed_at desc);

create table if not exists sm_intel.pain_gap_scores (
 id uuid primary key default gen_random_uuid(),
 problem_cluster_id uuid not null references public.market_problem_clusters(id) on delete restrict,
 region_code text not null default 'GR',
 period_start date not null,
 period_end date not null,
 demand_score numeric(6,3) check(demand_score between 0 and 100),
 verified_supply_score numeric(6,3) check(verified_supply_score between 0 and 100),
 supply_gap_score numeric(6,3) check(supply_gap_score between 0 and 100),
 commercial_intent_score numeric(6,3) check(commercial_intent_score between 0 and 100),
 trend_score numeric(6,3) check(trend_score between 0 and 100),
 seasonality_score numeric(6,3) check(seasonality_score between 0 and 100),
 urgency_score numeric(6,3) check(urgency_score between 0 and 100),
 confidence numeric(5,4) not null default 0 check(confidence between 0 and 1),
 verified_evidence_count integer not null default 0 check(verified_evidence_count>=0),
 counter_evidence_count integer not null default 0 check(counter_evidence_count>=0),
 methodology_version text not null,
 judgment text not null default 'candidate' check(judgment in ('candidate','verified','rejected','stale')),
 rationale jsonb not null default '{}'::jsonb,
 evaluated_at timestamptz not null default now(),
 unique(problem_cluster_id,region_code,period_start,period_end,methodology_version),
 check(period_end>=period_start),
 check(judgment<>'verified' or verified_evidence_count>=2)
);
create index if not exists sm_pain_gap_rank_idx on sm_intel.pain_gap_scores(region_code,judgment,supply_gap_score desc,demand_score desc);

create table if not exists sm_intel.merchant_rankings (
 id uuid primary key default gen_random_uuid(),
 merchant_profile_id uuid not null references public.merchant_profiles(id) on delete restrict,
 problem_cluster_id uuid references public.market_problem_clusters(id) on delete set null,
 region_code text not null default 'GR',
 assessed_on date not null default current_date,
 demand_fit_score numeric(6,3) check(demand_fit_score between 0 and 100),
 supply_advantage_score numeric(6,3) check(supply_advantage_score between 0 and 100),
 trust_score numeric(6,3) check(trust_score between 0 and 100),
 fulfillment_score numeric(6,3) check(fulfillment_score between 0 and 100),
 verified_incentive_score numeric(6,3) check(verified_incentive_score between 0 and 100),
 offer_economics_score numeric(6,3) check(offer_economics_score between 0 and 100),
 overall_score numeric(6,3) check(overall_score between 0 and 100),
 evidence_count integer not null default 0 check(evidence_count>=0),
 confidence numeric(5,4) not null default 0 check(confidence between 0 and 1),
 methodology_version text not null,
 review_status text not null default 'candidate' check(review_status in ('candidate','verified','rejected','stale')),
 rationale jsonb not null default '{}'::jsonb,
 evaluated_at timestamptz not null default now()
);
create index if not exists sm_merchant_rank_idx on sm_intel.merchant_rankings(region_code,assessed_on desc,overall_score desc);

create table if not exists sm_intel.pain_offer_matches (
 id uuid primary key default gen_random_uuid(),
 gap_score_id uuid not null references sm_intel.pain_gap_scores(id) on delete restrict,
 qualified_offer_id uuid not null references sm_intel.qualified_offers(id) on delete restrict,
 match_score numeric(6,3) check(match_score between 0 and 100),
 buyer_intent_cohort text,
 purchase_motivation text,
 verified_incentive jsonb not null default '{}'::jsonb,
 suitability_evidence jsonb not null default '[]'::jsonb,
 confidence numeric(5,4) not null default 0 check(confidence between 0 and 1),
 review_status text not null default 'candidate' check(review_status in ('candidate','verified','rejected','stale')),
 model_version text not null,
 evaluated_at timestamptz not null default now(),
 unique(gap_score_id,qualified_offer_id,model_version)
);
create index if not exists sm_match_rank_idx on sm_intel.pain_offer_matches(gap_score_id,review_status,match_score desc);

create table if not exists sm_intel.graph_nodes (
 id uuid primary key default gen_random_uuid(),
 tenant_key text not null default 'socialmarket' check(tenant_key='socialmarket'),
 market_code text not null default 'GR' check(market_code='GR'),
 node_type text not null check(node_type in ('problem','product','offer','merchant','program','category','evidence','region','season','intent','incentive')),
 source_table text not null,
 source_pk text not null,
 display_label text not null,
 metadata jsonb not null default '{}'::jsonb,
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now(),
 unique(tenant_key,id),
 unique(tenant_key,node_type,source_table,source_pk)
);
create index if not exists sm_graph_node_lookup_idx on sm_intel.graph_nodes(node_type,source_table,source_pk);

create table if not exists sm_intel.graph_edges (
 id uuid primary key default gen_random_uuid(),
 tenant_key text not null default 'socialmarket' check(tenant_key='socialmarket'),
 market_code text not null default 'GR' check(market_code='GR'),
 source_node_id uuid not null,
 target_node_id uuid not null,
 relation_type text not null check(relation_type in ('SOLVES','OFFERED_AS','OFFERED_BY','BELONGS_TO','SUPPORTED_BY','HAS_DEMAND','HAS_SUPPLY_GAP','MATCHES_INTENT','SEASONAL_IN','AVAILABLE_IN','HAS_VERIFIED_INCENTIVE','HAS_COMMISSION_TERMS','COMPETES_WITH','SUBSTITUTE_FOR')),
 evidence_confidence numeric(5,4) not null default 0 check(evidence_confidence between 0 and 1),
 review_status text not null default 'candidate' check(review_status in ('candidate','verified','rejected','stale')),
 extraction_model text,
 source_observed_at timestamptz,
 expires_at timestamptz,
 provenance jsonb not null default '{}'::jsonb,
 created_at timestamptz not null default now(),
 unique(tenant_key,id),
 foreign key (tenant_key,source_node_id) references sm_intel.graph_nodes(tenant_key,id) on delete cascade,
 foreign key (tenant_key,target_node_id) references sm_intel.graph_nodes(tenant_key,id) on delete cascade,
 check(source_node_id<>target_node_id)
);
create index if not exists sm_edges_forward_idx on sm_intel.graph_edges(tenant_key,source_node_id,relation_type,review_status);
create index if not exists sm_edges_backward_idx on sm_intel.graph_edges(tenant_key,target_node_id,relation_type,review_status);

create table if not exists sm_intel.graph_edge_evidence (
 id uuid primary key default gen_random_uuid(),
 edge_id uuid not null references sm_intel.graph_edges(id) on delete cascade,
 research_evidence_id uuid references sm_intel.research_evidence(id) on delete restrict,
 source_record_type text,
 source_record_id text,
 source_url text,
 observed_at timestamptz,
 polarity text not null default 'supports' check(polarity in ('supports','contradicts','context')),
 added_at timestamptz not null default now(),
 check(research_evidence_id is not null or source_record_id is not null or source_url is not null)
);
create index if not exists sm_edge_evidence_link_idx on sm_intel.graph_edge_evidence(edge_id,polarity);

create table if not exists sm_intel.decision_traces (
 id uuid primary key default gen_random_uuid(),
 market_code text not null default 'GR' check(market_code='GR'),
 region_code text not null default 'GR',
 intent_class text,
 problem_cluster_id uuid references public.market_problem_clusters(id) on delete set null,
 candidate_count integer not null default 0 check(candidate_count>=0),
 verified_offer_count integer not null default 0 check(verified_offer_count>=0),
 retrieval_mode text not null default 'lexical_sql',
 model_version text,
 evidence_refs jsonb not null default '[]'::jsonb,
 reason_codes jsonb not null default '[]'::jsonb,
 duration_ms integer check(duration_ms is null or duration_ms>=0),
 occurred_at timestamptz not null default now()
);

create or replace view sm_intel.promotion_ready_offers
with (security_invoker=true) as
select q.id as qualified_offer_id,q.raw_product_id,q.merchant_profile_id,
       r.product_title,r.category_raw,r.source_product_id,
       q.price_eur,q.calculated_commission_eur,q.tracking_url,q.valid_to
from sm_intel.qualified_offers q
join sm_intel.raw_products r on r.id=q.raw_product_id
join sm_intel.commission_terms t on t.id=q.commission_terms_id
where q.review_status='approved'
  and q.merchant_approval='approved'
  and q.tracking_verification='verified'
  and q.stock_available is true
  and t.review_status='verified'
  and (t.effective_until is null or t.effective_until>now())
  and (q.valid_to is null or q.valid_to>now())
  and r.source_state<>'removed'
  and q.calculated_commission_eur>=10;
revoke all on sm_intel.promotion_ready_offers from public,anon,authenticated;

-- Private data plane; no browser/client access and no exposure of other VMDB tenants.
do $$
declare t record;
begin
 for t in select tablename from pg_tables where schemaname='sm_intel' loop
   execute format('alter table sm_intel.%I enable row level security',t.tablename);
   execute format('revoke all on sm_intel.%I from public,anon,authenticated',t.tablename);
 end loop;
end $$;
revoke all on all functions in schema sm_intel from public,anon,authenticated;
grant usage on schema sm_intel to service_role;
grant select,insert,update,delete on all tables in schema sm_intel to service_role;
grant execute on function sm_intel.calculate_commission_eur(numeric,text,numeric) to service_role;
grant execute on function sm_intel.validate_qualified_offer() to service_role;
comment on table sm_intel.raw_products is 'Full Linkwise scan catalog, includes unqualified/quarantined records; no commercial admission implied';
comment on table sm_intel.qualified_offers is 'Hard admission >=EUR10 from verified commission terms; not automatically promotion-ready';
comment on table sm_intel.pain_gap_scores is 'Time- and region-scoped Greek demand versus verified local supply, research required';
comment on table sm_intel.graph_edges is 'Evidence-backed SocialMarket-only typed graph; candidate != verified';
