import crypto from 'node:crypto';
import registry from '@/data/site-registry.json';
import {agentCompletion} from '@/lib/model-router';
import {CAPABILITY_MAP,capabilityPolicy} from './capabilities';
import {RUN_STATES,transition} from './state-machine';
import {enqueueToolTask,finalizeBudget,loadRun,loadToolTask,reserveBudget,saveRun,saveStep} from './store';

function now(){return new Date().toISOString()}
function id(prefix='run'){return `${prefix}_${crypto.randomUUID()}`}
function trafficEligible(site){return site?.trafficEligible!==false}
const TOOL_CAPABILITIES=new Set(['code.change','deploy.preview','deploy.production','site.repair','experiment.run']);

function deterministicIntent(prompt=''){
  const p=prompt.toLowerCase();
  if(/status|health|site|sites|σ[άα]ιτ|διορθ|fix|repair|broken|error/.test(p)) return 'site-operations';
  if(/product|προϊόν|affiliate|commission|demand|ζήτηση/.test(p)) return 'commerce-opportunity';
  if(/landing|page|funnel|seo|content|copy|site/.test(p)) return 'growth-build';
  return 'general-orchestration';
}

function fallbackPlan(prompt,intent){
  if(intent==='site-operations') return [
    {id:'health',capability:'site.health',input:{scope:'all-managed-and-discovered'}},
    {id:'audit',capability:'site.audit',dependsOn:['health'],input:{scope:'failures-and-warnings'}},
    {id:'repair',capability:'site.repair',dependsOn:['audit'],input:{scope:'repairable-failures'}},
    {id:'verify',capability:'site.health',dependsOn:['repair'],input:{scope:'changed-sites'}}
  ];
  if(intent==='commerce-opportunity') return [
    {id:'research',capability:'market.research',input:{prompt}},
    {id:'rank',capability:'product.rank',dependsOn:['research'],input:{prompt}},
    {id:'design',capability:'affinity.design',dependsOn:['rank'],input:{prompt}},
    {id:'content',capability:'content.generate',dependsOn:['design'],input:{prompt}},
    {id:'code',capability:'code.change',dependsOn:['content'],input:{prompt,targetSiteId:'eu-local-day'}},
    {id:'preview',capability:'deploy.preview',dependsOn:['code'],input:{prompt,targetSiteId:'eu-local-day'}},
    {id:'verify',capability:'site.health',dependsOn:['preview'],input:{scope:'preview'}},
    {id:'production',capability:'deploy.production',dependsOn:['verify'],input:{prompt,targetSiteId:'eu-local-day'}}
  ];
  if(intent==='growth-build') return [
    {id:'audit',capability:'site.audit',input:{prompt}},
    {id:'design',capability:'affinity.design',dependsOn:['audit'],input:{prompt}},
    {id:'content',capability:'content.generate',dependsOn:['design'],input:{prompt}},
    {id:'code',capability:'code.change',dependsOn:['content'],input:{prompt,targetSiteId:'eu-local-day'}},
    {id:'preview',capability:'deploy.preview',dependsOn:['code'],input:{prompt,targetSiteId:'eu-local-day'}},
    {id:'verify',capability:'site.health',dependsOn:['preview'],input:{scope:'preview'}},
    {id:'production',capability:'deploy.production',dependsOn:['verify'],input:{prompt,targetSiteId:'eu-local-day'}}
  ];
  return [
    {id:'research',capability:'market.research',input:{prompt}},
    {id:'audit',capability:'site.audit',dependsOn:['research'],input:{prompt}}
  ];
}

function normalizePlan(plan){
  const steps=Array.isArray(plan)?plan:[];
  return steps.slice(0,20).map((s,i)=>{
    const capability=CAPABILITY_MAP[s.capability]?s.capability:'market.research';
    const policy=capabilityPolicy(capability);
    return {id:String(s.id||`step-${i+1}`),capability,dependsOn:Array.isArray(s.dependsOn)?s.dependsOn.map(String):[],input:s.input||{},state:'PENDING',requiresApproval:policy.requiresApproval,risk:policy.risk};
  });
}

