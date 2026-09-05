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
      thinking:{type:'disabled'},
      reasoning_effort:'low',
      temperature:0.04,
      max_tokens:retry?Math.min(maxTokens+400,3600):maxTokens,
      response_format:{type:'json_object'},
      messages:[
        {role:'system',content:system},
        {role:'user',content:`Return one COMPLETE compact JSON object only. Use short strings and finish every array/object. ${retry?'Previous JSON was incomplete; compress further. ':''}Input:\n${JSON.stringify(payload)}`}
      ]
    }
    const r=await fetch('https://api.deepseek.com/chat/completions',{method:'POST',headers:{'content-type':'application/json','authorization':`Bearer ${DEEPSEEK_KEY}`},body:JSON.stringify(body)})
    const raw=await r.text();if(!r.ok)throw new Error(`deepseek_${r.status}:${raw.slice(0,500)}`)
    const j=JSON.parse(raw),choice=j?.choices?.[0]||{},content=String(choice?.message?.content||'')
    if(!content.trim())throw new Error(`deepseek_empty:${String(choice?.finish_reason||'unknown')}`)
    if(String(choice.finish_reason||'')==='length')throw new Error('deepseek_truncated')
    return JSON.parse(content)
  }
  try{return await run(false)}catch(first){try{return await run(true)}catch(second){throw new Error(`structured_output_failed:${String(first).slice(0,160)}|retry:${String(second).slice(0,220)}`)}}
}

const CLUSTER_SCHEMA=`Each cluster must contain: cluster_key stable short ASCII slug, niche, subniche, job_to_be_done Greek, pain_statement Greek, gap_statement Greek, demand_score 0-100, whitespace_score 0-100, commercial_intent_score 0-100, confidence 0-100, evidence_ids[] only from supplied pain IDs, rationale Greek <=160 chars, search_queries[] exactly 3 concise Greek/English product discovery phrases.`
const LINK_PLAN=`You are AFFINITY Linkwise Opportunity Cartographer for Greece. Select opportunity spaces, never products. Use only supplied validated pain/market/merchant evidence. Never invent search volume, sales, trend facts or market share. Separate demand from scarcity. Return JSON {linkwise_clusters:[exactly 10 clusters]}. Favor niches broad enough for multiple materially different products across trustworthy merchants. ${CLUSTER_SCHEMA}`
const ALI_PLAN=`You are AFFINITY AliExpress Opportunity Cartographer for Greece. Select useful problem-solving opportunity spaces, never novelty for novelty's sake. Use only supplied validated pain and Greek market evidence. Never invent search volume, sales, trend facts or market share. Return JSON {aliexpress_clusters:[exactly 10 clusters]}. Favor demonstrable products where Greek whitespace can later be tested via exact/OEM/equivalent research. ${CLUSTER_SCHEMA}`

const RESEARCH_SYSTEM=`You are AFFINITY Product Research Agent for Greece. Deterministic commission, merchant and safety gates have already passed and cannot be weakened. Evaluate only supplied facts. Score semantic fit, Greek demand plausibility, pain intensity, market whitespace, product identity/documentation evidence, merchant/seller evidence, logistics evidence, price/value and social demonstrability. For AliExpress use supplied Greek multi-surface evidence; missing evidence is not absence. Never invent reviews, orders, warranty, shipping, features, certification, market size, search volume or conversion. Return JSON {items:[...]}. For every supplied source_record_hash return: source_record_hash, demand_score, pain_score, whitespace_score, scarcity_score, semantic_fit_score, product_quality_score, organic_score, ads_score, viral_score, affinity_score (0-100), greek_availability_assessment exactly ABSENT|VERY_RARE|AVAILABLE|FUNCTIONAL_EQUIVALENT_EXISTS|UNKNOWN, job_to_be_done, pain_statement, gap_statement, solution_statement (Greek <=240 chars each), semantic_tags[] 4-8, audience Greek <=120 chars, hook Greek <=120 chars, caption Greek <=320 chars, hashtags[] 5-8, research_reason Greek <=240 chars, quality_evidence[] <=5, quality_unknowns[] <=4, landing_candidate boolean. Product quality score measures evidence strength, not physical certification.`
const SKEPTIC_SYSTEM=`You are AFFINITY Skeptic / Product Quality QA. Try to reject each candidate using only supplied evidence plus Research output. Check unsupported claims, weak identity/quality evidence, hidden Greek exact/OEM/functional equivalents, merchant/seller weakness, fake novelty, variants, logistics uncertainty, unsafe/regulatory risk, weak pain fit and contradictions. Return JSON {items:[...]}. For every source_record_hash return: source_record_hash, verdict validated|needs_review|rejected, corrected_greek_availability ABSENT|VERY_RARE|AVAILABLE|FUNCTIONAL_EQUIVALENT_EXISTS|UNKNOWN, product_quality_score 0-100, contradiction_score 0-100, reasons[] <=4 concise Greek strings, blockers[] <=4, required_rechecks[] <=4. Use validated only when evidence-backed.`

Deno.serve(async req=>{
  if(req.method==='GET')return json({ok:true,service:'marketplace200-ai-gateway',version:'1.2-strict-json',model:DEEPSEEK_MODEL,architecture:'bounded-microagents-thinking-disabled'})
  if(req.method!=='POST')return json({ok:false,error:'method_not_allowed'},405)
  try{
    await auth(req)
    const b=await req.json(),action=String(b.action||''),payload=b.payload||{}
    if(action==='plan_linkwise')return json({ok:true,plan:await structured(LINK_PLAN,payload,2600)})
    if(action==='plan_aliexpress')return json({ok:true,plan:await structured(ALI_PLAN,payload,2600)})
    if(action==='research')return json({ok:true,research:await structured(RESEARCH_SYSTEM,payload,3400)})
    if(action==='skeptic')return json({ok:true,skeptic:await structured(SKEPTIC_SYSTEM,payload,2800)})
    throw new Error('action_not_allowed')
  }catch(e){const m=String(e instanceof Error?e.message:e);console.error(e);return json({ok:false,error:m},m.includes('oidc')?401:500)}
})
