import 'jsr:@supabase/functions-js/edge-runtime.d.ts'
import {createRemoteJWKSet,jwtVerify} from 'npm:jose@6.1.0'
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

type Mode='creative'|'audit'
async function auth(req:Request){
  const h=req.headers.get('authorization')||''
  if(!h.startsWith('Bearer '))throw new Error('missing_oidc')
  const {payload}=await jwtVerify(h.slice(7),JWKS,{issuer:ISSUER,audience:AUDIENCE})
  if(String(payload.repository_id||'')!==REPOSITORY_ID||String(payload.repository||'')!==REPOSITORY||String(payload.ref||'')!=='refs/heads/main'||!ALLOWED.has(String(payload.workflow_ref||'')))throw new Error('oidc_not_allowed')
}

async function deepseek(system:string,payload:any,mode:Mode){
  if(!DEEPSEEK_KEY)throw new Error('deepseek_not_configured')
  const call=async(maxTokens:number,retry=false)=>{
    const body={model:DEEPSEEK_MODEL,temperature:mode==='creative'?.18:.04,max_tokens:maxTokens,response_format:{type:'json_object'},messages:[
      {role:'system',content:system},
      {role:'user',content:`Return one complete JSON object only. ${retry?'Previous JSON was incomplete; be concise. ':''}Input:\n${JSON.stringify(payload)}`}
    ],thinking:{type:'disabled'},reasoning_effort:'low'}
    const r=await fetch('https://api.deepseek.com/chat/completions',{method:'POST',headers:{'content-type':'application/json','authorization':`Bearer ${DEEPSEEK_KEY}`},body:JSON.stringify(body)})
    const raw=await r.text();if(!r.ok)throw new Error(`deepseek_${r.status}:${raw.slice(0,600)}`)
    const j=JSON.parse(raw),choice=j?.choices?.[0]||{},text=String(choice?.message?.content||'')
    if(!text.trim()||choice?.finish_reason==='length')throw new Error(`incomplete_ai_response:${choice?.finish_reason||'empty'}`)
    return JSON.parse(text)
  }
  try{return await call(mode==='creative'?6500:3600,false)}catch{return await call(mode==='creative'?8200:4800,true)}
}

const CREATIVE_SYSTEM=`You are SocialMarket Creative Director for the Greek affiliate market. Create campaign-ready creative packs only from supplied verified product facts and the supplied source product image URL. Never invent specifications, compatibility, awards, reviews, guarantees, scarcity, shipping claims, discounts or performance benefits. Never alter the real brand/model/colour/material identity. The tracking_url is immutable and must be used exactly for CTA/QR payload instructions. Internal ranking/network KPI values must never appear in consumer copy. Produce JSON {"items":[...]}. For each source_record_hash return source_record_hash, campaign_theme, emotional_angle, audience, primary_message, and exactly 3 variants: (1) feed_4x5 for Instagram/Facebook, aspect_ratio 4:5; (2) reel_9x16 for Instagram/TikTok, aspect_ratio 9:16; (3) square_1x1 for Facebook/Instagram, aspect_ratio 1:1. Every variant must include id, platform[], aspect_ratio, hook, headline, subheadline, cta, caption, hashtags[] (5-10), visual_direction, composition, lighting, product_image_treatment, qr_spec {payload_rule:'exact_tracking_url', placement, contrast_rule, min_relative_size}, fidelity_rules[], and reel_storyboard[] (empty unless reel_9x16; for reel give 5-7 short scenes). Copy must be natural Greek, useful, evidence-grounded and distinct across variants. Use the real product image prominently; do not request a regenerated substitute product.`

const AUDIT_SYSTEM=`You are the independent SocialMarket Creative Skeptic. Audit supplied creative packs against supplied product facts. Reject unsupported claims, wrong price/discount, altered brand/model/colour/size, invented features, fake scarcity/social proof, misleading savings, consumer-facing use of internal KPI/model data, or any QR instruction that does not preserve the exact tracking URL. Also flag unreadable hierarchy, weak CTA, repetitive variants or poor product prominence. Return JSON {"items":[...]}. For each source_record_hash return source_record_hash, verdict exactly READY or NEEDS_REVIEW, risk_score 0-100, unsupported_claims[], fidelity_risks[], corrections[], audit_summary in Greek. Do not invent replacement facts.`

