create or replace view public.category_market_dashboard with (security_invoker=false) as
select
  m.id,
  m.taxonomy_id,
  m.category_name,
  m.subcategory_name,
  m.taxonomy_name,
  m.node_type,
  m.geography,
  m.observed_at,
  m.demand_score,
  m.competition_score,
  m.pain_gap_score,
  m.satisfaction_score,
  m.opportunity_score,
  m.confidence,
  m.validated_pain_clusters,
  m.methodology_version
from api.semantic_category_market_v2 m
where m.geography='GR';
revoke all on public.category_market_dashboard from public, anon, authenticated;
grant select on public.category_market_dashboard to authenticated, service_role;

create or replace view public.niche_candidates with (security_invoker=false) as
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
