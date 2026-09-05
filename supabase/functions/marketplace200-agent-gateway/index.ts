import 'jsr:@supabase/functions-js/edge-runtime.d.ts'
import {createRemoteJWKSet,jwtVerify} from 'npm:jose@6.1.0'
import postgres from 'https://deno.land/x/postgresjs@v3.4.5/mod.js'

const sql=postgres(Deno.env.get('SUPABASE_DB_URL')!,{prepare:false,max:1})
const ISSUER='https://token.actions.githubusercontent.com'
const AUDIENCE='socialmarket-supabase-worker'
const REPOSITORY_ID='1329707883'
const REPOSITORY='vmoulakakis/Socialmarket'
const ALLOWED=new Set(['vmoulakakis/Socialmarket/.github/workflows/semantic-marketplace-200.yml@refs/heads/main'])
const JWKS=createRemoteJWKSet(new URL(`${ISSUER}/.well-known/jwks`))
const DEEPSEEK_KEY=Deno.env.get('DEEPSEEK_API_KEY')||Deno.env.get('DEEP_SEEK_API_KEY')||''
const DEEPSEEK_MODEL=Deno.env.get('DEEPSEEK_MODEL')||'deepseek-v4-pro'
const BRAND_SLUG='lyseis-pou-axizoun'
const json=(x:unknown,s=200)=>new Response(JSON.stringify(x),{status:s,headers:{'content-type':'application/json','cache-control':'no-store'}})
const arr=(v:any)=>Array.isArray(v)?v:[]
const n=(v:any)=>{const x=Number(v);return Number.isFinite(x)?x:0}
const clamp=(v:any)=>Math.max(0,Math.min(100,n(v)))
const text=(v:any,max=1800)=>String(v||'').replace(/[\u0000-\u001f]+/g,' ').trim().slice(0,max)

async function auth(req:Request){
  const h=req.headers.get('authorization')||''
  if(!h.startsWith('Bearer '))throw new Error('missing_oidc')
  const {payload}=await jwtVerify(h.slice(7),JWKS,{issuer:ISSUER,audience:AUDIENCE})
  if(String(payload.repository_id||'')!==REPOSITORY_ID||String(payload.repository||'')!==REPOSITORY||String(payload.ref||'')!=='refs/heads/main'||!ALLOWED.has(String(payload.workflow_ref||'')))throw new Error('oidc_not_allowed')
}

async function structured(system:string,payload:any,maxTokens=6500){
  if(!DEEPSEEK_KEY)throw new Error('deepseek_not_configured')
  const call=async(retry:boolean)=>{
    const body:any={model:DEEPSEEK_MODEL,temperature:0.08,max_tokens:retry?Math.min(8000,maxTokens+1200):maxTokens,response_format:{type:'json_object'},messages:[
      {role:'system',content:system},
      {role:'user',content:`Return one complete JSON object only. ${retry?'Previous structured response failed; be shorter and never truncate strings. ':''}Input:\n${JSON.stringify(payload)}`}
    ],thinking:{type:'enabled'},reasoning_effort:'high'}
    const r=await fetch('https://api.deepseek.com/chat/completions',{method:'POST',headers:{'content-type':'application/json','authorization':`Bearer ${DEEPSEEK_KEY}`},body:JSON.stringify(body)})
    const raw=await r.text();if(!r.ok)throw new Error(`deepseek_${r.status}:${raw.slice(0,600)}`)
    const j=JSON.parse(raw),choice=j?.choices?.[0]||{},content=String(choice?.message?.content||'')
    if(!content.trim())throw new Error('deepseek_empty')
    if(['length','insufficient_system_resource'].includes(String(choice?.finish_reason||'')))throw new Error(`deepseek_incomplete:${choice.finish_reason}`)
    return JSON.parse(content)
  }
  try{return await call(false)}catch(first){try{return await call(true)}catch(second){throw new Error(`structured_output_failed:${String(first).slice(0,180)}|retry:${String(second).slice(0,220)}`)}}
}

