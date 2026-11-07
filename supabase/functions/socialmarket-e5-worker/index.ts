import 'jsr:@supabase/functions-js/edge-runtime.d.ts'
import { createRemoteJWKSet, jwtVerify } from 'npm:jose@6.1.0'
import postgres from 'npm:postgres@3.4.5'

// OIDC-only worker gateway. The secret DB URL never leaves this Edge Function.
const ISSUER = 'https://token.actions.githubusercontent.com'
const AUDIENCE = 'socialmarket-e5-worker'
const REPOSITORY_ID = '1329707883'
const REPOSITORY = 'vmoulakakis/Socialmarket'
const ALLOWED_WORKFLOWS = new Set([
 'vmoulakakis/Socialmarket/.github/workflows/socialmarket-e5-backfill.yml@refs/heads/main',
 'vmoulakakis/Socialmarket/.github/workflows/socialmarket-e5-backfill.yml@refs/heads/feat/agentic-shopper-evidence-gate-20261106',
])
const JWKS=createRemoteJWKSet(new URL(ISSUER+'/.well-known/jwks'))
const sha=/^[a-f0-9]{64}$/
const id=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
const response=(v:unknown,status=200)=>new Response(JSON.stringify(v),{
 status,headers:{'content-type':'application/json','cache-control':'no-store','x-robots-tag':'noindex'} })
function validVector(raw:unknown){
 if(!Array.isArray(raw)||raw.length!==384)return false
 if(!raw.every(x=>typeof x==='number'&&Number.isFinite(x)))return false
 const square=raw.reduce((n,x)=>n+x*x,0)
 return square>0.95 && square<1.05
}
Deno.serve(async req=>{
 if(req.method==='GET')return response({ok:true,service:'socialmarket-e5-worker',private:true})
 if(req.method!=='POST')return response({error:'method_not_allowed'},405)
 const header=req.headers.get('authorization')||''
 if(!header.startsWith('Bearer '))return response({error:'missing_oidc'},401)
 try{
  const {payload}=await jwtVerify(header.slice(7),JWKS,{issuer:ISSUER,audience:AUDIENCE})
  if(String(payload.repository_id||'')!==REPOSITORY_ID||
     String(payload.repository||'')!==REPOSITORY||
     !['refs/heads/main','refs/heads/feat/agentic-shopper-evidence-gate-20261106'].includes(String(payload.ref||''))||
     !ALLOWED_WORKFLOWS.has(String(payload.workflow_ref||''))) return response({error:'oidc_scope_denied'},403)
  const raw=await req.text()
  if(raw.length>12000)return response({error:'payload_too_large'},413)
  const body=JSON.parse(raw)
  const action=String(body?.action||'')
  const worker=String(body?.worker||'')
  if(!/^gha-e5-[a-zA-Z0-9-]{12,80}$/.test(worker))return response({error:'worker_invalid'},400)
  const pgUrl=Deno.env.get('SUPABASE_DB_URL')
  if(!pgUrl)return response({error:'db_not_configured'},503)
  const sql=postgres(pgUrl,{max:1,prepare:false,ssl:'require',connect_timeout:5,idle_timeout:5})
  try{
   if(action==='claim'){
    const limit=Math.min(16,Math.max(1,Math.trunc(Number(body?.limit)||8)))
    const rows=await sql.unsafe('select doc_id,doc_text,doc_hash from sm_intel.claim_embeddings($1,$2)',[worker,limit])
    return response({ok:true,claimed:rows.length,documents:rows})
   }
   if(action==='ack'){
    const docId=String(body.doc_id||'')
    const docHash=String(body.doc_hash||'')
    const error=body.error==null?null:String(body.error).slice(0,300)
    const vector=body.embedding
    if(!id.test(docId)||!sha.test(docHash))return response({error:'invalid_document_identity'},400)
    if(error===null&&!validVector(vector))return response({error:'invalid_384d_normalized_embedding'},400)
    const str=error===null?JSON.stringify(vector):null
    const out=await sql.unsafe('select sm_intel.ack_embedding($1::uuid,$2,$3,$4,$5) as acknowledged',[docId,worker,docHash,str,error])
    return response({ok:Boolean(out[0]?.acknowledged)})
   }
   return response({error:'unsupported_action'},400)
  }finally{await sql.end({timeout:2}).catch(()=>{})}
 }catch(e){
  const msg=e instanceof Error?e.message:'unknown'
  console.error('[socialmarket-e5-worker]',msg.slice(0,150))
  return response({error:'unauthorized_or_temporary_failure'},503)
 }
})
