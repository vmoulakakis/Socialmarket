-- SocialMarket v1 decision-safe data contracts, all private and read-only.
create or replace view sm_intel.market_opportunity_solutions with (security_invoker=true) as
select
 g.id as gap_assessment_id,p.id as problem_cluster_id,p.problem_title,p.category as problem_category,
 g.region_code,g.period_start,g.period_end,
 g.demand_score,g.verified_supply_score,g.supply_gap_score,g.trend_score,
 g.seasonality_score,g.commercial_intent_score,g.urgency_score,
 g.confidence as gap_confidence,g.verified_evidence_count,
 m.qualified_offer_id,q.raw_product_id,q.product_title,q.category_raw,
 q.price_eur,q.calculated_commission_eur,q.tracking_url,
 q.merchant_profile_id,merchant.merchant_name,
 m.match_score,m.confidence as suitability_confidence,
 m.buyer_intent_cohort,m.purchase_motivation,m.verified_incentive,
 mr.overall_score as verified_merchant_score,mr.demand_fit_score as merchant_demand_fit_score,
 mr.trust_score as merchant_trust_score,mr.fulfillment_score as merchant_fulfillment_score,
 m.evaluated_at as match_evaluated_at
from sm_intel.pain_gap_scores g
join public.market_problem_clusters p on p.id=g.problem_cluster_id and p.market_code='GR'
join sm_intel.pain_offer_matches m on m.gap_score_id=g.id and m.review_status='verified'
join sm_intel.promotion_ready_offers q on q.qualified_offer_id=m.qualified_offer_id
join public.merchant_profiles merchant on merchant.id=q.merchant_profile_id
left join lateral (
 select score.overall_score,score.demand_fit_score,score.trust_score,score.fulfillment_score
 from sm_intel.merchant_rankings score
 where score.merchant_profile_id=q.merchant_profile_id and score.region_code=g.region_code
   and score.review_status='verified' and score.assessed_on<=g.period_end
 order by score.assessed_on desc,score.evaluated_at desc limit 1
) mr on true
where g.judgment='verified' and g.period_end>=current_date
  and g.verified_evidence_count>=2;
revoke all on sm_intel.market_opportunity_solutions from public,anon,authenticated;
grant select on sm_intel.market_opportunity_solutions to service_role;

create or replace view sm_intel.gap_research_queue with (security_invoker=true) as
select
 p.id as problem_cluster_id,p.problem_title,p.category,p.subcategory,p.market_code,
 count(distinct ev.id) as candidate_evidence_count,
 count(distinct ev.id) filter(where ev.audit_status='verified') as verified_evidence_count,
 count(distinct ev.id) filter(where ev.signal_kind='demand' and ev.audit_status='verified') as verified_demand_sources,
 count(distinct ev.id) filter(where ev.signal_kind='supply' and ev.audit_status='verified') as verified_supply_sources,
 max(ev.observed_at) as newest_evidence_at,
 count(distinct gap.id) filter(where gap.judgment='verified') as verified_gap_assessments,
 case when count(distinct ev.id) filter(where ev.audit_status='verified')<2
  then 'research_and_independent_audit_needed'
  when count(distinct ev.id) filter(where ev.signal_kind='demand' and ev.audit_status='verified')=0
  then 'demand_verification_needed'
  when count(distinct ev.id) filter(where ev.signal_kind='supply' and ev.audit_status='verified')=0
  then 'supply_gap_verification_needed'
  else 'score_gap_by_region_and_time' end as next_research_action
from public.market_problem_clusters p
left join sm_intel.research_evidence ev on ev.problem_cluster_id=p.id
left join sm_intel.pain_gap_scores gap on gap.problem_cluster_id=p.id
where p.market_code='GR'
group by p.id,p.problem_title,p.category,p.subcategory,p.market_code;
revoke all on sm_intel.gap_research_queue from public,anon,authenticated;
grant select on sm_intel.gap_research_queue to service_role;
