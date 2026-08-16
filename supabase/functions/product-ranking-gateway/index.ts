import 'jsr:@supabase/functions-js/edge-runtime.d.ts'
import { createRemoteJWKSet, jwtVerify } from 'npm:jose@6.1.0'
import postgres from 'https://deno.land/x/postgresjs@v3.4.5/mod.js'

const sql=postgres(Deno.env.get('SUPABASE_DB_URL')!,{prepare:false,max:1})
const ISSUER='https://token.actions.githubusercontent.com'
const AUDIENCE='socialmarket-supabase-worker'
const REPOSITORY_ID='1329707883'
const REPOSITORY='vmoulakakis/Socialmarket'
const ALLOWED=new Set(['vmoulakakis/Socialmarket/.github/workflows/product-intelligence-v1.yml@refs/heads/main'])
const JWKS=createRemoteJWKSet(new URL(`${ISSUER}/.well-known/jwks`))
const DEEPSEEK_KEY=Deno.env.get('DEEPSEEK_API_KEY')||Deno.env.get('DEEP_SEEK_API_KEY')||''
const DEEPSEEK_MODEL=Deno.env.get('DEEPSEEK_MODEL')||'deepseek-v4-pro'
const json=(x:unknown,s=200)=>new Response(JSON.stringify(x),{status:s,headers:{'content-type':'application/json','cache-control':'no-store'}})
const clamp=(n:number,a=0,b=100)=>Math.max(a,Math.min(b,Number.isFinite(n)?n:0))

async function auth(req:Request){
  const h=req.headers.get('authorization')||''
  if(!h.startsWith('Bearer '))throw new Error('missing_oidc')
  const {payload}=await jwtVerify(h.slice(7),JWKS,{issuer:ISSUER,audience:AUDIENCE})
  if(String(payload.repository_id||'')!==REPOSITORY_ID||String(payload.repository||'')!==REPOSITORY||String(payload.ref||'')!=='refs/heads/main'||!ALLOWED.has(String(payload.workflow_ref||'')))throw new Error('oidc_not_allowed')
  return payload
}

type ThinkingMode='off'|'on'|'auto'
type AIAction='rank'|'audit'|'seo'
function complexity(payload:any,action:AIAction){
  const items=Array.isArray(payload?.items)?payload.items:[]
  if(!items.length)return 0
  let total=0
  for(const x of items){
    const pains=Array.isArray(x?.pain_rag)?x.pain_rag.length:0
    const themes=Array.isArray(x?.theme_rag)?x.theme_rag.length:0
    const confidence=Number(x?.merchant?.confidence||0)
    const commission=Number(x?.product?.expected_commission_eur||0)
    const deep=Number(x?.deep_demand_context?.score||0)
    let c=.18+Math.min(.18,pains*.025)+Math.min(.10,themes*.02)
    if(confidence>0&&confidence<.55)c+=.15
    if(commission>=40)c+=.10
    if(deep>=70)c+=.08
    if(action==='audit')c+=.20
    if(action==='seo')c=.15
    total+=Math.min(1,c)
  }
  return total/items.length
}
function chooseThinking(payload:any,action:AIAction,requested:ThinkingMode='auto'){
  if(requested==='on')return {enabled:true,complexity:1,reason:'forced'}
  if(requested==='off')return {enabled:false,complexity:0,reason:'forced_off'}
  const c=complexity(payload,action),threshold=action==='audit'?.55:action==='seo'?.95:.68
  return {enabled:c>=threshold,complexity:Number(c.toFixed(3)),reason:c>=threshold?'complex_case':'standard_case'}
}

async function deepseek(system:string,payload:any,action:AIAction,requested:ThinkingMode='auto'){
  if(!DEEPSEEK_KEY)throw new Error('deepseek_not_configured')
  const decision=chooseThinking(payload,action,requested)
  const call=async(maxTokens:number,retry=false)=>{
    const body:any={model:DEEPSEEK_MODEL,temperature:action==='seo'?.16:.08,max_tokens:maxTokens,response_format:{type:'json_object'},messages:[
      {role:'system',content:system},
      {role:'user',content:`Return one complete JSON object only. ${retry?'Previous JSON was incomplete; be concise. ':''}Input:\n${JSON.stringify(payload)}`}
    ]}
    if(decision.enabled){body.thinking={type:'enabled'};body.reasoning_effort='high'}else{body.thinking={type:'disabled'};body.reasoning_effort='low'}
    const r=await fetch('https://api.deepseek.com/chat/completions',{method:'POST',headers:{'content-type':'application/json','authorization':`Bearer ${DEEPSEEK_KEY}`},body:JSON.stringify(body)})
    const raw=await r.text();if(!r.ok)throw new Error(`deepseek_${r.status}:${raw.slice(0,600)}`)
    const j=JSON.parse(raw),choice=j?.choices?.[0]||{},content=String(choice?.message?.content||'')
    if(!content.trim()||choice?.finish_reason==='length')throw new Error(`incomplete_ai_response:${choice?.finish_reason||'empty'}`)
    return JSON.parse(content)
  }
  const normal=action==='seo'?6200:(decision.enabled?5200:3200),retryTokens=action==='seo'?8200:(decision.enabled?6800:4700)
  try{return {data:await call(normal,false),thinking:{...decision,retry:false}}}
  catch(first){return {data:await call(retryTokens,true),thinking:{...decision,retry:true,first_error:String(first).slice(0,160)}}}
}

