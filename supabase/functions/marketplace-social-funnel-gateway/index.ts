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
const BRAND_SLUG=Deno.env.get('SOCIALMARKET_BRAND_SLUG')||'lyseis-pou-axizoun'
const PUBLIC_BASE=(Deno.env.get('SOCIALMARKET_PUBLIC_BASE')||'https://socialmarket-theta.vercel.app').replace(/\/$/,'')
const json=(x:unknown,s=200)=>new Response(JSON.stringify(x),{status:s,headers:{'content-type':'application/json','cache-control':'no-store'}})
const arr=(v:any)=>Array.isArray(v)?v:[]
const text=(v:any,max=1800)=>String(v||'').replace(/[\u0000-\u001f]+/g,' ').trim().slice(0,max)

async function auth(req:Request){
 const h=req.headers.get('authorization')||''
 if(!h.startsWith('Bearer '))throw new Error('missing_oidc')
 const {payload}=await jwtVerify(h.slice(7),JWKS,{issuer:ISSUER,audience:AUDIENCE})
 if(String(payload.repository_id||'')!==REPOSITORY_ID||String(payload.repository||'')!==REPOSITORY||String(payload.ref||'')!=='refs/heads/main'||!ALLOWED.has(String(payload.workflow_ref||'')))throw new Error('oidc_not_allowed')
}

function creativeUrl(id:string,format:'feed'|'story'|'square'){
 return `${PUBLIC_BASE}/api/marketplace/creative/${encodeURIComponent(id)}?format=${format}`
}
function caseUrl(id:string){return `${PUBLIC_BASE}/marketplace/${encodeURIComponent(id)}`}
function socialCaption(x:any){
 const copy=x.social_copy||{}
 const hook=text(copy.hook||x.solution_statement||x.job_to_be_done,260)
 const pain=text(x.pain_statement,260)
 const tags=arr(copy.hashtags).map((v:any)=>text(v,70)).filter(Boolean).slice(0,8)
 return `${hook}\n\nΤο pain: ${pain}\n\nΔες το πλήρες case πριν αποφασίσεις. Τιμή και διαθεσιμότητα επιβεβαιώνονται στον τελικό προορισμό.${tags.length?`\n\n${tags.join(' ')}`:''}`
}

async function handoff(runId:string,limit:number){
 const brand=(await sql`select id from content.brand_sites where slug=${BRAND_SLUG} and active=true limit 1`)[0]
 if(!brand)throw new Error('brand_not_found')
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
   const x:any=rows[idx],id=String(x.id),landing=caseUrl(id),caption=socialCaption(x)
   const feed=creativeUrl(id,'feed'),story=creativeUrl(id,'story'),square=creativeUrl(id,'square')
   const sourceKey=`marketplace-social:${runId}:${x.source_record_hash}`
   const meta={origin:'semantic_social_gap_filler',marketplace_run_id:runId,source_record_hash:x.source_record_hash,semantic_cluster_key:x.semantic_cluster_key,niche:x.niche,subniche:x.subniche,case_url:landing,commercial_destination_url:x.tracking_url,creative_urls:{feed,story,square},creative_contract:'affinity-social-gap-filler-2026.09'}
   const ci=(await sql`insert into content.items(source_key,brand_site_id,title,angle,core_copy,cta,tracking_url,media_url,status,approved_at,metadata,updated_at)
     values(${sourceKey},${brand.id}::uuid,${text(x.product_name,700)},${text((x.social_copy||{}).hook||x.pain_statement,600)},${caption},'Δες το case',${landing},${feed},'approved',now(),${sql.json(meta)},now())
     on conflict(source_key) do update set title=excluded.title,angle=excluded.angle,core_copy=excluded.core_copy,cta=excluded.cta,tracking_url=excluded.tracking_url,media_url=excluded.media_url,metadata=excluded.metadata,status=case when content.items.status in ('queued','completed') then content.items.status else 'approved' end,updated_at=now() returning id`)[0]
   const base=Date.now()+(6+idx*22)*3600_000
   const payloads:any={
     facebook:{caption,hashtags:[],format:'post',media_url:square,tracking_url:landing,scheduled_for:new Date(base).toISOString(),priority:90-idx},
     instagram:{caption,hashtags:[],format:'post',media_url:feed,tracking_url:landing,scheduled_for:new Date(base+3600_000).toISOString(),priority:90-idx},
     tiktok:{caption,hashtags:[],format:'post',media_url:story,tracking_url:landing,scheduled_for:new Date(base+2*3600_000).toISOString(),priority:90-idx}
   }
   await sql`select * from publish.queue_content_item_v2(${ci.id}::uuid,${sql.json(payloads)},null::timestamptz)`
   await sql`update intel.marketplace200_items set handed_off_at=now() where id=${id}::uuid`
   jobs+=3;content.push({source_record_hash:x.source_record_hash,content_item_id:ci.id,case_url:landing,creative_urls:{feed,story,square}})
 }
 return {products_handed_off:content.length,outbox_jobs_queued:jobs,content,public_base:PUBLIC_BASE}
}

Deno.serve(async req=>{
 if(req.method==='GET')return json({ok:true,service:'marketplace-social-funnel-gateway',version:'1.0',public_base:PUBLIC_BASE})
 if(req.method!=='POST')return json({ok:false,error:'method_not_allowed'},405)
 try{await auth(req);const b=await req.json();if(String(b.action||'')!=='handoff')throw new Error('action_not_allowed');return json({ok:true,...await handoff(String(b.run_id||''),Number(b.limit||10))})}
 catch(e){const m=String(e instanceof Error?e.message:e);console.error(e);return json({ok:false,error:m},m.includes('oidc')?401:500)}
})
