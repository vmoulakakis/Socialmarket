import {createClient} from '@supabase/supabase-js';
import {APPROVED_SUPABASE_URL} from '@/lib/supabase-config';

function client(){
  const configuredUrl=process.env.SUPABASE_URL;
  if(configuredUrl&&configuredUrl!==APPROVED_SUPABASE_URL){
    console.warn('Ignoring stale SUPABASE_URL; orchestrator persistence is pinned to VMDB.');
  }
  const key=process.env.SUPABASE_SERVICE_ROLE_KEY;
  if(!key) return null;
  return createClient(APPROVED_SUPABASE_URL,key,{auth:{persistSession:false,autoRefreshToken:false}});
}

export async function persistenceHealth(){
  const db=client();
  if(!db) return {configured:false,ok:false,reason:'service-role-not-configured'};
  const {error}=await db.from('orchestrator_runs').select('id',{head:true,count:'exact'}).limit(1);
  return error?{configured:true,ok:false,reason:error.message}:{configured:true,ok:true};
}

export async function saveRun(run){
  const db=client();
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

export async function loadRun(id){
  const db=client();
  if(!db) return null;
  const {data,error}=await db.from('orchestrator_runs').select('*').eq('id',id).maybeSingle();
  if(error) throw error;
  return data;
}

export async function saveStep(runId,step){
  const db=client();
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
