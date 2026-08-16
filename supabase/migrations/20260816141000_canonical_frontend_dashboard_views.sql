create or replace view public.merchant_dashboard with (security_invoker=true) as
select distinct on (r.merchant_id)
  r.merchant_id,
  r.canonical_name,
  r.official_domain,
  r.primary_category,
  r.peer_group,
  r.trust_score,
  r.overall_opportunity_score,
  r.competition_intensity_score,
  r.greek_market_fit_score,
  r.deep_research_score,
  r.research_confidence,
  r.risk_flag,
  r.risk_reason,
  r.evidence_count,
  r.researched_at,
  r.global_rank,
  r.score_stage,
  r.methodology_version
from public.merchant_rankings r
order by r.merchant_id, r.global_rank nulls last, r.overall_opportunity_score desc nulls last, r.researched_at desc nulls last;

revoke all on public.merchant_dashboard from public, anon, authenticated;
grant select on public.merchant_dashboard to authenticated, service_role;

create or replace view public.category_market_dashboard with (security_invoker=true) as
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
