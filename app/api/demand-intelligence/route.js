import {NextResponse} from 'next/server';
import {APPROVED_PUBLISHABLE_KEY,APPROVED_SUPABASE_URL} from '@/lib/supabase-config';
import config from '@/config/demand-intelligence-v3.json';
import {deriveDemandV3} from '@/lib/demand-v3';
export const dynamic='force-dynamic';
export const maxDuration=60;
export async function POST(req){
 const authorization=req.headers.get('authorization')||'';
 if(!authorization.startsWith('Bearer '))return NextResponse.json({error:'admin_session_required'},{status:401});
 let body;try{body=await req.json();}catch{return NextResponse.json({error:'invalid_json'},{status:400});}
 if(!body||!/^\w{8}-\w{4}-\w{4}-\w{4}-\w{12}$/.test(body.taxonomy_id||''))return NextResponse.json({error:'valid_taxonomy_id_required'},{status:400});
 try{
  const upstream=await fetch(`${APPROVED_SUPABASE_URL}/rest/v1/rpc/socialmarket_workspace`,{method:'POST',headers:{apikey:APPROVED_PUBLISHABLE_KEY,authorization,'content-type':'application/json'},body:JSON.stringify({p_section:'demand-context',p_id:body.taxonomy_id,p_limit:90}),cache:'no-store',signal:AbortSignal.timeout(15000)});
  const payload=await upstream.json();
  if(!upstream.ok)return NextResponse.json(payload,{status:upstream.status});
  const context=payload.context;
  if(!context?.market)return NextResponse.json({error:'problem_cluster_not_found'},{status:404});
  let analysis=null,ai_error=null,model=null;
  if(body.action!=='context'){
   const aiRes=await fetch(`${APPROVED_SUPABASE_URL}/functions/v1/socialmarket-ai`,{method:'POST',headers:{apikey:APPROVED_PUBLISHABLE_KEY,authorization,'content-type':'application/json'},body:JSON.stringify({task:'demand',taxonomy_id:body.taxonomy_id,max_tokens:1200}),signal:AbortSignal.timeout(30000)});
   const ai=await aiRes.json();
   if(aiRes.ok){try{analysis=JSON.parse(ai.content);model=ai.model;}catch{ai_error='invalid_ai_response';}}
   else ai_error=ai.detail||ai.error||'canonical_ai_unavailable';
  }
  return NextResponse.json({ok:true,context,deterministic:deriveDemandV3(context,config),analysis,ai_error,model,config_version:config.version},{headers:{'cache-control':'no-store'}});
 }catch{return NextResponse.json({error:'demand_intelligence_upstream_unreachable'},{status:502});}
}