async function aiPlan(prompt,intent,ctx){
  try{
    const sites=registry.sites.map(s=>({id:s.id,role:s.role,managed:s.managed,repo:s.repo||null,trafficEligible:trafficEligible(s),knownIssues:s.knownIssues||[]}));
    const r=await agentCompletion({json:true,temperature:0.1,runId:ctx.runId,accessToken:ctx.accessToken,actor:'planner',capability:'plan',messages:[
      {role:'system',content:`You are the SocialMarket Autonomous Commerce OS planner. Build a minimal DAG from only these capabilities: ${Object.keys(CAPABILITY_MAP).join(', ')}. Never invent evidence. Prefer reversible actions. High-risk capabilities remain approval-gated. Any build that needs deployment must use code.change before deploy.preview. Production must depend on a verified preview. Never route commerce/growth work to trafficEligible=false. Return JSON {steps:[{id,capability,dependsOn,input}],reasoning_summary:string}.`},
      {role:'user',content:JSON.stringify({prompt,intent,sites})}
    ]});
    const parsed=JSON.parse(r.content||'{}');
    if(Array.isArray(parsed.steps)&&parsed.steps.length) return {steps:normalizePlan(parsed.steps),planner:{provider:r.provider,model:r.model,summary:parsed.reasoning_summary||null}};
  }catch(e){console.error('orchestrator ai planning failed; using deterministic fallback',e)}
  return {steps:normalizePlan(fallbackPlan(prompt,intent)),planner:{provider:'deterministic',model:null,summary:'fallback-plan'}};
}

async function checkUrl(url){
  const started=Date.now();
  try{
    const res=await fetch(url,{method:'GET',redirect:'follow',cache:'no-store',signal:AbortSignal.timeout(12000)});
    const robots=(res.headers.get('x-robots-tag')||'').toLowerCase();
    return {url,ok:res.ok,status:res.status,latencyMs:Date.now()-started,indexable:!robots.includes('noindex'),xRobotsTag:robots||null};
  }catch(e){return {url,ok:false,status:null,latencyMs:Date.now()-started,error:String(e)}}
}

function targetFor(step){
  const requested=step.input?.targetSiteId;
  if(requested){
    const site=registry.sites.find(s=>s.id===requested);
    if(site?.repo) return site;
  }
  if(step.capability==='site.repair') return registry.sites.find(s=>s.managed&&s.repo)||null;
  return registry.sites.find(s=>s.managed&&s.repo&&trafficEligible(s)&&s.role!=='control-plane')||null;
}

function findPreviewUrl(outputs){
  for(const value of Object.values(outputs||{})){
    const candidates=[value?.previewUrl,value?.url,value?.task?.output?.previewUrl,value?.task?.output?.url];
    const hit=candidates.find(x=>typeof x==='string'&&x.startsWith('http'));
    if(hit) return hit;
  }
  return null;
}

