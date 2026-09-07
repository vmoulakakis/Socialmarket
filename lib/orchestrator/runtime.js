import crypto from 'node:crypto';
import registry from '@/data/site-registry.json';
import {agentCompletion} from '@/lib/model-router';
import {CAPABILITY_MAP,capabilityPolicy} from './capabilities';
import {RUN_STATES,transition} from './state-machine';
import {saveRun,saveStep} from './store';

function now(){return new Date().toISOString()}
function id(prefix='run'){return `${prefix}_${crypto.randomUUID()}`}

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
    {id:'preview',capability:'deploy.preview',dependsOn:['content'],input:{prompt}},
    {id:'verify',capability:'site.health',dependsOn:['preview'],input:{scope:'preview'}},
    {id:'production',capability:'deploy.production',dependsOn:['verify'],input:{prompt}}
  ];
  return [
    {id:'research',capability:'market.research',input:{prompt}},
    {id:'audit',capability:'site.audit',dependsOn:['research'],input:{prompt}}
  ];
}

function normalizePlan(plan){
  const steps=Array.isArray(plan)?plan:[];
  return steps.map((s,i)=>{
    const capability=CAPABILITY_MAP[s.capability]?s.capability:'market.research';
    const policy=capabilityPolicy(capability);
    return {
      id:String(s.id||`step-${i+1}`),
      capability,
      dependsOn:Array.isArray(s.dependsOn)?s.dependsOn.map(String):[],
      input:s.input||{},
      state:'PENDING',
      requiresApproval:policy.requiresApproval,
      risk:policy.risk
    };
  });
}

