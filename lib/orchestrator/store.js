import {createClient} from '@supabase/supabase-js';

function client(){
  const url=process.env.SUPABASE_URL||process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key=process.env.SUPABASE_SERVICE_ROLE_KEY;
  if(!url||!key) return null;
  return createClient(url,key,{auth:{persistSession:false,autoRefreshToken:false}});
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
