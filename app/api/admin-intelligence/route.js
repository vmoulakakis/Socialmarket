import {NextResponse} from 'next/server';
import {APPROVED_PUBLISHABLE_KEY,APPROVED_SUPABASE_URL} from '@/lib/supabase-config';

export const dynamic='force-dynamic';

export async function POST(req){
  const authorization=req.headers.get('authorization')||'';
  if(!authorization.startsWith('Bearer ')) return NextResponse.json({error:'admin_session_required'},{status:401});

  let body;
  try{body=await req.json()}catch{return NextResponse.json({error:'invalid_json'},{status:400})}

  try{
    const upstream=await fetch(`${APPROVED_SUPABASE_URL}/functions/v1/admin-intelligence-gateway`,{
      method:'POST',
      headers:{
        apikey:APPROVED_PUBLISHABLE_KEY,
        authorization,
        'content-type':'application/json',
        accept:'application/json',
      },
      body:JSON.stringify(body),
      cache:'no-store',
    });
    const text=await upstream.text();
    let payload;
    try{payload=text?JSON.parse(text):null}catch{payload={error:text||`upstream_${upstream.status}`}}
    return NextResponse.json(payload,{status:upstream.status,headers:{'cache-control':'no-store'}});
  }catch(error){
    return NextResponse.json({error:'intelligence_upstream_unreachable',detail:String(error?.message||error)},{status:502});
  }
}
