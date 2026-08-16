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
const json=(x:unknown,s=200)=>new Response(JSON.stringify(x),{status:s,headers:{'content-type':'application/json','cache-control':'no-store'}})

async function auth(req:Request){
  const h=req.headers.get('authorization')||''
  if(!h.startsWith('Bearer '))throw new Error('missing_oidc')
  const {payload}=await jwtVerify(h.slice(7),JWKS,{issuer:ISSUER,audience:AUDIENCE})
  if(String(payload.repository_id||'')!==REPOSITORY_ID||String(payload.repository||'')!==REPOSITORY||String(payload.ref||'')!=='refs/heads/main'||!ALLOWED.has(String(payload.workflow_ref||'')))throw new Error('oidc_not_allowed')
  return payload
}

async function failRun(b:any){
  const runId=String(b.run_id||'')
  if(!runId)throw new Error('run_id_required')
  const stage=String(b.stage||'unknown').slice(0,120)
  const error=String(b.error||'unknown_error').slice(0,4000)
  const meta={...(b.metadata||{}),failure_stage:stage,failure_error:error,failed_at:new Date().toISOString()}
  const rows=await sql`
    update intel.product_ranking_runs
       set status='failed', completed_at=now(), metadata=coalesce(metadata,'{}'::jsonb)||${sql.json(meta)}
     where id=${runId}::uuid
     returning id
  `
  if(!rows[0])throw new Error('ranking_run_not_found')
  return rows[0]
}

Deno.serve(async req=>{
  if(req.method==='GET')return json({ok:true,service:'product-run-observability-gateway',version:'1.0',contract:{durable_failure_state:true}})
  if(req.method!=='POST')return json({error:'method_not_allowed'},405)
  try{
    await auth(req)
    const b=await req.json(),action=String(b.action||'')
    if(action==='health')return json({ok:true,version:'1.0'})
    if(action==='ranking_fail'){const r=await failRun(b);return json({ok:true,run_id:r.id,status:'failed'})}
    throw new Error('action_not_allowed')
  }catch(e){
    const message=String(e instanceof Error?e.message:e);console.error(e)
    const authFailure=message.includes('oidc')||message.includes('"exp" claim timestamp check failed')||message.includes('JWTExpired')
    return json({error:message},authFailure?401:500)
  }
})
