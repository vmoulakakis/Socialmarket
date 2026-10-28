import {gunzipSync} from "node:zlib";
import {safeAwinUrl} from "./policy.mjs";
export function parseCsv(s){
 const arr=[];let cells=[],v="",inside=false;
 for(let i=0;i<s.length;i++){
  const c=s[i];
  if(c==='"'){if(inside&&s[i+1]==='"'){v+='"';i++;}else inside=!inside;continue;}
  if(!inside&&(c===','||c==='\n'||c==='\r')){
   cells.push(v);v="";
   if(c===',')continue;
   if(c==='\r'&&s[i+1]==='\n')i++;
   if(cells.some(x=>x.trim()))arr.push(cells);
   cells=[];continue;
  }
  v+=c;
 }
 if(inside)throw Error("csv_unclosed_quote");
 if(v||cells.length){cells.push(v);arr.push(cells);}
 const [head,...rows]=arr;if(!head)return[];
 return rows.map(row=>Object.fromEntries(head.map((h,i)=>[h.replace(/^\uFEFF/,"").trim(),row[i]??""])));
}
export function toText(bytes){
 if(bytes.byteLength>25_000_000)throw Error("compressed_feed_too_large");
 const raw=bytes[0]===31&&bytes[1]===139?gunzipSync(bytes):Buffer.from(bytes);
 if(raw.byteLength>80_000_000)throw Error("feed_too_large");
 return raw.toString("utf8");
}
export function parseTire(row){
 const s=String(row.product_name||"")+" "+String(row.specifications||"");
 const m=s.match(/\b(1[3-9]\d|2\d\d|3[0-5]\d)\s*\/\s*([2-9]\d)\s*[Rr]\s*(1\d|2[0-4])\b/);
 return m?{tire_width:Number(m[1]),tire_profile:Number(m[2]),rim_diameter:Number(m[3])}:null;
}
export function getSeason(row){
 const s=String(row.product_name||"").toLowerCase();
 if(/all[\s-]?season|all[\s-]?weather|4[\s-]?season|4 εποχ/.test(s))return "all-season";
 if(/winter|χειμεριν/.test(s))return "winter";
 if(/summer|θεριν/.test(s))return "summer";
 return null;
}
export function prepareOffer(row,p,now=new Date()){
 const dims=parseTire(row),price=Number(String(row.search_price||row.store_price||"").replace(",","."));
 const id=String(row.aw_product_id||row.merchant_product_id||"").trim();
 if(!dims||!id||!Number.isFinite(price)||price<=0)return null;
 const link=safeAwinUrl(row.aw_deep_link);
 const estimated=p.commission_rate==null?null:Math.round(price*Number(p.commission_rate)*100)/100;
 const stocked=["1","true","yes","in stock","instock"].includes(String(row.in_stock||row.stock_status||"").toLowerCase());
 const publish=p.membership_status==="joined"&&p.publish_allowed===true&&process.env.CARCARE_PUBLISH_APPROVED==="true"&&
  estimated!==null&&estimated>=10&&stocked&&Boolean(link);
 const img=String(row.merchant_image_url||row.aw_image_url||"");
 return {advertiser_id:p.advertiser_id,source_product_id:id,title:String(row.product_name||"").slice(0,250),
  brand:String(row.brand_name||"").slice(0,100)||null,tracking_url:link,image_url:img.startsWith("https://")?img.slice(0,1200):null,
  price_eur:price,expected_commission_eur:estimated,currency:"EUR",in_stock:stocked,is_published:Boolean(publish),
  verified_at:now.toISOString(),updated_at:now.toISOString(),season:getSeason(row),wet_grip_grade:null,...dims};
}
