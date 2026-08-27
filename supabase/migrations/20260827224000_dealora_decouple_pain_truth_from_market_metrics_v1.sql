-- Pain truth and market-size/competition coverage are separate evidence questions.
-- A canonical taxonomy pain can be validated from strong independent consumer evidence
-- even when demand/competition market metrics are not yet available.

create or replace function evidence.normalize_and_validate_taxonomy_pain_v1()
returns trigger
language plpgsql
security invoker
set search_path = evidence, public, pg_temp
as $$
begin
  if new.entity_type <> 'taxonomy'
     or new.cluster_type not in ('pain','complaint','unmet_need','alternative_request') then
    return new;
  end if;

  -- Local models occasionally express 0-100 decision scores as 0-1 fractions.
  -- Normalize only audited category-pain rows; confidence intentionally remains 0-1.
  if coalesce(new.metadata->>'worker','') = 'semantic_category_pain_v4' then
    if new.pain_severity is not null and new.pain_severity > 0 and new.pain_severity <= 1 then
      new.pain_severity := new.pain_severity * 100;
    end if;
    if new.commercial_intent is not null and new.commercial_intent > 0 and new.commercial_intent <= 1 then
      new.commercial_intent := new.commercial_intent * 100;
    end if;
    if new.audit_score is not null and new.audit_score > 0 and new.audit_score <= 1 then
      new.audit_score := new.audit_score * 100;
    end if;
  end if;

  if coalesce(new.metadata->>'worker','') = 'semantic_category_pain_v4'
     and coalesce(new.metadata->>'ai_verdict','') = 'validated'
     and coalesce((new.metadata->>'independent_source_gate')::boolean,false)
     and coalesce(new.evidence_count,0) >= 3
     and coalesce(new.source_diversity,0) >= 2
     and coalesce(new.confidence,0) >= 0.72
     and coalesce(new.audit_score,0) >= 72
     and coalesce(new.pain_severity,0) >= 50
     and coalesce(new.commercial_intent,0) >= 35 then
    new.validation_status := 'validated';
    if new.embedding_status is distinct from 'ready' then
      new.embedding_status := 'pending';
    end if;
    new.metadata := coalesce(new.metadata,'{}'::jsonb) || jsonb_build_object(
      'pain_truth_gate','consumer_evidence_independent_v1',
      'market_metrics_required_for_pain_truth',false,
      'normalized_by','evidence.normalize_and_validate_taxonomy_pain_v1'
    );
  end if;

  return new;
end
$$;

drop trigger if exists trg_normalize_validate_taxonomy_pain_v1 on evidence.semantic_clusters;
create trigger trg_normalize_validate_taxonomy_pain_v1
before insert or update on evidence.semantic_clusters
for each row execute function evidence.normalize_and_validate_taxonomy_pain_v1();

-- Re-evaluate existing audited taxonomy rows through the trigger without deleting evidence.
update evidence.semantic_clusters
set updated_at = now()
where entity_type='taxonomy'
  and cluster_type in ('pain','complaint','unmet_need','alternative_request')
  and coalesce(metadata->>'worker','')='semantic_category_pain_v4';
