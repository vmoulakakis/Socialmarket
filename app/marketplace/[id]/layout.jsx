import {APPROVED_PUBLISHABLE_KEY,APPROVED_SUPABASE_URL} from '@/lib/supabase-config';

const BASE='https://socialmarket-theta.vercel.app';

async function getItem(id){
  const url=`${APPROVED_SUPABASE_URL}/rest/v1/socialmarket_marketplace200_public_v?id=eq.${encodeURIComponent(id)}&select=id,product_name,solution_statement,pain_statement,gap_statement,job_to_be_done,niche,subniche,image_url,semantic_tags`;
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
    keywords:[item.niche,item.subniche,...(Array.isArray(item.semantic_tags)?item.semantic_tags:[])].filter(Boolean).slice(0,10),
    alternates:{canonical},
    robots:{index:true,follow:true},
    openGraph:{title,description,type:'article',locale:'el_GR',url:canonical,siteName:'SocialMarket',images:[{url:socialImage,width:1080,height:1080,alt:`${item.product_name} — SocialMarket case solver`}]},
    twitter:{card:'summary_large_image',title,description,images:[socialImage]},
  };
}

export default async function CaseLayout({children,params}){
  const {id}=await params;
  const cleanId=decodeURIComponent(String(id||''));
  const item=await getItem(cleanId);
  if(!item)return children;
  const canonical=`${BASE}/marketplace/${encodeURIComponent(cleanId)}`;
  const description=String(item.solution_statement||item.pain_statement||'').slice(0,500);
  const schema={
    '@context':'https://schema.org',
    '@type':'WebPage',
    name:`${item.product_name} — SocialMarket`,
    description,
    url:canonical,
    inLanguage:'el-GR',
    isPartOf:{'@type':'WebSite',name:'SocialMarket',url:`${BASE}/marketplace`},
    about:{
      '@type':'Product',
      name:item.product_name,
      image:item.image_url||undefined,
      description,
      category:[item.niche,item.subniche].filter(Boolean).join(' / ')||undefined,
      keywords:(Array.isArray(item.semantic_tags)?item.semantic_tags:[]).join(', ')||undefined,
    },
    mainEntity:{
      '@type':'HowTo',
      name:item.job_to_be_done||`Πώς βοηθά το ${item.product_name}`,
      description:item.pain_statement||description,
      step:[
        {'@type':'HowToStep',name:'Pain',text:item.pain_statement||''},
        {'@type':'HowToStep',name:'Gap',text:item.gap_statement||''},
        {'@type':'HowToStep',name:'Solution',text:item.solution_statement||''},
      ].filter(x=>x.text),
    },
  };
  return <><script type="application/ld+json" dangerouslySetInnerHTML={{__html:JSON.stringify(schema).replace(/</g,'\\u003c')}}/>{children}</>;
}
