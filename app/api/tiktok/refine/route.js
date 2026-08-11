import { NextResponse } from 'next/server';
import { agentCompletion } from '@/lib/model-router';

function safeTag(v){return '#'+String(v||'SmartFind').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-zA-Z0-9Α-Ωα-ω]/g,'').slice(0,28)}
function fallback(posts){
 return posts.map(p=>{
  const x=p.product||{};const d=Number(x.discount_pct||0);const price=Number(x.price||0);const full=Number(x.full_price||0);
  const hook=d>=45?`Σχεδόν μισή τιμή — αλλά αξίζει;`:d>=30?`Αυτό το deal έχει ενδιαφέρον για έναν λόγο.`:`Ένα προϊόν που πέρασε κάτω από το radar.`;
  const caption=d>=30&&full?`${x.brand_name||''} ${x.product_name||''}: ${price.toFixed(2)}€ από ${full.toFixed(2)}€. Το σημαντικό δεν είναι μόνο η έκπτωση — είναι αν ταιριάζει πραγματικά σε αυτό που ψάχνεις.`:`${x.brand_name||''} ${x.product_name||''}: μια επιλογή που ξεχώρισε για value, merchant trust και χαμηλότερο commercial saturation.`;
  return {id:p.id,hook,title:String(`${x.brand_name||''} ${x.product_name||''}`).trim().slice(0,90),caption:caption.slice(0,1200),hashtags:[safeTag(x.brand_name),safeTag((x.category_raw||'Product').split('>').pop()),'#SmartFind','#SocialMarketGR'],creative_spec:{aspect_ratio:'9:16',duration_seconds:d>=35?9:12,template:d>=35?'Deal Reveal':'Problem → Product → Proof → CTA',qr:false,baked_url:false,promotional_watermark:false}};
 })
}

export async function POST(req){
 try{
  const body=await req.json();const posts=Array.isArray(body.posts)?body.posts.slice(0,25):[];
  if(!posts.length)return NextResponse.json({error:'posts_required'},{status:400});
  const compact=posts.map(p=>({id:p.id,strategy:p.strategy||'conversion',product:{product_name:p.product?.product_name,brand_name:p.product?.brand_name,category_raw:p.product?.category_raw,merchant_name:p.product?.merchant_name,price:p.product?.price,full_price:p.product?.full_price,discount_pct:p.product?.discount_pct,merchant_trust_score:p.product?.merchant_trust_score,selection_score:p.product?.selection_score}}));
  try{
   const ai=await agentCompletion({json:true,temperature:.55,messages:[{role:'system',content:`You are a senior Greek TikTok performance creative strategist. Return strict JSON {"posts":[...]}. For each supplied id create natural Greek copy that feels native, human and non-spammy. Never invent product features, stock scarcity, reviews, demand, delivery promises, or performance claims. You may use only supplied product facts. Each object: id, hook (max 90 chars), title (max 90), caption (max 1200), hashtags (4-7 strings), strategy, creative_spec. creative_spec must include aspect_ratio:"9:16", duration_seconds 8-15, template, qr:false, baked_url:false, promotional_watermark:false, shot_plan:[4 concise beats]. Do not put tracking URLs, QR instructions or affiliate language in TikTok media/caption. Prefer pattern interrupt, price anchoring when factual, identity/lifestyle framing, curiosity gap, and one clear native CTA. Avoid #fyp spam unless strongly justified.`},{role:'user',content:JSON.stringify({posts:compact})}]});
   const parsed=JSON.parse(ai.content||'{}');
   if(!Array.isArray(parsed.posts))throw new Error('invalid_ai_json');
   return NextResponse.json({provider:ai.provider,model:ai.model,posts:parsed.posts});
  }catch(e){return NextResponse.json({provider:'deterministic-fallback',model:null,warning:String(e.message||e),posts:fallback(compact)})}
 }catch(e){return NextResponse.json({error:String(e.message||e)},{status:500})}
}
