import {createHash} from 'node:crypto';

export const dynamic='force-dynamic';
const base=process.env.NEXT_PUBLIC_SUPABASE_URL||'https://prrehmcvpyhupvlhtbzg.supabase.co';
const key=process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY||'';
const hdr=(extra={})=>({apikey:key,Authorization:`Bearer ${key}`,'Content-Type':'application/json',...extra});

export async function GET(req,{params}){
  const {slug}=await params;
  if(!key||!slug)return new Response('Link unavailable',{status:503});
  const q=new URL(`${base}/rest/v1/affiliate_redirects`);q.searchParams.set('slug',`eq.${slug}`);q.searchParams.set('active','eq.true');q.searchParams.set('select','id,slug,platform,tracking_url_snapshot,valid_until');q.searchParams.set('limit','1');
  const r=await fetch(q,{headers:hdr(),cache:'no-store'});const rows=r.ok?await r.json():[];const hit=rows?.[0];
  if(!hit)return new Response('Link not found',{status:404});
  if(hit.valid_until&&new Date(hit.valid_until).getTime()<Date.now())return new Response('Offer expired',{status:410});
  const ua=req.headers.get('user-agent')||'',ref=req.headers.get('referer')||'';const fp=createHash('sha256').update(`${ua}|${ref}`).digest('hex').slice(0,24);
  fetch(`${base}/rest/v1/affiliate_click_events`,{method:'POST',headers:hdr({Prefer:'return=minimal'}),body:JSON.stringify({redirect_id:hit.id,slug:hit.slug,platform:hit.platform,referrer:ref.slice(0,1200),user_agent_hash:createHash('sha256').update(ua).digest('hex').slice(0,32),request_fingerprint:fp})}).catch(()=>{});
  return Response.redirect(hit.tracking_url_snapshot,302);
}