async function context(){
  const config=(await sql`select config from ops.marketplace200_config where config_key='production' limit 1`)[0]?.config||{}
  const programs=await sql`
    with aliases as (
      select merchant_id,array_agg(alias_name order by confidence desc nulls last) aliases from catalog.merchant_aliases group by merchant_id
    )
    select mp.id merchant_program_id,mp.merchant_id,mp.program_name,mp.raw_commission_pct,mp.raw_flat_commission,
      m.canonical_name,m.official_domain,m.primary_category,m.primary_subcategory,
      mr.global_rank,mr.trust_score,mr.research_confidence,mr.overall_opportunity_score,mr.risk_flag,
      coalesce(a.aliases,array[]::text[]) aliases
    from catalog.merchant_programs mp
    join catalog.merchants m on m.id=mp.merchant_id
    join api.merchant_rankings mr on mr.merchant_id=m.id and (mr.program_id=mp.id or mr.program_id is null)
    left join aliases a on a.merchant_id=m.id
    where mp.status is distinct from 'inactive'
      and coalesce(mr.trust_score,0)>=65
      and coalesce(mr.research_confidence,0)>=0.55
      and coalesce(mr.global_rank,9999)<=100
      and coalesce(mr.risk_flag,false)=false
    order by mr.global_rank asc,mr.trust_score desc`
  const pains=await sql`
    select id,cluster_type,canonical_text,category,subcategory,evidence_count,source_diversity,demand_score,competition_score,pain_severity,commercial_intent,audit_score,confidence
    from evidence.semantic_clusters
    where validation_status='validated' and cluster_type in ('pain','complaint','unmet_need','alternative_request')
    order by coalesce(commercial_intent,0) desc,coalesce(pain_severity,0) desc,coalesce(demand_score,0) desc limit 450`
  const markets=await sql`select category_name,subcategory_name,demand_score,competition_score,pain_gap_score,opportunity_score,confidence,observed_at from api.semantic_category_market_v2 order by confidence desc,opportunity_score desc limit 180`
  const published=await sql`select source_record_hash from public.socialmarket_top100_publication_state_v where published=true or passed_to_socialscheduler=true`
  const feedback=await sql`
    select i.metadata->>'top100_category' category,count(*) deliveries,
      coalesce(sum(case when m.metric->>'type'='clicks' then nullif(m.metric->>'value','')::numeric else 0 end),0) clicks,
      coalesce(sum(case when m.metric->>'type' in ('views','impressions','reach') then nullif(m.metric->>'value','')::numeric else 0 end),0) exposure,
      coalesce(sum(case when m.metric->>'type' in ('reactions','comments','shares','saves') then nullif(m.metric->>'value','')::numeric else 0 end),0) engagement
    from content.items i left join publish.delivery_history h on h.content_item_id=i.id
    left join lateral jsonb_array_elements(coalesce(h.buffer_metrics,'[]'::jsonb)) m(metric) on true
    where i.created_at>=now()-interval '90 days'
    group by i.metadata->>'top100_category' order by deliveries desc limit 60`
  return {config,programs,pains,markets,feedback,published_source_hashes:published.map((x:any)=>String(x.source_record_hash))}
}

const PLAN_SYSTEM=`You are AFFINITY Opportunity Cartographer for Greece. You do NOT select products. Build evidence-grounded semantic opportunity maps from supplied validated pain clusters, market snapshots, strict merchant universe and observed social feedback. Separate demand from scarcity and engagement from purchase intent. Never invent search volume, sales, market share or facts. Return JSON with linkwise_clusters exactly 10 and aliexpress_clusters exactly 10. Each cluster: cluster_key (stable short slug), niche, subniche, job_to_be_done in Greek, pain_statement in Greek, gap_statement in Greek, demand_score 0-100, whitespace_score 0-100, commercial_intent_score 0-100, confidence 0-100, evidence_ids[] only from supplied pain IDs, rationale in Greek, search_queries[] 3-6 concise English/Greek product-discovery phrases. Linkwise clusters must be broad enough to contain 10 distinct products from high-quality merchants. AliExpress clusters should favor demonstrable, useful products likely to have Greek whitespace, not novelty for novelty's sake.`

async function plan(){const c=await context();const result=await structured(PLAN_SYSTEM,{market:'GR',pain_clusters:c.pains,market_context:c.markets,eligible_merchants:c.programs.map((x:any)=>({merchant_id:x.merchant_id,merchant:x.canonical_name,category:x.primary_category,subcategory:x.primary_subcategory,rank:x.global_rank,trust:x.trust_score,confidence:x.research_confidence})),feedback:c.feedback,policy:c.config},7600);return {plan:result,context_summary:{eligible_merchant_programs:c.programs.length,pain_clusters:c.pains.length,markets:c.markets.length}}}

