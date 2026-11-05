import {NextResponse} from "next/server";
import {normalizeFeed,PROBLEMS,scoreMatch,selectProducts} from "../../../lib/catalog.mjs";
export const dynamic="force-dynamic";
export const runtime="nodejs";
const headers={"Cache-Control":"public, s-maxage=300, stale-while-revalidate=600"};
export async function GET(request){
 const rawUrl=process.env.LINKWISE_CARCARE_FEED_URL;
 if(!rawUrl)return NextResponse.json({state:"unconfigured",products:[],message:"Η σύνδεση με τον κατάλογο δεν έχει ρυθμιστεί."},{status:503});
 try{
  const source=new URL(rawUrl);
  if(source.protocol!=="https:"||source.hostname!=="affiliate.linkwi.se")throw Error("Invalid feed host");
  const search=new URL(request.url).searchParams;
  const problem=PROBLEMS[search.get("problem")]?search.get("problem"):"visibility";
  const q=String(search.get("q")||"").slice(0,120);
  const maxPriceRaw=Number(search.get("max")||0);
  const maxPrice=Number.isFinite(maxPriceRaw)&&maxPriceRaw>0?maxPriceRaw:null;
  const response=await fetch(source.href,{next:{revalidate:3600},signal:AbortSignal.timeout(55000)});
  if(!response.ok)throw Error("Feed "+response.status);
  const doc=await response.json(),all=normalizeFeed(doc);
  const counts=Object.fromEntries(Object.keys(PROBLEMS).map(key=>[key,all.filter(p=>scoreMatch(p,key)>0).length]));
  const total=all.filter(p=>scoreMatch(p,problem)>0).length;
  const products=selectProducts(all,{problem,q,maxPrice,limit:42});
  return NextResponse.json({state:"ready",problem,products,total,matched:products.length,auto_total:all.length,problem_counts:counts,updated_at:new Date().toISOString(),source:"Linkwise product feed"},{headers});
 }catch(error){
  console.error("CarCare catalog temporarily unavailable:",String(error?.message||error).slice(0,110));
  return NextResponse.json({state:"unavailable",products:[],message:"Ο ζωντανός κατάλογος δεν είναι διαθέσιμος αυτή τη στιγμή. Δοκίμασε ξανά."},{status:503,headers:{"Cache-Control":"no-store"}});
 }
}
