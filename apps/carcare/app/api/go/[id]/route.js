import {NextResponse} from "next/server";
import {eligible,safeAwinUrl} from "../../../../lib/policy.mjs";
export const dynamic="force-dynamic";
export async function GET(req,ctx){
 if(process.env.CARCARE_ENABLE_MONETIZATION!=="true")return NextResponse.json({error:"preview_only"},{status:403});
 const {id}=await ctx.params;
 if(!/^[0-9a-fA-F-]{36}$/.test(String(id)))return NextResponse.json({error:"invalid_id"},{status:400});
 const base=process.env.SUPABASE_URL,key=process.env.SUPABASE_PUBLISHABLE_KEY;
 if(!base||!key)return NextResponse.json({error:"unconfigured"},{status:503});
 try{
  const url=new URL("/rest/v1/carcare_offers",base);url.searchParams.set("select","*");url.searchParams.set("id","eq."+id);url.searchParams.set("limit","1");
  const res=await fetch(url,{headers:{apikey:key,Authorization:"Bearer "+key},cache:"no-store",signal:AbortSignal.timeout(9000)});
  if(!res.ok)throw Error("DB unavailable");
  const [offer]=await res.json();
  if(!eligible(offer))return NextResponse.json({error:"offer_unavailable"},{status:404});
  const redirect=safeAwinUrl(offer.tracking_url);
  if(!redirect)return NextResponse.json({error:"unsafe_link"},{status:422});
  return NextResponse.redirect(redirect,302,{headers:{"Cache-Control":"no-store","Referrer-Policy":"strict-origin-when-cross-origin"}});
 }catch{return NextResponse.json({error:"temporary_unavailable"},{status:503});}
}