async function aiPlan(prompt,intent){
  try{
    const r=await agentCompletion({json:true,temperature:0.1,messages:[
      {role:'system',content:`You are the SocialMarket Autonomous Commerce OS planner. Build a minimal DAG from only these capabilities: ${Object.keys(CAPABILITY_MAP).join(', ')}. Never invent evidence. Prefer reversible actions. High-risk capabilities must remain approval-gated. Return JSON {steps:[{id,capability,dependsOn,input}],reasoning_summary:string}.`},
      {role:'user',content:JSON.stringify({prompt,intent,sites:registry.sites.map(s=>({id:s.id,role:s.role,managed:s.managed,knownIssues:s.knownIssues||[]}))})}
    ]});
    const parsed=JSON.parse(r.content||'{}');
    if(Array.isArray(parsed.steps)&&parsed.steps.length) return {steps:normalizePlan(parsed.steps),planner:{provider:r.provider,model:r.model,summary:parsed.reasoning_summary||null}};
  }catch(e){
    console.error('orchestrator ai planning failed; using deterministic fallback',e);
  }
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

async function executeCapability(step,ctx){
  if(step.requiresApproval&&!ctx.approvedCapabilities?.includes(step.capability)){
    return {state:'WAITING_APPROVAL',output:{reason:'approval-required',capability:step.capability}};
  }
  if(step.capability==='site.health'){
    const targets=registry.sites.filter(s=>s.productionUrl).map(s=>({id:s.id,url:s.productionUrl,knownIssues:s.knownIssues||[]}));
    const checks=await Promise.all(targets.map(async t=>({...t,...await checkUrl(t.url)})));
    return {state:'COMPLETE',output:{checks,summary:{total:checks.length,healthy:checks.filter(x=>x.ok).length,unhealthy:checks.filter(x=>!x.ok).length,nonIndexable:checks.filter(x=>x.ok&&!x.indexable).map(x=>x.id)}}};
  }
  if(step.capability==='site.audit'){
    return {state:'COMPLETE',output:{registry:registry.sites.map(s=>({id:s.id,managed:s.managed,repo:s.repo,knownIssues:s.knownIssues||[]})),recommendation:'Prioritize broken deployments, runtime timeouts, noindex public funnels, missing affiliate tracking, then orphan Git linkage.'}};
  }
  if(['market.research','product.rank','affinity.design','content.generate'].includes(step.capability)){
    const r=await agentCompletion({json:true,temperature:0.2,messages:[
      {role:'system',content:`Execute capability ${step.capability} for SocialMarket. Use only supplied context. Separate evidence, inference and unknowns. Do not invent prices, demand, commission, tracking, merchant identity or deployment state. Return JSON.`},
      {role:'user',content:JSON.stringify({prompt:ctx.prompt,input:step.input,prior:ctx.outputs})}
    ]});
    let parsed;try{parsed=JSON.parse(r.content||'{}')}catch{parsed={raw:r.content}}
    return {state:'COMPLETE',output:{provider:r.provider,model:r.model,data:parsed}};
  }
  if(['code.change','deploy.preview','deploy.production','site.repair','experiment.run'].includes(step.capability)){
    return {state:'COMPLETE',output:{mode:'delegated-tool-action',capability:step.capability,ready:true,requirements:['Git-backed target or explicit adapter credentials','verification before production','rollback path'],note:'Runtime records and routes the action; execution is performed by the connected deployment/code adapter.'}};
  }
  return {state:'COMPLETE',output:{mode:'no-op',capability:step.capability}};
}

function depsComplete(step,steps){
  return (step.dependsOn||[]).every(d=>steps.find(x=>x.id===d)?.state==='COMPLETE');
}

export async function orchestrate({prompt,approvedCapabilities=[]}){
  if(!prompt||typeof prompt!=='string') throw new Error('prompt is required');
  let run={id:id(),prompt,state:RUN_STATES.REQUESTED,createdAt:now(),updatedAt:now(),history:[],outputs:{}};
  await saveRun(run).catch(()=>{});
  const intent=deterministicIntent(prompt);
  run={...run,intent};run=transition(run,RUN_STATES.UNDERSTOOD,{intent});
  const planned=await aiPlan(prompt,intent);
  run={...run,plan:planned.steps,planner:planned.planner};run=transition(run,RUN_STATES.PLANNED,{steps:planned.steps.length});
  const needsApproval=planned.steps.some(s=>s.requiresApproval&&!approvedCapabilities.includes(s.capability));
  if(needsApproval){run={...run,approvalRequired:true};run=transition(run,RUN_STATES.WAITING_APPROVAL,{capabilities:planned.steps.filter(s=>s.requiresApproval).map(s=>s.capability)});await saveRun(run).catch(()=>{});return run;}
  run=transition(run,RUN_STATES.EXECUTING);
  const steps=planned.steps.map(x=>({...x}));
  const ctx={prompt,approvedCapabilities,outputs:{}};
  let progress=true;
  while(progress&&steps.some(s=>s.state==='PENDING')){
    progress=false;
    for(const step of steps){
      if(step.state!=='PENDING'||!depsComplete(step,steps)) continue;
      progress=true;step.state='RUNNING';await saveStep(run.id,step).catch(()=>{});
      try{
        const result=await executeCapability(step,ctx);
        step.state=result.state;step.output=result.output;ctx.outputs[step.id]=result.output;
      }catch(e){step.state='FAILED';step.error=String(e);}
      await saveStep(run.id,step).catch(()=>{});
      if(step.state==='FAILED'){
        run={...run,plan:steps,error:{step:step.id,message:step.error}};run=transition(run,RUN_STATES.FAILED,{step:step.id});await saveRun(run).catch(()=>{});return run;
      }
    }
  }
  if(steps.some(s=>s.state==='PENDING')){
    run={...run,plan:steps,error:{message:'Unresolvable DAG dependencies'}};run=transition(run,RUN_STATES.FAILED);await saveRun(run).catch(()=>{});return run;
  }
  run={...run,plan:steps,result:{outputs:ctx.outputs}};run=transition(run,RUN_STATES.VERIFYING);
  run=transition(run,RUN_STATES.COMPLETE,{completedSteps:steps.length});
  await saveRun(run).catch(()=>{});
  return run;
}

export function getSiteRegistry(){return registry}
