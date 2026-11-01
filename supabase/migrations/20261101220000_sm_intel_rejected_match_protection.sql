-- P0: fail-closed relevance: do not expose previously rejected lexical candidate matches.
-- Preserve original contract, only remove excluded candidates.
CREATE OR REPLACE FUNCTION sm_intel.opportunity_brief_v3(p_problem_id uuid)
 RETURNS jsonb
 LANGUAGE sql
 STABLE
 SET search_path TO ''
AS $function$
select jsonb_build_object(
 'problem_id',p.id,'problem',p.problem_title,'category',p.category,
 'research',coalesce((select to_jsonb(r) from sm_intel.opportunity_research_v3 r
   where r.problem_cluster_id=p.id and r.region_code='GR'),'{}'::jsonb),
 'product_candidates',coalesce((select jsonb_agg(jsonb_build_object(
  'title',d.title,'source_state',d.source_state,'rrf_score',m.rrf_score,
  'relevance_review',m.relevance_review,'model_status',
    case when d.embedding_status='ready' then 'real_embedding' else 'fts_only' end)
  order by m.retrieval_rank)
  from sm_intel.opportunity_product_candidates_v3 m
  join sm_intel.search_documents d on d.id=m.document_id
  where m.problem_cluster_id=p.id and m.relevance_review <> 'rejected'),'[]'::jsonb),
 'commercially_approved_products',0,
 'rejected_candidates_hidden',(select count(*) from sm_intel.opportunity_product_candidates_v3 rejected where rejected.problem_cluster_id=p.id and rejected.relevance_review='rejected'),
 'assessment_status','research_only_not_purchase_advice'
)
from public.market_problem_clusters p where p.market_code='GR' and p.id=p_problem_id
$function$
;
