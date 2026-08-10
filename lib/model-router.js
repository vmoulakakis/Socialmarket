async function post(url,key,body){
 const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json','Authorization':`Bearer ${key}`},body:JSON.stringify(body)});
 if(!r.ok) throw new Error(`${r.status} ${await r.text()}`);
 return r.json();
}

export async function agentCompletion(o){
 const deepseek=process.env.DEEPSEEK_API_KEY;
 const deepseekModel=process.env.DEEPSEEK_MODEL||'deepseek-chat';
 if(deepseek){
  try{
   const data=await post('https://api.deepseek.com/chat/completions',deepseek,{model:deepseekModel,messages:o.messages,temperature:o.temperature??0.2,response_format:o.json?{type:'json_object'}:undefined,tools:o.tools});
   return {provider:'deepseek',model:deepseekModel,content:data.choices?.[0]?.message?.content??'',message:data.choices?.[0]?.message??null};
  }catch(e){console.error('DeepSeek failed, using OpenRouter failover',e)}
 }
 const openrouter=process.env.OPENROUTER_API_KEY;
 if(openrouter){
  const fallbackModel=process.env.OPENROUTER_FALLBACK_MODEL||'openrouter/free';
  const data=await post('https://openrouter.ai/api/v1/chat/completions',openrouter,{model:fallbackModel,messages:o.messages,temperature:o.temperature??0.2,response_format:o.json?{type:'json_object'}:undefined,tools:o.tools});
  return {provider:'openrouter',model:fallbackModel,content:data.choices?.[0]?.message?.content??'',message:data.choices?.[0]?.message??null};
 }
 throw new Error('No AI provider configured. Evidence-first market workflows can still run without an LLM; AI refinement cannot.');
}
