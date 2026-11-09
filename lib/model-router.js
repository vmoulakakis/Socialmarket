import {APPROVED_PUBLISHABLE_KEY,APPROVED_SUPABASE_URL} from '@/lib/supabase-config';
import {freePolicy,freeOpenRouterModels} from '@/lib/free-llm-policy.mjs';
import {finalizeBudget,releaseBudget,reserveBudget} from '@/lib/orchestrator/store';

const MAX_OUTPUT_TOKENS=Math.max(128,Math.min(Number(process.env.AGENT_MAX_OUTPUT_TOKENS||900),1600));
const AI_TIMEOUT_MS=Math.max(5000,Math.min(Number(process.env.AGENT_AI_TIMEOUT_MS||20000),30000));

async function post(url,key,body){
 const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json','Authorization':`Bearer ${key}`},body:JSON.stringify(body),signal:AbortSignal.timeout(AI_TIMEOUT_MS)});
 if(!r.ok) throw new Error(`${r.status} ${await r.text()}`);
 return r.json();
}

function outputTokens(data){
 return Number(data?.usage?.completion_tokens??data?.usage?.output_tokens??0)||0;
}

async function budgetedCall({provider,model,premium=false,o,call}){
 const maxTokens=Math.min(o.maxTokens||MAX_OUTPUT_TOKENS,MAX_OUTPUT_TOKENS);
 const common={runId:o.runId||null,actor:o.actor||'orchestrator',provider,model,metadata:{capability:o.capability||null}};
 let callBudget=null,tokenBudget=null,premiumBudget=null;
 try{
  callBudget=await reserveBudget('remote_llm_calls',1,common,o.accessToken||null);
  tokenBudget=await reserveBudget('llm_output_tokens',maxTokens,common,o.accessToken||null);
  if(premium) premiumBudget=await reserveBudget('premium_llm_calls',1,common,o.accessToken||null);
  const data=await call(maxTokens);
  await finalizeBudget(callBudget.reservation_id,1,{ok:true},o.accessToken||null);
  await finalizeBudget(tokenBudget.reservation_id,outputTokens(data),{ok:true},o.accessToken||null);
  if(premiumBudget) await finalizeBudget(premiumBudget.reservation_id,1,{ok:true},o.accessToken||null);
  return data;
 }catch(e){
  await Promise.allSettled([
   callBudget?.reservation_id?releaseBudget(callBudget.reservation_id,o.accessToken||null):Promise.resolve(),
   tokenBudget?.reservation_id?releaseBudget(tokenBudget.reservation_id,o.accessToken||null):Promise.resolve(),
   premiumBudget?.reservation_id?releaseBudget(premiumBudget.reservation_id,o.accessToken||null):Promise.resolve()
  ]);
  throw e;
 }
}

async function groqFreeCall(key,o){
 const model='openai/gpt-oss-20b';
 const data=await budgetedCall({
  provider:'groq',model,o,
  call:maxTokens=>post('https://api.groq.com/openai/v1/chat/completions',key,{
   model,messages:o.messages,temperature:o.temperature??0.2,max_tokens:maxTokens,
   response_format:o.json?{type:'json_object'}:undefined
  })
 });
 const content=data.choices?.[0]?.message?.content;
 if(typeof content!=='string'||!content.trim())throw new Error('groq_empty_completion');
 if(o.json)JSON.parse(content);
 return {provider:'groq',model,content,message:data.choices?.[0]?.message??null,usage:data.usage??null};
}

async function deepseekCall(key,model,o,premium=false){
 const data=await budgetedCall({provider:'deepseek',model,premium,o,call:(maxTokens)=>post('https://api.deepseek.com/chat/completions',key,{model,messages:o.messages,temperature:o.temperature??0.2,max_tokens:maxTokens,response_format:o.json?{type:'json_object'}:undefined,tools:o.tools})});
 return {provider:'deepseek',model,content:data.choices?.[0]?.message?.content??'',message:data.choices?.[0]?.message??null,usage:data.usage??null};
}

async function tryOpenRouter(o,{freeOnly=false}={}){
 const key=process.env.OPENROUTER_API_KEY;
 if(!key)return null;
 const configured=process.env.OPENROUTER_FALLBACK_MODEL||'nvidia/nemotron-3-ultra-550b-a55b:free';
 const models=freeOnly?freeOpenRouterModels(configured):[configured,'openrouter/free'];
 for(const model of models){
  try{
   const data=await budgetedCall({
    provider:'openrouter',model,o,
    call:maxTokens=>post('https://openrouter.ai/api/v1/chat/completions',key,{
     model,messages:o.messages,temperature:o.temperature??0.2,max_tokens:maxTokens,
     response_format:o.json?{type:'json_object'}:undefined,
     tools:o.tools
    })
   });
   const content=data.choices?.[0]?.message?.content??'';
   if(!content&&!data.choices?.[0]?.message?.tool_calls)throw new Error('empty_openrouter_response');
   if(o.json)JSON.parse(content);
   return {provider:'openrouter',model,content,message:data.choices?.[0]?.message??null,usage:data.usage??null};
  }catch(e){console.error('OpenRouter free inference failed',e?.name||'error')}
 }
 return null;
}

async function tryDeepseek(o){
 const deepseek=process.env.DEEPSEEK_API_KEY;
 if(!deepseek)return null;
 const primary=process.env.DEEPSEEK_MODEL||'deepseek-v4-flash';
 try{return await deepseekCall(deepseek,primary,o,false)}catch(e){console.error('DeepSeek primary failed',e?.name||'error')}
 if(primary!=='deepseek-v4-pro'&&o.allowPremiumEscalation===true){
  try{return await deepseekCall(deepseek,'deepseek-v4-pro',o,true)}catch(e){console.error('DeepSeek Pro escalation failed',e?.name||'error')}
 }
 return null;
}

export async function agentCompletion(o){
 const policy=freePolicy(process.env);
 // Keep the canonical budget ledger; never bypass agent/tool approval gates.
 // Free routes must not be assumed to implement tool calling consistently.
 const allowFree=!Array.isArray(o.tools)||o.tools.length===0;
 if(policy.enabled){
  if(allowFree&&policy.groq){
   try{return await groqFreeCall(process.env.GROQ_API_KEY,o)}
   catch(e){console.error('Groq free inference failed',e?.name||'error')}
  }
  if(allowFree&&policy.openrouter){
   const result=await tryOpenRouter(o,{freeOnly:true});
   if(result)return result;
  }
  // When free-only is enabled, fail closed. No paid or unverified fallback.
  if(policy.freeOnly)throw new Error('free_llm_exhausted_or_unavailable');
 }
 const deepseek=await tryDeepseek(o);
 if(deepseek)return deepseek;
 const openrouter=await tryOpenRouter(o,{freeOnly:false});
 if(openrouter)return openrouter;
 if(o.accessToken){
  const r=await fetch(APPROVED_SUPABASE_URL+'/functions/v1/socialmarket-ai',{
   method:'POST',headers:{apikey:APPROVED_PUBLISHABLE_KEY,authorization:'Bearer '+o.accessToken,'content-type':'application/json'},
   body:JSON.stringify({task:'completion',messages:o.messages,max_tokens:Math.min(o.maxTokens||MAX_OUTPUT_TOKENS,MAX_OUTPUT_TOKENS)}),signal:AbortSignal.timeout(30000)
  });
  const result=await r.json();
  if(!r.ok)throw new Error(result.error||'canonical_ai_unavailable');
  return result;
 }
 throw new Error('No usable AI provider/budget available. Deterministic workflows can still run; AI refinement cannot.');
}
