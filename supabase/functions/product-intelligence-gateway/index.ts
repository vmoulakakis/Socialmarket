import 'jsr:@supabase/functions-js/edge-runtime.d.ts'
import { createRemoteJWKSet, jwtVerify } from 'npm:jose@6.1.0'
import postgres from 'https://deno.land/x/postgresjs@v3.4.5/mod.js'

const sql=postgres(Deno.env.get('SUPABASE_DB_URL')!,{prepare:false})
const ISSUER='https://token.actions.githubusercontent.com'
const AUDIENCE='socialmarket-supabase-worker'
const REPOSITORY_ID='1329707883'
const REPOSITORY='vmoulakakis/Socialmarket'
const ALLOWED=new Set(['vmoulakakis/Socialmarket/.github/workflows/product-intelligence-v1.yml@refs/heads/main'])
const JWKS=createRemoteJWKSet(new URL(`${ISSUER}/.well-known/jwks`))
const DEEPSEEK_KEY=Deno.env.get('DEEPSEEK_API_KEY')||Deno.env.get('DEEP_SEEK_API_KEY')||''
const DEEPSEEK_MODEL=Deno.env.get('DEEPSEEK_MODEL')||'deepseek-v4-pro'
const json=(x:unknown,s=200)=>new Response(JSON.stringify(x),{status:s,headers:{'content-type':'application/json'}})
const clamp=(n:number,a=0,b=100)=>Math.max(a,Math.min(b,n))

async function auth(req:Request){
  const h=req.headers.get('authorization')||''
  if(!h.startsWith('Bearer '))throw new Error('missing_oidc')
  const {payload}=await jwtVerify(h.slice(7),JWKS,{issuer:ISSUER,audience:AUDIENCE})
  if(String(payload.repository_id||'')!==REPOSITORY_ID||String(payload.repository||'')!==REPOSITORY||String(payload.ref||'')!=='refs/heads/main'||!ALLOWED.has(String(payload.workflow_ref||'')))throw new Error('oidc_not_allowed')
  return payload
}

async function context(){
  const programs=await sql`
    with merchant_score as (
      select merchant_id,
             max(solution_whitespace_score) as solution_whitespace_score,
             max(demand_beacon_score) as demand_beacon_score,
             max(demand_score) as demand_score,
             max(case when competition_score>0 then competition_score end) as competition_score,
             max(trust_score) as trust_score,
             max(confidence) as confidence
      from api.merchant_dual_role_scores group by merchant_id
    ), aliases as (
      select merchant_id,array_agg(alias_name order by confidence desc nulls last) as aliases
      from catalog.merchant_aliases group by merchant_id
    )
    select mp.id as merchant_program_id,mp.merchant_id,mp.program_name,mp.raw_commission_pct,mp.raw_flat_commission,
           m.canonical_name,m.normalized_name,m.official_domain,m.primary_category,m.primary_subcategory,
           coalesce(ms.solution_whitespace_score,0) as solution_whitespace_score,
           coalesce(ms.demand_beacon_score,0) as demand_beacon_score,coalesce(ms.demand_score,0) as demand_score,
           coalesce(ms.competition_score,50) as competition_score,coalesce(ms.trust_score,0) as trust_score,
           coalesce(ms.confidence,0) as confidence,coalesce(pol.promotion_mode,'eligible') as promotion_mode,
           coalesce(pol.dominant_market,false) as dominant_market,coalesce(a.aliases,array[]::text[]) as aliases
    from catalog.merchant_programs mp join catalog.merchants m on m.id=mp.merchant_id
    left join merchant_score ms on ms.merchant_id=m.id
    left join catalog.merchant_promotion_policy pol on pol.merchant_id=m.id
    left join aliases a on a.merchant_id=m.id
    where mp.status is distinct from 'inactive'`
  const pains=await sql`
    select id,cluster_type,canonical_text,category,subcategory,evidence_count,source_diversity,demand_score,
           competition_score,pain_severity,commercial_intent,audit_score,confidence
    from evidence.semantic_clusters
    where validation_status='validated' and cluster_type in ('pain','complaint','unmet_need','alternative_request')
    order by coalesce(commercial_intent,0) desc,coalesce(pain_severity,0) desc,coalesce(demand_score,0) desc
    limit 1200`
  const themes=await sql`select id,slug,name,parent_id,theme_type,active_from,peak_date,active_to,semantic_brief,base_demand_score,confidence from intel.demand_themes where status='active' order by parent_id nulls first,name`
  return {programs,pain_clusters:pains,themes}
}

