-- SocialMarket AI Architect v1.2 -- graph program provenance and objective KPIs.
-- Source joins use exact program IDs only; never merchant-name similarity as proof.
create or replace view sm_intel.orchestrator_objective_health with (security_invoker=true) as
select
 'socialmarket_greece_v1'::text portfolio,
 (select count(*) from sm_intel.raw_products) raw_products,
 (select count(*) from sm_intel.raw_products where last_seen_at>=now()-interval '7 days') fresh_products_7d,
 (select count(*) from sm_intel.merchant_program_directory) merchant_program_rows,
 (select count(*) from sm_intel.merchant_program_directory where linkwise_program_id is null) missing_program_ids,
 (select count(*) from sm_intel.merchant_program_directory where terms_valid_to is null) unknown_terms_valid_to,
 (select count(*) from sm_intel.commission_terms where review_status='verified') verified_commission_terms,
 (select count(*) from sm_intel.qualified_offers) qualified_offers,
 (select count(*) from sm_intel.promotion_ready_offers) promotion_ready_offers,
 (select count(*) from sm_intel.search_documents) searchable_docs,
 (select count(*) from sm_intel.search_documents where embedding_status='ready') vector_docs,
 (select count(*) from sm_intel.graph_nodes) graph_nodes,
 (select count(*) from sm_intel.graph_edges) graph_edges,
 (select count(*) from sm_intel.graph_edges where review_status='verified') graph_verified_edges,
 (select count(*) from sm_intel.agent_tasks) agent_tasks,
 (select count(*) from sm_intel.agent_tasks where state='queued') agent_queued,
 (select count(*) from sm_intel.agent_tasks where state='candidate') agent_candidates,
 (select count(*) from sm_intel.agent_tasks where state='reviewed') agent_reviewed,
 (select count(*) from sm_intel.agent_learning_observations where review_state='verified') reviewed_learning_events,
 now() as observed_at;
revoke all on sm_intel.orchestrator_objective_health from public,anon,authenticated;
grant select on sm_intel.orchestrator_objective_health to service_role;

create or replace function sm_intel.link_verified_program_ids()
returns jsonb language plpgsql security invoker set search_path='' as $$
declare n int;
begin
 with chosen as (
 select r.id raw_id,p.id program_id,
  rn.id source_node_id,pn.id target_node_id,
  r.last_seen_at observed_at
 from sm_intel.raw_products r
 join sm_intel.merchant_program_directory p on p.linkwise_program_id=r.program_id
   and p.linkwise_program_id is not null and p.publisher_key='CD104'
 join sm_intel.graph_nodes rn on rn.source_table='sm_intel.raw_products' and rn.source_pk=r.id::text and rn.node_type='product'
 join sm_intel.graph_nodes pn on pn.source_table='sm_intel.merchant_program_directory' and pn.source_pk=p.id::text and pn.node_type='program'
 where r.program_id<> 'unknown' and r.source_product_id is not null
 ), added as (
 insert into sm_intel.graph_edges(source_node_id,target_node_id,relation_type,review_status,evidence_confidence,source_observed_at,provenance)
 select a.source_node_id,a.target_node_id,'BELONGS_TO','candidate',0,
  a.observed_at,jsonb_build_object('identity_source','exact_linkwise_program_id',
   'raw_product_id',a.raw_id,'merchant_program_directory_id',a.program_id,
   'verification','candidate_only_source_id')
 from chosen a
 where not exists(select 1 from sm_intel.graph_edges g
  where g.source_node_id=a.source_node_id and g.target_node_id=a.target_node_id and g.relation_type='BELONGS_TO')
 returning id)
 select count(*) into n from added;
 return jsonb_build_object('candidate_product_program_edges_added',n,
 'warning','exact_program_id_consistency_is_not_current_publisher_approval');
end $$;
revoke all on function sm_intel.link_verified_program_ids() from public,anon,authenticated;
grant execute on function sm_intel.link_verified_program_ids() to service_role;
