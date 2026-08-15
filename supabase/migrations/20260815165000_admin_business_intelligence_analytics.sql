create table if not exists ops.product_intelligence_run_profiles (
  id uuid primary key default gen_random_uuid(),
  phase text not null check (phase in ('A','B')),
  status text not null default 'completed',
  config_version integer,
  profile jsonb not null,
  recorded_at timestamptz not null default now()
);
alter table ops.product_intelligence_run_profiles enable row level security;
create index if not exists product_intelligence_run_profiles_phase_time_idx on ops.product_intelligence_run_profiles(phase,recorded_at desc);

create or replace function public.admin_product_pipeline_analytics()
returns jsonb language plpgsql security definer set search_path=''
as $$ declare a jsonb; b jsonb; begin
  if not public.socialmarket_is_admin() then raise exception 'admin_only'; end if;
  select profile into a from ops.product_intelligence_run_profiles where phase='A' order by recorded_at desc limit 1;
  select profile into b from ops.product_intelligence_run_profiles where phase='B' order by recorded_at desc limit 1;
  return jsonb_build_object('latest_phase_a',a,'latest_phase_b',b,
    'recent_runs',coalesce((select jsonb_agg(to_jsonb(x) order by x.recorded_at desc) from (select id,phase,status,config_version,recorded_at,profile from ops.product_intelligence_run_profiles order by recorded_at desc limit 30)x),'[]'::jsonb),
    'phase_a_exclusions',coalesce(a->'excluded_reasons','[]'::jsonb),'phase_b_stats',coalesce(b,'{}'::jsonb));
end $$;
revoke all on function public.admin_product_pipeline_analytics() from public;
grant execute on function public.admin_product_pipeline_analytics() to authenticated;

