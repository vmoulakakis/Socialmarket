import 'jsr:@supabase/functions-js/edge-runtime.d.ts'
import { createRemoteJWKSet, jwtVerify } from 'npm:jose@6.1.0'
import { createClient } from 'npm:@supabase/supabase-js@2.57.4'

/**
 * Private source-truth boundary for the EUR15-first affiliate discovery worker.
 * This DOES NOT grant network approval, stock or publish rights to any product.
 * No user-controlled URL is fetched; affiliate links are parsed but never followed.
 */
const ISSUER='https://token.actions.githubusercontent.com'
const AUDIENCE='socialmarket-commission15-discovery'
const REPO='vmoulakakis/Socialmarket'
const REPO_ID='1329707883'
const WORKFLOW='.github/workflows/linkwise-commission15-discovery.yml'
const ALLOWED=new Set([
  REPO+'/'+WORKFLOW+'@refs/heads/main',
  REPO+'/'+WORKFLOW+'@refs/heads/feat/agentic-shopper-evidence-gate-20261106'
])
const jwks=createRemoteJWKSet(new URL(ISSUER+'/.well-known/jwks'))
const reply=(body:unknown,status=200)=>new Response(JSON.stringify(body),{status,headers:{
 'content-type':'application/json','cache-control':'no-store','x-content-type-options':'nosniff'
}})
type Obj=Record<string,unknown>
const uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
const digits=/^[1-9][0-9]*$/
const n=(x:unknown)=>x===null||x===undefined||x===''?null:Number(x)
const good=(x:unknown,min=0,max=100)=>{const v=n(x);return v!==null&&Number.isFinite(v)&&v>=min&&v<=max?v:null}
function expectedCommission(price:number,p:Obj){
 const flat=n(p.flat_commission_min_eur)??n(p.flat_commission_eur)
 const pct=n(p.percent_commission_min)??n(p.percent_commission)
 const amounts=[flat&&flat>0?flat:null,pct&&pct>0?price*pct/100:null].filter((x):x is number=>x!==null&&Number.isFinite(x))
 return amounts.length?Math.round(Math.min(...amounts)*10000)/10000:null
}
function routeIdentity(input:unknown){
 try{
  const u=new URL(String(input||''))
  if(u.protocol!=='https:'||u.hostname!=='go.linkwi.se'||u.username||u.password)return null
  const m=/^\/z\/([1-9][0-9]*)-0\/CD104\/?$/.exec(u.pathname)
  if(!m)return null
  const destination=new URL(u.searchParams.get('lnkurl')||'')
  if(!['http:','https:'].includes(destination.protocol)||!destination.hostname)return null
  return {program_id:m[1],domain:destination.hostname.toLowerCase().replace(/^www\./,'')}
 }catch{return null}
}
function asObject(v:unknown):Obj{return v&&typeof v==='object'&&!Array.isArray(v)?v as Obj:{}}
function present(raw:Obj,validProgram:Obj){
 const id=String(raw.source_product_id||'')
 const name=String(raw.product_title||'')
 const link=String(raw.original_tracking_url||'')
 const identity=routeIdentity(link)
 const price=n(raw.price_eur)
 const candidate=n(raw.calculated_commission_eur)
 if(!digits.test(String(raw.program_id||''))||!identity||identity.program_id!==raw.program_id||
    !id||id.length>160||!name||name.length>250||!price||!Number.isFinite(price)||price<=0||
    !candidate||!Number.isFinite(candidate)||candidate<15)throw Error('invalid_source_candidate')
 const amount=expectedCommission(price,validProgram)
 if(amount===null||amount<15||Math.abs(candidate-amount)>.011)throw Error('candidate_calculation_not_source_grounded')
 const titleKey=String(raw.problem_key||'unmatched').slice(0,100)
 if(!titleKey)return null
 const stage='research_candidate'
 const clamp=(value:unknown)=>good(value,0,100)
 const evidence=(Array.isArray(raw.evidence_refs)?raw.evidence_refs:[])
   .filter(x=>typeof x==='string'&&x.length<=100).slice(0,12)
 const mapped=String(raw.merchant_domain||'').toLowerCase().replace(/^www\./,'')
 if(mapped&&identity.domain!==mapped)throw Error('merchant_destination_conflict')
 const valid=raw.valid_to?String(raw.valid_to):null
 if(valid&&!Number.isFinite(Date.parse(valid)))throw Error('invalid_date_source')
 const score=clamp(raw.opportunity_score)
 if(score===null)throw Error('score_invalid')
 return {
  run_key:String(raw.run_key||''),
  source_key:'linkwise',
  source_product_id:id,program_id:identity.program_id,merchant_domain:identity.domain,
  product_title:name,category_text:String(raw.category_text||'').slice(0,350)||null,
  price_eur:price,calculated_commission_eur:amount,
  commission_basis:String(raw.commission_basis||'historical_program_terms').slice(0,90),
  commission_provenance:{source:String(validProgram.source||'historical_network_table').slice(0,80),
    imported_at:validProgram.imported_at||null,source_network_id:identity.program_id,
    publisher_approval_not_verified:true,pricing_method:'conservative_observed_or_min'},
  original_tracking_url:link,image_url:raw.image_url?String(raw.image_url).slice(0,2400):null,
  stock_state:['in_stock','out_of_stock','unknown'].includes(String(raw.stock_state))?raw.stock_state:'unknown',
  valid_to:valid,problem_key:titleKey,
  problem_cluster_id:typeof raw.problem_cluster_id==='string'&&uuid.test(raw.problem_cluster_id)?raw.problem_cluster_id:null,
  pain_fit_score:clamp(raw.pain_fit_score)||0,
  demand_score:clamp(raw.demand_score),
  competition_score:clamp(raw.competition_score),
  conversion_proxy_score:clamp(raw.conversion_proxy_score),
  opportunity_score:score,
  evidence_level:'hypothesis_only',
  evidence_refs:evidence,
  stage,
  feed_observed_at:new Date().toISOString(),
  updated_at:new Date().toISOString(),
 }
}
Deno.serve(async req=>{
 if(req.method==='GET')return reply({service:'socialmarket-commission15-discovery',private:true,write_mode:'research_only'})
 if(req.method!=='POST')return reply({error:'method_not_allowed'},405)
 const incoming=req.headers.get('authorization')||''
 if(!incoming.startsWith('Bearer '))return reply({error:'oidc_required'},401)
 try{
  const {payload}=await jwtVerify(incoming.slice(7),jwks,{issuer:ISSUER,audience:AUDIENCE})
  if(String(payload.repository_id)!==REPO_ID||String(payload.repository)!==REPO||
     !ALLOWED.has(String(payload.workflow_ref||''))||
     !['refs/heads/main','refs/heads/feat/agentic-shopper-evidence-gate-20261106'].includes(String(payload.ref||'')))
   return reply({error:'workflow_scope_denied'},403)
  const raw=await req.text()
  if(raw.length>240000)return reply({error:'payload_too_large'},413)
  const body=asObject(JSON.parse(raw))
  const action=String(body.action||'')
  const url=Deno.env.get('SUPABASE_URL'),serviceRole=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')
  if(!url||!serviceRole)return reply({error:'service_config_missing'},503)
  const sb=createClient(url,serviceRole,{auth:{autoRefreshToken:false,persistSession:false}})
  if(action==='context'){
   const [rates,problems,observations,events]=await Promise.all([
    sb.from('linkwise_program_commissions')
      .select('linkwise_program_id,flat_commission_min_eur,flat_commission_eur,percent_commission_min,percent_commission,source,imported_at')
      .not('linkwise_program_id','is',null).limit(500),
    sb.from('market_problem_clusters')
      .select('id,problem_key,problem_title,problem_description,pain_severity_score,purchase_urgency_score')
      .eq('market_code','GR').limit(200),
    sb.from('market_demand_observations')
      .select('problem_cluster_id,demand_score,competition_score,source_url,source_tier,confidence,expires_at')
      .eq('market_code','GR').gt('expires_at',new Date().toISOString()).limit(500),
    sb.from('commerce_performance_events').select('id',{count:'exact',head:true})
   ])
   if(rates.error||problems.error||observations.error||events.error)return reply({error:'source_context_unavailable'},503)
   const clean=(rates.data||[]).filter(p=>digits.test(String(p.linkwise_program_id||'')))
   const byProblem=new Map<string,Obj[]>()
   for(const row of observations.data||[]){
    if(!row.source_url||!String(row.source_url).startsWith('https://')||
       n(row.confidence)===null||Number(row.confidence)<.75||Number(row.source_tier)>2)continue
    const k=String(row.problem_cluster_id)
    byProblem.set(k,[...(byProblem.get(k)||[]),row])
   }
   const enriched=(problems.data||[]).map(x=>{
    const evidence=byProblem.get(x.id)||[]
    // Both demand and supply/competition require two distinct external sources.
    const domains=new Set(evidence.map(z=>{try{return new URL(String(z.source_url)).hostname}catch{return ''}}))
    const independent=domains.size>=2?evidence:[]
    const avg=(key:string)=>{const v=independent.map(q=>n(q[key])).filter((a):a is number=>a!==null&&Number.isFinite(a));return v.length?v.reduce((a,b)=>a+b,0)/v.length:null}
    return {...x,verified_demand_score:avg('demand_score'),
      verified_competition_score:avg('competition_score')}
   })
   return reply({ok:true,programs:clean,problems:enriched,
      source_observation_count:observations.data?.length||0,
      first_party_conversion_event_count:events.count||0,
      rates_status:'historical_terms_estimates_not_verified_current_commissions',
      result_mode:'research_only'})
  }
  const key=String(body.run_key||'')
  if(!uuid.test(key))return reply({error:'run_key_invalid'},400)
  if(action==='begin'){
   const rows=[{run_key:key,source_key:'linkwise',status:'partial',
      workflow_ref:String(payload.workflow_ref),metrics:{scope:body.scope||'unconfirmed',
      provenance:'source_observed_not_certified'}}]
   const saved=await sb.from('ai_discovery_runs_v2').upsert(rows,{onConflict:'run_key'})
   if(saved.error)return reply({error:'begin_failed'},503)
   return reply({ok:true,run_key:key,status:'partial'})
  }
  if(action==='save'){
   const incomingRows=body.candidates
   if(!Array.isArray(incomingRows)||incomingRows.length<1||incomingRows.length>40)return reply({error:'batch_must_be_1_to_40'},400)
   const ids=[...new Set(incomingRows.map((x:Obj)=>String(asObject(x).program_id||'')))]
   if(ids.length>40||ids.some(x=>!digits.test(x)))return reply({error:'program_invalid'},400)
   const [source,run]=await Promise.all([
    sb.from('linkwise_program_commissions').select(
      'linkwise_program_id,flat_commission_min_eur,flat_commission_eur,percent_commission_min,percent_commission,source,imported_at'
    ).in('linkwise_program_id',ids),
    sb.from('ai_discovery_runs_v2').select('run_key').eq('run_key',key).eq('status','partial').maybeSingle()
   ])
   if(source.error||run.error||!run.data)return reply({error:'missing_program_or_active_run'},409)
   const prices=new Map<string,Obj>((source.data||[]).map(x=>[String(x.linkwise_program_id),x] as [string,Obj]))
   const records=[]
   for(const item of incomingRows){
    const raw=asObject(item),pid=String(raw.program_id||'')
    const program=prices.get(pid)
    if(!program)return reply({error:'source_program_rate_missing'},422)
    const clean=present({...raw,run_key:key},program)
    if(!clean)return reply({error:'invalid_candidate'},422)
    records.push(clean)
   }
   const result=await sb.from('ai_discovery_candidates_v2').upsert(records,{
     onConflict:'run_key,source_key,source_product_id,problem_key',ignoreDuplicates:false
   })
   if(result.error)return reply({error:'candidate_write_failed'},503)
   return reply({ok:true,saved:records.length,stage:'research_candidate'})
  }
  if(action==='finish'){
   const counts=asObject(body.counts)
   const numeric=(k:string)=>{const x=n(counts[k]);return x===null||!Number.isSafeInteger(x)||x<0?0:x}
   const rows={
    status:'completed',scanned_count:numeric('scanned'),
    commission_eligible_count:numeric('commission15_eligible'),
    unpriced_count:numeric('missing_program_terms_not_evaluable'),
    below_floor_count:numeric('below_15_eur'),
    stored_candidates:Math.max(0,Math.min(10000,Number(body.ranked_research_candidates)||0)),
    metrics:{scope:String(body.scope||'unknown').slice(0,80),
      eligible_definition:'only estimated_earned_commission_gte_15_eur',
      program_rate_count:n(body.program_rate_count)||0,
      conversion_claim:'no observed CVR; heuristic proxy only',
      candidate_status:'not_promotion_approved'},
    finished_at:new Date().toISOString(),updated_at:new Date().toISOString()
   }
   const saved=await sb.from('ai_discovery_runs_v2').update(rows).eq('run_key',key).eq('status','partial').select('run_key').maybeSingle()
   if(saved.error||!saved.data)return reply({error:'run_finish_failed'},409)
   return reply({ok:true,run_key:key,status:'completed',stage:'research_only'})
  }
  return reply({error:'invalid_action'},400)
 }catch(e){
  console.error('[socialmarket-opportunity-gateway]',String(e).slice(0,210))
  return reply({error:'unauthorized_or_validation_failure'},503)
 }
})
