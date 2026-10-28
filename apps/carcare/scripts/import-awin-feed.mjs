import {createClient} from "@supabase/supabase-js";
import {parseCsv,toText,prepareOffer} from "../lib/awin-feed.mjs";
const env=process.env,id=Number(env.AWIN_ADVERTISER_ID);
if(!Number.isInteger(id)||id<=0||!env.AWIN_DATAFEED_URL||!env.SUPABASE_URL||!env.SUPABASE_SECRET_KEY)throw Error("missing_feed_config");
const url=new URL(env.AWIN_DATAFEED_URL);
if(url.protocol!=="https:"||!["productdata.awin.com","datafeed.api.productserve.com"].includes(url.hostname)||url.username||url.password)throw Error("invalid_feed_url");
const db=createClient(env.SUPABASE_URL,env.SUPABASE_SECRET_KEY,{auth:{persistSession:false,autoRefreshToken:false}});
const {data:programme,error:pe}=await db.from("carcare_programmes").select("advertiser_id,membership_status,commission_rate,publish_allowed").eq("advertiser_id",id).single();
if(pe||!programme)throw Error("programme_not_in_database");
let runId;
try{
 const {data:run,error:re}=await db.from("carcare_feed_runs").insert({advertiser_id:id,state:"running"}).select("id").single();
 if(re)throw Error("run_log_failed");runId=run.id;
 const response=await fetch(url,{signal:AbortSignal.timeout(30000)});
 if(!response.ok)throw Error("feed_http_"+response.status);
 const all=parseCsv(toText(new Uint8Array(await response.arrayBuffer()))).slice(0,1500);
 let imported=0;
 for(let offset=0;offset<all.length;offset+=100){
  const rows=all.slice(offset,offset+100).map(row=>prepareOffer(row,programme)).filter(Boolean);
  if(!rows.length)continue;
  const {error}=await db.from("carcare_offers").upsert(rows,{onConflict:"advertiser_id,source_product_id"});
  if(error)throw Error("upsert_"+error.code);imported+=rows.length;
 }
 await db.from("carcare_feed_runs").update({state:"success",finished_at:new Date().toISOString(),import_count:imported}).eq("id",runId);
 console.log(JSON.stringify({state:"success",advertiser_id:id,rows:imported,joined:programme.membership_status==="joined",publishing_allowed:programme.publish_allowed}));
}catch(error){
 if(runId)await db.from("carcare_feed_runs").update({state:"failed",finished_at:new Date().toISOString(),error_code:String(error.message).slice(0,80)}).eq("id",runId);
 throw Error("awin_feed_import_failed:"+String(error.message).replace(/https?:\/\/\S+/g,"[redacted]"));
}
