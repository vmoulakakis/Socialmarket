import {NextResponse} from 'next/server';
import {APPROVED_PUBLISHABLE_KEY,APPROVED_SUPABASE_URL} from '@/lib/supabase-config';
import config from '@/config/demand-intelligence-v3.json';
import {deriveDemandV3} from '@/lib/demand-v3';

export const dynamic='force-dynamic';

function authHeader(req){const auth=req.headers.get('authorization')||'';return auth.startsWith('Bearer ')?auth:null}
async function parse(upstream){const text=await upstream.text();try{return text?JSON.parse(text):null}catch{return {error:text||`upstream_${upstream.status}`}}}

export async function POST(req){
 const authorization=authHeader(req);if(!authorization)return NextResponse.json({error:'admin_session_required'},{status:401});
 try{
  const body=await req.json(),taxonomyId=String(body.taxonomy_id||'');
  if(!taxonomyId)return NextResponse.json({error:'taxonomy_id_required'},{status:400});
  const contextRes=await fetch(`${APPROVED_SUPABASE_URL}/rest/v1/rpc/admin_demand_deep_context`,{method:'POST',headers:{apikey:APPROVED_PUBLISHABLE_KEY,authorization,'content-type':'application/json',accept:'application/json'},body:JSON.stringify({p_taxonomy_id:taxonomyId,p_query:body.query||null,p_limit:Math.max(10,Math.min(Number(body.limit||config.retrieval.max_evidence||50),120))}),cache:'no-store'});
  const context=await parse(contextRes);if(!contextRes.ok||context?.error)return NextResponse.json({error:context?.error||`context_${contextRes.status}`,detail:context?.message||context?.detail||null},{status:contextRes.status||502});
  const deterministic=deriveDemandV3(context,config);
  if(body.action==='context')return NextResponse.json({ok:true,context,deterministic,config_version:config.version},{headers:{'cache-control':'no-store'}});
  const aiRes=await fetch(`${APPROVED_SUPABASE_URL}/functions/v1/demand-intelligence-gateway`,{method:'POST',headers:{apikey:APPROVED_PUBLISHABLE_KEY,authorization,'content-type':'application/json',accept:'application/json'},body:JSON.stringify({context,deterministic}),cache:'no-store'});
  const ai=await parse(aiRes);
  if(!aiRes.ok||ai?.error)return NextResponse.json({ok:true,context,deterministic,analysis:null,ai_error:ai?.error||`ai_${aiRes.status}`,ai_detail:ai?.detail||null,config_version:config.version},{headers:{'cache-control':'no-store'}});
  return NextResponse.json({ok:true,context,deterministic,analysis:ai.analysis||null,run_id:ai.run_id||null,model:ai.model||null,usage:ai.usage||null,persist_warning:ai.persist_warning||null,config_version:config.version},{headers:{'cache-control':'no-store'}});
 }catch(error){return NextResponse.json({error:'demand_intelligence_upstream_unreachable',detail:String(error?.message||error)},{status:502})}
}
