import {NextResponse} from 'next/server';
import {APPROVED_PUBLISHABLE_KEY,APPROVED_SUPABASE_URL} from '@/lib/supabase-config';

export const dynamic='force-dynamic';

function authHeader(req){
  const auth=req.headers.get('authorization')||'';
  if(!auth.startsWith('Bearer ')) return null;
  return auth;
}

export async function GET(req){
  const authorization=authHeader(req);
  if(!authorization) return NextResponse.json({error:'admin_session_required'},{status:401});

  try{
    const upstream=await fetch(`${APPROVED_SUPABASE_URL}/rest/v1/rpc/admin_dashboard_snapshot`,{
      method:'POST',
      headers:{
        apikey:APPROVED_PUBLISHABLE_KEY,
        authorization,
        'content-type':'application/json',
        accept:'application/json',
      },
      body:'{}',
      cache:'no-store',
    });
    const text=await upstream.text();
    let payload;
    try{payload=text?JSON.parse(text):null}catch{payload={error:text||`upstream_${upstream.status}`}}
    return NextResponse.json(payload,{status:upstream.status,headers:{'cache-control':'no-store'}});
  }catch(error){
    return NextResponse.json({error:'dashboard_upstream_unreachable',detail:String(error?.message||error)},{status:502});
  }
}
