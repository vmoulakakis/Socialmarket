import 'jsr:@supabase/functions-js/edge-runtime.d.ts'
import { createClient } from 'npm:@supabase/supabase-js@2.57.4'

const ADMIN='vmoulakakis@gmail.com'
const DEEPSEEK_KEY=Deno.env.get('DEEPSEEK_API_KEY')||Deno.env.get('DEEP_SEEK_API_KEY')||''
const MODEL=Deno.env.get('DEEPSEEK_MODEL')||'deepseek-v4-pro'
const SUPABASE_URL=Deno.env.get('SUPABASE_URL')!
const ANON_KEY=Deno.env.get('SUPABASE_ANON_KEY')!
const json=(x:unknown,s=200)=>new Response(JSON.stringify(x),{status:s,headers:{'content-type':'application/json','cache-control':'no-store'}})

function decodeJwt(token:string){const part=token.split('.')[1];if(!part)throw new Error('invalid_jwt');const normalized=part.replace(/-/g,'+').replace(/_/g,'/');const pad='='.repeat((4-normalized.length%4)%4);return JSON.parse(atob(normalized+pad))}
async function deepseek(system:string,input:unknown,maxTokens=2500){if(!DEEPSEEK_KEY)throw new Error('deepseek_not_configured');const r=await fetch('https://api.deepseek.com/chat/completions',{method:'POST',headers:{'content-type':'application/json','authorization':`Bearer ${DEEPSEEK_KEY}`},body:JSON.stringify({model:MODEL,temperature:0.12,max_tokens:maxTokens,response_format:{type:'json_object'},messages:[{role:'system',content:system},{role:'user',content:JSON.stringify(input)}]})});const raw=await r.text();if(!r.ok)throw new Error(`deepseek_${r.status}:${raw.slice(0,500)}`);const j=JSON.parse(raw);return {data:JSON.parse(String(j?.choices?.[0]?.message?.content||'{}')),usage:j?.usage||{}}}

