import crypto from 'node:crypto';
import {createClient} from '@supabase/supabase-js';
import {APPROVED_SUPABASE_URL,APPROVED_PUBLISHABLE_KEY} from './supabase-config.js';
const key=()=>process.env.VMDB_SUPABASE_SERVICE_ROLE_KEY ||
   (process.env.SUPABASE_URL===APPROVED_SUPABASE_URL?process.env.SUPABASE_SERVICE_ROLE_KEY:null);

export function aiAvailable(){
 return process.env.SHOPPER_PUBLIC_AI_ENABLED==='true'&&!!key();
}
export function visitorHash(req,secret){
 // Treat forwarding headers as advisory. A WAF rule is still required at launch.
 const ip=String(req.headers.get('x-vercel-forwarded-for')||req.headers.get('x-forwarded-for')||'anonymous').split(',')[0].trim().slice(0,64);
 const ua=String(req.headers.get('user-agent')||'unknown').slice(0,180);
 return crypto.createHmac('sha256',secret).update(ip+'|'+ua).digest('hex');
}
export async function takeSlot(req){
 const token=key();if(!token) return false;
 const db=createClient(APPROVED_SUPABASE_URL,token,{auth:{persistSession:false,autoRefreshToken:false}});
 const actor=visitorHash(req,token);
 const {data,error}=await db.rpc('shopper_take_daily_slot',{p_actor_hash:actor,p_limit:3});
 if(error){console.error('[buyer-ai] quota not ready:',error.message);return false;}
 return data===true;
}
export async function completeViaGateway(task){
 const token=key();
 if(!token||!aiAvailable())throw new Error('model_not_authorized');
 const r=await fetch(APPROVED_SUPABASE_URL+'/functions/v1/shopper-ai-gateway',{
   method:'POST',
   headers:{'Content-Type':'application/json','Authorization':'Bearer '+token,'apikey':APPROVED_PUBLISHABLE_KEY},
   body:JSON.stringify({task:'buyer-crew',max_tokens:Math.min(550,Math.max(160,Number(task.maxTokens||450))),
     messages:task.messages.map(x=>({role:x.role,content:String(x.content||'').slice(0,8500)}))}),
   signal:AbortSignal.timeout(26000),cache:'no-store'
 });
 if(!r.ok)throw new Error('gateway_unavailable');
 const result=await r.json();
 if(!result?.content||typeof result.content!=='string')throw new Error('empty_ai_response');
 return {content:result.content,provider:result.provider||'private_gateway',model:result.model||'not_reported'};
}
