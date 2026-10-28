import {NextResponse} from "next/server";
import {eligible} from "../../../lib/policy.mjs";
export const dynamic="force-dynamic";
export async function GET(){
 const headers={"Cache-Control":"no-store"};
 if(process.env.CARCARE_ENABLE_MONETIZATION!=="true")return NextResponse.json({offers:[],state:"preview"},{headers});
 const base=process.env.SUPABASE_URL,key=process.env.SUPABASE_PUBLISHABLE_KEY;
 if(!base||!key)return NextResponse.json({offers:[],state:"unconfigured"},{status:503,headers});
 try{
  const url=new URL("/rest/v1/carcare_offers",base);
  url.searchParams.set("select","id,title,brand,image_url,tracking_url,price_eur,expected_commission_eur,currency,in_stock,is_published,verified_at,tire_width,tire_profile,rim_diameter,season,wet_grip_grade");
  url.searchParams.set("limit","150");
  const res=await fetch(url,{headers:{apikey:key,Authorization:"Bearer "+key},cache:"no-store",signal:AbortSignal.timeout(9000)});
  if(!res.ok)throw Error("DB unavailable");
  const data=await res.json();
  return NextResponse.json({state:"ready",offers:(Array.isArray(data)?data:[]).filter(o=>eligible(o))},{headers});
 }catch{return NextResponse.json({offers:[],state:"unavailable",message:"Δεν είναι διαθέσιμος ο έλεγχος προσφορών."},{status:503,headers});}
}
