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
const json=(x:unknown,s=200)=>new Response(JSON.stringify(x),{status:s,headers:{'content-type':'application/json','cache-control':'no-store'}})
const arr=(v:any)=>Array.isArray(v)?v:[]
const text=(v:any,max=1000)=>String(v??'').trim().slice(0,max)
const n=(v:any)=>{const x=Number(v);return Number.isFinite(x)?x:0}

async function auth(req:Request){
 const h=req.headers.get('authorization')||''
 if(!h.startsWith('Bearer '))throw new Error('missing_oidc')
 const {payload}=await jwtVerify(h.slice(7),JWKS,{issuer:ISSUER,audience:AUDIENCE})
 if(String(payload.repository_id||'')!==REPOSITORY_ID||String(payload.repository||'')!==REPOSITORY||String(payload.ref||'')!=='refs/heads/main'||!ALLOWED.has(String(payload.workflow_ref||'')))throw new Error('oidc_not_allowed')
}

async function state(){
 const sourceStates=await sql`select source_network,source_partition,baseline_completed,source_fingerprint,etag,last_modified,content_length,last_checked_at,last_changed_at,metadata from intel.marketplace_source_state order by source_network,source_partition`
 const programs=await sql`
   select mp.id merchant_program_id,mp.merchant_id,mp.program_name,mp.external_program_id,mp.raw_commission_pct,mp.raw_flat_commission,
     m.canonical_name,m.official_domain,m.primary_category,m.primary_subcategory,
     mr.global_rank,mr.trust_score,mr.research_confidence,mr.risk_flag,
     pcs.conversion_rate,pcs.epc,pcs.approval_rate,pcs.approval_days,pcs.commercial_score,pcs.data_confidence,pcs.rank_score,
     case when mp.external_program_id is not null
       and coalesce(mr.risk_flag,false)=false and coalesce(mr.trust_score,0)>=65 and coalesce(mr.research_confidence,0)>=0.55 and coalesce(mr.global_rank,9999)<=100
       and coalesce(pcs.data_confidence,0)>=80 and coalesce(pcs.commercial_score,0)>=55
       then 'trusted' else 'discovery' end retrieval_tier
   from catalog.merchant_programs mp
   join catalog.merchants m on m.id=mp.merchant_id
   join api.merchant_rankings mr on mr.merchant_id=m.id and (mr.program_id=mp.id or mr.program_id is null)
   left join lateral (select s.* from intel.program_commercial_snapshots s where s.program_id=mp.id order by s.observed_at desc limit 1) pcs on true
   where mp.status is distinct from 'inactive'
     and coalesce(mr.risk_flag,false)=false and coalesce(mr.global_rank,9999)<=100
   order by case when mp.external_program_id is not null then 0 else 1 end,coalesce(pcs.commercial_score,0) desc,mr.global_rank asc`
 const sellers=await sql`select source_network,seller_id,seller_name,seller_url,trust_state,evidence_score,confidence,validated_products,rejected_products,seen_products,tracking_successes,last_seen_at,last_validated_at from intel.marketplace_seller_registry where trust_state<>'blocked' order by case trust_state when 'trusted' then 0 else 1 end,evidence_score desc,confidence desc limit 500`
 return {source_states:sourceStates,programs,sellers,linkwise_baseline_completed:sourceStates.some((x:any)=>x.source_network==='linkwise'&&x.source_partition==='baseline'&&x.baseline_completed===true)}
}

async function diff(body:any){
 const network=text(body.source_network,80);const items=arr(body.items).slice(0,1000).map((x:any)=>({source_product_id:text(x.source_product_id,300),product_fingerprint:text(x.product_fingerprint,180)})).filter((x:any)=>x.source_product_id&&x.product_fingerprint)
 if(!network||!items.length)return {items:[]}
 const rows=await sql`
   with incoming as (
     select * from jsonb_to_recordset(${sql.json(items)}::jsonb) as x(source_product_id text,product_fingerprint text)
   )
   select i.source_product_id,
     case when l.source_product_id is null then 'new' when l.product_fingerprint is distinct from i.product_fingerprint then 'changed' else 'unchanged' end status
   from incoming i left join intel.marketplace_product_ledger l on l.source_network=${network} and l.source_product_id=i.source_product_id`
 return {items:rows}
}

