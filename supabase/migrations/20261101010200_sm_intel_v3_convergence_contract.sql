-- SocialMarket 3.0 convergence contract.
-- One read model across historical opportunity scouting and strict verified-v3 signals.
-- Do not merge candidate evidence into verified evidence or approve affiliate links.
create or replace view sm_intel.intelligence_convergence_v3 with (security_invoker=true) as
select p.id problem_cluster_id,p.problem_title,p.category,
       coalesce(old.evidence_status,'research_needed') legacy_research_status,
       coalesce(old.demand_sources,0) historical_demand_sources,
       coalesce(old.supply_sources,0) historical_supply_sources,
       coalesce(old.counter_sources,0) historical_counter_sources,
       coalesce(src.total_observations,0) v3_observation_count,
       coalesce(src.verified_demand,0) verified_demand_sources,
       coalesce(src.verified_supply,0) verified_supply_sources,
       coalesce(src.independent_sources,0) independent_verified_sources,
       coalesce(src.candidate_observations,0) historical_candidates,
       coalesce(count(c.document_id) filter(where c.relevance_review<>'rejected'),0) unreviewed_product_matches,
       coalesce(count(c.document_id) filter(where c.relevance_review='rejected'),0) rejected_product_matches,
       case when coalesce(src.verified_demand,0)>0
                  and coalesce(src.verified_supply,0)>0
                  and coalesce(src.independent_sources,0)>=2
             then 'eligible_for_independent_market_review'
            when coalesce(src.candidate_observations,0)>0
             then 'research_sources_need_verification'
            else 'demand_and_supply_research_missing' end intelligence_state,
       (select count(*) from sm_intel.market_assessments_v3 a
         where a.problem_cluster_id=p.id and a.judgment='verified_opportunity') verified_assessments
from public.market_problem_clusters p
left join sm_intel.opportunity_research_v3 old on old.problem_cluster_id=p.id and old.region_code='GR'
left join sm_intel.market_evidence_coverage_v3 src on src.problem_cluster_id=p.id
left join sm_intel.opportunity_product_candidates_v3 c on c.problem_cluster_id=p.id
where p.market_code='GR'
group by p.id,p.problem_title,p.category,old.evidence_status,old.demand_sources,old.supply_sources,
 old.counter_sources,src.total_observations,src.verified_demand,src.verified_supply,
 src.independent_sources,src.candidate_observations;
revoke all on sm_intel.intelligence_convergence_v3 from public,anon,authenticated;
grant select on sm_intel.intelligence_convergence_v3 to service_role;
