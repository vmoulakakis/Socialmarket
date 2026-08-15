import 'jsr:@supabase/functions-js/edge-runtime.d.ts'
import {createClient} from 'npm:@supabase/supabase-js@2.57.4'

const ADMIN='vmoulakakis@gmail.com'
const DEEPSEEK_KEY=Deno.env.get('DEEPSEEK_API_KEY')||Deno.env.get('DEEP_SEEK_API_KEY')||''
const MODEL=Deno.env.get('DEEPSEEK_MODEL')||'deepseek-v4-pro'
const SUPABASE_URL=Deno.env.get('SUPABASE_URL')!
const ANON_KEY=Deno.env.get('SUPABASE_ANON_KEY')!
const cors={'access-control-allow-origin':'*','access-control-allow-headers':'authorization, apikey, content-type','access-control-allow-methods':'GET,POST,OPTIONS'}
const json=(x:unknown,s=200)=>new Response(JSON.stringify(x),{status:s,headers:{...cors,'content-type':'application/json','cache-control':'no-store'}})

function decodeJwt(token:string){
 const part=token.split('.')[1];if(!part)throw new Error('invalid_jwt')
 const normalized=part.replace(/-/g,'+').replace(/_/g,'/'),pad='='.repeat((4-normalized.length%4)%4)
 return JSON.parse(atob(normalized+pad))
}

async function deepseek(system:string,input:unknown,maxTokens=5200){
 if(!DEEPSEEK_KEY)throw new Error('deepseek_not_configured')
 const r=await fetch('https://api.deepseek.com/chat/completions',{method:'POST',headers:{'content-type':'application/json','authorization':`Bearer ${DEEPSEEK_KEY}`},body:JSON.stringify({model:MODEL,temperature:.08,max_tokens:maxTokens,response_format:{type:'json_object'},messages:[{role:'system',content:system},{role:'user',content:JSON.stringify(input)}]})})
 const raw=await r.text();if(!r.ok)throw new Error(`deepseek_${r.status}:${raw.slice(0,700)}`)
 const j=JSON.parse(raw),content=String(j?.choices?.[0]?.message?.content||'{}')
 return {data:JSON.parse(content),usage:j?.usage||{}}
}