async function executeCapability(step,ctx){
  if(step.requiresApproval&&!ctx.approvedCapabilities?.includes(step.capability)) return {state:'WAITING_APPROVAL',output:{reason:'approval-required',capability:step.capability}};
  if(step.capability==='site.health'){
    const preview=step.input?.scope==='preview'?findPreviewUrl(ctx.outputs):null;
    const targets=preview?[{id:'preview',url:preview,trafficEligible:true,knownIssues:[]}]:registry.sites.filter(s=>s.productionUrl).map(s=>({id:s.id,url:s.productionUrl,trafficEligible:trafficEligible(s),knownIssues:s.knownIssues||[]}));
    const checks=await Promise.all(targets.map(async t=>({...t,...await checkUrl(t.url)})));
    return {state:'COMPLETE',output:{checks,summary:{total:checks.length,healthy:checks.filter(x=>x.ok).length,unhealthy:checks.filter(x=>!x.ok).length,nonIndexable:checks.filter(x=>x.ok&&!x.indexable).map(x=>x.id),trafficBlocked:checks.filter(x=>!x.trafficEligible).map(x=>x.id)}}};
  }
  if(step.capability==='site.audit') return {state:'COMPLETE',output:{registry:registry.sites.map(s=>({id:s.id,managed:s.managed,repo:s.repo,trafficEligible:trafficEligible(s),knownIssues:s.knownIssues||[]})),recommendation:'Prioritize broken deployments, runtime timeouts, noindex public funnels, missing affiliate tracking, then orphan Git linkage. Traffic-ineligible sites remain fail-closed until verified.'}};
  if(['market.research','product.rank','affinity.design','content.generate'].includes(step.capability)){
    const eligibleSites=registry.sites.filter(trafficEligible).map(s=>({id:s.id,role:s.role,repo:s.repo||null,productionUrl:s.productionUrl||null}));
    const r=await agentCompletion({json:true,temperature:0.2,runId:ctx.runId,accessToken:ctx.accessToken,actor:step.capability,capability:step.capability,messages:[
      {role:'system',content:`Execute capability ${step.capability} for SocialMarket. Use only supplied context. Separate evidence, inference and unknowns. Do not invent prices, demand, commission, tracking, merchant identity or deployment state. Only trafficEligible sites may be commerce/growth destinations. Return compact JSON.`},
      {role:'user',content:JSON.stringify({prompt:ctx.prompt,input:step.input,prior:ctx.outputs,eligibleSites})}
    ]});
    let parsed;try{parsed=JSON.parse(r.content||'{}')}catch{parsed={raw:r.content}}
    return {state:'COMPLETE',output:{provider:r.provider,model:r.model,data:parsed,usage:r.usage||null}};
  }
  if(TOOL_CAPABILITIES.has(step.capability)){
    const site=targetFor(step);
    if(!site?.repo) throw new Error(`no_git_target_for:${step.capability}`);
    if(step.capability!=='site.repair'&&!trafficEligible(site)) throw new Error(`traffic_ineligible_target:${site.id}`);
    const payload={
      prompt:ctx.prompt,
      input:step.input||{},
      prior:ctx.outputs||{},
      targetSiteId:site.id,
      targetRepo:site.repo,
      approved:Boolean(!step.requiresApproval||ctx.approvedCapabilities?.includes(step.capability)),
      requestedAt:now()
    };
    const task=await enqueueToolTask(ctx.runId,step,payload,ctx.accessToken);
    return {state:'WAITING_TOOL',output:{mode:'github-agent-tool',taskId:task.id,state:task.state,targetRepo:site.repo,targetSiteId:site.id}};
  }
  return {state:'COMPLETE',output:{mode:'no-op',capability:step.capability}};
}

function depsComplete(step,steps){return (step.dependsOn||[]).every(d=>steps.find(x=>x.id===d)?.state==='COMPLETE')}
function outputsFrom(steps){return Object.fromEntries(steps.filter(s=>s.output).map(s=>[s.id,s.output]))}

