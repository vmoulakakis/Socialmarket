import {APPROVED_PUBLISHABLE_KEY,APPROVED_SUPABASE_URL} from '@/lib/supabase-config';

const BASE='https://socialmarket-theta.vercel.app';
const COLLECTIONS=['goniakoi-kanapedes','veloudinoi-kanapedes','kanapedes-krevati','premium-kanapedes'];

async function getJson(url){
  const r=await fetch(url,{headers:{apikey:APPROVED_PUBLISHABLE_KEY,Authorization:`Bearer ${APPROVED_PUBLISHABLE_KEY}`},next:{revalidate:900}});
  if(!r.ok)return [];
  return r.json();
}

export default async function sitemap(){
  const now=new Date();
  const entries=[
    {url:`${BASE}/marketplace`,changeFrequency:'daily',priority:1,lastModified:now},
    {url:`${BASE}/luxecorner`,changeFrequency:'daily',priority:1,lastModified:now},
    ...COLLECTIONS.map(slug=>({url:`${BASE}/luxecorner/collections/${slug}`,changeFrequency:'weekly',priority:.9,lastModified:now}))
  ];

  try{
    const marketUrl=`${APPROVED_SUPABASE_URL}/rest/v1/socialmarket_marketplace200_public_v?select=id,run_date&order=affinity_score.desc&limit=1000`;
    const rows=await getJson(marketUrl);
    for(const row of rows||[]){
      if(!row?.id)continue;
      entries.push({url:`${BASE}/marketplace/${encodeURIComponent(String(row.id))}`,changeFrequency:'weekly',priority:.78,lastModified:row.run_date?new Date(`${row.run_date}T00:00:00Z`):now});
    }
  }catch{}

  try{
    const luxeUrl=`${APPROVED_SUPABASE_URL}/rest/v1/luxecorner_top100_public_v?select=source_product_id&order=rank.asc&limit=100`;
    const products=await getJson(luxeUrl);
    for(const p of products||[]){
      if(!p?.source_product_id)continue;
      entries.push({url:`${BASE}/luxecorner/product/${encodeURIComponent(String(p.source_product_id))}`,changeFrequency:'daily',priority:.84,lastModified:now});
    }
  }catch{}

  return entries;
}
