import {NextResponse} from "next/server";
export const dynamic="force-dynamic";
export const runtime="nodejs";
const ALLOWED_TRACKING_HOSTS=["linkwi.se","linkwise.gr"];
const validUrl=value=>{try{const u=new URL(String(value||""));return u.protocol==="https:"&&!u.username&&!u.password&&ALLOWED_TRACKING_HOSTS.some(h=>u.hostname===h||u.hostname.endsWith("."+h))?u.href:null}catch{return null}};
const available=v=>{if(v===false||v===0||v==="0")return false;const t=String(v??"").toLowerCase().trim();return !["false","no","out of stock","out_of_stock","unavailable","μη διαθέσιμο","όχι","0"].includes(t)};
const rowsOf=data=>Array.isArray(data)?data:Array.isArray(data?.products)?data.products:Array.isArray(data?.items)?data.items:Array.isArray(data?.data)?data.data:Array.isArray(data?.product)?data.product:[];
export function normalizeFeed(data,now=new Date()){
 const seen=new Set();
 return rowsOf(data).flatMap((p,i)=>{
  const tracking_url=validUrl(p.tracking_url);
  const price=Number(String(p.price??p.price_eur??"").replace(",","."));
  const expiry=p.valid_to?new Date(p.valid_to):null;
  const starts=p.valid_from?new Date(p.valid_from):null;
  const image_url=(()=>{try{const u=new URL(p.image_url||p.thumb_url);return u.protocol==="https:"?u.href:null}catch{return null}})();
  const title=String(p.product_name||p.model_name||p.title||"").trim();
  const id=String(p.lw_product_id||p.product_id||i);
  if(!tracking_url||!title||!Number.isFinite(price)||price<=0||String(p.currency||"EUR").toUpperCase()!=="EUR"||!available(p.in_stock)||!available(p.availability)||expiry&&(!Number.isFinite(expiry.getTime())||expiry<now)||starts&&(!Number.isFinite(starts.getTime())||starts>now)||seen.has(id))return [];
  seen.add(id);
  return [{id,title,description:String(p.description||"").replace(/<[^>]*>/g," ").slice(0,650),brand:String(p.brand_name||p.brand||""),category:String(p.category||""),merchant:String(p.program_name||""),image_url,tracking_url,price,full_price:Number(p.full_price)||null,on_sale:p.on_sale===true||p.on_sale==="1"||p.on_sale==="true",valid_to:p.valid_to||null}];
 });
}
export async function GET(){
 const url=process.env.LINKWISE_CARCARE_FEED_URL;
 if(!url)return NextResponse.json({state:"unconfigured",products:[],message:"Δεν έχει ρυθμιστεί ακόμη η σύνδεση με τον κατάλογο."},{status:503});
 try{
  const parsed=new URL(url);
  if(parsed.protocol!=="https:"||parsed.hostname!=="affiliate.linkwi.se")throw Error("Invalid feed source");
  const response=await fetch(parsed.href,{next:{revalidate:3600},signal:AbortSignal.timeout(25000)});
  if(!response.ok)throw Error("Feed HTTP "+response.status);
  const data=await response.json();
  const products=normalizeFeed(data);
  return NextResponse.json({state:"ready",products,updated_at:new Date().toISOString(),total:products.length},{headers:{"Cache-Control":"public, s-maxage=900, stale-while-revalidate=1800"}});
 }catch(e){console.error("CarCare feed fetch:",e?.message);return NextResponse.json({state:"unavailable",products:[],message:"Η ενημέρωση προϊόντων δεν είναι προσωρινά διαθέσιμη. Δοκίμασε ξανά."},{status:503})}
}
