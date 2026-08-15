-- Admin Intelligence Console boundary. Production migration applied 2026-08-15.
create table if not exists ops.admin_action_log (
  id uuid primary key default gen_random_uuid(),
  actor_email text not null,
  action_type text not null,
  entity_type text,
  entity_id text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
alter table ops.admin_action_log enable row level security;

create or replace function public.socialmarket_is_admin() returns boolean
language sql stable security definer set search_path=''
as $$ select lower(coalesce(auth.jwt()->>'email',''))='vmoulakakis@gmail.com' and lower(coalesce(auth.jwt()->'app_metadata'->>'provider',''))='google' $$;
revoke all on function public.socialmarket_is_admin() from public;
grant execute on function public.socialmarket_is_admin() to authenticated;

create or replace function public.admin_log_action(p_action_type text,p_entity_type text default null,p_entity_id text default null,p_metadata jsonb default '{}'::jsonb)
returns uuid language plpgsql security definer set search_path=''
as $$ declare v_id uuid; begin if not public.socialmarket_is_admin() then raise exception 'admin_only'; end if; insert into ops.admin_action_log(actor_email,action_type,entity_type,entity_id,metadata) values(lower(auth.jwt()->>'email'),p_action_type,p_entity_type,p_entity_id,coalesce(p_metadata,'{}'::jsonb)) returning id into v_id; return v_id; end $$;
revoke all on function public.admin_log_action(text,text,text,jsonb) from public;
grant execute on function public.admin_log_action(text,text,text,jsonb) to authenticated;

create or replace function public.admin_ai_log(p_task_type text,p_provider text,p_model_name text,p_status text,p_input_tokens bigint default 0,p_output_tokens bigint default 0,p_metadata jsonb default '{}'::jsonb)
returns uuid language plpgsql security definer set search_path=''
as $$ declare v_id uuid; begin if not public.socialmarket_is_admin() then raise exception 'admin_only'; end if; insert into ops.admin_action_log(actor_email,action_type,entity_type,metadata) values(lower(auth.jwt()->>'email'),'ai_'||p_task_type,'ai',jsonb_build_object('provider',p_provider,'model',p_model_name,'status',p_status,'input_tokens',p_input_tokens,'output_tokens',p_output_tokens)||coalesce(p_metadata,'{}'::jsonb)) returning id into v_id; return v_id; end $$;
revoke all on function public.admin_ai_log(text,text,text,text,bigint,bigint,jsonb) from public;
grant execute on function public.admin_ai_log(text,text,text,text,bigint,bigint,jsonb) to authenticated;

create or replace function public.admin_dashboard_snapshot() returns jsonb
language plpgsql security definer set search_path=''
as $$ declare out_json jsonb; begin
 if not public.socialmarket_is_admin() then raise exception 'admin_only'; end if;
 select jsonb_build_object(
 'generated_at',now(),
 'kpis',jsonb_build_object('merchants',(select count(*) from catalog.merchants),'merchant_programs',(select count(*) from catalog.merchant_programs),'products',(select count(*) from catalog.products),'offers',(select count(*) from catalog.product_offers),'validated_products',(select count(*) from catalog.products where status='validated'),'validated_pains',(select count(*) from evidence.semantic_clusters where validation_status='validated' and cluster_type in ('pain','complaint','unmet_need','alternative_request')),'evidence_observations',(select count(*) from evidence.observations),'social_mentions',(select count(*) from intel.merchant_social_mentions),'audits',(select count(*) from evidence.audit_results),'research_jobs',(select count(*) from ops.research_jobs),'collection_jobs',(select count(*) from ops.collection_jobs)),
 'pain_gaps',coalesce((select jsonb_agg(to_jsonb(x)) from (select id,entity_type,cluster_type,canonical_text,category,subcategory,evidence_count,source_diversity,demand_score,competition_score,pain_severity,commercial_intent,audit_score,confidence,validation_status,updated_at from evidence.semantic_clusters where validation_status='validated' and cluster_type in ('pain','complaint','unmet_need','alternative_request') order by coalesce(commercial_intent,0) desc,coalesce(pain_severity,0) desc limit 200)x),'[]'::jsonb),
 'merchants',coalesce((select jsonb_agg(to_jsonb(x)) from (select merchant_id,canonical_name,taxonomy_name,demand_score,competition_score,pain_gap_score,social_pain_score,social_mentions,trust_score,confidence,solution_whitespace_score,demand_beacon_score from api.merchant_dual_role_scores order by solution_whitespace_score desc nulls last limit 300)x),'[]'::jsonb),
 'products',coalesce((select jsonb_agg(to_jsonb(x)) from (select product_id,canonical_title,brand_name,model_name,category,subcategory,product_status,offer_id,merchant_id,merchant_name,effective_price,full_price,discount_pct,expected_commission_eur,commission_rate_pct,tracking_url,image_url,times_bought,pain_gap_fit_score,merchant_opportunity_score,greek_demand_score,competition_score,seasonal_theme_score,merchant_trust_score,commission_score,product_evidence_confidence,final_opportunity_score,validation_status,audit_summary,evidence_count,observed_at,methodology_version from api.product_opportunities order by final_opportunity_score desc nulls last limit 500)x),'[]'::jsonb),
 'audits',coalesce((select jsonb_agg(to_jsonb(x)) from (select id,entity_type,entity_id,target_type,target_id,audited_at,audit_agent,identity_score,source_quality_score,source_diversity_score,contradiction_score,taxonomy_score,demand_validation_score,competition_validation_score,pain_validation_score,social_validation_score,overall_score,verdict,reasons,contradictions,supporting_evidence_ids,methodology_version from evidence.audit_results order by audited_at desc limit 300)x),'[]'::jsonb),
 'research_jobs',coalesce((select jsonb_agg(to_jsonb(x)) from (select id,entity_type,entity_id,job_type,status,priority,reason,requested_at,attempt_count,last_error,completed_at from ops.research_jobs order by requested_at desc limit 300)x),'[]'::jsonb),
 'collection_jobs',coalesce((select jsonb_agg(to_jsonb(x)) from (select id,entity_type,entity_id,collection_type,status,priority,reason,collector_policy,requested_at,attempt_count,last_error,completed_at from ops.collection_jobs order by requested_at desc limit 300)x),'[]'::jsonb),
 'ai_usage',coalesce((select jsonb_agg(to_jsonb(x)) from (select usage_day,provider,model_name,task_type,calls,input_tokens,output_tokens,estimated_cost_usd,updated_at from ops.ai_usage_daily order by usage_day desc limit 300)x),'[]'::jsonb),
 'ai_requests',coalesce((select jsonb_agg(to_jsonb(x)) from (select id,task_id,task_type,provider,model_name,complexity_score,escalation_reason,status,input_tokens,output_tokens,estimated_cost_usd,created_at,completed_at from ops.ai_remote_request_log order by created_at desc limit 300)x),'[]'::jsonb),
 'social',coalesce((select jsonb_agg(to_jsonb(x)) from (select id,merchant_id,platform,source_url,source_type,published_at,text_excerpt,likes_count,replies_count,views_count,sentiment_score,pain_probability,complaint_probability,intent_cluster,source_confidence,observed_at from intel.merchant_social_mentions order by observed_at desc limit 500)x),'[]'::jsonb),
 'category_market',coalesce((select jsonb_agg(to_jsonb(x)) from (select cms.id,cms.taxonomy_id,tn.name taxonomy_name,cms.geography,cms.observed_at,cms.demand_score,cms.competition_score,cms.pain_gap_score,cms.satisfaction_score,cms.opportunity_score,cms.confidence,cms.methodology_version from intel.category_market_snapshots cms left join catalog.taxonomy_nodes tn on tn.id=cms.taxonomy_id order by cms.observed_at desc limit 500)x),'[]'::jsonb),
 'admin_actions',coalesce((select jsonb_agg(to_jsonb(x)) from (select id,actor_email,action_type,entity_type,entity_id,metadata,created_at from ops.admin_action_log order by created_at desc limit 200)x),'[]'::jsonb)
 ) into out_json; return out_json; end $$;
revoke all on function public.admin_dashboard_snapshot() from public;
grant execute on function public.admin_dashboard_snapshot() to authenticated;
