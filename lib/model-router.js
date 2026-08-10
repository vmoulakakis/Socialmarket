async function post(url,key,body){const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json','Authorization':`Bearer ${key}`},body:JSON.stringify(body)});if(!r.ok) throw new Error(`${r.status} ${await r.text()}`);return r.json()}
export async function agentCompletion(o){
 const deepseek=process.env.DEEPSEEK_API_KEY;
 if(deepseek){try{const data=await post('https://api.deepseek.com/chat/completions',deepseek,{model:'deepseek-chat',messages:o.messages,temperature:o.temperature??0.2,response_format:o.json?{type:'json_object'}:undefined});return {provider:'deepseek',content:data.choices?.[0]?.message?.content??''}}catch(e){console.error('DeepSeek failed, using failover',e)}}
 const openrouter=process.env.OPENROUTER_API_KEY;
 if(openrouter){const data=await post('https://openrouter.ai/api/v1/chat/completions',openrouter,{model:'openrouter/free',messages:o.messages,temperature:o.temperature??0.2,response_format:o.json?{type:'json_object'}:undefined});return {provider:'openrouter/free',content:data.choices?.[0]?.message?.content??''}}
 throw new Error('No AI provider configured.');
}
