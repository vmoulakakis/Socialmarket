create unique index if not exists semantic_clusters_entity_text_uniq
on evidence.semantic_clusters(entity_type,entity_id,cluster_type,md5(canonical_text));

create or replace function evidence.materialize_merchant_pain_clusters()
returns trigger
language plpgsql
security definer
set search_path=''
as $$
declare
  v_verdict text;
  v_audit numeric;
  v_diversity integer;
  v_pain text;
  v_status text;
begin
  if new.metadata->>'worker' <> 'merchant_intelligence_v4' then return new; end if;
  v_verdict := coalesce(new.metadata->'audit'->>'verdict','needs_review');
  if v_verdict='rejected' then return new; end if;
  v_audit := nullif(new.metadata->'audit'->>'overall_score','')::numeric;
  v_diversity := coalesce(nullif(new.metadata->'audit'->>'source_diversity_score','')::numeric,0)::integer;
  v_status := case when v_verdict='validated' then 'validated' else 'pending' end;

  for v_pain in select jsonb_array_elements_text(coalesce(new.metadata->'pain_language','[]'::jsonb))
  loop
    if length(trim(v_pain)) < 12 then continue; end if;
    insert into evidence.semantic_clusters(
      entity_type,entity_id,cluster_type,canonical_text,category,subcategory,
      evidence_count,source_diversity,audit_score,confidence,validation_status,
      embedding_status,metadata,updated_at
    ) values(
      'merchant',new.merchant_id,'pain',trim(v_pain),
      (select primary_category from catalog.merchants where id=new.merchant_id),
      (select primary_subcategory from catalog.merchants where id=new.merchant_id),
      new.evidence_count,v_diversity,v_audit,new.confidence,v_status,
      case when v_status='validated' then 'pending' else 'stale' end,
      jsonb_build_object('source_snapshot_id',new.id,'audit_verdict',v_verdict,'worker','merchant_intelligence_v4','relevance_gate','entity_bound_v2'),now()
    )
    on conflict(entity_type,entity_id,cluster_type,md5(canonical_text)) do update set
      category=excluded.category,subcategory=excluded.subcategory,evidence_count=excluded.evidence_count,
      source_diversity=excluded.source_diversity,audit_score=excluded.audit_score,confidence=excluded.confidence,
      validation_status=excluded.validation_status,
      embedding_status=case when evidence.semantic_clusters.canonical_text=excluded.canonical_text and evidence.semantic_clusters.validation_status=excluded.validation_status and evidence.semantic_clusters.embedding_status='ready' then 'ready' else excluded.embedding_status end,
      metadata=evidence.semantic_clusters.metadata||excluded.metadata,updated_at=now();
  end loop;
  return new;
end $$;

drop trigger if exists trg_materialize_merchant_pain_clusters on intel.merchant_research_snapshots;
create trigger trg_materialize_merchant_pain_clusters
after insert on intel.merchant_research_snapshots
for each row execute function evidence.materialize_merchant_pain_clusters();
