/* CarCare AI v2: controlled ingestion from user-specified Linkwise source into VMDB.
   Runs server-side only. Never substitutes fabricated offers on an empty source. */
import {createHash} from "node:crypto";
const source=process.env.LINKWISE_CARCARE_V2_FEED_URL;
const secret=process.env.CARCARE_SYNC_SECRET;
const supabase=process.env.NEXT_PUBLIC_CARCARE_SUPABASE_URL;
const worker=supabase?supabase+"/functions/v1/carcare-ai-worker":null;
const timeout=(ms)=>AbortSignal.timeout(ms);
function clean(s,n=600){return String(s??"").replace(/<[^>]*>/g," ").replace(/&amp;amp;/g,"&").replace(/&amp;/g,"&").replace(/&gt;/g,">").slice(0,n).trim()}
function price(v){if(v==null||v==="")return null;let t=String(v).replace(/[^0-9,.\-]/g,"");const c=t.lastIndexOf(","),d=t.lastIndexOf(".");if(c>=0&&d>=0)t=c>d?t.replace(/\./g,"").replace(",","."):t.replace(/,/g,"");else if(c>=0)t=t.replace(",",".");const n=Number(t);return Number.isFinite(n)&&n>=0?n:null}
function url(x,{tracking=false}={}){try{const u=new URL(String(x||""));if(u.protocol!=="https:"||u.username||u.password)return null;if(tracking&&!["linkwi.se","linkwise.gr"].some(h=>u.hostname===h||u.hostname.endsWith("."+h)))return null;return u.href}catch{return null}}
function vertical(category,title){const c=clean(category+" "+title,1000).normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase();
 if(/ασφαλ|insurance|ασφαλισ/.test(c)){if(/αυτοκιν|οχημ|car|vehicle|motor/.test(c))return "car_insurance";if(/κατοικ|σπιτ|home|property/.test(c))return "home_insurance";if(/υγει|health|medical/.test(c))return "health_insurance";return "insurance_other"}
 if(/τραπεζ|bank|χρηματοδ|finance|loan|δανει|πιστωτ|credit/.test(c))return "finance";
 if(/αυτοκιν|vehicle|automotive|car parts|υαλοκαθαρισ|ανταλλακτικ/.test(c))return "automotive";
 return "other";
}
function date(value){if(!value)return null;const d=new Date(/^\d{4}-\d{2}-\d{2}$/.test(value)?value+"T12:00:00Z":value);return Number.isFinite(+d)?d.toISOString():null}
function normalize(p){const title=clean(p.product_name||p.model_name||"",550),category=clean(p.category,600);
 const merchant=clean(p.program_name||(typeof p.program==="string"?p.program:p.program?.name)||"",240);
 const sourceId=clean(p.product_id||p.lw_product_id||"",250);
 const v=vertical(category,title);
 const inStock=p.in_stock==null||p.in_stock===""?v!=="automotive":!["N","0","false","no","out of stock","μη διαθέσιμο"].includes(String(p.in_stock).trim().toLowerCase());
 const track=url(p.tracking_url,{tracking:true}),image=url(p.image_url||p.thumb_url);
 const pr=price(p.price),full=price(p.full_price);
 const from=date(p.valid_from),to=date(p.valid_to);
 if(!title||!sourceId||!category||!track||!inStock||String(p.currency||"EUR").toUpperCase()!=="EUR"||(v==="automotive"&&!(pr>0))||(to&&Date.parse(to)<Date.now())||(from&&Date.parse(from)>Date.now()))return null;
 const key=createHash("sha256").update(["linkwise_v2",merchant,sourceId].join("::")).digest("hex");
 return {product_key:"v2:"+key,feed_key:"linkwise_v2",source_product_id:sourceId,title,description:clean(p.description,3000),category,vertical:v,brand:clean(p.brand_name,240),merchant,price_eur:pr,full_price_eur:full,currency:"EUR",in_stock:true,valid_from:from,valid_to:to,image_url:image,tracking_url:track,product_specs:{size:clean(p.size,120),colour:clean(p.colour,90),custom:typeof p.custom==="string"?clean(p.custom,400):null},evidence:{source:"Linkwise live v2 JSON",observed_at:new Date().toISOString(),auto_classified:true}};
}
async function invoke(action,other={},attempt=1){const response=await fetch(worker,{method:"POST",headers:{"content-type":"application/json","x-carcare-sync-secret":secret},body:JSON.stringify({action,...other}),signal:timeout(45000)});let data;try{data=await response.json()}catch{throw Error("worker_invalid_response")}if(!response.ok){if(attempt<3&&response.status>=500){await new Promise(r=>setTimeout(r,750*attempt));return invoke(action,other,attempt+1)}throw Error("worker_http_"+response.status+"_"+String(data.error||""))}return data}
async function main(){
 if(!source||!secret||!worker){console.log("CarCare AI sync: configuration missing; skipping");return}
 const u=new URL(source);if(u.protocol!=="https:"||u.hostname!=="affiliate.linkwi.se")throw Error("invalid_source_host");
 const response=await fetch(u,{signal:timeout(60000),headers:{accept:"application/json"}});
 if(!response.ok)throw Error("feed_http_"+response.status);
 const raw=await response.json();
 const rows=Array.isArray(raw)?raw:Array.isArray(raw?.products)?raw.products:[];
 if(!Array.isArray(rows))throw Error("invalid_feed_type");
 if(rows.length>100000)throw Error("oversized_feed");
 console.log("CarCare AI feed: raw_rows="+rows.length);
 const normalized=[...new Map(rows.map(normalize).filter(Boolean).map(x=>[x.product_key,x])).values()];
 console.log("CarCare AI feed: validated_rows="+normalized.length);
 const start=await invoke("start",{source_count:rows.length});
 let accepted=0;
 for(let i=0;i<normalized.length;i+=150){
  const batch=normalized.slice(i,i+150);
  const result=await invoke("batch",{run_id:start.run_id,rows:batch});
  accepted+=Number(result.upserted||0);
 }
 const finished=await invoke("finish",{run_id:start.run_id,accepted,rejected:rows.length-normalized.length});
 console.log("CarCare AI ingestion: status="+finished.state+" imported="+accepted+"; no fallback products synthesized");
 const k=await invoke("embed",{kind:"knowledge",limit:8});
 console.log("CarCare AI knowledge embedding: "+k.embedded+"/"+k.candidates+"; failures="+k.failed_count);
}
await main().catch(e=>{console.error("CarCare AI sync error:",String(e.message||e).slice(0,180));process.exitCode=1});