Deno.serve(async(req)=>{
 if(req.method==='GET')return json({ok:true,service:'admin-intelligence-gateway',model:MODEL,deepseek_configured:Boolean(DEEPSEEK_KEY)})
 if(req.method!=='POST')return json({error:'method_not_allowed'},405)
 try{
  const auth=req.headers.get('authorization')||'';if(!auth.startsWith('Bearer '))throw new Error('missing_auth')
  const token=auth.slice(7);const claims=decodeJwt(token);if(String(claims.email||'').toLowerCase()!==ADMIN)throw new Error('admin_only')
  const sb=createClient(SUPABASE_URL,ANON_KEY,{global:{headers:{Authorization:`Bearer ${token}`}}})
  const body=await req.json();const action=String(body.action||'')
  if(action==='business_brief'){
   const bi=body.bi||{};const source={generated_at:bi.generated_at,pipeline:bi.pipeline||{},freshness:bi.freshness||{},queue_alerts:bi.queue_alerts||{},ai_summary:bi.ai_summary||{},audit_distribution:(bi.audit_distribution||[]).slice(0,10),evidence_by_source:(bi.evidence_by_source||[]).slice(0,20),evidence_by_platform:(bi.evidence_by_platform||[]).slice(0,20),top_pain_clusters:(bi.top_pain_clusters||[]).slice(0,30),merchant_opportunities:(bi.merchant_opportunities||[]).slice(0,30),product_opportunities:(bi.product_opportunities||[]).slice(0,30),research_job_health:(bi.research_job_health||[]).slice(0,40),collection_job_health:(bi.collection_job_health||[]).slice(0,40),merchant_runs:(bi.merchant_runs||[]).slice(0,20),product_config:bi.product_config||null}
   const system=`You are SocialMarket AI Business Intelligence Analyst. Analyze ONLY the supplied production metrics. Never invent revenue, traffic, search volume, conversions, market share, users, products, costs, or trends not present in the input. Missing data must be called out explicitly. Separate OBSERVED FACTS from INFERENCES. Focus on the Greek affiliate intelligence business. Produce strict JSON: {executive_summary, data_health:{score_0_100,issues:[...],freshness_comment}, pipeline_health:{score_0_100,bottlenecks:[...],conversion_observations:[...]}, opportunity_insights:[{title,why_it_matters,evidence,confidence_0_100}], operational_risks:[{risk,severity,action}], ai_efficiency:{assessment,actions:[...]}, recommended_actions:[{priority:'P0'|'P1'|'P2',action,reason,expected_effect,metric_to_watch}], questions_to_answer_next:[...]}. If product output is zero, treat it as a pipeline blocker rather than pretending there are product opportunities.`
   const r=await deepseek(system,source,4200);await sb.rpc('admin_ai_log',{p_task_type:'business_brief',p_provider:'deepseek',p_model_name:MODEL,p_status:'success',p_input_tokens:Number(r.usage?.prompt_tokens||0),p_output_tokens:Number(r.usage?.completion_tokens||0),p_metadata:{generated_at:bi.generated_at||null}});return json({ok:true,model:MODEL,brief:r.data,usage:r.usage})
  }
  if(action==='forecast'){
   const source={generated_at:body.generated_at,category_market:(body.category_market||[]).slice(0,120),pain_gaps:(body.pain_gaps||[]).slice(0,80),merchants:(body.merchants||[]).slice(0,80),social:(body.social||[]).slice(0,100)}
   const system=`You are SocialMarket Forecast Analyst for the Greek affiliate market. Use ONLY supplied evidence. Never invent search volumes, market shares, social metrics, or dates. Distinguish observed facts from inference. Produce JSON: {as_of, horizon_months:3, market_outlook, confidence_0_100, drivers:[{name,direction,confidence,evidence}], category_forecasts:[{category,current_signal,month_1,month_2,month_3,confidence,why}], risks:[...], affiliate_actions:[...], methodology_note}. Forecast scores are directional 0-100 indices, not fabricated volumes. If evidence is sparse, lower confidence explicitly.`
   const r=await deepseek(system,source,3200);await sb.rpc('admin_ai_log',{p_task_type:'forecast',p_provider:'deepseek',p_model_name:MODEL,p_status:'success',p_input_tokens:Number(r.usage?.prompt_tokens||0),p_output_tokens:Number(r.usage?.completion_tokens||0),p_metadata:{horizon_months:3}});return json({ok:true,model:MODEL,forecast:r.data,usage:r.usage})
  }
  if(action==='promo'){
   const product=body.product||{};const pain=body.pain||null;const platforms=Array.isArray(body.platforms)?body.platforms:['facebook','instagram','tiktok','linkedin'];if(!product.tracking_url)throw new Error('tracking_url_required')
   const system=`You are SocialMarket Affiliate Creative Agent. Use ONLY supplied product, merchant, validated pain and commercial facts. Do not invent features, reviews, scarcity, discounts or performance claims. Keep the exact tracking_url unchanged. Produce JSON: {product_card:{headline,subheadline,bullets,cta,disclaimer}, image_prompt, posts:{facebook:{copy,hashtags},instagram:{caption,hashtags},tiktok:{hook,script,caption,hashtags},linkedin:{copy,hashtags}}, audit:{claims_used:[...],unsupported_claims_avoided:[...],evidence_note}}. Greek language unless product context clearly requires English. Professional, conversion-oriented, non-spammy.`
   const r=await deepseek(system,{product,pain,platforms},3600);await sb.rpc('admin_ai_log',{p_task_type:'promo',p_provider:'deepseek',p_model_name:MODEL,p_status:'success',p_input_tokens:Number(r.usage?.prompt_tokens||0),p_output_tokens:Number(r.usage?.completion_tokens||0),p_metadata:{product_id:product.product_id||null,platforms}});return json({ok:true,model:MODEL,promo:r.data,usage:r.usage})
  }
  throw new Error('action_not_allowed')
 }catch(e){const msg=String(e instanceof Error?e.message:e);return json({error:msg},msg.includes('admin_only')?403:400)}
})
