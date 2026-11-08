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
const object=(v:unknown):v is Record<string,unknown>=>!!v&&typeof v==='object'&&!Array.isArray(v)
// Only aggregate telemetry crosses this boundary. URLs, headers, tokens and raw
// transport errors are deliberately absent from the source metadata contract.
function sourceMetadata(value:unknown){
 if(value===undefined)return {}
 if(!object(value))return null
 const clean:Record<string,unknown>={}
 const textKeys=['source_kind','source_scope','scope','source_integrity','source_fingerprint','content_type','error_code','error_type','source_parse_error_type','error_class']
 const numberKeys=['source_bytes','source_size_bytes','bytes_read','elapsed_seconds','record_offset','checkpoint_offset','expected_min_records','expected_records','http_status','content_length']
 for(const k of textKeys){
  if(value[k]!=null){
   if(typeof value[k]!=='string'||!/^[-A-Za-z0-9_ .:;+/=]{0,180}$/.test(value[k] as string))return null
   if(k==='error_class'&&!/^[A-Za-z0-9_:.-]{1,180}$/.test(value[k] as string))return null
   clean[k]=value[k]
  }
 }
 for(const k of ['source_sha256','source_uri_hash','rule_revision_hash','signal_revision_hash']){
  if(value[k]!=null){if(typeof value[k]!=='string'||!/^[a-f0-9]{64}$/i.test(value[k] as string))return null;clean[k]=value[k]}
 }
 for(const k of ['source_etag','source_signature']){
  if(value[k]!=null){
   const v=value[k]
   if(typeof v!=='string'||!(/^(?:W\/)?"[A-Za-z0-9._:+/=-]{1,150}"$/.test(v)||(k==='source_signature'&&/^local:[0-9]+:[0-9]+$/.test(v))))return null
   if(k==='source_signature'&&v.startsWith('W/'))return null
   clean[k]=v
  }
 }
 if(value.source_last_modified!=null){
  if(typeof value.source_last_modified!=='string'||!/^[A-Z][a-z]{2}, [0-9]{2} [A-Z][a-z]{2} [0-9]{4} [0-9]{2}:[0-9]{2}:[0-9]{2} GMT$/.test(value.source_last_modified))return null
  clean.source_last_modified=value.source_last_modified
 }
 for(const k of numberKeys){
  if(value[k]!=null){const n=numeric(value[k]);if(n===null||n<0||n>Number.MAX_SAFE_INTEGER||(k==='expected_records'&&!Number.isSafeInteger(n)))return null;clean[k]=n}
 }
 if(value.eof_reached!==undefined){if(typeof value.eof_reached!=='boolean')return null;clean.eof_reached=value.eof_reached}
 if(value.scope_verified_by_publisher!==undefined&&value.scope_verified_by_publisher!==false)return null
 clean.scope_verified_by_publisher=false
 return clean
}
function observedCounts(value:unknown){
 if(!object(value))return null
 const counts:Record<string,number|string>={}
 if(Object.keys(value).length>64)return null
 for(const [k,v] of Object.entries(value)){
  if(!/^[a-z][a-z0-9_]{0,63}$/.test(k))return null
  if(k==='source_integrity'||k==='source_parse_error_type'){
   if(typeof v!=='string'||!/^[A-Za-z0-9_]{1,64}$/.test(v))return null
   counts[k]=v
  }else{
   if(typeof v!=='number'||!Number.isSafeInteger(v)||v<0)return null
   counts[k]=v
  }
 }
 const scanned=Number(counts.scanned??0)
 if(['commission_eligible','commission_unknown','below_15'].reduce((sum,k)=>sum+Number(counts[k]??0),0)>scanned)return null
 return counts
}
const baseMetrics={source_scope:'configured_feed_unknown_scope',scope_verified_by_publisher:false,hard_filter_eur:15,commission_basis:'historical_source_estimate',verified_demand:false,verified_conversion:false,auto_publish:false}

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
  if(new TextEncoder().encode(raw).byteLength>140000)return respond({error:'payload_too_large'},413)
  let body:Record<string,unknown>
  try{const parsed=JSON.parse(raw);if(!object(parsed))return respond({error:'invalid_body'},400);body=parsed}catch{return respond({error:'invalid_json'},400)}
  const url=Deno.env.get('SUPABASE_URL'),key=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')
  if(!url||!key)return respond({error:'private_db_unavailable'},503)
  const db=createClient(url,key,{auth:{persistSession:false,autoRefreshToken:false}})
  if(body.action==='commission_rules'){
   // Read real network-program-rate map; no Merchant-360 admission hard gate.
   const {data,error}=await db.from('linkwise_program_commissions')
    .select('linkwise_program_id,program_name,actual_http_site,flat_commission_eur,flat_commission_min_eur,flat_commission_max_eur,percent_commission,percent_commission_min,percent_commission_max,source,imported_at')
    .limit(1000)
   if(error)return respond({error:'rate_query_failed'},503)
   const programs=data||[],mapped=programs.filter(x=>x.linkwise_program_id)
   return respond({ok:true,rules:Object.fromEntries(mapped.map(x=>[x.linkwise_program_id,x])),programs,
     rule_count:programs.length,mapped_rule_count:mapped.length,rate_semantics:'historical_estimate_not_approved_payout'})
  }
  if(body.action==='begin_research'){
    const run=str(body.run_key,80),metadata=sourceMetadata(body.source_metadata)
    if(!uuid.test(run))return respond({error:'invalid_run_key'},400)
    if(metadata===null)return respond({error:'invalid_source_metadata'},400)
    const {error}=await db.from('ai_discovery_runs_v2').upsert({
      run_key:run,source_key:'linkwise',status:'partial',workflow_ref:str(payload.workflow_ref,300),
      metrics:{...baseMetrics,stage:'streaming',source_metadata:metadata}
    },{onConflict:'run_key',ignoreDuplicates:true})
    if(error)return respond({error:'research_run_insert_failed'},503)
    const current=await db.from('ai_discovery_runs_v2').select('status').eq('run_key',run).maybeSingle()
    if(current.error||!current.data)return respond({error:'research_run_read_failed'},503)
    return respond({ok:true,run_key:run,status:current.data.status})
  }
  if(body.action==='checkpoint_research'||body.action==='finish_research'){
    const run=str(body.run_key,80)
    if(!uuid.test(run))return respond({error:'invalid_run_key'},400)
    const stats=observedCounts(body.counts),metadata=sourceMetadata(body.source_metadata)
    if(stats===null)return respond({error:'invalid_counts'},400)
    if(metadata===null)return respond({error:'invalid_source_metadata'},400)
    const finishing=body.action==='finish_research'
    if(finishing&&!['completed','partial','failed'].includes(String(body.status)))return respond({error:'invalid_run_status'},400)
    const errorCode=body.error_code
    if(errorCode!==undefined&&(typeof errorCode!=='string'||!/^[A-Za-z0-9_]{1,100}$/.test(errorCode)))return respond({error:'invalid_error_code'},400)
    const current=await db.from('ai_discovery_runs_v2').select('status,metrics,scanned_count').eq('run_key',run).maybeSingle()
    if(current.error)return respond({error:'research_run_read_failed'},503)
    if(!current.data)return respond({error:'research_run_not_started'},404)
    const scanned=Number(stats.scanned??0)
    if(scanned<Number(current.data.scanned_count||0))return respond({error:'checkpoint_counter_regression'},409)
    const previous=object(current.data.metrics)?current.data.metrics:{}
    const previousMetadata=object(previous.source_metadata)?previous.source_metadata:{}
    const expectedRecords=Math.max(Number(previousMetadata.expected_records||0),Number(metadata.expected_records||0))
    const mergedMetadata={...previousMetadata,...metadata,expected_records:expectedRecords}
    const coverageMet=expectedRecords===0||scanned>=expectedRecords
    const completed=finishing&&body.status==='completed'&&stats.source_integrity==='complete_json'&&coverageMet
    if(current.data.status==='completed'&&!completed)return respond({error:'research_run_already_completed'},409)
    const countResult=await db.from('ai_discovery_candidates_v2').select('id',{count:'exact',head:true}).eq('run_key',run)
    if(countResult.error)return respond({error:'run_count_failed'},503)
    const update:Record<string,unknown>={status:completed?'completed':'partial',scanned_count:scanned,
      commission_eligible_count:Number(stats.commission_eligible??0),unpriced_count:Number(stats.commission_unknown??0),below_floor_count:Number(stats.below_15??0),
      stored_candidates:countResult.count||0,
      metrics:{...previous,...baseMetrics,stage:finishing?'finished':'streaming',counts:stats,
      source_metadata:mergedMetadata,source_integrity:stats.source_integrity??'unknown',coverage_threshold_met:coverageMet,
      ...(finishing?{requested_status:body.status,completion_verified:completed,
        error_code:errorCode??(completed?null:!coverageMet?'source_smaller_than_requested_universe':body.status==='failed'?'worker_failed':body.status==='completed'?'source_incomplete':'partial_source')}:{})}}
    if(finishing)update.finished_at=new Date().toISOString()
    const {error}=await db.from('ai_discovery_runs_v2').update(update).eq('run_key',run)
    if(error)return respond({error:'run_finalize_failed'},503)
    return respond({ok:true,run_key:run,status:completed?'completed':'partial',persisted_count:countResult.count||0})
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
   const current=await db.from('ai_discovery_runs_v2').select('status').eq('run_key',run).maybeSingle()
   if(current.error)return respond({error:'research_run_read_failed'},503)
   if(!current.data)return respond({error:'research_run_not_started'},404)
   if(current.data.status==='completed')return respond({error:'research_run_already_completed'},409)
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
