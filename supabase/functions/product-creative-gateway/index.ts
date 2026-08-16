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
const SUPABASE_URL=Deno.env.get('SUPABASE_URL')||''
const SERVICE_KEY=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')||''
const CREATIVE_BUCKET='socialmarket-creatives'
const DEFAULT_BRAND_SLUG=Deno.env.get('PRODUCT_CREATIVE_BRAND_SLUG')||'lyseis-pou-axizoun'
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

function cleanSegment(v:unknown){return String(v||'').replace(/[^a-zA-Z0-9._-]/g,'_').slice(0,160)}
function decodeBase64(data:string){
  const raw=atob(data);const out=new Uint8Array(raw.length)
  for(let i=0;i<raw.length;i++)out[i]=raw.charCodeAt(i)
  return out
}
async function uploadAsset(b:any){
  if(!SUPABASE_URL||!SERVICE_KEY)throw new Error('storage_runtime_credentials_missing')
  const runId=cleanSegment(b.run_id),hash=cleanSegment(b.source_record_hash),variantId=cleanSegment(b.variant_id)
  if(!runId||!hash||!variantId)throw new Error('asset_identity_required')
  const bytes=decodeBase64(String(b.base64_png||''));if(bytes.length<1000||bytes.length>8*1024*1024)throw new Error('asset_size_invalid')
  const path=`rankings/${runId}/${hash}/${variantId}.png`
  const r=await fetch(`${SUPABASE_URL}/storage/v1/object/${CREATIVE_BUCKET}/${path}`,{method:'POST',headers:{apikey:SERVICE_KEY,authorization:`Bearer ${SERVICE_KEY}`,'content-type':'image/png','x-upsert':'true','cache-control':'31536000'},body:bytes})
  const raw=await r.text();if(!r.ok)throw new Error(`creative_asset_upload_${r.status}:${raw.slice(0,500)}`)
  return {path,asset_url:`${SUPABASE_URL}/storage/v1/object/public/${CREATIVE_BUCKET}/${path}`,bytes:bytes.length}
}

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

function platforms(v:any){return (Array.isArray(v)?v:[]).map(x=>String(x).toLowerCase()).filter(x=>['facebook','instagram','tiktok'].includes(x))}
function platformFormat(variantId:string,platform:string){if(variantId==='reel_9x16'&&platform==='instagram')return 'reel';return 'post'}

async function persistContent(b:any){
  const runId=String(b.run_id||''),hash=String(b.source_record_hash||''),pack=b.creative_pack&&typeof b.creative_pack==='object'?b.creative_pack:{},audit=b.creative_audit&&typeof b.creative_audit==='object'?b.creative_audit:{}
  const variants=Array.isArray(pack.variants)?pack.variants:[]
  if(!runId||!hash||variants.length!==3)throw new Error('complete_creative_pack_required')
  if(variants.some((v:any)=>!String(v?.asset_url||'').startsWith('https://')))throw new Error('all_creative_asset_urls_required')
  const brandSlug=String(b.brand_slug||DEFAULT_BRAND_SLUG),brand=await sql`select id,slug,name from content.brand_sites where slug=${brandSlug} and active=true limit 1`
  if(!brand[0])throw new Error(`creative_brand_not_found:${brandSlug}`)
  const verdict=String(audit.verdict||'').toUpperCase(),approved=verdict==='READY'
  const productName=String(b.product_name||'Ranked product'),merchantId=String(b.merchant_id||'').match(/^[0-9a-f-]{36}$/i)?String(b.merchant_id):null,trackingUrl=String(b.tracking_url||'')
  if(!trackingUrl.startsWith('http'))throw new Error('tracking_url_required')
  const schedules=b.schedules&&typeof b.schedules==='object'?b.schedules:{}
  const contentIds:any[]=[];let queued=0
  for(const variant of variants){
    const variantId=String(variant.id||''),sourceKey=`ranked:${runId}:${hash}:${variantId}`,caption=String(variant.caption||''),assetUrl=String(variant.asset_url||'')
    if(!variantId||!caption)throw new Error(`creative_variant_incomplete:${variantId}`)
    const metadata={origin:'ranked_product_creative',creative_run_id:runId,source_record_hash:hash,global_rank:b.global_rank??null,variant_id:variantId,aspect_ratio:variant.aspect_ratio??null,platforms:platforms(variant.platform),hashtags:Array.isArray(variant.hashtags)?variant.hashtags.slice(0,10):[],creative_audit:audit,product_image_url:b.image_url??null,product_name:productName,merchant_name:b.merchant_name??null,affiliate_disclosure:true}
    const rows=await sql`insert into content.items(source_key,brand_site_id,merchant_id,title,angle,core_copy,cta,tracking_url,media_url,status,approved_at,metadata,updated_at)
      values(${sourceKey},${brand[0].id}::uuid,${merchantId}::uuid,${`${productName} — ${variantId}`},${String(pack.campaign_theme||pack.emotional_angle||'')},${caption},${String(variant.cta||'')},${trackingUrl},${assetUrl},${approved?'approved':'draft'},${approved?new Date().toISOString():null}::timestamptz,${sql.json(metadata)},now())
      on conflict(source_key) do update set title=excluded.title,angle=excluded.angle,core_copy=excluded.core_copy,cta=excluded.cta,tracking_url=excluded.tracking_url,media_url=excluded.media_url,metadata=excluded.metadata,status=case when content.items.status in('queued','completed') then content.items.status else excluded.status end,approved_at=case when content.items.status in('queued','completed') then content.items.approved_at else excluded.approved_at end,updated_at=now() returning id,status`
    const item=rows[0];contentIds.push({id:item.id,variant_id:variantId,status:item.status,media_url:assetUrl})
    const variantSchedules=schedules[variantId]&&typeof schedules[variantId]==='object'?schedules[variantId]:{}
    if(approved&&Object.keys(variantSchedules).length){
      const payloads:any={}
      for(const p of platforms(variant.platform)){
        const scheduledFor=String(variantSchedules[p]||'')
        if(!scheduledFor)continue
        payloads[p]={caption,hashtags:Array.isArray(variant.hashtags)?variant.hashtags:[],format:platformFormat(variantId,p),media_url:assetUrl,tracking_url:trackingUrl,scheduled_for:scheduledFor,priority:Math.max(1,Math.min(100,Number(b.priority||50)))}
      }
      if(Object.keys(payloads).length){
        await sql`select * from publish.queue_content_item_v2(${item.id}::uuid,${sql.json(payloads)},null::timestamptz)`;queued+=Object.keys(payloads).length
      }
    }
  }
  await sql`update intel.product_rankings set creative_pack=${sql.json(pack)},creative_audit=${sql.json(audit)},creative_content_count=${contentIds.length},creative_status=${approved?'ready':'needs_review'},creative_generated_at=coalesce(creative_generated_at,now()) where run_id=${runId}::uuid and source_record_hash=${hash}`
  return {content_items:contentIds,queued,approved}
}