async function continueExecution(run,steps,ctx){
  if(run.state!==RUN_STATES.EXECUTING) run=transition(run,RUN_STATES.EXECUTING);
  let progress=true;
  while(progress&&steps.some(s=>s.state==='PENDING')){
    progress=false;
    for(const step of steps){
      if(step.state!=='PENDING'||!depsComplete(step,steps)) continue;
      progress=true;step.state='RUNNING';await saveStep(run.id,step,ctx.accessToken);
      try{const result=await executeCapability(step,ctx);step.state=result.state;step.output=result.output;ctx.outputs[step.id]=result.output}catch(e){step.state='FAILED';step.error=String(e)}
      await saveStep(run.id,step,ctx.accessToken);
      if(step.state==='FAILED'){
        run={...run,plan:steps,error:{step:step.id,message:step.error}};run=transition(run,RUN_STATES.FAILED,{step:step.id});await saveRun(run,ctx.accessToken);return run;
      }
      if(step.state==='WAITING_APPROVAL'){
        run={...run,plan:steps,approvalRequired:true};run=transition(run,RUN_STATES.WAITING_APPROVAL,{capability:step.capability,step:step.id});await saveRun(run,ctx.accessToken);return run;
      }
      if(step.state==='WAITING_TOOL'){
        run={...run,plan:steps};run=transition(run,RUN_STATES.WAITING_TOOL,{capability:step.capability,step:step.id,taskId:step.output?.taskId});await saveRun(run,ctx.accessToken);return run;
      }
    }
  }
  if(steps.some(s=>s.state==='PENDING')){
    run={...run,plan:steps,error:{message:'Unresolvable DAG dependencies'}};run=transition(run,RUN_STATES.FAILED);await saveRun(run,ctx.accessToken);return run;
  }
  run={...run,plan:steps,result:{outputs:ctx.outputs},approvalRequired:false};run=transition(run,RUN_STATES.VERIFYING);run=transition(run,RUN_STATES.COMPLETE,{completedSteps:steps.length});await saveRun(run,ctx.accessToken);return run;
}

export async function orchestrate({prompt,approvedCapabilities=[],accessToken=null}){
  if(!prompt||typeof prompt!=='string') throw new Error('prompt is required');
  let run={id:id(),prompt,state:RUN_STATES.REQUESTED,createdAt:now(),updatedAt:now(),history:[],outputs:{}};
  const runBudget=await reserveBudget('orchestrator_runs',1,{runId:run.id,actor:'orchestrator'},accessToken);
  await finalizeBudget(runBudget.reservation_id,1,{accepted:true},accessToken);
  await saveRun(run,accessToken);
  const intent=deterministicIntent(prompt);run={...run,intent};run=transition(run,RUN_STATES.UNDERSTOOD,{intent});
  const planned=await aiPlan(prompt,intent,{runId:run.id,accessToken});run={...run,plan:planned.steps,planner:planned.planner};run=transition(run,RUN_STATES.PLANNED,{steps:planned.steps.length});
  const steps=planned.steps.map(x=>({...x}));
  return continueExecution(run,steps,{runId:run.id,prompt,approvedCapabilities,accessToken,outputs:{}});
}

export async function resumeOrchestration({runId,approvedCapabilities=[],accessToken=null}){
  const row=await loadRun(runId,accessToken);if(!row) throw new Error('run_not_found');
  if(row.state==='COMPLETE'||row.state==='FAILED') return row;
  let run={...row,approvalRequired:Boolean(row.approval_required)};
  const steps=(row.plan||[]).map(s=>({...s}));
  for(const step of steps){
    if(step.state==='WAITING_APPROVAL'){
      if(!approvedCapabilities.includes(step.capability)) return run;
      step.state='PENDING';step.output=null;
    }
    if(step.state==='WAITING_TOOL'){
      const task=await loadToolTask(runId,step.id,accessToken);
      if(!task||['queued','running'].includes(task.state)) return {...run,toolTask:task||null};
      if(task.state==='failed'||task.state==='cancelled'){
        step.state='FAILED';step.error=task.error||`tool_task_${task.state}`;
        run={...run,plan:steps,error:{step:step.id,message:step.error}};run=transition(run,RUN_STATES.FAILED,{step:step.id});await saveStep(runId,step,accessToken);await saveRun(run,accessToken);return run;
      }
      step.state='COMPLETE';step.output={...(step.output||{}),task:{id:task.id,state:task.state,output:task.output}};await saveStep(runId,step,accessToken);
    }
  }
  const ctx={runId,prompt:row.prompt,approvedCapabilities,accessToken,outputs:outputsFrom(steps)};
  return continueExecution(run,steps,ctx);
}

export function getSiteRegistry(){return registry}
