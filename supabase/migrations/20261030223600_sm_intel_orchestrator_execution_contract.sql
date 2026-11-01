-- SocialMarket AI architect v1: specialist delegation, candidate-only outcomes and evidence-aware learning.
create or replace function sm_intel.enqueue_specialists()
returns jsonb language plpgsql security invoker set search_path='' as $$
declare commissions int; graph_n int; skeptics int; architect_n int;
begin
 with x as (
  insert into sm_intel.agent_tasks(objective_key,agent_role,subject_kind,subject_key,priority,input_refs)
  select 'trustworthy_merchant_coverage','commission_verifier','program',p.id::text,75,
   jsonb_build_object('program_name',p.program_name,
    'terms_valid_to',p.terms_valid_to,'current_publisher_approved',p.approved_for_publisher)
  from sm_intel.merchant_program_directory p
  on conflict(objective_key,agent_role,subject_kind,subject_key,output_version) do nothing returning id)
 select count(*) into commissions from x;
 with x as (
 insert into sm_intel.agent_tasks(objective_key,agent_role,subject_kind,subject_key,priority,input_refs)
 select 'hybrid_graphrag_quality','graphrag_librarian','pain_gap',p.id::text,65,
   jsonb_build_object('source','public.market_problem_clusters','goal','evidence_graph_and_embedding_quality')
 from public.market_problem_clusters p where p.market_code='GR'
 on conflict(objective_key,agent_role,subject_kind,subject_key,output_version) do nothing returning id)
 select count(*) into graph_n from x;
 with x as (
 insert into sm_intel.agent_tasks(objective_key,agent_role,subject_kind,subject_key,priority,input_refs)
 select 'greek_high_demand_low_supply','commercial_skeptic','pain_gap',p.id::text,85,
  jsonb_build_object('source','public.market_problem_clusters','review','verify_demand_vs_supply_and_counterevidence')
 from public.market_problem_clusters p where p.market_code='GR'
 on conflict(objective_key,agent_role,subject_kind,subject_key,output_version) do nothing returning id)
 select count(*) into skeptics from x;
 with x as (
 insert into sm_intel.agent_tasks(objective_key,agent_role,subject_kind,subject_key,priority,input_refs)
 values('learn_from_outcomes','ai_architect','portfolio','socialmarket_greece_v1',60,
   '{"scope":"SocialMarket AI only","mode":"review and prioritize, no autonomous commercial approvals"}'::jsonb)
 on conflict(objective_key,agent_role,subject_kind,subject_key,output_version) do nothing returning id)
 select count(*) into architect_n from x;
 return jsonb_build_object('commission_agents',commissions,'graph_agents',graph_n,
   'skeptic_agents',skeptics,'architect_agents',architect_n);
end $$;

create or replace function sm_intel.complete_agent_task(
 p_task_id uuid,p_worker text,p_run_id uuid,p_findings jsonb,
 p_evidence_refs jsonb,p_uncertainty jsonb,p_has_source_evidence boolean
) returns boolean language plpgsql security invoker set search_path='' as $$
declare affected int;
begin
 if p_findings is null or jsonb_typeof(p_findings)<>'object'
   or p_evidence_refs is null or jsonb_typeof(p_evidence_refs)<>'array'
   or p_uncertainty is null or jsonb_typeof(p_uncertainty)<>'object'
   or pg_catalog.length(p_findings::text)>16000 then
  raise exception 'invalid_agent_outcome';
 end if;
 update sm_intel.agent_tasks
 set state=case when p_has_source_evidence and jsonb_array_length(p_evidence_refs)>0
                  then 'candidate' else 'needs_evidence' end,
     findings=p_findings,evidence_refs=p_evidence_refs,uncertainty=p_uncertainty,
     claimed_at=null,claimed_by=null,last_run_id=p_run_id,last_evaluated_at=now(),updated_at=now(),
     next_attempt_at=case when p_has_source_evidence and jsonb_array_length(p_evidence_refs)>0
                          then now()+interval '30 days'
                          else now()+interval '7 days' end
 where id=p_task_id and state='claimed' and claimed_by=p_worker;
 get diagnostics affected=row_count;
 return affected=1;
end $$;

create or replace function sm_intel.record_learning_from_events()
returns jsonb language plpgsql security invoker set search_path='' as $$
declare n int;
begin
 with ins as (
 insert into sm_intel.agent_learning_observations(
  source_family,source_event_id,subject_kind,subject_key,event_at,facts,
  confidence,review_state)
 select 'affiliate_conversion',e.id::text,
        case when e.product_candidate_id is not null then 'product' else 'merchant' end,
        coalesce(e.product_candidate_id::text,e.merchant_id::text),e.occurred_at,
        jsonb_build_object('event_type',e.event_type,'revenue_eur',e.revenue_eur,
        'commission_eur',e.commission_eur,'platform',e.platform,'source_name',e.source_name),
        0,'candidate'
 from public.commerce_performance_events e
 where (e.product_candidate_id is not null or e.merchant_id is not null)
 and e.source_name is not null
 on conflict(source_family,source_event_id) do nothing returning id)
 select count(*) into n from ins;
 return jsonb_build_object('new_candidate_events',n,'policy','requires_attribution_review');
end $$;

revoke all on function sm_intel.enqueue_specialists() from public,anon,authenticated;
revoke all on function sm_intel.complete_agent_task(uuid,text,uuid,jsonb,jsonb,jsonb,boolean) from public,anon,authenticated;
revoke all on function sm_intel.record_learning_from_events() from public,anon,authenticated;
grant execute on function sm_intel.enqueue_specialists() to service_role;
grant execute on function sm_intel.complete_agent_task(uuid,text,uuid,jsonb,jsonb,jsonb,boolean) to service_role;
grant execute on function sm_intel.record_learning_from_events() to service_role;