async function finalize(b:any){
  const runId=String(b.run_id||''),minRanked=Math.max(100,Number(b.minimum_ranked||100)),minCreatives=Math.max(20,Number(b.minimum_creatives||20)),minContentPacks=Math.max(20,Number(b.minimum_content_packs||20))
  const counts=await sql`select count(*)::int ranked,count(*) filter(where creative_pack<>'{}'::jsonb)::int creatives,count(*) filter(where creative_content_count=3)::int content_packs from intel.product_rankings where run_id=${runId}::uuid`
  if(!counts[0])throw new Error('ranking_run_not_found')
  const ranked=Number(counts[0].ranked||0),creatives=Number(counts[0].creatives||0),contentPacks=Number(counts[0].content_packs||0)
  const passed=ranked>=minRanked&&creatives>=minCreatives&&contentPacks>=minContentPacks
  const metadata={...(b.metadata||{}),final_contract:{minimum_ranked:minRanked,minimum_creatives:minCreatives,minimum_content_packs:minContentPacks,ranked,creatives,content_packs:contentPacks,creative_assets:contentPacks*3,passed}}
  if(!passed){
    await sql`update intel.product_ranking_runs set status='failed',completed_at=now(),records_seen=${Number(b.records_seen||0)},eligible_candidates=${Number(b.eligible_candidates||0)},ai_ranked=${Number(b.ai_ranked||0)},saved_count=${ranked},metadata=metadata||${sql.json(metadata)} where id=${runId}::uuid`
    throw new Error(`final_output_contract_failed:ranked=${ranked}/${minRanked};creatives=${creatives}/${minCreatives};content_packs=${contentPacks}/${minContentPacks}`)
  }
  const rows=await sql`update intel.product_ranking_runs set status='completed',completed_at=now(),records_seen=${Number(b.records_seen||0)},eligible_candidates=${Number(b.eligible_candidates||0)},ai_ranked=${Number(b.ai_ranked||0)},saved_count=${ranked},metadata=metadata||${sql.json(metadata)} where id=${runId}::uuid returning id`
  if(!rows[0])throw new Error('ranking_run_not_found')
  return {ranked,creatives,content_packs:contentPacks,creative_assets:contentPacks*3}
}

Deno.serve(async req=>{
  if(req.method==='GET')return json({ok:true,service:'product-creative-gateway',version:'1.3',deepseek_configured:Boolean(DEEPSEEK_KEY),deepseek_model:DEEPSEEK_MODEL,contract:{minimum_ranked:100,top_creatives:20,variants_per_product:3,durable_assets_per_product:3,canonical_content:true,scheduler_handoff:'content.items_to_rolling_outbox'}})
  if(req.method!=='POST')return json({error:'method_not_allowed'},405)
  try{
    await auth(req);const b=await req.json(),action=String(b.action||'')
    if(action==='health')return json({ok:true,version:'1.3',deepseek_configured:Boolean(DEEPSEEK_KEY),contract:{minimum_ranked:100,top_creatives:20,variants_per_product:3,durable_assets_per_product:3,canonical_content:true,scheduler_handoff:'content.items_to_rolling_outbox'}})
    if(action==='generate'){const items=(Array.isArray(b.items)?b.items:[]).slice(0,5),r=await deepseek(CREATIVE_SYSTEM,{items},'creative');return json({ok:true,items:Array.isArray(r?.items)?r.items:[]})}
    if(action==='audit'){const items=(Array.isArray(b.items)?b.items:[]).slice(0,5),r=await deepseek(AUDIT_SYSTEM,{items},'audit');return json({ok:true,items:Array.isArray(r?.items)?r.items:[]})}
    if(action==='upload_asset')return json({ok:true,...await uploadAsset(b)})
    if(action==='save_creatives')return json({ok:true,saved:await saveCreatives(String(b.run_id||''),Array.isArray(b.items)?b.items:[])})
    if(action==='persist_content')return json({ok:true,...await persistContent(b)})
    if(action==='finalize')return json({ok:true,...await finalize(b)})
    throw new Error('action_not_allowed')
  }catch(e){
    const message=String(e instanceof Error?e.message:e);console.error(e)
    const authFailure=message.includes('oidc')||message.includes('"exp" claim timestamp check failed')||message.includes('JWTExpired')
    return json({error:message},authFailure?401:500)
  }
})