async function checkpoint(body:any){
 const network=text(body.source_network,80);const items=arr(body.items).slice(0,1000).map((x:any)=>({
   source_product_id:text(x.source_product_id,300),source_record_hash:text(x.source_record_hash,300)||null,product_fingerprint:text(x.product_fingerprint,180),merchant_id:text(x.merchant_id,80)||null,merchant_program_id:text(x.merchant_program_id,80)||null,external_program_id:text(x.external_program_id,100)||null,seller_id:text(x.seller_id||x.shop_id,300)||null,product_name:text(x.product_name,700)||null,price_eur:n(x.price_eur??x.sale_price_eur)||null,expected_commission_eur:n(x.expected_commission_eur)||null,metadata:x.metadata||{}
 })).filter((x:any)=>x.source_product_id&&x.product_fingerprint)
 if(!network||!items.length)return {upserted:0}
 await sql`
   insert into intel.marketplace_product_ledger(source_network,source_product_id,source_record_hash,product_fingerprint,merchant_id,merchant_program_id,external_program_id,seller_id,product_name,price_eur,expected_commission_eur,first_seen_at,last_seen_at,last_changed_at,metadata)
   select ${network},x.source_product_id,x.source_record_hash,x.product_fingerprint,nullif(x.merchant_id,'')::uuid,nullif(x.merchant_program_id,'')::uuid,x.external_program_id,x.seller_id,x.product_name,x.price_eur,x.expected_commission_eur,now(),now(),now(),coalesce(x.metadata,'{}'::jsonb)
   from jsonb_to_recordset(${sql.json(items)}::jsonb) as x(source_product_id text,source_record_hash text,product_fingerprint text,merchant_id text,merchant_program_id text,external_program_id text,seller_id text,product_name text,price_eur numeric,expected_commission_eur numeric,metadata jsonb)
   on conflict(source_network,source_product_id) do update set source_record_hash=excluded.source_record_hash,product_fingerprint=excluded.product_fingerprint,merchant_id=coalesce(excluded.merchant_id,intel.marketplace_product_ledger.merchant_id),merchant_program_id=coalesce(excluded.merchant_program_id,intel.marketplace_product_ledger.merchant_program_id),external_program_id=coalesce(excluded.external_program_id,intel.marketplace_product_ledger.external_program_id),seller_id=coalesce(excluded.seller_id,intel.marketplace_product_ledger.seller_id),product_name=excluded.product_name,price_eur=excluded.price_eur,expected_commission_eur=excluded.expected_commission_eur,last_seen_at=now(),last_changed_at=case when intel.marketplace_product_ledger.product_fingerprint is distinct from excluded.product_fingerprint then now() else intel.marketplace_product_ledger.last_changed_at end,metadata=intel.marketplace_product_ledger.metadata||excluded.metadata`
 const sellerRows=items.filter((x:any)=>x.seller_id)
 for(const x of sellerRows){await sql`insert into intel.marketplace_seller_registry(source_network,seller_id,seller_name,seller_url,seen_products,last_seen_at,metadata) values(${network},${x.seller_id},${text(x.metadata?.seller_name,400)||null},${text(x.metadata?.seller_url,1000)||null},1,now(),${sql.json(x.metadata||{})}) on conflict(source_network,seller_id) do update set seller_name=coalesce(excluded.seller_name,intel.marketplace_seller_registry.seller_name),seller_url=coalesce(excluded.seller_url,intel.marketplace_seller_registry.seller_url),seen_products=intel.marketplace_seller_registry.seen_products+1,last_seen_at=now(),metadata=intel.marketplace_seller_registry.metadata||excluded.metadata`}
 return {upserted:items.length}
}

async function learnPrograms(body:any){
 const mappings=arr(body.mappings).slice(0,300);let learned=0,conflicts=0
 for(const m of mappings){const id=text(m.merchant_program_id,80),external=text(m.external_program_id,100);if(!id||!external)continue
   const current=(await sql`select external_program_id from catalog.merchant_programs where id=${id}::uuid limit 1`)[0]
   if(!current)continue
   if(current.external_program_id&&String(current.external_program_id)!==external){conflicts++;continue}
   const r=await sql`update catalog.merchant_programs set external_program_id=${external},source_network=coalesce(source_network,'linkwise'),updated_at=now() where id=${id}::uuid and (external_program_id is null or external_program_id=${external}) returning id`
   if(r.length)learned++
 }
 return {learned,conflicts}
}