type ThinkingMode='off'|'on'|'auto'

function batchComplexity(payload:any,action:'enrich'|'audit'){
  const items=Array.isArray(payload?.items)?payload.items:[]
  if(!items.length)return 0
  let total=0
  for(const x of items){
    const painCount=Array.isArray(x?.pain_rag)?x.pain_rag.length:0
    const themeCount=Array.isArray(x?.theme_rag)?x.theme_rag.length:0
    const confidence=Number(x?.merchant?.confidence ?? x?.product_evidence_confidence ?? 0)
    const commission=Number(x?.expected_commission_eur ?? x?.product?.expected_commission_eur ?? 0)
    const contradictions=Array.isArray(x?.contradictions)?x.contradictions.length:0
    let score=0.20
    score+=Math.min(0.20,painCount*0.03)
    score+=Math.min(0.10,themeCount*0.02)
    if(confidence>0 && confidence<0.55)score+=0.18
    if(commission>=40)score+=0.10
    if(commission>=75)score+=0.08
    if(contradictions>0)score+=0.20
    if(action==='audit')score+=0.18
    total+=Math.min(1,score)
  }
  return total/items.length
}

function chooseThinking(payload:any,action:'enrich'|'audit',requested:ThinkingMode='auto'){
  if(requested==='on')return {enabled:true,complexity:1,reason:'forced'}
  if(requested==='off')return {enabled:false,complexity:0,reason:'forced_off'}
  const complexity=batchComplexity(payload,action)
  const threshold=action==='audit'?0.58:0.72
  return {enabled:complexity>=threshold,complexity:Number(complexity.toFixed(3)),reason:complexity>=threshold?'complex_case':'standard_case'}
}

async function deepseek(system:string,payload:unknown,action:'enrich'|'audit',requested:ThinkingMode='auto'){
  if(!DEEPSEEK_KEY)throw new Error('deepseek_not_configured')
  const decision=chooseThinking(payload,action,requested)
  const body:any={model:DEEPSEEK_MODEL,temperature:0.1,max_tokens:decision.enabled?5000:2200,response_format:{type:'json_object'},messages:[{role:'system',content:system},{role:'user',content:`Return JSON only. Input:
${JSON.stringify(payload)}`}] }
  if(decision.enabled){body.thinking={type:'enabled'};body.reasoning_effort='high'}
  else{body.thinking={type:'disabled'};body.reasoning_effort='low'}
  const r=await fetch('https://api.deepseek.com/chat/completions',{method:'POST',headers:{'content-type':'application/json','authorization':`Bearer ${DEEPSEEK_KEY}`},body:JSON.stringify(body)})
  const raw=await r.text()
  if(!r.ok)throw new Error(`deepseek_${r.status}:${raw.slice(0,800)}`)
  const j=JSON.parse(raw);const content=j?.choices?.[0]?.message?.content
  if(!content)throw new Error('deepseek_empty_content')
  return {data:JSON.parse(content),thinking:decision}
}

const ENRICH_SYSTEM=`You are SocialMarket Product Research Agent. Analyze only the supplied product facts, merchant context and RAG evidence. Never invent product features, prices, commission, merchant facts, pain evidence or IDs. A product is useful only when it plausibly solves one or more supplied validated pain/unmet-need clusters. Large/dominant merchant offers have already been removed. Produce JSON {"items":[...]}. For every input source_record_hash return: source_record_hash, canonical_title, brand_name, model_name, category, subcategory, human_description (Greek, evidence-grounded, no hype), semantic_text, pain_cluster_ids (ONLY IDs supplied in pain_rag), theme_ids (ONLY IDs supplied in theme_rag), pain_gap_fit_score 0-100, seasonal_theme_score 0-100, product_evidence_confidence 0-100, pain_rationale, theme_rationale, unsupported_claims[]. If evidence is weak, use low scores and empty IDs.`