const RANK_SYSTEM=`You are SocialMarket Product Ranking Strategist for the Greek affiliate market. Identify which supplied products deserve promotion now. This is RANKING, not validation. Use only supplied product facts, merchant intelligence, deterministic metrics, optional pain RAG, seasonal themes, Deep Demand context and observed NETWORK PROGRAM KPI baselines. Network conversion/EPC/approval are program-level evidence, never claim they are product-level observed sales. Deep Demand fields are DERIVED/MODELED context: never rewrite them as observed sales, search volume or causal truth. If temporal_decision says WITHHOLD_PRODUCTION_FORECAST, do not make a trend prediction from the temporal model. Missing pain evidence must NEVER automatically reject a product; it simply removes that supporting signal. Missing competition is UNKNOWN and must not be treated as low competition. Never invent demand, sales, reviews, features, commission, price or market share. Evaluate product-market fit, value proposition, conversion environment, creative/content potential, timing, purchase friction and channel fit. Produce JSON {"items":[...]}. For every input source_record_hash return: source_record_hash, category, subcategory, product_market_fit_score 0-100, creative_potential_score 0-100, value_score 0-100, confidence_score 0-100, promotion_angle in Greek, promotion_reason in Greek, audience in Greek, recommended_channels[] chosen from Facebook|Instagram|TikTok|YouTube|Search|Blog, risk_flags[], rationale in Greek. Prefer specific evidence-grounded promotion angles over hype.`

const RANK_AUDIT_SYSTEM=`You are the independent SocialMarket Ranking Skeptic. Challenge a proposed promotion ranking without turning missing pain evidence into rejection. Use only supplied facts and clearly distinguish observed from derived/model outputs. Look for wrong merchant/product interpretation, weak value, high competition, low demand support, over-read Deep Demand/forecast signals, misleading interpretation of program-level network KPIs, poor creative suitability, excessive purchase friction, suspicious pricing, weak confidence, or unsupported AI claims. Return JSON {"items":[...]}. For every source_record_hash return: source_record_hash, risk_score 0-100 where 100 is highest promotion risk, confidence_adjustment between -30 and 10, risk_flags[], reasons[], audit_summary in Greek. Do not change deterministic price or commission. Do not invent facts. The output is a risk adjustment for ranking, not a VALIDATED/REJECTED gate.`

const SEO_SYSTEM=`You are SocialMarket SEO Product Editor for Greece. Rewrite only the supplied product facts into concise, high-intent Greek SEO content for an affiliate product page. Never invent specifications, compatibility, benefits, certifications, reviews, guarantees, availability, prices, discounts or performance claims that are not explicitly present in the input. Program/network KPI baselines and modeled economics are internal analytics and MUST NOT appear in consumer-facing copy. Preserve brand/model spelling. Prefer natural Greek commercial search language, clear problem-solution framing and specific known attributes. Avoid keyword stuffing and hype. Return JSON {"items":[...]}. For every input source_record_hash return exactly: source_record_hash, title (max 65 chars), meta_description (max 160 chars), short_description (1-2 sentences), description (80-140 Greek words), keywords (8-16 distinct search phrases), search_intent (one concise Greek phrase), slug (lowercase latin/ascii words separated by hyphens), feature_bullets (3-6 bullets using only supplied facts). If source facts are sparse, write less rather than inventing.`

