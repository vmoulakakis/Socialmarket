import 'jsr:@supabase/functions-js/edge-runtime.d.ts'
import {createRemoteJWKSet,jwtVerify} from 'npm:jose@6.1.0'

const ISSUER='https://token.actions.githubusercontent.com'
const AUDIENCE='socialmarket-supabase-worker'
const REPOSITORY_ID='1329707883'
const REPOSITORY='vmoulakakis/Socialmarket'
const ALLOWED=new Set(['vmoulakakis/Socialmarket/.github/workflows/semantic-marketplace-200.yml@refs/heads/main'])
const JWKS=createRemoteJWKSet(new URL(`${ISSUER}/.well-known/jwks`))
const DEEPSEEK_KEY=Deno.env.get('DEEPSEEK_API_KEY')||Deno.env.get('DEEP_SEEK_API_KEY')||''
const DEEPSEEK_MODEL=Deno.env.get('DEEPSEEK_MODEL')||'deepseek-v4-pro'
const json=(x:unknown,s=200)=>new Response(JSON.stringify(x),{status:s,headers:{'content-type':'application/json','cache-control':'no-store'}})

async function auth(req:Request){
  const h=req.headers.get('authorization')||''
  if(!h.startsWith('Bearer '))throw new Error('missing_oidc')
  const {payload}=await jwtVerify(h.slice(7),JWKS,{issuer:ISSUER,audience:AUDIENCE})
  if(String(payload.repository_id||'')!==REPOSITORY_ID||String(payload.repository||'')!==REPOSITORY||String(payload.ref||'')!=='refs/heads/main'||!ALLOWED.has(String(payload.workflow_ref||'')))throw new Error('oidc_not_allowed')
}

async function structured(system:string,payload:unknown,maxTokens:number){
  if(!DEEPSEEK_KEY)throw new Error('deepseek_not_configured')
  const run=async(retry=false)=>{
    const body={
      model:DEEPSEEK_MODEL,
      temperature:0.05,
      max_tokens:retry?Math.min(maxTokens+600,5200):maxTokens,
      response_format:{type:'json_object'},
      messages:[
        {role:'system',content:system},
        {role:'user',content:`Return one COMPLETE JSON object only. Be concise; never pad prose. ${retry?'A previous JSON response was incomplete. Use shorter strings and finish every array/object. ':''}Input:\n${JSON.stringify(payload)}`}
      ]
    }
    const r=await fetch('https://api.deepseek.com/chat/completions',{method:'POST',headers:{'content-type':'application/json','authorization':`Bearer ${DEEPSEEK_KEY}`},body:JSON.stringify(body)})
    const raw=await r.text();if(!r.ok)throw new Error(`deepseek_${r.status}:${raw.slice(0,500)}`)
    const j=JSON.parse(raw),choice=j?.choices?.[0]||{},content=String(choice?.message?.content||'')
    if(!content.trim())throw new Error('deepseek_empty')
    if(String(choice.finish_reason||'')==='length')throw new Error('deepseek_truncated')
    return JSON.parse(content)
  }
  try{return await run(false)}catch(first){
    try{return await run(true)}catch(second){throw new Error(`structured_output_failed:${String(first).slice(0,160)}|retry:${String(second).slice(0,220)}`)}
  }
}

const PLAN_SYSTEM=`You are AFFINITY Opportunity Cartographer for Greece. You select opportunity spaces, not products. Use only the supplied validated pain evidence, market context, strict merchant universe and observed feedback. Never invent search volume, sales, market share or trend facts. Separate demand from scarcity and engagement from purchase intent. Return JSON with exactly 10 linkwise_clusters and exactly 10 aliexpress_clusters. Each cluster must contain: cluster_key (short stable ASCII slug), niche, subniche, job_to_be_done in Greek, pain_statement in Greek, gap_statement in Greek, demand_score 0-100, whitespace_score 0-100, commercial_intent_score 0-100, confidence 0-100, evidence_ids[] using only supplied pain IDs, rationale in Greek <=220 chars, search_queries[] with 3-5 concise Greek/English product-discovery phrases. Linkwise clusters must plausibly support multiple distinct products across strict merchants. AliExpress clusters should favor useful demonstrable products with plausible Greek whitespace, never novelty alone.`

const RESEARCH_SYSTEM=`You are AFFINITY Product Research Agent for Greece. Deterministic commission, merchant and safety gates have already passed and cannot be weakened. Evaluate only supplied facts. Score semantic fit to the opportunity cluster, Greek demand plausibility, pain intensity, market whitespace, product identity/documentation evidence, merchant/seller evidence, logistics evidence, price/value and social demonstrability. For AliExpress use the supplied Greek multi-surface evidence; do not turn missing evidence into absence. Never invent reviews, orders, warranty, shipping, features, certification, market size, search volume or conversion. Return JSON {items:[...]}. For every supplied source_record_hash return: source_record_hash, demand_score, pain_score, whitespace_score, scarcity_score, semantic_fit_score, product_quality_score, organic_score, ads_score, viral_score, affinity_score (all 0-100), greek_availability_assessment exactly ABSENT|VERY_RARE|AVAILABLE|FUNCTIONAL_EQUIVALENT_EXISTS|UNKNOWN, job_to_be_done, pain_statement, gap_statement, solution_statement (Greek, each <=320 chars), semantic_tags[] 4-8, audience (Greek <=180 chars), hook (Greek <=180 chars), caption (Greek <=450 chars), hashtags[] 5-8, research_reason (Greek <=350 chars), quality_evidence[] <=6, quality_unknowns[] <=5, landing_candidate boolean. product_quality_score measures strength of available evidence, not physical certification.`

const SKEPTIC_SYSTEM=`You are AFFINITY Skeptic / Product Quality QA. Try to reject each candidate. Use only supplied product evidence plus Research Agent output. Look for unsupported claims, weak identity, weak quality evidence, hidden Greek exact/OEM/functional equivalents, low merchant/seller evidence, misleading novelty, duplicate/variant pollution, logistics uncertainty, unsafe/regulatory risk, weak pain fit and contradictions. Hard gates cannot be overridden. Return JSON {items:[...]}. For every source_record_hash return: source_record_hash, verdict exactly validated|needs_review|rejected, corrected_greek_availability exactly ABSENT|VERY_RARE|AVAILABLE|FUNCTIONAL_EQUIVALENT_EXISTS|UNKNOWN, product_quality_score 0-100, contradiction_score 0-100 where 100 means evidence is internally consistent, reasons[] <=5 concise Greek strings, blockers[] <=5, required_rechecks[] <=5. Use validated only when the candidate is commercially responsible and evidence-backed.`

Deno.serve(async req=>{
  if(req.method==='GET')return json({ok:true,service:'marketplace200-ai-gateway',version:'1.0',model:DEEPSEEK_MODEL,architecture:'single-llm-call-per-request'})
  if(req.method!=='POST')return json({ok:false,error:'method_not_allowed'},405)
  try{
    await auth(req)
    const b=await req.json(),action=String(b.action||'')
    if(action==='plan')return json({ok:true,plan:await structured(PLAN_SYSTEM,b.payload||{},4300)})
    if(action==='research')return json({ok:true,research:await structured(RESEARCH_SYSTEM,b.payload||{},4300)})
    if(action==='skeptic')return json({ok:true,skeptic:await structured(SKEPTIC_SYSTEM,b.payload||{},3600)})
    throw new Error('action_not_allowed')
  }catch(e){
    const m=String(e instanceof Error?e.message:e);console.error(e)
    return json({ok:false,error:m},m.includes('oidc')?401:500)
  }
})
