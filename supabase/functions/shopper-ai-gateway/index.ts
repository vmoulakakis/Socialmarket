import 'jsr:@supabase/functions-js/edge-runtime.d.ts';
import {createClient} from 'npm:@supabase/supabase-js@2.57.4';
import postgres from 'npm:postgres@3.4.5';

// Internal gateway, not a browser API. Existing service-role key is mandatory.
const json=(data:unknown,status=200)=>new Response(JSON.stringify(data),
 {status,headers:{'content-type':'application/json','cache-control':'no-store','x-robots-tag':'noindex'}});
function equal(a:string,b:string):boolean {
 const enc=new TextEncoder(),x=enc.encode(a),y=enc.encode(b);
 if(!x.length||x.length!==y.length)return false;
 let diff=0;for(let i=0;i<x.length;i++)diff|=x[i]^y[i];
 return diff===0;
}
Deno.serve(async(req:Request)=>{
 if(req.method==='GET')return json({ok:true,service:'shopper-ai-gateway',private:true,version:1});
 if(req.method!=='POST')return json({error:'method_not_allowed'},405);
 const service=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')||'';
 const bearer=(req.headers.get('authorization')||'').replace(/^Bearer /,'');
 if(!service||!equal(bearer,service))return json({error:'internal_service_auth_required'},401);
 let body:any;
 try{
   const raw=await req.text();
   if(raw.length>12000)return json({error:'payload_too_large'},413);
   body=JSON.parse(raw);
 }catch{return json({error:'invalid_json'},400);}
 if(body?.task!=='buyer-crew'||!Array.isArray(body.messages)||body.messages.length!==2)
   return json({error:'unsupported_task'},400);
 const messages=body.messages;
 if(messages.some((m:any)=>!m||!['system','user'].includes(m.role)||typeof m.content!=='string')||
    messages[0].role!=='system'||messages[1].role!=='user'||
    messages[0].content.length>3600||messages[1].content.length>8500)
   return json({error:'unsafe_messages'},400);
 const maxTokens=Math.max(160,Math.min(550,Number(body.max_tokens)||450));
 const url=Deno.env.get('SUPABASE_URL')||'';
 const db=createClient(url,service,{auth:{persistSession:false,autoRefreshToken:false}});
 const reservations:any[]=[];
 let dispatched=false;
 try{
   for(const [metric,quantity] of [['shopper_llm_calls',1],['remote_llm_calls',1],['llm_output_tokens',maxTokens]] as [string,number][]){
     const {data,error}=await db.rpc('reserve_agent_budget',{
       p_metric:metric,p_quantity:quantity,p_actor:'socialmarket-shopper',
       p_provider:'deepseek',p_metadata:{task:'buyer-crew',gateway:'shopper-ai-gateway'}
     });
     if(error||!data?.allowed)throw Error('budget_unavailable');
     reservations.push({metric,...data});
   }
   const pgUrl=Deno.env.get('SUPABASE_DB_URL');
   if(!pgUrl)throw Error('provider_configuration_unavailable');
   const sql=postgres(pgUrl,{max:1,prepare:false,connect_timeout:5,ssl:'require'});
   let providerKey:string|undefined;
   try{
     const out=await sql.unsafe("SELECT decrypted_secret FROM vault.decrypted_secrets WHERE name='deepseek_api_key' LIMIT 1");
     providerKey=out[0]?.decrypted_secret;
   }finally{await sql.end({timeout:1}).catch(()=>{});}
   if(!providerKey)throw Error('provider_configuration_unavailable');
   const modelRes=await fetch('https://api.deepseek.com/models',{
     headers:{authorization:'Bearer '+providerKey},signal:AbortSignal.timeout(5500)
   });
   if(!modelRes.ok)throw Error('provider_models_unavailable');
   const models=(await modelRes.json()).data?.map((m:{id:string})=>m.id)||[];
   const model=[Deno.env.get('SOCIALMARKET_DEEPSEEK_MODEL'),'deepseek-chat','deepseek-v4-flash']
     .find(m=>m&&models.includes(m));
   if(!model)throw Error('compatible_model_unavailable');
   dispatched=true;
   const r=await fetch('https://api.deepseek.com/chat/completions',{
     method:'POST',headers:{authorization:'Bearer '+providerKey,'content-type':'application/json'},
     body:JSON.stringify({model,messages,temperature:0,max_tokens:maxTokens,response_format:{type:'json_object'}}),
     signal:AbortSignal.timeout(22000)
   });
   if(!r.ok)throw Error('provider_request_failed');
   const response=await r.json();
   const content=response.choices?.[0]?.message?.content;
   if(typeof content!=='string'||!content||content.length>14000)throw Error('invalid_provider_response');
   const used=Math.max(0,Math.min(maxTokens,Number(response.usage?.completion_tokens)||maxTokens));
   for(const x of reservations){
     await db.rpc('finalize_agent_budget',{p_reservation_id:x.reservation_id,
       p_actual_quantity:x.metric==='llm_output_tokens'?used:1,p_metadata:{ok:true,model}});
   }
   return json({ok:true,content,provider:'deepseek',model});
 }catch(e){
   const reason=e instanceof Error?e.message:'provider_unavailable';
   for(const x of reservations){
     try{
       if(dispatched)await db.rpc('finalize_agent_budget',{
         p_reservation_id:x.reservation_id,p_actual_quantity:x.metric==='llm_output_tokens'?maxTokens:1,
         p_metadata:{ok:false,reason:'provider_or_json_failure'}});
       else await db.rpc('release_agent_budget',{p_reservation_id:x.reservation_id});
     }catch{/* Audit reconciliation errors are logged outside this response. */}
   }
   return json({error:'ai_temporarily_unavailable',reason:
     ['budget_unavailable','provider_configuration_unavailable','compatible_model_unavailable'].includes(reason)?
       reason:'provider_failure'},503);
 }
});