const AUDIT_SYSTEM=`You are SocialMarket Product Skeptic/Audit Agent. Your job is to try to prove the Product Research Agent wrong. Use only raw product facts, merchant context, supplied RAG evidence and the proposed enrichment. Never invent IDs or facts. Reject products that do not clearly solve a supplied validated pain/unmet need, whose description claims unsupported features, or whose RAG match is merely keyword noise. Commission >= EUR10 and dominant-merchant exclusion were deterministic gates and must not be overridden. Produce JSON {"items":[...]}. For each source_record_hash return verdict exactly validated|needs_review|rejected, pain_cluster_ids ONLY from supplied pain_rag, theme_ids ONLY from supplied theme_rag, pain_scores object keyed by accepted pain IDs, theme_scores object keyed by accepted theme IDs, pain_gap_fit_score 0-100, seasonal_theme_score 0-100, product_evidence_confidence 0-100, identity_score 0-100, source_quality_score 0-100, source_diversity_score 0-100, contradiction_score 0-100 where 100 means no material contradiction, taxonomy_score 0-100, demand_validation_score 0-100, competition_validation_score 0-100, pain_validation_score 0-100, social_validation_score 0-100, overall_score 0-100, pain_rationale, theme_rationale, audit_summary, reasons[], contradictions[]. Use validated only for genuinely evidence-backed solver products.`

