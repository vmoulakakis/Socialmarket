-- Idempotent manual backfill: run only after migrations; historical candidate evidence, never auto-approve or promote.
-- Step 1
with inserted as (
 insert into sm_intel.graph_nodes(node_type,source_table,source_pk,display_label,metadata)
 select 'product','sm_intel.raw_products',r.id::text,coalesce(nullif(r.product_title,''),r.source_product_id,r.record_key),
 jsonb_build_object('source_key',r.source_key,'program_id',r.program_id,'source_state',r.source_state)
 from sm_intel.raw_products r
 on conflict(tenant_key,node_type,source_table,source_pk) do nothing returning id)
 select count(*) added_product_nodes from inserted;

-- Step 2
with inserted as (
 insert into sm_intel.graph_nodes(node_type,source_table,source_pk,display_label,metadata)
 select 'evidence','sm_intel.research_evidence',s.id::text,coalesce(s.source_family,'Evidence')||' / '||s.signal_kind,
 jsonb_build_object('source_family',s.source_family,'signal_kind',s.signal_kind,'audit_status',s.audit_status)
 from sm_intel.research_evidence s
 on conflict(tenant_key,node_type,source_table,source_pk) do nothing returning id)
 select count(*) added_evidence_nodes from inserted;

-- Step 3
with inserted as (
 insert into sm_intel.graph_edges(source_node_id,target_node_id,relation_type,review_status,evidence_confidence,source_observed_at,provenance)
 select pn.id,mn.id,'OFFERED_BY','candidate',0,e.last_seen_at,
 jsonb_build_object('source','public.commerce_feed_eligible_offers','record_id',e.id)
 from sm_intel.raw_products r
 join public.commerce_feed_eligible_offers e
 on r.record_key=concat_ws('|',e.program_id,e.source_product_id) and e.source_key='linkwise'
 join sm_intel.graph_nodes pn on pn.source_table='sm_intel.raw_products' and pn.source_pk=r.id::text and pn.node_type='product'
 join sm_intel.graph_nodes mn on mn.source_table='public.merchant_profiles' and mn.source_pk=e.merchant_profile_id::text and mn.node_type='merchant'
 where e.merchant_profile_id is not null
 and not exists (select 1 from sm_intel.graph_edges ge
   where ge.source_node_id=pn.id and ge.target_node_id=mn.id and ge.relation_type='OFFERED_BY')
 returning id) select count(*) added_product_merchant_edges from inserted;

-- Step 4
with inserted as (
 insert into sm_intel.graph_edges(source_node_id,target_node_id,relation_type,review_status,evidence_confidence,source_observed_at,provenance)
 select pn.id,en.id,'SUPPORTED_BY','candidate',0,e.observed_at,
 jsonb_build_object('source','sm_intel.research_evidence','evidence_id',e.id)
 from sm_intel.research_evidence e
 join sm_intel.graph_nodes pn on pn.source_table='public.market_problem_clusters'
 and pn.source_pk=e.problem_cluster_id::text and pn.node_type='problem'
 join sm_intel.graph_nodes en on en.source_table='sm_intel.research_evidence'
 and en.source_pk=e.id::text and en.node_type='evidence'
 where e.problem_cluster_id is not null
 and not exists (select 1 from sm_intel.graph_edges ge
    where ge.source_node_id=pn.id and ge.target_node_id=en.id and ge.relation_type='SUPPORTED_BY')
 returning id) select count(*) added_problem_evidence_edges from inserted;

-- Step 5
with inserted as (
 insert into sm_intel.graph_edges(source_node_id,target_node_id,relation_type,review_status,evidence_confidence,source_observed_at,provenance)
 select mn.id,en.id,'SUPPORTED_BY','candidate',0,e.observed_at,
 jsonb_build_object('source','sm_intel.research_evidence','evidence_id',e.id)
 from sm_intel.research_evidence e
 join sm_intel.graph_nodes mn on mn.source_table='public.merchant_profiles'
 and mn.source_pk=e.signal_value->>'merchant_id' and mn.node_type='merchant'
 join sm_intel.graph_nodes en on en.source_table='sm_intel.research_evidence'
 and en.source_pk=e.id::text and en.node_type='evidence'
 where e.source_family='merchant_evidence'
 and not exists (select 1 from sm_intel.graph_edges ge
   where ge.source_node_id=mn.id and ge.target_node_id=en.id and ge.relation_type='SUPPORTED_BY')
 returning id) select count(*) added_merchant_evidence_edges from inserted;

-- Step 6
with inserted as (
 insert into sm_intel.graph_edge_evidence(edge_id,research_evidence_id,source_record_type,source_record_id,source_url,observed_at,polarity)
 select ge.id,e.id,'sm_intel.research_evidence',e.id::text,e.source_url,e.observed_at,'context'
 from sm_intel.graph_edges ge
 join sm_intel.research_evidence e on ge.provenance->>'evidence_id'=e.id::text
 where ge.relation_type='SUPPORTED_BY'
 and not exists(select 1 from sm_intel.graph_edge_evidence ee where ee.edge_id=ge.id and ee.research_evidence_id=e.id)
 returning id) select count(*) linked_research_evidence from inserted;

-- Step 7
with inserted as (
 insert into sm_intel.graph_edge_evidence(edge_id,source_record_type,source_record_id,source_url,observed_at,polarity)
 select ge.id,'public.commerce_feed_eligible_offers',e.id::text,e.tracking_url,e.last_seen_at,'context'
 from sm_intel.graph_edges ge
 join public.commerce_feed_eligible_offers e on ge.provenance->>'record_id'=e.id::text
 where ge.relation_type='OFFERED_BY'
 and not exists(select 1 from sm_intel.graph_edge_evidence ee where ee.edge_id=ge.id and ee.source_record_id=e.id::text)
 returning id) select count(*) linked_offer_evidence from inserted;
