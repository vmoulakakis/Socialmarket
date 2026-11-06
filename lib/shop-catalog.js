import {createClient} from '@supabase/supabase-js';
import {APPROVED_SUPABASE_URL} from './supabase-config.js';
import {getLuxeTop100} from './luxecorner.js';
import {decodeLinkwiseRoute} from './linkwise-identity.mjs';
const FLOOR=10;
const EXCLUDED=/video surveillance|smart public safety|weapon|gun|airsoft|spy|hidden camera|security camera|cctv|self-defense|lockpick/i;
const key=()=>process.env.VMDB_SUPABASE_SERVICE_ROLE_KEY ||
  (process.env.SUPABASE_URL===APPROVED_SUPABASE_URL?process.env.SUPABASE_SERVICE_ROLE_KEY:null);
let cached={expires:0,products:[],sourceStatus:'unloaded'};
function httpsHost(v,allowed){try{const u=new URL(v);return u.protocol==='https:'&&!u.username&&!u.password&&allowed(u.hostname.toLowerCase())}catch{return false}}
const image=v=>httpsHost(v,h=>h.endsWith('.aliexpress-media.com')||h.endsWith('.alicdn.com')||h.endsWith('.aliexpress.com')||h.endsWith('.laredoute.gr')||h.endsWith('.laredoute.com')||h.endsWith('.linkwi.se'));
const aeUrl=v=>httpsHost(v,h=>h==='s.click.aliexpress.com'||h==='a.aliexpress.com');
const cut=(v,n=160)=>String(v||'').trim().slice(0,n);
function freshness(when,now){
 const t=Date.parse(when||'');if(!Number.isFinite(t)||t>now.getTime()+3600000)return 'unknown';
 const age=now.getTime()-t;
 return age<=48*3600000?'recent':age<=14*86400000?'aging':'stale';
}
export function categoryLabel(raw){
 const t=String(raw||'').toLowerCase();
 if(/lighting|chandelier|lamp/.test(t))return 'Φωτισμός';
 if(/car|automotive|vehicle/.test(t))return 'Αυτοκίνητο';
 if(/home|furniture|decor|sofa/.test(t))return 'Σπίτι';
 if(/garden/.test(t))return 'Κήπος';
 if(/tool|instrument|measurement/.test(t))return 'Εργαλεία';
 if(/electronics|camera|phone|computer|device/.test(t))return 'Τεχνολογία';
 if(/pet/.test(t))return 'Κατοικίδια';
 return 'Άλλα';
}
function fromAli(row,now){
 const c=row?.ai_product_candidates;
 if(!c||typeof c!=='object'||!aeUrl(row.promotion_url)||!image(c.image_url)||
    EXCLUDED.test(String(c.title||'')+' '+String(c.category||''))||
    !Number.isFinite(Number(row.price_eur))||Number(row.price_eur)<=0||
    !Number.isFinite(Number(row.expected_commission_eur))||Number(row.expected_commission_eur)<FLOOR||
    c.source_key!=='aliexpress'||!c.source_product_id)return null;
 const f=freshness(row.last_seen_at,now);
 if(f==='unknown'||f==='stale')return null;
 return {id:'ae:'+c.source_product_id,source:'AliExpress',title:cut(c.title,220),
   category:categoryLabel(c.category),sourceCategory:cut(c.category,100),merchant:'AliExpress',
   price:Number(row.price_eur),commissionEur:Number(row.expected_commission_eur),image:c.image_url,href:row.promotion_url,
   observedAt:row.last_seen_at,availability:'unknown',researchStatus:'checking',
   freshness:f,landingPriceVerified:false};
}
function fromLinkwise(row){
 if(!row?.source_product_id||!row?.product_name||
    EXCLUDED.test(String(row.product_name||'')+' '+String(row.category_raw||''))||
    !image(row.image_url)||!decodeLinkwiseRoute(row.tracking_url)||
    !Number.isFinite(Number(row.price_eur))||Number(row.price_eur)<=0||
    Number(row.calculated_commission_eur)<FLOOR)return null;
 return {id:'lw:'+row.program_id+':'+row.source_product_id,source:'Linkwise',title:cut(row.product_name,220),
   category:'Σπίτι',sourceCategory:cut(row.category_raw,100),
   merchant:cut(row.program_name,80)||'Linkwise συνεργάτης',price:Number(row.price_eur),commissionEur:Number(row.calculated_commission_eur),
   image:row.image_url,href:row.tracking_url,observedAt:null,
   availability:'unknown',researchStatus:'checking',freshness:'unknown',landingPriceVerified:false};
}
export async function getShopCatalog({now=new Date(),refresh=false}={}){
 if(!refresh&&cached.expires>Date.now())return {products:cached.products,sourceStatus:cached.sourceStatus};
 const rows=[];let sourceStatus='partial';
 if(key()){
  try{
   const db=createClient(APPROVED_SUPABASE_URL,key(),{auth:{persistSession:false,autoRefreshToken:false}});
   const cutoff=new Date(now.getTime()-14*86400000).toISOString();
   const {data,error}=await db.from('ai_product_offers')
     .select('id,price_eur,expected_commission_eur,promotion_url,last_seen_at,ai_product_candidates!inner(source_product_id,title,category,image_url,source_key)')
     .gte('expected_commission_eur',FLOOR).gte('last_seen_at',cutoff).order('last_seen_at',{ascending:false}).limit(800);
   if(error)throw error;
   rows.push(...(data||[]).map(row=>fromAli(row,now)).filter(Boolean));
   sourceStatus='vmdb-research';
  }catch(error){console.error('[shop-catalog] VMDB read:',error?.message||'unavailable');sourceStatus='vmdb-unavailable';}
 }else sourceStatus='server-key-unavailable';
 try{
   const luxe=await getLuxeTop100();
   rows.push(...(luxe||[]).slice(0,50).map(fromLinkwise).filter(Boolean));
   if(sourceStatus!=='vmdb-research')sourceStatus='limited-linkwise';
 }catch(error){console.error('[shop-catalog] Linkwise read:',error?.message||'unavailable');}
 const seen=new Set();
 const products=rows.filter(p=>{if(seen.has(p.id))return false;seen.add(p.id);return true})
   .sort((a,b)=>({recent:3,aging:2,unknown:1,stale:0}[b.freshness]-{recent:3,aging:2,unknown:1,stale:0}[a.freshness])||a.price-b.price);
 cached={expires:Date.now()+90_000,products,sourceStatus};
 return {products,sourceStatus};
}
export function shopBuyerRows(products){
 return products.map(p=>({source_product_id:p.id,product_name:p.title,category_raw:p.sourceCategory||p.category,
   program_name:p.merchant,price_eur:p.price,expected_commission_eur:p.commissionEur,
   tracking_url:p.href,image_url:p.image,in_stock:null,valid_to:null,
   last_seen_at:p.observedAt,is_active:true,audit_status:'PENDING',evidence_ids:[]}));
}

export function toPublicProducts(products){
 return products.map(({id,title,category,sourceCategory,merchant,price,image,href,observedAt,availability,source,researchStatus,freshness,landingPriceVerified})=>({id,title,category,sourceCategory,merchant,price,image,href,observedAt,availability,source,researchStatus,freshness,landingPriceVerified}));
}
