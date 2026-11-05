import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import {createClient} from "npm:@supabase/supabase-js@2.57.4";

const EXPECTED_SECRET_SHA256="b3f2c332847d0dae5d339c482b90c59b599dde78b25d698271835b73b58ffc80";
const EnglishKnowledge:Record<string,string>={
 ev_battery_health:"Used electric vehicle battery health, state of health, battery degradation, inspection before buying a secondhand EV; specialist diagnostics required.",
 dpf_diagnostics:"Diesel particulate filter DPF system diagnostic pressure temperature fault codes before expensive part replacement.",
 ac_microleaks:"Car air conditioning refrigerant microleak recurring, technician leak diagnosis and legal refrigerant handling.",
 parasitic_battery_drain:"Car battery parasitic drain intermittent electrical consumption troubleshooting by auto electrician."
};
const englishVertical:Record<string,string>={
 automotive:"automotive car parts servicing maintenance",car_insurance:"car insurance policy offers",
 home_insurance:"home property insurance policy",health_insurance:"health insurance policy",
 finance:"banking financial services",other:"other service"
};
const json=(data:unknown,status=200)=>new Response(JSON.stringify(data),{status,headers:{"content-type":"application/json; charset=utf-8","cache-control":"no-store"}});
async function validSecret(header:string|null){
 if(!header||header.length>200)return false;
 const bytes=await crypto.subtle.digest("SHA-256",new TextEncoder().encode(header));
 const hex=[...new Uint8Array(bytes)].map(x=>x.toString(16).padStart(2,"0")).join("");
 let difference=0;for(let i=0;i<64;i++)difference|=hex.charCodeAt(i)^EXPECTED_SECRET_SHA256.charCodeAt(i);
 return difference===0;
}
const text=(x:unknown,max=500)=>String(x??"").slice(0,max);
Deno.serve(async(req:Request)=>{
 if(req.method!=="POST")return json({error:"method_not_allowed"},405);
 if(!await validSecret(req.headers.get("x-carcare-sync-secret")))return json({error:"unauthorized"},401);
 if(Number(req.headers.get("content-length")||0)>1000000)return json({error:"payload_too_large"},413);
 const supabaseUrl=Deno.env.get("SUPABASE_URL"),serviceKey=Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
 if(!supabaseUrl||!serviceKey)return json({error:"service_configuration_missing"},503);
 const db=createClient(supabaseUrl,serviceKey,{auth:{persistSession:false,autoRefreshToken:false}});
 let payload:any;
 try{payload=await req.json()}catch{return json({error:"invalid_json"},400)}
 const action=text(payload?.action,50);
 try{
  if(action==="start"){
   const n=Number(payload?.source_count||0);
   if(!Number.isInteger(n)||n<0||n>1000000)return json({error:"invalid_source_count"},400);
   const {data,error}=await db.rpc("carcare_sync_start",{p_feed_key:"linkwise_v2",p_source_count:n});
   if(error)throw error;return json({run_id:data,source_count:n});
  }
  if(action==="batch"){
   const rows=payload?.rows;
   if(!Array.isArray(rows)||rows.length>250||!rows.length||typeof payload?.run_id!=="string")return json({error:"invalid_batch"},400);
   for(const row of rows){
    if(row.feed_key!=="linkwise_v2"||!row.product_key||!row.title||!row.tracking_url)return json({error:"invalid_row"},400);
    const u=new URL(row.tracking_url);
    if(u.protocol!=="https:"||!(u.hostname==="linkwi.se"||u.hostname.endsWith(".linkwi.se")||u.hostname==="linkwise.gr"||u.hostname.endsWith(".linkwise.gr")))return json({error:"invalid_tracking"},400);
   }
   const {data,error}=await db.rpc("carcare_ingest_batch",{p_sync_id:payload.run_id,p_rows:rows});
   if(error)throw error;return json({upserted:data});
  }
  if(action==="finish"){
   const accepted=Number(payload?.accepted||0),rejected=Number(payload?.rejected||0);
   if(!Number.isInteger(accepted)||accepted<0||!Number.isInteger(rejected)||rejected<0)return json({error:"invalid_counts"},400);
   const {data,error}=await db.rpc("carcare_sync_finish",{p_sync_id:payload?.run_id,p_accepted:accepted,p_rejected:rejected,p_notes:{"source":"linkwise_v2","source_empty":accepted===0}});
   if(error)throw error;return json({completed:data,state:accepted>0?"completed":"empty_source"});
  }
  if(action==="embed"){
   const max=Math.min(20,Math.max(1,Number(payload?.limit||8)));
   const model=new Supabase.ai.Session("gte-small");
   const kind=payload?.kind==="products"?"products":"knowledge";
   const fn=kind==="products"?"carcare_pending_product_embeddings":"carcare_pending_embeddings";
   const {data:docs,error}=await db.rpc(fn,{p_limit:max});
   if(error)throw error;
   let saved=0;const failed:string[]=[];
   for(const doc of docs||[]){
    const content=kind==="knowledge"
      ?(EnglishKnowledge[doc.document_key]||"Automotive guidance and technical diagnostic knowledge.")
      :[englishVertical[doc.vertical]||"product",doc.brand,doc.title,doc.category].filter(Boolean).join(" ").slice(0,600);
    try{
      const vector=await model.run(content,{mean_pool:true,normalize:true});
      const embedding=Array.from(vector as number[]);
      if(embedding.length!==384)throw Error("vector_dimension_mismatch");
      const store=kind==="products"?"carcare_store_product_embedding":"carcare_store_knowledge_embedding";
      const args=kind==="products"?{p_product_id:doc.id,p_embedding:JSON.stringify(embedding),p_model:"gte-small/en"}:{p_document_id:doc.id,p_embedding:JSON.stringify(embedding),p_model:"gte-small/en"};
      const {error:saveError}=await db.rpc(store,args);
      if(saveError)throw saveError;saved++;
    }catch(e){failed.push(text(e instanceof Error?e.message:e,120))}
   }
   return json({kind,candidates:(docs||[]).length,embedded:saved,failed_count:failed.length,errors:failed.slice(0,3),model:"gte-small/en",language_warning:"English-only model; Greek covered through lexical search."});
  }
  return json({error:"invalid_action"},400);
 }catch(error){console.error("CarCare AI worker:",text(error instanceof Error?error.message:error,160));return json({error:"worker_operation_failed"},503)}
});
