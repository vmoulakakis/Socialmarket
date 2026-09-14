const MAX_OUTPUT_TOKENS=Math.max(128,Math.min(Number(process.env.AGENT_MAX_OUTPUT_TOKENS||900),1600));
const AI_TIMEOUT_MS=Math.max(5000,Math.min(Number(process.env.AGENT_AI_TIMEOUT_MS||20000),30000));

async function post(url,key,body){
 const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json','Authorization':`Bearer ${key}`},body:JSON.stringify(body),signal:AbortSignal.timeout(AI_TIMEOUT_MS)});
 if(!r.ok) throw new Error(`${r.status} ${await r.text()}`);
 return r.json();
}

async function deepseekCall(key,model,o){
 const data=await post('https://api.deepseek.com/chat/completions',key,{model,messages:o.messages,temperature:o.temperature??0.2,max_tokens:Math.min(o.maxTokens||MAX_OUTPUT_TOKENS,MAX_OUTPUT_TOKENS),response_format:o.json?{type:'json_object'}:undefined,tools:o.tools});
 return {provider:'deepseek',model,content:data.choices?.[0]?.message?.content??'',message:data.choices?.[0]?.message??null,usage:data.usage??null};
}

export async function agentCompletion(o){
 const deepseek=process.env.DEEPSEEK_API_KEY;
 if(deepseek){
  const primary=process.env.DEEPSEEK_MODEL||'deepseek-v4-flash';
  try{return await deepseekCall(deepseek,primary,o)}catch(e){console.error('DeepSeek primary failed',e)}
  if(primary!=='deepseek-v4-pro'&&o.allowPremiumEscalation===true){
   try{return await deepseekCall(deepseek,'deepseek-v4-pro',o)}catch(e){console.error('DeepSeek Pro escalation failed',e)}
  }
 }
 const openrouter=process.env.OPENROUTER_API_KEY;
 if(openrouter){
  const models=[process.env.OPENROUTER_FALLBACK_MODEL||'nvidia/nemotron-3-ultra-550b-a55b:free','openrouter/free'];
  for(const model of models){
   try{
    const data=await post('https://openrouter.ai/api/v1/chat/completions',openrouter,{model,messages:o.messages,temperature:o.temperature??0.2,max_tokens:Math.min(o.maxTokens||MAX_OUTPUT_TOKENS,MAX_OUTPUT_TOKENS),response_format:o.json?{type:'json_object'}:undefined,tools:o.tools});
    return {provider:'openrouter',model,content:data.choices?.[0]?.message?.content??'',message:data.choices?.[0]?.message??null,usage:data.usage??null};
   }catch(e){console.error(`OpenRouter ${model} failed`,e)}
  }
 }
 throw new Error('No AI provider configured. Deterministic workflows can still run; AI refinement cannot.');
}
