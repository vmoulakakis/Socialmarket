create or replace function evidence.mirror_merchant_evidence()
returns trigger
language plpgsql
security definer
set search_path = evidence, public
as $$
begin
  insert into evidence.observations(
    entity_type, entity_id, source_kind, platform, source_url, source_domain,
    collector, title, body, metrics, metadata, confidence, validation_status, content_hash
  ) values (
    'merchant', new.merchant_id, new.evidence_type,
    nullif(new.metadata->>'platform',''), new.source_url, new.source_domain,
    coalesce(nullif(new.metadata->>'collector',''),'merchant_research_gateway'),
    new.title, new.snippet,
    coalesce(new.metadata->'metrics','{}'::jsonb), new.metadata,
    coalesce(new.confidence,0),
    case when coalesce(new.confidence,0) >= 0.7 then 'validated' else 'pending' end,
    coalesce(new.content_hash, md5(coalesce(new.source_url,'') || '|' || coalesce(new.title,'') || '|' || coalesce(new.snippet,'')))
  )
  on conflict(entity_type, entity_id, source_kind, content_hash)
  do update set collected_at=now(), confidence=greatest(evidence.observations.confidence,excluded.confidence), metadata=evidence.observations.metadata || excluded.metadata;
  return new;
end $$;

drop trigger if exists trg_mirror_merchant_evidence on intel.merchant_evidence;
create trigger trg_mirror_merchant_evidence
after insert or update on intel.merchant_evidence
for each row execute function evidence.mirror_merchant_evidence();

create or replace function evidence.mirror_merchant_audit()
returns trigger
language plpgsql
security definer
set search_path = evidence, public
as $$
declare a jsonb;
begin
  a := new.metadata->'audit';
  if a is null then return new; end if;
  insert into evidence.audit_results(
    entity_type,entity_id,target_type,target_id,audit_agent,
    identity_score,source_quality_score,source_diversity_score,contradiction_score,
    taxonomy_score,demand_validation_score,competition_validation_score,pain_validation_score,
    social_validation_score,overall_score,verdict,reasons,contradictions,metadata
  ) values (
    'merchant',new.merchant_id,'merchant_research_snapshot',new.id,'skeptic_v1',
    nullif(a->>'identity_score','')::numeric,
    nullif(a->>'source_quality_score','')::numeric,
    nullif(a->>'source_diversity_score','')::numeric,
    nullif(a->>'contradiction_score','')::numeric,
    nullif(a->>'taxonomy_score','')::numeric,
    nullif(a->>'demand_validation_score','')::numeric,
    nullif(a->>'competition_validation_score','')::numeric,
    nullif(a->>'pain_validation_score','')::numeric,
    nullif(a->>'social_validation_score','')::numeric,
    nullif(a->>'overall_score','')::numeric,
    coalesce(nullif(a->>'verdict',''),'needs_review'),
    coalesce(a->'reasons','[]'::jsonb),coalesce(a->'contradictions','[]'::jsonb),
    jsonb_build_object('snapshot_methodology',new.methodology_version,'snapshot_metadata',new.metadata-'audit')
  );
  return new;
end $$;

drop trigger if exists trg_mirror_merchant_audit on intel.merchant_research_snapshots;
create trigger trg_mirror_merchant_audit
after insert on intel.merchant_research_snapshots
for each row execute function evidence.mirror_merchant_audit();