async function markSource(body:any){
 const network=text(body.source_network,80),partition=text(body.source_partition,200);if(!network||!partition)throw new Error('source_state_key_required')
 await sql`insert into intel.marketplace_source_state(source_network,source_partition,baseline_completed,source_fingerprint,etag,last_modified,content_length,last_checked_at,last_changed_at,metadata) values(${network},${partition},${Boolean(body.baseline_completed)},${text(body.source_fingerprint,300)||null},${text(body.etag,500)||null},${text(body.last_modified,500)||null},${body.content_length==null?null:n(body.content_length)},now(),case when ${Boolean(body.changed)} then now() else null end,${sql.json(body.metadata||{})}) on conflict(source_network,source_partition) do update set baseline_completed=excluded.baseline_completed or intel.marketplace_source_state.baseline_completed,source_fingerprint=coalesce(excluded.source_fingerprint,intel.marketplace_source_state.source_fingerprint),etag=coalesce(excluded.etag,intel.marketplace_source_state.etag),last_modified=coalesce(excluded.last_modified,intel.marketplace_source_state.last_modified),content_length=coalesce(excluded.content_length,intel.marketplace_source_state.content_length),last_checked_at=now(),last_changed_at=case when ${Boolean(body.changed)} then now() else intel.marketplace_source_state.last_changed_at end,metadata=intel.marketplace_source_state.metadata||excluded.metadata`
 return {updated:true}
}

async function recordEvaluations(body:any){
 const network=text(body.source_network,80),items=arr(body.items).slice(0,500);let updated=0
 for(const x of items){const pid=text(x.source_product_id,300),decision=text(x.quality_decision,40),seller=text(x.seller_id||x.shop_id,300);if(!pid)continue
   await sql`update intel.marketplace_product_ledger set last_evaluated_at=now(),last_quality_decision=${decision||null},metadata=metadata||${sql.json({product_quality_score:n(x.product_quality_score),affinity_score:n(x.affinity_score),skeptic_verdict:text(x.skeptic_verdict,40)})} where source_network=${network} and source_product_id=${pid}`;updated++
   if(seller){const validated=decision==='SELECTED'&&text(x.skeptic_verdict,40)==='validated';const rejected=decision==='REJECTED';const tracking=Boolean(x.tracking_url)
     await sql`insert into intel.marketplace_seller_registry(source_network,seller_id,validated_products,rejected_products,tracking_successes,last_seen_at,last_validated_at) values(${network},${seller},${validated?1:0},${rejected?1:0},${tracking?1:0},now(),${validated?new Date():null}) on conflict(source_network,seller_id) do update set validated_products=intel.marketplace_seller_registry.validated_products+${validated?1:0},rejected_products=intel.marketplace_seller_registry.rejected_products+${rejected?1:0},tracking_successes=intel.marketplace_seller_registry.tracking_successes+${tracking?1:0},last_seen_at=now(),last_validated_at=case when ${validated} then now() else intel.marketplace_seller_registry.last_validated_at end`
     await sql`update intel.marketplace_seller_registry set evidence_score=least(100,validated_products*28+tracking_successes*4-greatest(0,rejected_products)*18),confidence=least(1.0,(validated_products+rejected_products)::numeric/4.0),trust_state=case when rejected_products>=3 and validated_products=0 then 'blocked' when validated_products>=2 and (validated_products::numeric/greatest(1,validated_products+rejected_products))>=0.75 and tracking_successes>=2 then 'trusted' else 'discovery' end where source_network=${network} and seller_id=${seller}`
   }
 }
 return {updated}
}

Deno.serve(async(req)=>{
 if(req.method==='GET')return json({ok:true,service:'marketplace-incremental-gateway',version:'1.0',strategy:'baseline-once-then-product-deltas'})
 if(req.method!=='POST')return json({ok:false,error:'method_not_allowed'},405)
 try{await auth(req);const b=await req.json();const action=text(b.action,60);let result:any
   if(action==='state')result=await state()
   else if(action==='diff')result=await diff(b)
   else if(action==='checkpoint')result=await checkpoint(b)
   else if(action==='learn_programs')result=await learnPrograms(b)
   else if(action==='mark_source')result=await markSource(b)
   else if(action==='record_evaluations')result=await recordEvaluations(b)
   else throw new Error('action_not_allowed')
   return json({ok:true,...result})
 }catch(e){const m=String(e instanceof Error?e.message:e);console.error(e);return json({ok:false,error:m},m.includes('oidc')?401:500)}
})