async function decisionContext(){
  const markets=await sql`
    with latest as (
      select distinct on (taxonomy_id) taxonomy_id,status,generated_at,analysis
      from intel.demand_model_lab_runs where geography='GR' order by taxonomy_id,generated_at desc
    )
    select m.taxonomy_id,m.category_name,m.subcategory_name,m.taxonomy_name,m.demand_score,m.competition_score,m.pain_gap_score,m.opportunity_score,m.confidence,m.observed_at,
           l.status as model_status,l.generated_at as model_generated_at,l.analysis->'market_structure'->'fuzzy'->'whitespace' as whitespace,
           l.analysis->'market_structure'->'fuzzy'->'state' as fuzzy_state,l.analysis->'temporal_lab'->>'decision' as temporal_decision,
           l.analysis->'temporal_lab'->'gate' as temporal_gate,l.analysis->'graph_rag'->'summary' as graph_summary,l.analysis->'causal_skeptic'->'readiness' as causal_readiness
    from api.semantic_category_market_v2 m left join latest l on l.taxonomy_id=m.taxonomy_id where m.taxonomy_id is not null
  `
  const merchants=await sql`select id as merchant_id,primary_category,primary_subcategory from catalog.merchants where status is distinct from 'inactive'`
  const programKpis=await sql`
    select distinct on (program_id) program_id,conversion_rate,epc,approval_rate,approval_days,commercial_score,data_confidence,rank_score,observed_at
    from intel.program_commercial_snapshots order by program_id,observed_at desc
  `
  const firstParty30d=await sql`
    select program_id,sum(impressions)::bigint impressions,sum(views)::bigint views,sum(sessions)::bigint sessions,sum(outbound_clicks)::bigint outbound_clicks,
      sum(conversions_approved)::bigint conversions_approved,sum(commission_approved_eur)::numeric commission_approved_eur,
      sum(media_spend_eur)::numeric media_spend_eur,sum(content_cost_eur)::numeric content_cost_eur,max(metric_date) latest_metric_date
    from ops.affiliate_performance_daily where metric_date>=current_date-29 and program_id is not null group by program_id
  `
  return {markets,merchants,program_kpis:programKpis,first_party_30d:firstParty30d,semantics:{deep_demand:'derived_context_not_observed_sales',temporal:'shadow_or_withheld_unless_explicitly_promoted',causal:'never_assumed',network_kpis:'observed_program_baseline_not_product_sales',first_party:'observed_only_when_rows_exist',missing:'no_bonus'}}
}

async function startRun(b:any){
  const key=String(b.run_key||'').slice(0,160);if(!key)throw new Error('run_key_required')
  const rows=await sql`insert into intel.product_ranking_runs(run_key,engine_version,status,metadata) values(${key},${String(b.engine_version||'ranking_v3')},'running',${sql.json(b.metadata||{})}) on conflict(run_key) do update set engine_version=excluded.engine_version,status='running',started_at=now(),completed_at=null,metadata=intel.product_ranking_runs.metadata||excluded.metadata returning id`
  return rows[0]
}

async function saveRankings(runId:string,items:any[]){
  let saved=0
  for(const x of items.slice(0,40)){
    const merchantId=String(x.merchant_id||''),hash=String(x.source_record_hash||''),key=String(x.canonical_key||'')
    if(!merchantId||!hash||!key)continue
    await sql`insert into intel.product_rankings(
      run_id,source_record_hash,canonical_key,external_product_id,merchant_id,merchant_program_id,merchant_name,product_name,brand_name,model_name,category,subcategory,
      effective_price,full_price,discount_pct,expected_commission_eur,tracking_url,image_url,in_stock,times_bought,merchant_demand_score,competition_score,merchant_whitespace_score,merchant_trust_score,
      pain_signal_score,seasonal_score,commercial_score,network_performance_score,purchase_signal_score,deep_demand_score,deep_demand_status,deep_demand_context,ai_product_fit_score,ai_creative_score,ai_value_score,ai_confidence,ai_risk_score,rank_score,rank_band,
      promotion_angle,promotion_reason,audience,recommended_channels,risk_flags,product_attributes,kpi_snapshot,seo_content,seo_generated_at,evidence_summary,ai_summary
    ) values(
      ${runId}::uuid,${hash},${key},${x.external_product_id||null},${merchantId}::uuid,${x.merchant_program_id||null},${String(x.merchant_name||'Unknown').slice(0,500)},${String(x.product_name||'Product').slice(0,800)},${x.brand_name||null},${x.model_name||null},${x.category||null},${x.subcategory||null},
      ${x.effective_price??null},${x.full_price??null},${x.discount_pct??null},${x.expected_commission_eur??null},${x.tracking_url||null},${x.image_url||null},${x.in_stock??null},${x.times_bought??null},${x.merchant_demand_score??null},${x.competition_score??null},${x.merchant_whitespace_score??null},${x.merchant_trust_score??null},
      ${x.pain_signal_score??null},${x.seasonal_score??null},${x.commercial_score??null},${x.network_performance_score??null},${x.purchase_signal_score??null},${x.deep_demand_score??null},${x.deep_demand_status||null},${sql.json(x.deep_demand_context||{})},${x.ai_product_fit_score??null},${x.ai_creative_score??null},${x.ai_value_score??null},${x.ai_confidence??null},${x.ai_risk_score??null},${clamp(Number(x.rank_score||0))},${String(x.rank_band||'WATCHLIST')},
      ${x.promotion_angle||null},${x.promotion_reason||null},${x.audience||null},${sql.json(Array.isArray(x.recommended_channels)?x.recommended_channels:[])},${sql.json(Array.isArray(x.risk_flags)?x.risk_flags:[])},${sql.json(x.product_attributes||{})},${sql.json(x.kpi_snapshot||{})},${sql.json(x.seo_content||{})},${x.seo_generated_at||null},${sql.json(x.evidence_summary||{})},${x.ai_summary||null}
    ) on conflict(run_id,source_record_hash) do update set rank_score=excluded.rank_score,rank_band=excluded.rank_band,deep_demand_score=excluded.deep_demand_score,deep_demand_status=excluded.deep_demand_status,deep_demand_context=excluded.deep_demand_context,network_performance_score=excluded.network_performance_score,ai_product_fit_score=excluded.ai_product_fit_score,ai_creative_score=excluded.ai_creative_score,ai_value_score=excluded.ai_value_score,ai_confidence=excluded.ai_confidence,ai_risk_score=excluded.ai_risk_score,promotion_angle=excluded.promotion_angle,promotion_reason=excluded.promotion_reason,audience=excluded.audience,recommended_channels=excluded.recommended_channels,risk_flags=excluded.risk_flags,product_attributes=excluded.product_attributes,kpi_snapshot=excluded.kpi_snapshot,seo_content=excluded.seo_content,seo_generated_at=excluded.seo_generated_at,evidence_summary=excluded.evidence_summary,ai_summary=excluded.ai_summary,ranked_at=now()`
    saved++
  }
  return saved
}

