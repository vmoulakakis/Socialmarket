-- SocialMarket: verified research coverage must use fresh observations,
-- not merely non-expired source rows or legacy inferred demand scores.
create or replace view sm_intel.market_evidence_coverage_v3 with (security_invoker=true) as
with sourced as (
 select p.id problem_cluster_id,p.problem_title,p.category,p.subcategory,
   s.id evidence_id,s.signal_type,s.evidence_status,s.independent_source_key,
   s.observed_at,s.expires_at,
   (
     s.evidence_status='verified'
     and s.observed_at>=now()-interval '90 days'
     and s.observed_at<=now()
     and (s.expires_at is null or s.expires_at>now())
     and s.independent_source_key is not null
   ) fresh_verified
 from public.market_problem_clusters p
 left join sm_intel.market_signals_v3 s on
   s.problem_cluster_id=p.id and s.region_code='GR'
 where p.market_code='GR'
), metrics as (
 select problem_cluster_id,problem_title,category,subcategory,
   count(evidence_id) total_observations,
   count(evidence_id) filter(where signal_type='demand' and fresh_verified) verified_demand,
   count(evidence_id) filter(where signal_type='supply' and fresh_verified) verified_supply,
   count(distinct independent_source_key) filter(where fresh_verified) independent_sources,
   count(evidence_id) filter(where evidence_status='candidate') candidate_observations,
   max(observed_at) latest_observation
 from sourced
 group by problem_cluster_id,problem_title,category,subcategory
)
select problem_cluster_id,problem_title,category,subcategory,'GR'::text region_code,
 total_observations,verified_demand,verified_supply,independent_sources,
 candidate_observations,latest_observation,
 case
   when verified_demand=0 then 'verify_demand'
   when verified_supply=0 then 'verify_supply'
   when independent_sources<2 then 'verify_independent_source'
   else 'ready_for_assessment'
 end next_action
from metrics;
revoke all on sm_intel.market_evidence_coverage_v3 from public,anon,authenticated;
grant select on sm_intel.market_evidence_coverage_v3 to service_role;
