import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "jsr:@supabase/supabase-js@2";

const sb=createClient(Deno.env.get("SUPABASE_URL")!,Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);
const BATCH=750;
function n(v:unknown):number|null{const x=Number(String(v??"").replace(",","."));return Number.isFinite(x)?x:null;}
function b(v:unknown):boolean{return [true,1,"1","true","yes","Y","y"].includes(v as never);}
function comm(price:number|null,m:any):{value:number|null,basis:string}{
  if(price==null)return {value:null,basis:"unknown"};
  const flat=n(m?.flat_commission_max_eur??m?.flat_commission_min_eur);
  const pct=n(m?.percent_commission_max??m?.percent_commission_min);
  const a:{value:number,basis:string}[]=[];
  if(flat!=null)a.push({value:flat,basis:"flat"});
  if(pct!=null)a.push({value:price*pct/100,basis:`percent:${pct}`});
  if(!a.length)return {value:null,basis:"unknown"};
  return a.sort((x,y)=>y.value-x.value)[0];
}
async function hash(v:unknown){const bytes=new TextEncoder().encode(JSON.stringify(v));const d=await crypto.subtle.digest("SHA-256",bytes);return [...new Uint8Array(d)].map(x=>x.toString(16).padStart(2,"0")).join("");}

Deno.serve(async(req:Request)=>{
  if(req.method==="GET")return Response.json({ok:true,service:"linkwise-feed-ingest",version:3,policy:"merchant360-first-fail-closed",min_expected_commission_eur:15});
  if(req.method!=="POST")return Response.json({error:"method_not_allowed"},{status:405});
  const body=await req.json().catch(()=>({}));
  const feed=String(body.feed_url??Deno.env.get("LINKWISE_FEED_URL")??"");
  if(!feed)return Response.json({error:"feed_url missing"},{status:400});
  const dry=body.dry_run===true,max=Number(body.max_records||0);

  const {data:eligibleMerchants,error:me}=await sb.from("merchant_product_discovery_eligible").select("id,legacy_merchant_id,merchant_name,flat_commission_min_eur,flat_commission_max_eur,percent_commission_min,percent_commission_max,expected_commission_eur,confidence_adjusted_score,hard_gate_pass,eligible_for_product_discovery");
  if(me)return Response.json({error:me.message},{status:500});
  const approved=(eligibleMerchants??[]).filter((m:any)=>m.hard_gate_pass===true&&m.eligible_for_product_discovery===true&&m.legacy_merchant_id);
  if(!approved.length)return Response.json({ok:true,policy:"merchant360-first-fail-closed",eligible_merchants:0,scanned:0,eligible:0,written:0,reason:"no_merchant_passed_canonical_product_discovery_gate"});
  const mm=new Map<string,any>();for(const m of approved)mm.set(String(m.legacy_merchant_id),m);

  const r=await fetch(feed);if(!r.ok)return Response.json({error:`feed ${r.status}`},{status:502});
  const json=await r.json();const rows=Array.isArray(json)?json:(json.products??json.items??json.data??[]);
  let scanned=0,eligible=0,written=0,invalid=0,merchantRejected=0,under15=0,outstock=0;let out:any[]=[];
  for(const p of rows){
    if(max&&scanned>=max)break;scanned++;
    const price=n(p.price),program=String(p.program_id??""),m=mm.get(program);
    if(!m){merchantRejected++;continue;}
    if(!p.product_id||!p.tracking_url||!p.product_name||price==null||price<=0){invalid++;continue;}
    if(p.in_stock!==undefined&&!b(p.in_stock)){outstock++;continue;}
    const ec=comm(price,m);if(ec.value==null||ec.value<15){under15++;continue;}
    eligible++;
    const raw={product_id:p.product_id,program_id:program,program_name:p.program_name??m.merchant_name,sku:p.sku??null,model_name:p.model_name??null,product_name:p.product_name,category:p.category??null,price,tracking_url:p.tracking_url,image_url:p.image_url??p.thumb_url??null,in_stock:true,valid_from:p.valid_from??null,valid_to:p.valid_to??null,on_sale:p.on_sale??null,discount:p.discount??null,times_bought:p.times_bought??null};
    out.push({source_key:"linkwise_cd104",source_product_id:String(p.product_id),program_id:program,program_name:p.program_name??m.merchant_name??null,sku:p.sku?String(p.sku):null,model_name:p.model_name??null,product_name:String(p.product_name),category_raw:p.category??null,price_eur:price,expected_commission_eur:ec.value,commission_basis:ec.basis,tracking_url:p.tracking_url,image_url:p.image_url??p.thumb_url??null,in_stock:true,valid_from:p.valid_from??null,valid_to:p.valid_to??null,on_sale:p.on_sale??null,discount:n(p.discount),times_bought:n(p.times_bought),content_hash:await hash(raw),raw_snapshot:raw,last_seen_at:new Date().toISOString(),is_active:true,intelligence_status:"pending"});
    if(out.length>=BATCH&&!dry){const {error}=await sb.from("commerce_feed_eligible_offers").upsert(out,{onConflict:"source_key,program_id,source_product_id"});if(error)return Response.json({error:error.message,scanned},{status:500});written+=out.length;out=[];}
  }
  if(out.length&&!dry){const {error}=await sb.from("commerce_feed_eligible_offers").upsert(out,{onConflict:"source_key,program_id,source_product_id"});if(error)return Response.json({error:error.message,scanned},{status:500});written+=out.length;}
  return Response.json({ok:true,policy:"merchant360-first + product expected commission>=15EUR",dry_run:dry,eligible_merchants:approved.length,scanned,eligible,written,invalid,merchant_rejected:merchantRejected,out_of_stock:outstock,commission_under_15:under15});
});