const RESEARCH_SYSTEM=`You are AFFINITY Product Research Agent. Evaluate only supplied facts and evidence for a Greek buyer. Hard commercial gates were deterministic and cannot be weakened. Analyze semantic fit to the supplied opportunity cluster, demand plausibility, pain intensity, Greek whitespace, product identity/documentation, merchant or seller quality, logistics evidence, price/value, social demonstrability, organic and ads potential. For AliExpress inspect the supplied multi-surface Greek market evidence and distinguish exact/OEM evidence from possible functional alternatives. Do not invent reviews, orders, warranty, shipping, features, certification, market size, search volume or conversion. Return JSON {items:[...]}. Each item must return source_record_hash, demand_score, pain_score, whitespace_score, scarcity_score, semantic_fit_score, product_quality_score, organic_score, ads_score, viral_score, affinity_score, greek_availability_assessment exactly ABSENT|VERY_RARE|AVAILABLE|FUNCTIONAL_EQUIVALENT_EXISTS|UNKNOWN, job_to_be_done, pain_statement, gap_statement, solution_statement, semantic_tags[] 4-10, audience, hook, caption in Greek, hashtags[] 5-9, research_reason, quality_evidence[], quality_unknowns[], landing_candidate boolean. Product quality score measures evidence strength, not physical certification.`
const SKEPTIC_SYSTEM=`You are AFFINITY Skeptic and Quality Assurance Agent. Your job is to try to reject each candidate. Use only supplied product facts, Greek evidence, merchant/seller evidence, opportunity cluster and Research Agent output. Look for unsupported claims, weak identity, weak quality evidence, hidden Greek exact/OEM/functional equivalents, low merchant/seller quality, misleading novelty, duplicate/variant pollution, logistics uncertainty, safety/regulatory issues, weak pain fit and contradictions. Hard gates cannot be overridden. Return JSON {items:[...]}. For each source_record_hash return verdict exactly validated|needs_review|rejected, corrected_greek_availability exactly ABSENT|VERY_RARE|AVAILABLE|FUNCTIONAL_EQUIVALENT_EXISTS|UNKNOWN, product_quality_score 0-100, contradiction_score 0-100 where 100 means no material contradiction, reasons[], blockers[], required_rechecks[]. Only use validated when the candidate is commercially responsible and evidence-backed.`

async function evaluate(items:any[]){
  if(items.length<1||items.length>8)throw new Error('evaluate_batch_must_be_1_to_8')
  const research=await structured(RESEARCH_SYSTEM,{market:'GR',items},6600)
  const skeptic=await structured(SKEPTIC_SYSTEM,{market:'GR',items,research:arr(research?.items)},6000)
  const rm=new Map(arr(research?.items).map((x:any)=>[String(x.source_record_hash),x]))
  const sm=new Map(arr(skeptic?.items).map((x:any)=>[String(x.source_record_hash),x]))
  return items.map((raw:any)=>{const key=String(raw.source_record_hash),r:any=rm.get(key)||{},s:any=sm.get(key)||{};const availability=String(s.corrected_greek_availability||r.greek_availability_assessment||raw.greek_availability||'UNKNOWN');const quality=Math.min(clamp(r.product_quality_score),clamp(s.product_quality_score));const verdict=String(s.verdict||'needs_review');const selected=verdict==='validated'&&quality>=75&&clamp(r.affinity_score)>=76&&(raw.portfolio!=='aliexpress'||['ABSENT','VERY_RARE'].includes(availability));return {...raw,...r,greek_availability:availability,product_quality_score:quality,skeptic_verdict:verdict,quality_decision:selected?'SELECTED':verdict==='rejected'?'REJECTED':'HOLD',skeptic_reasons:arr(s.reasons),skeptic_blockers:arr(s.blockers),required_rechecks:arr(s.required_rechecks),contradiction_score:clamp(s.contradiction_score)}})
}