async function saveCreatives(runId:string,items:any[]){
  let saved=0
  for(const x of items.slice(0,40)){
    const hash=String(x.source_record_hash||'');if(!hash)continue
    const pack=x.creative_pack&&typeof x.creative_pack==='object'?x.creative_pack:{}
    const audit=x.creative_audit&&typeof x.creative_audit==='object'?x.creative_audit:{}
    const hasPack=Object.keys(pack).length>0
    const verdict=String(audit.verdict||'').toUpperCase()
    const status=!hasPack?'failed':verdict==='READY'?'ready':'needs_review'
    const rows=await sql`update intel.product_rankings set creative_pack=${sql.json(pack)},creative_audit=${sql.json(audit)},creative_status=${status},creative_generated_at=now() where run_id=${runId}::uuid and source_record_hash=${hash} returning id`
    if(rows[0])saved++
  }
  return saved
}

async function finalize(b:any){
  const runId=String(b.run_id||''),minRanked=Math.max(100,Number(b.minimum_ranked||100)),minCreatives=Math.max(20,Number(b.minimum_creatives||20))
  const counts=await sql`select count(*)::int ranked,count(*) filter(where creative_pack<>'{}'::jsonb)::int creatives from intel.product_rankings where run_id=${runId}::uuid`
  if(!counts[0])throw new Error('ranking_run_not_found')
  const ranked=Number(counts[0].ranked||0),creatives=Number(counts[0].creatives||0)
  const metadata={...(b.metadata||{}),final_contract:{minimum_ranked:minRanked,minimum_creatives:minCreatives,ranked,creatives,passed:ranked>=minRanked&&creatives>=minCreatives}}
  if(ranked<minRanked||creatives<minCreatives){
    await sql`update intel.product_ranking_runs set status='failed',completed_at=now(),records_seen=${Number(b.records_seen||0)},eligible_candidates=${Number(b.eligible_candidates||0)},ai_ranked=${Number(b.ai_ranked||0)},saved_count=${ranked},metadata=metadata||${sql.json(metadata)} where id=${runId}::uuid`
    throw new Error(`final_output_contract_failed:ranked=${ranked}/${minRanked};creatives=${creatives}/${minCreatives}`)
  }
  const rows=await sql`update intel.product_ranking_runs set status='completed',completed_at=now(),records_seen=${Number(b.records_seen||0)},eligible_candidates=${Number(b.eligible_candidates||0)},ai_ranked=${Number(b.ai_ranked||0)},saved_count=${ranked},metadata=metadata||${sql.json(metadata)} where id=${runId}::uuid returning id`
  if(!rows[0])throw new Error('ranking_run_not_found')
  return {ranked,creatives}
}

Deno.serve(async req=>{
  if(req.method==='GET')return json({ok:true,service:'product-creative-gateway',version:'1.0',deepseek_configured:Boolean(DEEPSEEK_KEY),deepseek_model:DEEPSEEK_MODEL,contract:{minimum_ranked:100,top_creatives:20,variants_per_product:3}})
  if(req.method!=='POST')return json({error:'method_not_allowed'},405)
  try{
    await auth(req);const b=await req.json(),action=String(b.action||'')
    if(action==='health')return json({ok:true,version:'1.0',deepseek_configured:Boolean(DEEPSEEK_KEY),contract:{minimum_ranked:100,top_creatives:20,variants_per_product:3}})
    if(action==='generate'){
      const items=(Array.isArray(b.items)?b.items:[]).slice(0,5),r=await deepseek(CREATIVE_SYSTEM,{items},'creative')
      return json({ok:true,items:Array.isArray(r?.items)?r.items:[]})
    }
    if(action==='audit'){
      const items=(Array.isArray(b.items)?b.items:[]).slice(0,5),r=await deepseek(AUDIT_SYSTEM,{items},'audit')
      return json({ok:true,items:Array.isArray(r?.items)?r.items:[]})
    }
    if(action==='save_creatives')return json({ok:true,saved:await saveCreatives(String(b.run_id||''),Array.isArray(b.items)?b.items:[])})
    if(action==='finalize')return json({ok:true,...await finalize(b)})
    throw new Error('action_not_allowed')
  }catch(e){const message=String(e instanceof Error?e.message:e);console.error(e);return json({error:message},message.includes('oidc')?401:500)}
})