async function completeRun(b:any){
  const rows=await sql`update intel.product_ranking_runs set status='completed',completed_at=now(),records_seen=${Number(b.records_seen||0)},eligible_candidates=${Number(b.eligible_candidates||0)},ai_ranked=${Number(b.ai_ranked||0)},saved_count=${Number(b.saved_count||0)},metadata=metadata||${sql.json(b.metadata||{})} where id=${String(b.run_id)}::uuid returning id`
  if(!rows[0])throw new Error('ranking_run_not_found')
}

Deno.serve(async req=>{
  if(req.method==='GET')return json({ok:true,service:'product-ranking-gateway',version:'3.3',deepseek_configured:Boolean(DEEPSEEK_KEY),deepseek_model:DEEPSEEK_MODEL})
  if(req.method!=='POST')return json({error:'method_not_allowed'},405)
  try{
    await auth(req);const b=await req.json(),action=String(b.action||'')
    if(action==='health')return json({ok:true,version:'3.3',deepseek_configured:Boolean(DEEPSEEK_KEY),deepseek_model:DEEPSEEK_MODEL})
    if(action==='decision_context')return json({ok:true,...await decisionContext()})
    if(action==='rank'){
      const items=(Array.isArray(b.items)?b.items:[]).slice(0,10),r=await deepseek(RANK_SYSTEM,{items},'rank',String(b.thinking||'auto') as ThinkingMode)
      return json({ok:true,thinking:r.thinking,items:Array.isArray(r.data?.items)?r.data.items:[]})
    }
    if(action==='rank_audit'){
      const items=(Array.isArray(b.items)?b.items:[]).slice(0,10),r=await deepseek(RANK_AUDIT_SYSTEM,{items},'audit',String(b.thinking||'auto') as ThinkingMode)
      return json({ok:true,thinking:r.thinking,items:Array.isArray(r.data?.items)?r.data.items:[]})
    }
    if(action==='seo_enrich'){
      const items=(Array.isArray(b.items)?b.items:[]).slice(0,10),r=await deepseek(SEO_SYSTEM,{items},'seo',String(b.thinking||'off') as ThinkingMode)
      return json({ok:true,thinking:r.thinking,items:Array.isArray(r.data?.items)?r.data.items:[]})
    }
    if(action==='ranking_start'){const r=await startRun(b);return json({ok:true,run_id:r.id})}
    if(action==='save_rankings'){const saved=await saveRankings(String(b.run_id||''),Array.isArray(b.items)?b.items:[]);return json({ok:true,saved})}
    if(action==='ranking_complete'){await completeRun(b);return json({ok:true})}
    throw new Error('action_not_allowed')
  }catch(e){const message=String(e instanceof Error?e.message:e);console.error(e);return json({error:message},message.includes('oidc')?401:500)}
})
