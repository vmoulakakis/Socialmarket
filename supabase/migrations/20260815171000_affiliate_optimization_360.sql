create table if not exists ops.affiliate_performance_daily (
  id uuid primary key default gen_random_uuid(),
  metric_date date not null,
  product_id uuid references catalog.products(id) on delete set null,
  offer_id uuid references catalog.product_offers(id) on delete set null,
  merchant_id uuid references catalog.merchants(id) on delete set null,
  program_id uuid references catalog.merchant_programs(id) on delete set null,
  content_item_id uuid,
  publishing_outbox_id uuid,
  channel text not null check (channel in ('organic_social','paid_social','paid_search','seo_content','email','direct','other')),
  platform text not null default 'other',
  variant_key text not null default 'control',
  impressions bigint not null default 0 check (impressions>=0),
  views bigint not null default 0 check (views>=0),
  sessions bigint not null default 0 check (sessions>=0),
  outbound_clicks bigint not null default 0 check (outbound_clicks>=0),
  conversions_pending integer not null default 0 check (conversions_pending>=0),
  conversions_approved integer not null default 0 check (conversions_approved>=0),
  conversions_rejected integer not null default 0 check (conversions_rejected>=0),
  commission_pending_eur numeric not null default 0,
  commission_approved_eur numeric not null default 0,
  media_spend_eur numeric not null default 0,
  content_cost_eur numeric not null default 0,
  source text not null default 'manual',
  source_ref text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
alter table ops.affiliate_performance_daily enable row level security;
create index if not exists affiliate_performance_daily_date_idx on ops.affiliate_performance_daily(metric_date desc);
create index if not exists affiliate_performance_daily_offer_idx on ops.affiliate_performance_daily(offer_id,metric_date desc);
create index if not exists affiliate_performance_daily_channel_idx on ops.affiliate_performance_daily(channel,platform,metric_date desc);
create unique index if not exists affiliate_performance_daily_dedupe_idx on ops.affiliate_performance_daily(
  metric_date,channel,platform,variant_key,
  coalesce(offer_id,'00000000-0000-0000-0000-000000000000'::uuid),
  coalesce(publishing_outbox_id,'00000000-0000-0000-0000-000000000000'::uuid),source
);

create table if not exists ops.affiliate_optimization_runs (
  id uuid primary key default gen_random_uuid(),
  mode text not null default 'simulation' check (mode in ('simulation','forecast','ai_brief')),
  assumptions jsonb not null default '{}'::jsonb,
  result jsonb not null default '{}'::jsonb,
  created_by text,
  created_at timestamptz not null default now()
);
alter table ops.affiliate_optimization_runs enable row level security;

create or replace function public.admin_affiliate_optimization_snapshot()
returns jsonb
language plpgsql
security definer
set search_path=''
as $$
declare out_json jsonb; begin
  if not public.socialmarket_is_admin() then raise exception 'admin_only'; end if;
  with latest_program as (
    select distinct on (pcs.program_id)
      pcs.*,mp.merchant_id,mp.program_name,mp.raw_commission_pct,mp.raw_flat_commission,
      m.canonical_name merchant_name,m.primary_category,
      mds.demand_score merchant_demand_score,mds.competition_score merchant_competition_score,
      mds.pain_gap_score merchant_pain_gap_score,mds.trust_score merchant_trust_score,
      mds.solution_whitespace_score,mds.demand_beacon_score
    from intel.program_commercial_snapshots pcs
    join catalog.merchant_programs mp on mp.id=pcs.program_id
    join catalog.merchants m on m.id=mp.merchant_id
    left join api.merchant_dual_role_scores mds on mds.merchant_id=m.id
    order by pcs.program_id,pcs.observed_at desc
  ),program_rows as (
    select program_id,merchant_id,program_name,merchant_name,primary_category,observed_at,
      conversion_rate,epc,approval_rate,approval_days,commission_pct_min,commission_pct_max,commission_pct_mid,
      flat_commission_min,flat_commission_max,flat_commission_mid,conversion_percentile,epc_percentile,
      approval_percentile,approval_speed_percentile,commission_percentile,commercial_score,data_confidence,rank_score,
      merchant_demand_score,merchant_competition_score,merchant_pain_gap_score,merchant_trust_score,solution_whitespace_score,demand_beacon_score,
      case when coalesce(epc_percentile,0)>=80 and coalesce(conversion_percentile,0)>=70 and coalesce(approval_percentile,0)>=70 then 'scale_candidate'
        when coalesce(epc_percentile,0)>=75 and coalesce(approval_percentile,100)<40 then 'approval_risk'
        when coalesce(conversion_percentile,0)>=75 and coalesce(epc_percentile,0)<50 then 'payout_limited'
        when coalesce(merchant_demand_score,0)>=70 and coalesce(conversion_percentile,0)<40 then 'funnel_opportunity'
        when coalesce(commercial_score,0)>=70 then 'high_priority' else 'monitor' end reaction_signal,
      case when epc is null or approval_rate is null then null else round((epc*approval_rate/100.0)::numeric,4) end quality_adjusted_epc
    from latest_program
  ),product_forecast as (
    select po.*,off.merchant_program_id as program_id,lp.program_name,lp.conversion_rate network_conversion_rate,lp.epc network_epc,
      lp.approval_rate network_approval_rate,lp.approval_days network_approval_days,lp.data_confidence network_data_confidence,
      lp.commercial_score program_commercial_score,
      case when lp.conversion_rate is null then null else round(lp.conversion_rate::numeric,3) end expected_conversions_per_100_clicks,
      case when lp.conversion_rate is null or lp.approval_rate is null then null else round((lp.conversion_rate*lp.approval_rate/100.0)::numeric,3) end expected_approved_conversions_per_100_clicks,
      case when lp.conversion_rate is null or po.expected_commission_eur is null then null else round((lp.conversion_rate*po.expected_commission_eur)::numeric,2) end expected_gross_commission_per_100_clicks,
      case when lp.conversion_rate is null or lp.approval_rate is null or po.expected_commission_eur is null then null else round((lp.conversion_rate*po.expected_commission_eur*lp.approval_rate/100.0)::numeric,2) end expected_approved_commission_per_100_clicks,
      case when lp.conversion_rate is null or lp.approval_rate is null or po.expected_commission_eur is null then null else round((lp.conversion_rate*po.expected_commission_eur*lp.approval_rate/10000.0)::numeric,4) end break_even_cpc_eur
    from api.product_opportunities po
    join catalog.product_offers off on off.id=po.offer_id
    left join latest_program lp on lp.program_id=off.merchant_program_id
  ),fp as (
    select channel,platform,sum(impressions) impressions,sum(views) views,sum(sessions) sessions,sum(outbound_clicks) outbound_clicks,
      sum(conversions_pending) conversions_pending,sum(conversions_approved) conversions_approved,sum(conversions_rejected) conversions_rejected,
      sum(commission_pending_eur) commission_pending_eur,sum(commission_approved_eur) commission_approved_eur,
      sum(media_spend_eur) media_spend_eur,sum(content_cost_eur) content_cost_eur,
      case when sum(impressions)>0 then round((sum(outbound_clicks)::numeric/sum(impressions))*100,3) end outbound_ctr_pct,
      case when sum(outbound_clicks)>0 then round((sum(conversions_approved)::numeric/sum(outbound_clicks))*100,3) end approved_cvr_pct,
      case when sum(outbound_clicks)>0 then round(sum(commission_approved_eur)::numeric/sum(outbound_clicks),4) end own_epc_eur,
      case when sum(media_spend_eur)+sum(content_cost_eur)>0 then round((sum(commission_approved_eur)-sum(media_spend_eur)-sum(content_cost_eur))::numeric/(sum(media_spend_eur)+sum(content_cost_eur))*100,2) end roi_pct,
      case when sum(outbound_clicks)>0 then round(sum(media_spend_eur)::numeric/sum(outbound_clicks),4) end paid_cpc_eur
    from ops.affiliate_performance_daily where metric_date>=current_date-29 group by channel,platform
  )
  select jsonb_build_object(
    'generated_at',now(),
    'data_coverage',jsonb_build_object(
      'network_program_snapshots',(select count(*) from latest_program),
      'network_programs_with_conversion',(select count(*) from latest_program where conversion_rate is not null),
      'network_programs_with_epc',(select count(*) from latest_program where epc is not null),
      'network_programs_with_approval',(select count(*) from latest_program where approval_rate is not null),
      'validated_products',(select count(*) from catalog.products where status='validated'),
      'product_forecasts',(select count(*) from product_forecast),
      'first_party_metric_rows_30d',(select count(*) from ops.affiliate_performance_daily where metric_date>=current_date-29),
      'published_outbox_rows',(select count(*) from api.publishing_outbox where status='published'),
      'evidence_observations',(select count(*) from evidence.observations),
      'validated_pain_clusters',(select count(*) from evidence.semantic_clusters where validation_status='validated' and cluster_type in ('pain','complaint','unmet_need','alternative_request'))),
    'program_performance',coalesce((select jsonb_agg(to_jsonb(x) order by x.rank_score desc nulls last) from (select * from program_rows order by rank_score desc nulls last limit 300)x),'[]'::jsonb),
    'reaction_queue',coalesce((select jsonb_agg(to_jsonb(x) order by x.rank_score desc nulls last) from (select * from program_rows where reaction_signal<>'monitor' order by rank_score desc nulls last limit 100)x),'[]'::jsonb),
    'product_profitability',coalesce((select jsonb_agg(to_jsonb(x) order by x.final_opportunity_score desc nulls last) from (select * from product_forecast order by final_opportunity_score desc nulls last limit 200)x),'[]'::jsonb),
    'first_party_30d',coalesce((select jsonb_agg(to_jsonb(fp) order by commission_approved_eur desc) from fp),'[]'::jsonb),
    'first_party_totals_30d',(select jsonb_build_object('impressions',coalesce(sum(impressions),0),'views',coalesce(sum(views),0),'sessions',coalesce(sum(sessions),0),'outbound_clicks',coalesce(sum(outbound_clicks),0),'conversions_pending',coalesce(sum(conversions_pending),0),'conversions_approved',coalesce(sum(conversions_approved),0),'conversions_rejected',coalesce(sum(conversions_rejected),0),'commission_pending_eur',coalesce(sum(commission_pending_eur),0),'commission_approved_eur',coalesce(sum(commission_approved_eur),0),'media_spend_eur',coalesce(sum(media_spend_eur),0),'content_cost_eur',coalesce(sum(content_cost_eur),0)) from ops.affiliate_performance_daily where metric_date>=current_date-29),
    'channel_evidence',coalesce((select jsonb_agg(to_jsonb(x) order by x.observations desc) from (select coalesce(platform,'web') platform,count(*) observations,count(*) filter(where validation_status='validated') validated,round(avg(confidence)::numeric,3) avg_confidence,max(collected_at) latest_at from evidence.observations group by coalesce(platform,'web'))x),'[]'::jsonb),
    'publishing_by_platform',coalesce((select jsonb_agg(to_jsonb(x) order by x.total desc) from (select platform,count(*) total,count(*) filter(where status='published') published,count(*) filter(where status='failed') failed,max(published_at) latest_published_at from api.publishing_outbox group by platform)x),'[]'::jsonb),
    'network_kpi_summary',(select jsonb_build_object('avg_conversion_rate',round(avg(conversion_rate)::numeric,3),'median_conversion_rate',round(percentile_cont(0.5) within group(order by conversion_rate)::numeric,3),'avg_epc',round(avg(epc)::numeric,3),'median_epc',round(percentile_cont(0.5) within group(order by epc)::numeric,3),'avg_approval_rate',round(avg(approval_rate)::numeric,3),'median_approval_rate',round(percentile_cont(0.5) within group(order by approval_rate)::numeric,3),'avg_commercial_score',round(avg(commercial_score)::numeric,2),'latest_observed_at',max(observed_at)) from latest_program),
    'methodology',jsonb_build_object(
      'observed',jsonb_build_array('network conversion_rate','network EPC','network approval_rate','merchant demand/competition/pain/trust','evidence counts','publishing status','first-party metrics when present'),
      'estimated',jsonb_build_array('product conversions per 100 clicks = network program conversion rate applied to product','approved conversions = estimated conversions × network approval rate','product commission per 100 clicks = estimated conversions × product expected commission','break-even CPC = estimated approved commission / 100 clicks'),
      'warning','Network program KPIs are baselines across the affiliate network. Channel-specific paid/organic performance is not first-party fact until SocialMarket records its own traffic and conversion metrics.')) into out_json;
  return out_json;
end $$;
revoke all on function public.admin_affiliate_optimization_snapshot() from public;
grant execute on function public.admin_affiliate_optimization_snapshot() to authenticated;

create or replace function public.admin_save_affiliate_optimization_run(p_mode text,p_assumptions jsonb,p_result jsonb)
returns uuid language plpgsql security definer set search_path=''
as $$ declare rid uuid; begin
  if not public.socialmarket_is_admin() then raise exception 'admin_only'; end if;
  if p_mode not in ('simulation','forecast','ai_brief') then raise exception 'invalid_mode'; end if;
  insert into ops.affiliate_optimization_runs(mode,assumptions,result,created_by)
  values(p_mode,coalesce(p_assumptions,'{}'::jsonb),coalesce(p_result,'{}'::jsonb),lower(auth.jwt()->>'email')) returning id into rid;
  return rid;
end $$;
revoke all on function public.admin_save_affiliate_optimization_run(text,jsonb,jsonb) from public;
grant execute on function public.admin_save_affiliate_optimization_run(text,jsonb,jsonb) to authenticated;
