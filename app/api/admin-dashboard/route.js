import {NextResponse} from 'next/server';
import {APPROVED_PUBLISHABLE_KEY,APPROVED_SUPABASE_URL} from '@/lib/supabase-config';
export const dynamic='force-dynamic';
export async function GET(req){
 const authorization=req.headers.get('authorization')||'';
 if(!authorization.startsWith('Bearer '))return NextResponse.json({error:'admin_session_required'},{status:401});
 try{
  const upstream=await fetch(`${APPROVED_SUPABASE_URL}/rest/v1/rpc/socialmarket_workspace`,{method:'POST',headers:{apikey:APPROVED_PUBLISHABLE_KEY,authorization,'content-type':'application/json'},body:JSON.stringify({p_section:'overview'}),cache:'no-store',signal:AbortSignal.timeout(15000)});
  const payload=await upstream.json();
  return NextResponse.json(payload,{status:upstream.status,headers:{'cache-control':'no-store'}});
 }catch{return NextResponse.json({error:'dashboard_upstream_unreachable'},{status:502});}
}