async function upsertItem(x:any){
  const merchantId=String(x.merchant_id||''),programId=x.merchant_program_id||null,key=String(x.canonical_key||''),hash=String(x.source_record_hash||'')
  if(!merchantId||!key||!hash||Number(x.expected_commission_eur||0)<10)throw new Error('invalid_product_payload')
  if(String(x.validation_status||'')!=='validated')throw new Error('nonvalidated_product_persistence_rejected')
  if(!Array.isArray(x.pain_matches)||x.pain_matches.length<1)throw new Error('validated_pain_required')
  const policy=await sql`select promotion_mode,dominant_market from catalog.merchant_promotion_policy where merchant_id=${merchantId} limit 1`
  if(policy[0]?.dominant_market||['demand_beacon_only','blocked'].includes(policy[0]?.promotion_mode))throw new Error('dominant_merchant_offer_rejected')
  let pr=await sql`select id from catalog.products where canonical_key=${key} limit 1`
  let productId=pr[0]?.id
  if(!productId){
    pr=await sql`insert into catalog.products(canonical_key,canonical_title,brand_name,model_name,gtin,mpn,category,subcategory,status,semantic_text,metadata) values(${key},${String(x.canonical_title||x.product_name_raw||'Product').slice(0,500)},${x.brand_name||null},${x.model_name||null},${x.gtin||null},${x.mpn||null},${x.category||null},${x.subcategory||null},${x.validation_status==='validated'?'validated':x.validation_status==='rejected'?'rejected':'needs_review'},${x.semantic_text||null},${sql.json({human_description:x.human_description||null,source:'product-intelligence-v1'})}) returning id`;productId=pr[0].id
  }else{
    await sql`update catalog.products set canonical_title=${String(x.canonical_title||x.product_name_raw||'Product').slice(0,500)},brand_name=coalesce(${x.brand_name||null},brand_name),model_name=coalesce(${x.model_name||null},model_name),gtin=coalesce(${x.gtin||null},gtin),mpn=coalesce(${x.mpn||null},mpn),category=coalesce(${x.category||null},category),subcategory=coalesce(${x.subcategory||null},subcategory),status=${x.validation_status==='validated'?'validated':x.validation_status==='rejected'?'rejected':'needs_review'},semantic_text=coalesce(${x.semantic_text||null},semantic_text),metadata=metadata||${sql.json({human_description:x.human_description||null})},updated_at=now() where id=${productId}`
  }
  let orow=await sql`select id from catalog.product_offers where source_feed=${x.source_feed||'linkwise-products.json'} and source_record_hash=${hash} limit 1`
  let offerId=orow[0]?.id
  if(!offerId){
    orow=await sql`insert into catalog.product_offers(product_id,merchant_id,merchant_program_id,source_feed,external_product_id,source_record_hash,program_name_raw,product_name_raw,description_raw,category_raw,effective_price,full_price,discount_pct,currency,commission_rate_pct,flat_commission_eur,expected_commission_eur,commission_rule,commission_confidence,tracking_url,image_url,thumb_url,in_stock,availability,times_bought,valid_from,valid_to,dominant_market_excluded,eligible,eligibility_reason,raw_metadata) values(${productId},${merchantId},${programId},${x.source_feed||'linkwise-products.json'},${x.external_product_id||null},${hash},${x.program_name_raw||null},${x.product_name_raw||null},${x.description_raw||null},${x.category_raw||null},${Number(x.effective_price)},${x.full_price??null},${x.discount_pct??null},${x.currency||'EUR'},${x.commission_rate_pct??null},${x.flat_commission_eur??null},${Number(x.expected_commission_eur)},${x.commission_rule||'unknown'},${Number(x.commission_confidence||0)},${x.tracking_url},${x.image_url||null},${x.thumb_url||null},${x.in_stock??null},${x.availability||null},${x.times_bought??null},${x.valid_from||null},${x.valid_to||null},false,true,'commission>=10 + merchant eligible',${sql.json({enrichment:x.enrichment||{}})}) returning id`;offerId=orow[0].id
  }else{
    await sql`update catalog.product_offers set product_id=${productId},merchant_id=${merchantId},merchant_program_id=${programId},effective_price=${Number(x.effective_price)},full_price=${x.full_price??null},discount_pct=${x.discount_pct??null},commission_rate_pct=${x.commission_rate_pct??null},flat_commission_eur=${x.flat_commission_eur??null},expected_commission_eur=${Number(x.expected_commission_eur)},commission_rule=${x.commission_rule||'unknown'},commission_confidence=${Number(x.commission_confidence||0)},tracking_url=${x.tracking_url},image_url=${x.image_url||null},thumb_url=${x.thumb_url||null},in_stock=${x.in_stock??null},availability=${x.availability||null},times_bought=${x.times_bought??null},valid_from=${x.valid_from||null},valid_to=${x.valid_to||null},eligible=true,eligibility_reason='commission>=10 + merchant eligible',last_seen_at=now(),raw_metadata=raw_metadata||${sql.json({enrichment:x.enrichment||{}})} where id=${offerId}`
  }
  for(const p of (x.pain_matches||[]).slice(0,12)){
    await sql`insert into intel.product_pain_matches(product_id,pain_cluster_id,match_score,evidence_confidence,rationale,metadata) select ${productId},id,${clamp(Number(p.score||0))},${p.confidence??null},${p.rationale||null},${sql.json({audit:x.audit?.verdict||null})} from evidence.semantic_clusters where id=${String(p.id)} and validation_status='validated' on conflict(product_id,pain_cluster_id) do update set match_score=excluded.match_score,evidence_confidence=excluded.evidence_confidence,rationale=excluded.rationale,metadata=intel.product_pain_matches.metadata||excluded.metadata,updated_at=now()`
  }
  for(const t of (x.theme_matches||[]).slice(0,10)){
    await sql`insert into intel.product_theme_matches(product_id,theme_id,relevance_score,seasonal_score,rationale,metadata) select ${productId},id,${clamp(Number(t.relevance_score||0))},${clamp(Number(t.seasonal_score||0))},${t.rationale||null},${sql.json({audit:x.audit?.verdict||null})} from intel.demand_themes where id=${String(t.id)} and status='active' on conflict(product_id,theme_id) do update set relevance_score=excluded.relevance_score,seasonal_score=excluded.seasonal_score,rationale=excluded.rationale,metadata=intel.product_theme_matches.metadata||excluded.metadata,updated_at=now()`
  }
  const s=x.scores||{}
  const snap=await sql`insert into intel.product_intelligence_snapshots(product_id,offer_id,merchant_id,pain_gap_fit_score,merchant_opportunity_score,greek_demand_score,competition_score,seasonal_theme_score,merchant_trust_score,commission_score,discount_score,product_evidence_confidence,dominant_market_penalty,final_opportunity_score,validation_status,audit_summary,evidence_count,metadata) values(${productId},${offerId},${merchantId},${s.pain_gap_fit_score??null},${s.merchant_opportunity_score??null},${s.greek_demand_score??null},${s.competition_score??null},${s.seasonal_theme_score??null},${s.merchant_trust_score??null},${s.commission_score??null},${s.discount_score??null},${s.product_evidence_confidence??null},0,${s.final_opportunity_score??null},${x.validation_status||'needs_review'},${x.audit_summary||null},${Number(x.evidence_count||0)},${sql.json({audit:x.audit||{},enrichment:x.enrichment||{},method:'agentic-rag-v1'})}) returning id`
  const a=x.audit||{}
  await sql`insert into evidence.audit_results(entity_type,entity_id,target_type,target_id,audit_agent,identity_score,source_quality_score,source_diversity_score,contradiction_score,taxonomy_score,demand_validation_score,competition_validation_score,pain_validation_score,social_validation_score,overall_score,verdict,reasons,contradictions,methodology_version,metadata) values('product',${productId},'product_intelligence_snapshot',${snap[0].id},'product-skeptic-v1',${a.identity_score??null},${a.source_quality_score??null},${a.source_diversity_score??null},${a.contradiction_score??null},${a.taxonomy_score??null},${a.demand_validation_score??null},${a.competition_validation_score??null},${a.pain_validation_score??null},${a.social_validation_score??null},${a.overall_score??null},${x.validation_status||'needs_review'},${sql.json(a.reasons||[])},${sql.json(a.contradictions||[])},'product-audit-v1',${sql.json({source_record_hash:hash})})`
  if(x.semantic_text){
    await sql`insert into evidence.semantic_clusters(entity_type,entity_id,cluster_type,canonical_text,category,subcategory,evidence_count,source_diversity,demand_score,competition_score,pain_severity,commercial_intent,audit_score,confidence,validation_status,embedding_status,metadata,updated_at) values('product',${productId},'product_solution',${String(x.semantic_text).slice(0,5000)},${x.category||null},${x.subcategory||null},${Number(x.evidence_count||0)},${Math.min(10,(x.pain_matches||[]).length)},${s.greek_demand_score??null},${s.competition_score??null},${s.pain_gap_fit_score??null},${s.commission_score??null},${a.overall_score??null},${clamp(Number(s.product_evidence_confidence||0))/100},${x.validation_status||'needs_review'},${x.validation_status==='validated'?'pending':'stale'},${sql.json({offer_id:offerId,expected_commission_eur:x.expected_commission_eur,final_opportunity_score:s.final_opportunity_score})},now()) on conflict(entity_type,entity_id,cluster_type,md5(canonical_text)) do update set validation_status=excluded.validation_status,embedding_status=case when excluded.validation_status='validated' and evidence.semantic_clusters.validation_status=excluded.validation_status and evidence.semantic_clusters.embedding_status='ready' then 'ready' else excluded.embedding_status end,metadata=evidence.semantic_clusters.metadata||excluded.metadata,updated_at=now()`
  }
  return {product_id:productId,offer_id:offerId,snapshot_id:snap[0].id}
}