create or replace function public.admin_business_intelligence_snapshot()
returns jsonb language plpgsql security definer set search_path=''
as $$ declare out_json jsonb; begin
 if not public.socialmarket_is_admin() then raise exception 'admin_only'; end if;
 select jsonb_build_object(
  'generated_at',now(),
  'pipeline',jsonb_build_object(
    'merchants',(select count(*) from catalog.merchants),'merchant_programs',(select count(*) from catalog.merchant_programs),
    'evidence_observations',(select count(*) from evidence.observations),'validated_observations',(select count(*) from evidence.observations where validation_status='validated'),
    'semantic_clusters',(select count(*) from evidence.semantic_clusters),'validated_pain_clusters',(select count(*) from evidence.semantic_clusters where validation_status='validated' and cluster_type in ('pain','complaint','unmet_need','alternative_request')),
    'embedded_clusters',(select count(*) from evidence.semantic_clusters where embedding_status='ready'),'products',(select count(*) from catalog.products),
    'validated_products',(select count(*) from catalog.products where status='validated'),'offers',(select count(*) from catalog.product_offers),
    'eligible_offers',(select count(*) from catalog.product_offers where eligible),'product_intelligence_snapshots',(select count(*) from intel.product_intelligence_snapshots),
    'product_pain_matches',(select count(*) from intel.product_pain_matches)),
  'freshness',jsonb_build_object(
    'latest_evidence_at',(select max(collected_at) from evidence.observations),'latest_audit_at',(select max(audited_at) from evidence.audit_results),
    'latest_semantic_cluster_at',(select max(updated_at) from evidence.semantic_clusters),'latest_product_intelligence_at',(select max(observed_at) from intel.product_intelligence_snapshots),
    'latest_merchant_run_started_at',(select max(started_at) from intel.merchant_research_runs),'latest_merchant_run_finished_at',(select max(finished_at) from intel.merchant_research_runs),
    'evidence_24h',(select count(*) from evidence.observations where collected_at>=now()-interval '24 hours'),'evidence_7d',(select count(*) from evidence.observations where collected_at>=now()-interval '7 days'),
    'stale_clusters_7d',(select count(*) from evidence.semantic_clusters where updated_at<now()-interval '7 days' and validation_status='validated')),
  'evidence_by_source',coalesce((select jsonb_agg(to_jsonb(x) order by x.observations desc) from (select source_kind,count(*) observations,count(*) filter(where validation_status='validated') validated,round(avg(confidence)::numeric,3) avg_confidence,max(collected_at) latest_at from evidence.observations group by source_kind)x),'[]'::jsonb),
  'evidence_by_platform',coalesce((select jsonb_agg(to_jsonb(x) order by x.observations desc) from (select coalesce(platform,'web') platform,count(*) observations,round(avg(confidence)::numeric,3) avg_confidence,max(collected_at) latest_at from evidence.observations group by coalesce(platform,'web'))x),'[]'::jsonb),
  'audit_distribution',coalesce((select jsonb_agg(to_jsonb(x) order by x.audits desc) from (select verdict,count(*) audits,round(avg(overall_score)::numeric,2) avg_overall,round(avg(source_quality_score)::numeric,2) avg_source_quality,round(avg(source_diversity_score)::numeric,2) avg_source_diversity,round(avg(pain_validation_score)::numeric,2) avg_pain_validation,max(audited_at) latest_at from evidence.audit_results group by verdict)x),'[]'::jsonb),
  'top_pain_clusters',coalesce((select jsonb_agg(to_jsonb(x) order by x.opportunity_index desc nulls last) from (select id,canonical_text,category,subcategory,evidence_count,source_diversity,demand_score,competition_score,pain_severity,commercial_intent,audit_score,confidence,updated_at,round((coalesce(demand_score,0)*0.30+coalesce(pain_severity,0)*0.30+(100-coalesce(competition_score,50))*0.20+coalesce(commercial_intent,0)*0.15+least(coalesce(source_diversity,0)*10,100)*0.05)::numeric,2) opportunity_index from evidence.semantic_clusters where validation_status='validated' and cluster_type in ('pain','complaint','unmet_need','alternative_request') order by opportunity_index desc nulls last limit 100)x),'[]'::jsonb),
  'merchant_opportunities',coalesce((select jsonb_agg(to_jsonb(x) order by x.solution_whitespace_score desc nulls last) from (select merchant_id,canonical_name,taxonomy_name,demand_score,competition_score,pain_gap_score,social_pain_score,social_mentions,trust_score,confidence,solution_whitespace_score,demand_beacon_score from api.merchant_dual_role_scores order by solution_whitespace_score desc nulls last limit 100)x),'[]'::jsonb),
  'product_opportunities',coalesce((select jsonb_agg(to_jsonb(x) order by x.final_opportunity_score desc nulls last) from (select * from api.product_opportunities order by final_opportunity_score desc nulls last limit 200)x),'[]'::jsonb),
  'research_job_health',coalesce((select jsonb_agg(to_jsonb(x) order by x.jobs desc) from (select entity_type,job_type,status,count(*) jobs,round(avg(extract(epoch from(coalesce(completed_at,now())-requested_at))/60.0)::numeric,1) avg_age_minutes,max(attempt_count) max_attempts,count(*) filter(where last_error is not null) with_error from ops.research_jobs group by entity_type,job_type,status)x),'[]'::jsonb),
  'collection_job_health',coalesce((select jsonb_agg(to_jsonb(x) order by x.jobs desc) from (select entity_type,collection_type,status,count(*) jobs,round(avg(extract(epoch from(coalesce(completed_at,now())-requested_at))/60.0)::numeric,1) avg_age_minutes,max(attempt_count) max_attempts,count(*) filter(where last_error is not null) with_error from ops.collection_jobs group by entity_type,collection_type,status)x),'[]'::jsonb),
  'queue_alerts',jsonb_build_object('research_failed',(select count(*) from ops.research_jobs where status='failed'),'research_stuck_running',(select count(*) from ops.research_jobs where status='running' and lease_expires_at<now()),'research_queued_over_6h',(select count(*) from ops.research_jobs where status='queued' and requested_at<now()-interval '6 hours'),'collection_failed',(select count(*) from ops.collection_jobs where status='failed'),'collection_stuck_running',(select count(*) from ops.collection_jobs where status='running' and lease_expires_at<now()),'collection_queued_over_6h',(select count(*) from ops.collection_jobs where status='queued' and requested_at<now()-interval '6 hours')),
  'ai_summary',jsonb_build_object('calls_7d',(select coalesce(sum(calls),0) from ops.ai_usage_daily where usage_day>=current_date-6),'input_tokens_7d',(select coalesce(sum(input_tokens),0) from ops.ai_usage_daily where usage_day>=current_date-6),'output_tokens_7d',(select coalesce(sum(output_tokens),0) from ops.ai_usage_daily where usage_day>=current_date-6),'estimated_cost_usd_7d',(select coalesce(round(sum(estimated_cost_usd)::numeric,4),0) from ops.ai_usage_daily where usage_day>=current_date-6),'remote_requests_7d',(select count(*) from ops.ai_remote_request_log where created_at>=now()-interval '7 days'),'remote_failures_7d',(select count(*) from ops.ai_remote_request_log where created_at>=now()-interval '7 days' and status not in ('completed','success')),'avg_remote_latency_seconds_7d',(select round(avg(extract(epoch from(completed_at-created_at)))::numeric,2) from ops.ai_remote_request_log where created_at>=now()-interval '7 days' and completed_at is not null)),
  'ai_daily',coalesce((select jsonb_agg(to_jsonb(x) order by x.usage_day asc) from (select usage_day,sum(calls) calls,sum(input_tokens) input_tokens,sum(output_tokens) output_tokens,round(sum(estimated_cost_usd)::numeric,4) estimated_cost_usd from ops.ai_usage_daily where usage_day>=current_date-29 group by usage_day)x),'[]'::jsonb),
  'ai_by_model',coalesce((select jsonb_agg(to_jsonb(x) order by x.calls desc) from (select provider,model_name,task_type,sum(calls) calls,sum(input_tokens) input_tokens,sum(output_tokens) output_tokens,round(sum(estimated_cost_usd)::numeric,4) estimated_cost_usd from ops.ai_usage_daily where usage_day>=current_date-29 group by provider,model_name,task_type)x),'[]'::jsonb),
  'merchant_runs',coalesce((select jsonb_agg(to_jsonb(x) order by x.started_at desc) from (select id,status,scope,merchant_count,evidence_count,model_version,started_at,finished_at,error,case when finished_at is not null then round((extract(epoch from(finished_at-started_at))/60.0)::numeric,1) end duration_minutes from intel.merchant_research_runs order by started_at desc limit 30)x),'[]'::jsonb),
  'product_config',(select jsonb_build_object('version',version,'config',config,'updated_by',updated_by,'updated_at',updated_at) from ops.product_intelligence_config where id=1)
 ) into out_json;
 return out_json;
end $$;
revoke all on function public.admin_business_intelligence_snapshot() from public;
grant execute on function public.admin_business_intelligence_snapshot() to authenticated;
