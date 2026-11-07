import {NextResponse} from 'next/server';
import {getShopCatalog,toPublicProducts} from '@/lib/shop-catalog';
import {searchShopCatalog} from '@/lib/shop-search.mjs';
export const runtime='nodejs';
export const dynamic='force-dynamic';
export async function GET(request){
 const u=new URL(request.url);
 const query=String(u.searchParams.get('q')||'').trim().slice(0,160);
 const category=String(u.searchParams.get('category')||'Όλα').slice(0,60);
 const budget=String(u.searchParams.get('budget')||'').slice(0,10);
 const sort=['relevance','price-asc','price-desc','fresh'].includes(u.searchParams.get('sort'))?u.searchParams.get('sort'):'relevance';
 const page=Math.min(30,Math.max(1,Number(u.searchParams.get('page')||1)));
 try{
   const {products,sourceStatus}=await getShopCatalog();
   const matching=searchShopCatalog(products,{query,category,budget,sort,page,perPage:24});
   const categories=Array.from(new Set(products.map(p=>p.category))).filter(Boolean);
   return NextResponse.json({
     items:toPublicProducts(matching.results),total:matching.total,page:matching.page,
     hasMore:matching.hasMore,sourceStatus,categories:['Όλα',...categories],
     catalogCount:products.length,disclosure:'Affiliate links. All prices and availability require merchant confirmation.',
     verifiedStockCount:0,aiModelExecuted:false
   },{headers:{'Cache-Control':'no-store','X-Robots-Tag':'noindex'}});
 }catch{
   return NextResponse.json({items:[],total:0,catalogCount:0,sourceStatus:'unavailable',categories:['Όλα'],hasMore:false,error:'catalog_temporarily_unavailable'},
    {status:503,headers:{'Cache-Control':'no-store'}});
 }
}
