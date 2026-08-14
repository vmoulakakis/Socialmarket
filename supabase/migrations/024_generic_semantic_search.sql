create index if not exists semantic_clusters_gte_hnsw_idx
on evidence.semantic_clusters using hnsw (embedding_gte extensions.vector_cosine_ops)
where embedding_gte is not null and validation_status='validated';

create or replace function evidence.search_semantic_clusters(
  p_embedding text,
  p_entity_type text default null,
  p_cluster_types text[] default null,
  p_limit integer default 20,
  p_min_confidence numeric default 0.55
)
returns table(
  id uuid, entity_type text, entity_id uuid, cluster_type text,
  canonical_text text, category text, subcategory text,
  demand_score numeric, competition_score numeric, pain_severity numeric,
  commercial_intent numeric, audit_score numeric, confidence numeric,
  similarity double precision, evidence_count integer, source_diversity integer,
  metadata jsonb
)
language sql stable security definer set search_path=''
as $$
  select c.id,c.entity_type,c.entity_id,c.cluster_type,c.canonical_text,c.category,c.subcategory,
         c.demand_score,c.competition_score,c.pain_severity,c.commercial_intent,c.audit_score,c.confidence,
         1 - (c.embedding_gte OPERATOR(extensions.<=>) p_embedding::extensions.vector) as similarity,
         c.evidence_count,c.source_diversity,c.metadata
  from evidence.semantic_clusters c
  where c.validation_status='validated'
    and c.embedding_status='ready'
    and c.embedding_gte is not null
    and c.confidence >= coalesce(p_min_confidence,0.55)
    and (p_entity_type is null or c.entity_type=p_entity_type)
    and (p_cluster_types is null or c.cluster_type=any(p_cluster_types))
  order by c.embedding_gte OPERATOR(extensions.<=>) p_embedding::extensions.vector
  limit greatest(1,least(coalesce(p_limit,20),100));
$$;
