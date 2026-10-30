import {NextResponse} from 'next/server';
import {adminAuth} from '@/lib/admin-auth';
import {APPROVED_PUBLISHABLE_KEY,APPROVED_SUPABASE_URL} from '@/lib/supabase-config';

export const runtime='nodejs';
export const dynamic='force-dynamic';
export const maxDuration=30;

const ACTIONS=new Set(['sync_search_docs','queue_research','pause_objective','resume_objective']);
const HEADERS={'cache-control':'private, no-store, max-age=0','x-content-type-options':'nosniff'};
async function proxyRpc(accessToken,fn,body){
 const upstream=await fetch(APPROVED_SUPABASE_URL+'/rest/v1/rpc/'+fn,{
  method:'POST',headers:{'content-type':'application/json','apikey':APPROVED_PUBLISHABLE_KEY,
   'authorization':'Bearer '+accessToken},body:JSON.stringify(body),
  cache:'no-store',signal:AbortSignal.timeout(25000)
 });
 const result=await upstream.json().catch(()=>null);
 if(!upstream.ok){
  // Never leak SQL/PostgREST internals to the browser.
  return NextResponse.json({ok:false,error:upstream.status===403?'admin_access_denied':'cockpit_backend_unavailable'},
   {status:upstream.status===401||upstream.status===403?403:502,headers:HEADERS});
 }
 return NextResponse.json(result,{status:200,headers:HEADERS});
}

export async function GET(req){
 const auth=await adminAuth(req);
 if(!auth)return NextResponse.json({ok:false,error:'admin_login_required'},{status:401,headers:HEADERS});
 try{return await proxyRpc(auth.accessToken,'socialmarket_cockpit_snapshot',{});}
 catch{return NextResponse.json({ok:false,error:'cockpit_backend_timeout'},{status:503,headers:HEADERS});}
}
export async function POST(req){
 const auth=await adminAuth(req);
 if(!auth)return NextResponse.json({ok:false,error:'admin_login_required'},{status:401,headers:HEADERS});
 const size=Number(req.headers.get('content-length')||0);
 if(size>2000)return NextResponse.json({error:'request_too_large'},{status:413,headers:HEADERS});
 let payload;try{payload=await req.json()}catch{return NextResponse.json({error:'invalid_json'},{status:400,headers:HEADERS})}
 const action=payload?.action;
 const target=payload?.target??null;
 if(!ACTIONS.has(action)||Object.keys(payload).some(k=>!['action','target'].includes(k))
  ||(target!==null&&(typeof target!=='string'||!/^[-a-z_0-9]{1,80}$/.test(target)))
  ||(action==='pause_objective'||action==='resume_objective'?target===null:target!==null)){
  return NextResponse.json({error:'unsupported_operation'},{status:400,headers:HEADERS});
 }
 try{return await proxyRpc(auth.accessToken,'socialmarket_cockpit_command',
       {p_action:action,p_target:target})}
 catch{return NextResponse.json({error:'command_backend_unavailable'},{status:503,headers:HEADERS});}
}
