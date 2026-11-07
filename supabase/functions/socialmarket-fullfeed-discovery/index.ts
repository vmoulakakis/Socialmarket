import 'jsr:@supabase/functions-js/edge-runtime.d.ts'
import { createRemoteJWKSet,jwtVerify } from 'npm:jose@6.1.0'
import { createClient } from 'npm:@supabase/supabase-js@2.57.4'

// Research candidates only. Source URLs never rewritten. No approval/publish endpoints.
const ISSUER='https://token.actions.githubusercontent.com'
const AUDIENCE='socialmarket-fullfeed-discovery'
const REPO_ID='1329707883'
const REPO='vmoulakakis/Socialmarket'
const WORKFLOWS=new Set([
 'vmoulakakis/Socialmarket/.github/workflows/full-feed-discovery.yml@refs/heads/main',
 'vmoulakakis/Socialmarket/.github/workflows/full-feed-discovery.yml@refs/heads/feat/agentic-shopper-evidence-gate-20261106'
])
const JWKS=createRemoteJWKSet(new URL(ISSUER+'/.well-known/jwks'))
const respond=(data:unknown,status=200)=>new Response(JSON.stringify(data),{status,headers:{'content-type':'application/json','cache-control':'no-store','x-robots-tag':'noindex'}})
const numeric=(x:unknown)=>typeof x==='number'&&Number.isFinite(x)?x:null
const cap=(x:unknown)=>Math.max(0,Math.min(100,numeric(x)??0))
const str=(v:unknown,n=400)=>String(v??'').slice(0,n)
const RE=/^https:\/\/go\.linkwi\.se\/z\/([1-9][0-9]*)-0\/CD104\/\?lnkurl=/
const uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

Deno.serve(async req=>{
 if(req.method==='GET')return respond({service:'socialmarket-fullfeed-discovery',private:true,status:'research_only'})
 if(req.method!=='POST')return respond({error:'post_only'},405)
 const auth=req.headers.get('authorization')||''
 if(!auth.startsWith('Bearer '))return respond({error:'oidc_required'},401)
 try {
  const {payload}=await jwtVerify(auth.slice(7),JWKS,{issuer:ISSUER,audience:AUDIENCE})
  if(String(payload.repository)!==REPO||String(payload.repository_id)!==REPO_ID||
    !WORKFLOWS.has(String(payload.workflow_ref))||
    !['refs/heads/main','refs/heads/feat/agentic-shopper-evidence-gate-20261106'].includes(String(payload.ref)))
    return respond({error:'workflow_not_authorized'},403)
  const raw=await req.text()
  if(raw.length>140000)return respond({error:'payload_too_large'},413)
  let body:Record<string,unknown>
  try{body=JSON.parse(raw)}catch{return respond({error:'invalid_json'},400)}
  const url=Deno.env.get('SUPABASE_URL'),key=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')
  if(!url||!key)return respond({error:'private_db_unavailable'},503)
  const db=createClient(url,key,{auth:{persistSession:false,autoRefreshToken:false}})
  if(body.action==='commission_rules'){
   // Read real network-program-rate map; no Merchant-360 admission hard gate.
   const {data,error}=await db.from('linkwise_program_commissions')
    .select('linkwise_program_id,program_name,flat_commission_eur,flat_commission_min_eur,percent_commission,percent_commission_min,source,imported_at')
    .limit(1000)
   if(error)return respond({error:'rate_query_failed'},503)
   return respond({ok:true,rules:Object.fromEntries((data||[]).filter(x=>x.linkwise_program_id).map(x=>[x.linkwise_program_id,x])),
     rule_count:data?.length||0,rate_semantics:'historical_estimate_not_approved_payout'})
  }
  if(body.action==='store_research'){
   const rows=body.rows
   const run=str(body.run_key,80)
   if(!uuid.test(run)||!Array.isArray(rows)||!rows.length||rows.length>20)
     return respond({error:'invalid_batch'},400)
   const records=[]
   for(const x of rows) {
    if(!x||typeof x!=='object'||Array.isArray(x))return respond({error:'invalid_row'},400)
    const r=x as Record<string,unknown>,link=str(r.original_tracking_url,4000),m=RE.exec(link)
    const calculated=numeric(r.calculated_commission_eur),price=numeric(r.price_eur)
    if(!m||m[1]!==str(r.program_id)||calculated===null||calculated<15||price===null||price<=0||
       !r.source_product_id||!r.product_title||!r.commission_basis)return respond({error:'source_or_commission_gate_failed'},400)
    const references=Array.isArray(r.evidence_refs)?r.evidence_refs.filter(z=>typeof z==='string').slice(0,12):[]
    const score=r.opportunity_score==null?null:cap(r.opportunity_score)
    records.push({
      run_key:run,source_key:'linkwise',source_product_id:str(r.source_product_id,150),
      program_id:str(r.program_id,30),merchant_domain:str(r.merchant_domain,255),
      product_title:str(r.product_title,550),category_text:str(r.category_text,255),
      price_eur:price,calculated_commission_eur:calculated,
      commission_basis:str(r.commission_basis,100),
      commission_provenance:r.commission_provenance&&typeof r.commission_provenance==='object'?r.commission_provenance:{},
      original_tracking_url:link,image_url:r.image_url?str(r.image_url,3000):null,
      stock_state:['in_stock','out_of_stock','unknown'].includes(String(r.stock_state))?r.stock_state:'unknown',
      valid_to:r.valid_to||null,
      problem_key:str(r.problem_key||'unclassified',150),
      pain_fit_score:numeric((r.components as Record<string,unknown>)?.pain_fit),
      demand_score:numeric((r.components as Record<string,unknown>)?.demand),
      competition_score:numeric((r.components as Record<string,unknown>)?.low_competition)===null?null:100-cap((r.components as Record<string,unknown>)?.low_competition),
      conversion_proxy_score:numeric((r.components as Record<string,unknown>)?.conversion),
      opportunity_score:score,
      evidence_level:r.evidence_level==='source_observed'?'source_observed':'hypothesis_only',
      evidence_refs:references,
      stage:'research_candidate',feed_observed_at:r.feed_observed_at||null,
    })
   }
   const {error}=await db.from('ai_discovery_candidates_v2').upsert(records,
     {onConflict:'run_key,source_key,source_product_id,problem_key'})
   if(error){console.error('research_write_failed',error.code);return respond({error:'research_write_failed'},503)}
   return respond({ok:true,accepted:records.length,kind:'unapproved_research_only'})
  }
  return respond({error:'unknown_action'},400)
 }catch(e){
  console.error('fullfeed-gateway-error',e instanceof Error?e.name:'unknown')
  return respond({error:'verification_or_gateway_failure'},503)
 }
})
