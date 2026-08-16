create or replace view public.merchant_profiles with (security_invoker=true) as
select distinct on (r.merchant_id)
  r.merchant_id as id,
  r.canonical_name as merchant_name,
  null::numeric as internal_trust_score,
  r.trust_score,
  r.research_confidence as trust_confidence,
  null::numeric as external_reputation_score,
  null::numeric as external_reputation_confidence,
  coalesce(r.risk_flag,false) as external_risk_flag,
  r.risk_reason as external_risk_reason,
  null::numeric as complaint_risk_score,
  null::numeric as review_footprint_score,
  case when r.identity_confidence is null then null
       when r.identity_confidence <= 1 then r.identity_confidence*100
       else r.identity_confidence end as business_identity_score,
  r.official_domain,
  null::numeric as domain_age_years,
  r.evidence_count,
  null::bigint as active_offer_count,
  null::numeric as duplicate_win_rate,
  r.researched_at as last_researched_at
from public.merchant_rankings r
order by r.merchant_id, r.global_rank nulls last, r.overall_opportunity_score desc nulls last, r.researched_at desc nulls last;

revoke all on public.merchant_profiles from public, anon, authenticated;
grant select on public.merchant_profiles to authenticated, service_role;

create or replace view public.niche_candidates with (security_invoker=true) as
select
  m.id,
  coalesce(m.subcategory_name,m.taxonomy_name,m.category_name) as label,
  m.category_name as category_raw,
  null::bigint as product_count,
  null::bigint as merchant_count,
  null::bigint as brand_count,
  null::numeric as median_price,
  null::bigint as total_times_bought,
  null::numeric as cluster_cohesion,
  m.demand_score as demand_proxy,
  m.competition_score as seller_saturation_proxy,
  m.opportunity_score as discovery_score,
  null::numeric as trend_demand,
  null::numeric as forecast_growth,
  m.competition_score as seller_competition,
  null::numeric as ad_pressure_proxy,
  m.opportunity_score as market_score,
  m.confidence as market_confidence,
  null::boolean as competition_kill,
  null::text as kill_reason,
  case when coalesce(m.validated_pain_clusters,0)>0 then 'validated_signal' else 'research_only' end as status,
  m.observed_at as created_at
from api.semantic_category_market_v2 m
where m.geography='GR';

revoke all on public.niche_candidates from public, anon, authenticated;
grant select on public.niche_candidates to authenticated, service_role;
