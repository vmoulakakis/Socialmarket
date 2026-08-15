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
const json=(x:unknown,s=200)=>new Response(JSON.stringify(x),{status:s,headers:{'content-type':'application/json','cache-control':'no-store'}})

async function auth(req:Request){
  const h=req.headers.get('authorization')||''
  if(!h.startsWith('Bearer '))throw new Error('missing_oidc')
  const {payload}=await jwtVerify(h.slice(7),JWKS,{issuer:ISSUER,audience:AUDIENCE})
  if(String(payload.repository_id||'')!==REPOSITORY_ID||String(payload.repository||'')!==REPOSITORY||String(payload.ref||'')!=='refs/heads/main'||!ALLOWED.has(String(payload.workflow_ref||'')))throw new Error('oidc_not_allowed')
}

async function currentConfig(){
  const rows=await sql`select config,version,updated_by,updated_at from ops.product_intelligence_config where id=1 limit 1`
  if(!rows.length)throw new Error('product_config_missing')
  return rows[0]
}

Deno.serve(async(req:Request)=>{
  if(req.method==='OPTIONS')return new Response('ok')
  try{
    await auth(req)
    if(req.method==='GET')return json({ok:true,...await currentConfig()})
    if(req.method!=='POST')return json({error:'method_not_allowed'},405)
    const body=await req.json();const action=String(body.action||'config')
    if(action==='config')return json({ok:true,...await currentConfig()})
    if(action==='save_run_profile'){
      const phase=String(body.phase||'')
      if(!['A','B'].includes(phase))throw new Error('invalid_phase')
      const profile=body.profile
      if(!profile||typeof profile!=='object'||Array.isArray(profile))throw new Error('invalid_profile')
      const cfg=await currentConfig()
      const rows=await sql`insert into ops.product_intelligence_run_profiles(phase,status,config_version,profile) values(${phase},${String(body.status||'completed')},${Number(cfg.version||0)},${sql.json(profile)}) returning id,recorded_at`
      return json({ok:true,...rows[0],config_version:cfg.version})
    }
    throw new Error('action_not_allowed')
  }catch(e){return json({error:String((e as Error)?.message||e)},401)}
})