Deno.serve(async req=>{
 if(req.method==='OPTIONS')return new Response(null,{status:204,headers:cors})
 if(req.method==='GET')return json({ok:true,service:'demand-intelligence-gateway',version:'3.0',model:MODEL,deepseek_configured:Boolean(DEEPSEEK_KEY)})
 if(req.method!=='POST')return json({error:'method_not_allowed'},405)
 try{
  const auth=req.headers.get('authorization')||'';if(!auth.startsWith('Bearer '))throw new Error('missing_auth')
  const token=auth.slice(7),claims=decodeJwt(token);if(String(claims.email||'').toLowerCase()!==ADMIN)throw new Error('admin_only')
  const body=await req.json(),context=body.context||{},deterministic=body.deterministic||{}
  if(!context.taxonomy_id||!context.market)throw new Error('demand_context_required')
  const evidence=(Array.isArray(context.retrieved_evidence)?context.retrieved_evidence:[]).slice(0,40).map((x:any)=>({id:x.id,source_kind:x.source_kind,platform:x.platform,source_domain:x.source_domain,source_url:x.source_url,title:x.title,body:String(x.body||'').slice(0,1100),published_at:x.published_at,collected_at:x.collected_at,confidence:x.confidence,validation_status:x.validation_status,retrieval:x.retrieval,metrics:x.metrics}))
  const supply=(Array.isArray(context.supply_context)?context.supply_context:[]).slice(0,30)
  const history=(Array.isArray(context.history)?context.history:[]).slice(0,180)
  const pains=(Array.isArray(context.validated_pains)?context.validated_pains:[]).slice(0,25)
  const sourceMix=(Array.isArray(context.source_mix)?context.source_mix:[]).slice(0,30)
  const input={market:context.market,query:context.query,evidence,source_mix:sourceMix,supply,validated_pains:pains,history,deterministic,retrieval_semantics:context.retrieval_semantics,forecast_gate:deterministic.forecast_gate||context.forecast_gate}
  const system=`You are SocialMarket Demand Intelligence V3, a skeptical senior Greek market strategist, econometric analyst and affiliate-market researcher. Use ONLY the supplied production bundle. You are NOT allowed to create or modify canonical demand, competition, pain, opportunity or confidence scores. Never invent search volume, market size, market share, paid-ad spend, impressions, CPC, CTR, sales, first-party conversions, dates or Greek macro figures. Linkwise/merchant program metrics are network baselines unless explicitly labelled first-party. Macro/official sources may be discussed only when their actual evidence rows are supplied; a source registry or domain name alone is not a measurement. Supply context can explain market tension but must never rewrite demand. Correlation is not causation. Missing remains missing. If deterministic.forecast_gate.status is WITHHELD, neural/future quantitative forecasting is forbidden; explain the data sufficiency problem instead. Fuzzy memberships are analytical state descriptors, not observed facts. Explicitly search the supplied evidence for contradictions and weak links; absence is not contradiction. Produce strict JSON with: {executive_thesis:{headline,summary,confidence_0_100,confidence_basis},market_state:{label,why,canonical_metrics,fuzzy_membership},demand_decomposition:[{driver,evidence,source_type,confidence_0_100,classification:'OBSERVED'|'DERIVED'}],greek_context:[{finding,evidence,source,classification,limits}],supply_response:{assessment,merchant_environment,commercial_quality,risk,relationship_to_demand,causality_warning},demand_supply_tension:{assessment,evidence,opportunity_implication,limits},contradictions:[{claim,supporting,contradicting,status:'explicit_conflict'|'weak_support'|'unresolved'}],confidence_decomposition:{source_diversity,authority,freshness,retrieval_quality,canonical_confidence,missing_dimensions,overall_comment},history_diagnostics:{what_is_observed,change_description,limits},forecast_lab:{status,allowed_models,withheld_models,why,next_gate},affiliate_implications:[{priority,implication,evidence,what_not_to_assume}],recommended_actions:[{priority,action,why,evidence_needed,metric_to_watch}],falsification_tests:[{thesis,test,would_falsify}],next_evidence_to_collect:[{priority,evidence,source_family,why}],claim_audit:{observed_claims,derived_claims,modeled_claims,withheld_claims,unsupported_claims_avoided}}. Be analytical and specific, not generic. Prefer 3-7 high-value items per list.`
  const r=await deepseek(system,input,6200)
  const sb=createClient(SUPABASE_URL,ANON_KEY,{global:{headers:{Authorization:`Bearer ${token}`}}})
  const evidenceIds=evidence.map((x:any)=>x.id).filter(Boolean)
  const {data:runId,error:saveError}=await sb.rpc('admin_save_demand_analysis_v3',{p_taxonomy_id:context.taxonomy_id,p_market_observed_at:context.market?.observed_at||null,p_data_contract:{canonical_metrics_read_only:true,missing_remains_missing:true,retrieval:context.retrieval_semantics||{}},p_analysis:r.data,p_evidence_ids:evidenceIds,p_status:'completed'})
  await sb.rpc('admin_ai_log',{p_task_type:'demand_intelligence_v3',p_provider:'deepseek',p_model_name:MODEL,p_status:'success',p_input_tokens:Number(r.usage?.prompt_tokens||0),p_output_tokens:Number(r.usage?.completion_tokens||0),p_metadata:{taxonomy_id:context.taxonomy_id,run_id:runId||null,evidence_count:evidence.length,save_error:saveError?.message||null,forecast_status:deterministic?.forecast_gate?.status||null}})
  return json({ok:true,model:MODEL,run_id:runId||null,analysis:r.data,usage:r.usage,persist_warning:saveError?.message||null})
 }catch(e){const msg=String(e instanceof Error?e.message:e);return json({error:msg},msg.includes('admin_only')?403:400)}
})
