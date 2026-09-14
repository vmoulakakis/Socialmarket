import {createClient} from '@supabase/supabase-js';
import {APPROVED_PUBLISHABLE_KEY,APPROVED_SUPABASE_URL} from '@/lib/supabase-config';

function client(accessToken=null){
  const configuredUrl=process.env.SUPABASE_URL;
  if(configuredUrl&&configuredUrl!==APPROVED_SUPABASE_URL){
    console.warn('Ignoring stale SUPABASE_URL; orchestrator persistence is pinned to VMDB.');
  }
  const serviceKey=process.env.SUPABASE_SERVICE_ROLE_KEY;
  if(serviceKey){
    return createClient(APPROVED_SUPABASE_URL,serviceKey,{auth:{persistSession:false,autoRefreshToken:false}});
  }
  if(!accessToken) return null;
  return createClient(APPROVED_SUPABASE_URL,APPROVED_PUBLISHABLE_KEY,{
    auth:{persistSession:false,autoRefreshToken:false},
    global:{headers:{Authorization:`Bearer ${accessToken}`}}
  });
}

export async function persistenceHealth(accessToken=null){
  const db=client(accessToken);
  if(!db) return {configured:false,ok:false,reason:'no-service-role-or-admin-token'};
  const {error}=await db.from('orchestrator_runs').select('id',{head:true,count:'exact'}).limit(1);
  return error?{configured:true,ok:false,reason:error.message}:{configured:true,ok:true,mode:process.env.SUPABASE_SERVICE_ROLE_KEY?'service-role':'admin-jwt'};
}

export async function saveRun(run,accessToken=null){
  const db=client(accessToken);
  if(!db) return {persisted:false,reason:'supabase-not-configured'};
  const payload={
    id:run.id,
    prompt:run.prompt,
    state:run.state,
    intent:run.intent||null,
    plan:run.plan||null,
    result:run.result||null,
    error:run.error||null,
    history:run.history||[],
    approval_required:Boolean(run.approvalRequired),
    updated_at:new Date().toISOString()
  };
  const {error}=await db.from('orchestrator_runs').upsert(payload,{onConflict:'id'});
  if(error) throw error;
  return {persisted:true};
}

export async function loadRun(id,accessToken=null){
  const db=client(accessToken);
  if(!db) return null;
  const {data,error}=await db.from('orchestrator_runs').select('*').eq('id',id).maybeSingle();
  if(error) throw error;
  return data;
}

export async function saveStep(runId,step,accessToken=null){
  const db=client(accessToken);
  if(!db) return {persisted:false,reason:'supabase-not-configured'};
  const {error}=await db.from('orchestrator_steps').upsert({
    run_id:runId,
    step_id:step.id,
    capability:step.capability,
    state:step.state,
    input:step.input||null,
    output:step.output||null,
    error:step.error||null,
    requires_approval:Boolean(step.requiresApproval),
    updated_at:new Date().toISOString()
  },{onConflict:'run_id,step_id'});
  if(error) throw error;
  return {persisted:true};
}

export async function loadSteps(runId,accessToken=null){
  const db=client(accessToken);
  if(!db) return [];
  const {data,error}=await db.from('orchestrator_steps').select('*').eq('run_id',runId);
  if(error) throw error;
  return data||[];
}

export async function enqueueToolTask(runId,step,payload={},accessToken=null){
  const db=client(accessToken);
  if(!db) throw new Error('persistence_required_for_tool_task');
  const row={
    run_id:runId,
    step_id:step.id,
    capability:step.capability,
    target_site_id:payload.targetSiteId||null,
    target_repo:payload.targetRepo||null,
    payload,
    priority:Number.isFinite(payload.priority)?Math.max(0,Math.min(100,payload.priority)):50,
    max_attempts:2
  };
  const {data,error}=await db.from('agent_tool_tasks').upsert(row,{onConflict:'run_id,step_id'}).select('*').single();
  if(error) throw error;
  return data;
}

export async function loadToolTask(runId,stepId,accessToken=null){
  const db=client(accessToken);
  if(!db) return null;
  const {data,error}=await db.from('agent_tool_tasks').select('*').eq('run_id',runId).eq('step_id',stepId).maybeSingle();
  if(error) throw error;
  return data;
}

export async function reserveBudget(metric,quantity,{runId=null,actor='orchestrator',provider=null,model=null,metadata={}}={},accessToken=null){
  const db=client(accessToken);
  if(!db) throw new Error('budget_store_not_configured');
  const {data,error}=await db.rpc('reserve_agent_budget',{p_metric:metric,p_quantity:quantity,p_run_id:runId,p_actor:actor,p_provider:provider,p_model:model,p_metadata:metadata});
  if(error) throw error;
  if(!data?.allowed) throw new Error(`budget_exhausted:${metric}:${data?.reason||'limit'}`);
  return data;
}

export async function finalizeBudget(reservationId,actualQuantity,metadata={},accessToken=null){
  const db=client(accessToken); if(!db||!reservationId) return false;
  const {data,error}=await db.rpc('finalize_agent_budget',{p_reservation_id:reservationId,p_actual_quantity:Math.max(0,Number(actualQuantity)||0),p_metadata:metadata});
  if(error) throw error; return Boolean(data);
}

export async function releaseBudget(reservationId,accessToken=null){
  const db=client(accessToken); if(!db||!reservationId) return false;
  const {data,error}=await db.rpc('release_agent_budget',{p_reservation_id:reservationId});
  if(error) throw error; return Boolean(data);
}
