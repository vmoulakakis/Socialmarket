import {APPROVED_PUBLISHABLE_KEY,APPROVED_SUPABASE_URL} from '@/lib/supabase-config';

const BASE='https://socialmarket-theta.vercel.app';

async function getItem(id){
  const url=`${APPROVED_SUPABASE_URL}/rest/v1/socialmarket_marketplace200_public_v?id=eq.${encodeURIComponent(id)}&select=id,product_name,solution_statement,pain_statement,niche,subniche,image_url`;
  const r=await fetch(url,{headers:{apikey:APPROVED_PUBLISHABLE_KEY,Authorization:`Bearer ${APPROVED_PUBLISHABLE_KEY}`},next:{revalidate:300}});
  if(!r.ok)return null;
  const rows=await r.json();
  return rows?.[0]||null;
}

export async function generateMetadata({params}){
  const {id}=await params;
  const cleanId=decodeURIComponent(String(id||''));
  const item=await getItem(cleanId);
  if(!item)return {title:'SocialMarket — Case Solver',robots:{index:false,follow:true}};
  const title=`${item.product_name} — SocialMarket`;
  const description=String(item.solution_statement||item.pain_statement||'Δες το pain, το gap και γιατί αυτή η λύση αξίζει να εξεταστεί.').slice(0,190);
  const canonical=`${BASE}/marketplace/${encodeURIComponent(cleanId)}`;
  const socialImage=`${BASE}/api/marketplace/creative/${encodeURIComponent(cleanId)}?format=square`;
  return {
    title,
    description,
    alternates:{canonical},
    robots:{index:true,follow:true},
    openGraph:{title,description,type:'article',locale:'el_GR',url:canonical,siteName:'SocialMarket',images:[{url:socialImage,width:1080,height:1080,alt:`${item.product_name} — SocialMarket case solver`}]},
    twitter:{card:'summary_large_image',title,description,images:[socialImage]},
  };
}

export default function CaseLayout({children}){return children;}