async function persist(body:any){
  const items=arr(body.items).filter((x:any)=>String(x.quality_decision)==='SELECTED')
  const clusters=arr(body.clusters)
  const link=items.filter((x:any)=>x.portfolio==='linkwise'),ali=items.filter((x:any)=>x.portfolio==='aliexpress')
  if(link.length>100||ali.length>100||items.length>200)throw new Error('portfolio_size_violation')
  const merchantCounts=new Map<string,number>(),sellerCounts=new Map<string,number>()
  for(const x of items){
    if(n(x.expected_commission_eur)<=30)throw new Error('commission_floor_violation')
    if(clamp(x.product_quality_score)<75||clamp(x.affinity_score)<76||String(x.skeptic_verdict)!=='validated')throw new Error('quality_gate_violation')
    if(!text(x.tracking_url)||!text(x.image_url))throw new Error('tracking_or_image_missing')
    if(x.portfolio==='linkwise'){
      if(n(x.merchant_trust_score)<65||n(x.merchant_research_confidence)<0.55||n(x.merchant_global_rank)>100||x.merchant_risk_flag===true)throw new Error('merchant_gate_violation')
      const key=String(x.merchant_id||x.merchant_name||'');merchantCounts.set(key,(merchantCounts.get(key)||0)+1);if((merchantCounts.get(key)||0)>3)throw new Error(`merchant_cap_violation:${key}`)
    }else{
      if(!['ABSENT','VERY_RARE'].includes(String(x.greek_availability)))throw new Error('aliexpress_greek_exclusive_gate_violation')
      const key=String(x.merchant_name||x.seller_name||'unknown');sellerCounts.set(key,(sellerCounts.get(key)||0)+1);if((sellerCounts.get(key)||0)>3)throw new Error(`seller_cap_violation:${key}`)
    }
  }
  const run=(await sql`insert into intel.marketplace200_runs(run_date,status,source_counts,eligible_counts,selected_counts,semantic_cluster_count,model,metadata,completed_at)
    values(current_date,'completed',${sql.json(body.source_counts||{})},${sql.json(body.eligible_counts||{})},${sql.json({linkwise:link.length,aliexpress:ali.length,total:items.length})},${clusters.length},${DEEPSEEK_MODEL},${sql.json(body.metadata||{})},now()) returning id`)[0]
  for(const c of clusters){await sql`insert into intel.marketplace200_semantic_clusters(run_id,cluster_key,portfolio,cluster_rank,niche,subniche,job_to_be_done,pain_statement,gap_statement,demand_score,whitespace_score,commercial_intent_score,confidence,evidence,selected) values(${run.id}::uuid,${text(c.cluster_key,180)},${c.portfolio},${n(c.cluster_rank)},${text(c.niche,300)},${text(c.subniche,300)||null},${text(c.job_to_be_done,900)},${text(c.pain_statement,1200)},${text(c.gap_statement,1200)},${clamp(c.demand_score)},${clamp(c.whitespace_score)},${clamp(c.commercial_intent_score)},${clamp(c.confidence)},${sql.json(c.evidence||{})},true)`}
  for(const x of items){await sql`insert into intel.marketplace200_items(run_id,portfolio,source_record_hash,source_product_id,source_network,semantic_cluster_key,niche,subniche,job_to_be_done,pain_statement,gap_statement,solution_statement,merchant_id,merchant_name,merchant_global_rank,merchant_trust_score,merchant_research_confidence,seller_quality_score,product_name,brand_name,image_url,tracking_url,detail_url,sale_price_eur,expected_commission_eur,demand_score,pain_score,whitespace_score,scarcity_score,semantic_fit_score,product_quality_score,organic_score,ads_score,viral_score,affinity_score,greek_availability,quality_decision,skeptic_verdict,evidence_summary,semantic_tags,social_copy,landing_candidate)
      values(${run.id}::uuid,${x.portfolio},${text(x.source_record_hash,260)},${text(x.source_product_id,260)||null},${text(x.source_network,80)},${text(x.semantic_cluster_key,180)},${text(x.niche,300)},${text(x.subniche,300)||null},${text(x.job_to_be_done,900)},${text(x.pain_statement,1200)},${text(x.gap_statement,1200)},${text(x.solution_statement,1200)},${x.merchant_id||null},${text(x.merchant_name,400)||null},${x.merchant_global_rank??null},${x.merchant_trust_score??null},${x.merchant_research_confidence??null},${x.seller_quality_score??null},${text(x.product_name,900)},${text(x.brand_name,300)||null},${text(x.image_url,2500)},${text(x.tracking_url,4500)},${text(x.detail_url,4500)||null},${n(x.sale_price_eur)},${n(x.expected_commission_eur)},${clamp(x.demand_score)},${clamp(x.pain_score)},${clamp(x.whitespace_score)},${clamp(x.scarcity_score)},${clamp(x.semantic_fit_score)},${clamp(x.product_quality_score)},${clamp(x.organic_score)},${clamp(x.ads_score)},${clamp(x.viral_score)},${clamp(x.affinity_score)},${x.greek_availability||null},'SELECTED','validated',${sql.json(x.evidence_summary||{})},${sql.json(arr(x.semantic_tags).slice(0,14))},${sql.json({audience:x.audience||'',hook:x.hook||'',caption:x.caption||'',hashtags:arr(x.hashtags).slice(0,12),research_reason:x.research_reason||'',skeptic_reasons:arr(x.skeptic_reasons),quality_unknowns:arr(x.quality_unknowns)})},${Boolean(x.landing_candidate)})`}
  return {run_id:String(run.id),selected_counts:{linkwise:link.length,aliexpress:ali.length,total:items.length},merchant_max:Math.max(0,...merchantCounts.values()),seller_max:Math.max(0,...sellerCounts.values())}
}