Deno.serve(async(req)=>{
  if(req.method==='GET')return json({ok:true,service:'product-intelligence-gateway',version:'1.2',deepseek_configured:Boolean(DEEPSEEK_KEY),deepseek_model:DEEPSEEK_MODEL})
  if(req.method!=='POST')return json({error:'method_not_allowed'},405)
  try{
    await auth(req);const b=await req.json();const action=String(b.action||'')
    if(action==='health')return json({ok:true,deepseek_configured:Boolean(DEEPSEEK_KEY),deepseek_model:DEEPSEEK_MODEL})
    if(action==='context')return json({ok:true,...await context()})
    if(action==='enrich'){
      const items=(Array.isArray(b.items)?b.items:[]).slice(0,12);const r=await deepseek(ENRICH_SYSTEM,{items},'enrich',String(b.thinking||'auto') as ThinkingMode);const out=r.data;return json({ok:true,thinking:r.thinking,items:Array.isArray(out.items)?out.items:[]})
    }
    if(action==='audit'){
      const items=(Array.isArray(b.items)?b.items:[]).slice(0,12);const r=await deepseek(AUDIT_SYSTEM,{items},'audit',String(b.thinking||'auto') as ThinkingMode);const out=r.data;return json({ok:true,thinking:r.thinking,items:Array.isArray(out.items)?out.items:[]})
    }
    if(action==='save_batch'){
      const items=(Array.isArray(b.items)?b.items:[]).slice(0,40);let saved=0;const ids=[]
      for(const x of items){const r=await upsertItem(x);saved++;ids.push(r)}
      return json({ok:true,saved,ids})
    }
    throw new Error('action_not_allowed')
  }catch(e){console.error(e);return json({error:String(e instanceof Error?e.message:e)},401)}
})
