import { NextResponse } from 'next/server';
import { agentCompletion } from '@/lib/model-router';
import {adminAuth} from '@/lib/admin-auth';

export const maxDuration=60;
export async function POST(req){
 const auth=await adminAuth(req);
 if(!auth)return NextResponse.json({error:'admin_session_required'},{status:401});
 try{
  const body=await req.json();const posts=Array.isArray(body.posts)?body.posts.slice(0,25):[];
  if(!posts.length)return NextResponse.json({error:'posts_required'},{status:400});
  const compact=posts.map(p=>({id:p.id,strategy:p.strategy||'conversion',product:{product_name:p.product?.product_name,brand_name:p.product?.brand_name,category_raw:p.product?.category_raw,merchant_name:p.product?.merchant_name,price:p.product?.price,full_price:p.product?.full_price,discount_pct:p.product?.discount_pct,merchant_trust_score:p.product?.merchant_trust_score,selection_score:p.product?.selection_score}}));
  try{
   const ai=await agentCompletion({accessToken:auth.accessToken,json:true,temperature:.55,messages:[{role:'system',content:`You are a senior Greek TikTok performance creative strategist. Return strict JSON {"posts":[...]}. For each supplied id create natural Greek copy that feels native, human and non-spammy. Never invent product features, stock scarcity, reviews, demand, delivery promises, or performance claims. You may use only supplied product facts. Each object: id, hook (max 90 chars), title (max 90), caption (max 1200), hashtags (4-7 strings), strategy, creative_spec. creative_spec must include aspect_ratio:"9:16", duration_seconds 8-15, template, qr:false, baked_url:false, promotional_watermark:false, shot_plan:[4 concise beats]. Do not put tracking URLs, QR instructions or affiliate language in TikTok media/caption. Prefer pattern interrupt, price anchoring when factual, identity/lifestyle framing, curiosity gap, and one clear native CTA. Avoid #fyp spam unless strongly justified.`},{role:'user',content:JSON.stringify({posts:compact})}]});
   const parsed=JSON.parse(ai.content||'{}');
   if(!Array.isArray(parsed.posts))throw new Error('invalid_ai_json');
   return NextResponse.json({provider:ai.provider,model:ai.model,posts:parsed.posts});
  }catch(e){return NextResponse.json({error:'ai_refinement_unavailable'}, {status:503})}
 }catch(e){return NextResponse.json({error:String(e.message||e)},{status:500})}
}