async function handoff(runId:string,limit:number){
  const brand=(await sql`select id from content.brand_sites where slug=${BRAND_SLUG} and active=true limit 1`)[0];if(!brand)throw new Error('brand_not_found')
  const take=Math.max(1,Math.min(20,limit));const per=Math.ceil(take/2)
  const rows=await sql`
    with ranked as (
      select i.*,row_number() over(partition by i.portfolio order by i.affinity_score desc,i.demand_score desc) rn
      from intel.marketplace200_items i
      left join public.socialmarket_top100_publication_state_v p on p.source_record_hash=i.source_record_hash
      where i.run_id=${runId}::uuid and i.quality_decision='SELECTED' and i.skeptic_verdict='validated' and i.handed_off_at is null
        and not coalesce(p.passed_to_socialscheduler,false) and not coalesce(p.published,false)
    ) select * from ranked where rn<=${per} order by affinity_score desc limit ${take}`
  let jobs=0;const content=[]
  for(let idx=0;idx<rows.length;idx++){
    const x:any=rows[idx],copy=x.social_copy||{},caption=`${text(copy.caption||copy.hook||x.solution_statement,1800)}\n\nΔιαφήμιση · Επιλεγμένη πρόταση προϊόντος.`
    const sourceKey=`marketplace200:${runId}:${x.source_record_hash}`
    const meta={origin:'semantic_marketplace_200',marketplace_run_id:runId,portfolio:x.portfolio,source_record_hash:x.source_record_hash,semantic_cluster_key:x.semantic_cluster_key,niche:x.niche,subniche:x.subniche,affinity_score:Number(x.affinity_score),product_quality_score:Number(x.product_quality_score),landing_candidate:Boolean(x.landing_candidate)}
    const ci=(await sql`insert into content.items(source_key,brand_site_id,title,angle,core_copy,cta,tracking_url,media_url,status,approved_at,metadata,updated_at) values(${sourceKey},${brand.id}::uuid,${text(x.product_name,700)},${text(copy.hook||x.pain_statement,600)},${caption},'Δες τη λύση',${x.tracking_url},${x.image_url},'approved',now(),${sql.json(meta)},now()) on conflict(source_key) do update set title=excluded.title,angle=excluded.angle,core_copy=excluded.core_copy,tracking_url=excluded.tracking_url,media_url=excluded.media_url,metadata=excluded.metadata,status=case when content.items.status in ('queued','completed') then content.items.status else 'approved' end,updated_at=now() returning id`)[0]
    const base=Date.now()+(6+idx*22)*3600_000,tags=arr(copy.hashtags).map((v:any)=>text(v,80)).filter(Boolean)
    const payloads:any={facebook:{caption,hashtags:tags,format:'post',media_url:x.image_url,tracking_url:x.tracking_url,scheduled_for:new Date(base).toISOString(),priority:90-idx},instagram:{caption,hashtags:tags,format:'post',media_url:x.image_url,tracking_url:x.tracking_url,scheduled_for:new Date(base+3600_000).toISOString(),priority:90-idx},tiktok:{caption,hashtags:tags,format:'post',media_url:x.image_url,tracking_url:x.tracking_url,scheduled_for:new Date(base+2*3600_000).toISOString(),priority:90-idx}}
    await sql`select * from publish.queue_content_item_v2(${ci.id}::uuid,${sql.json(payloads)},null::timestamptz)`
    await sql`update intel.marketplace200_items set handed_off_at=now() where id=${x.id}::uuid`;jobs+=3;content.push({source_record_hash:x.source_record_hash,content_item_id:ci.id,portfolio:x.portfolio})
  }
  return {products_handed_off:content.length,outbox_jobs_queued:jobs,content}
}

Deno.serve(async req=>{
  if(req.method==='GET')return json({ok:true,service:'marketplace200-agent-gateway',version:'1.0',model:DEEPSEEK_MODEL})
  if(req.method!=='POST')return json({error:'method_not_allowed'},405)
  try{await auth(req);const b=await req.json(),action=String(b.action||'')
    if(action==='context')return json({ok:true,...await context()})
    if(action==='plan')return json({ok:true,...await plan()})
    if(action==='evaluate')return json({ok:true,items:await evaluate(arr(b.items))})
    if(action==='persist')return json({ok:true,...await persist(b)})
    if(action==='handoff')return json({ok:true,...await handoff(String(b.run_id||''),Number(b.limit||10))})
    throw new Error('action_not_allowed')
  }catch(e){const m=String(e instanceof Error?e.message:e);console.error(e);return json({ok:false,error:m},m.includes('oidc')?401:500)}
})
