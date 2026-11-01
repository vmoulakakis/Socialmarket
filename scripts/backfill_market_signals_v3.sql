-- Safe, idempotent candidate-only historic market signals bridge
-- Candidate-only bridge from historical evidence. No automatic verification or fabricated demand.
with added as (
 insert into sm_intel.market_signals_v3(
  problem_cluster_id,region_code,signal_type,metric_name,
  qualitative_finding,source_family,source_record_id,source_url,
  observed_at,expires_at,raw_payload,evidence_status,source_fingerprint)
 select e.problem_cluster_id,coalesce(nullif(e.region_code,''),'GR'),
  case when e.signal_kind in ('supply','competition','demand') then e.signal_kind
       else 'competition' end,
  'legacy_'||e.signal_kind,
  left(coalesce(e.signal_value->>'snippet',e.signal_value->>'title',e.source_family),750),
  'legacy_evidence:'||e.source_family,e.id::text,e.source_url,e.observed_at,
  e.expires_at,e.signal_value,'candidate',e.source_sha256
 from sm_intel.research_evidence e
 where e.problem_cluster_id is not null
 on conflict(source_family,source_record_id,signal_type,problem_cluster_id) do nothing
 returning id
)
select count(*) inserted_candidate_market_evidence from added;
