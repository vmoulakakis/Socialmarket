import {APPROVED_PUBLISHABLE_KEY,APPROVED_SUPABASE_URL} from '@/lib/supabase-config';

const BASE='https://socialmarket-theta.vercel.app';

export default async function sitemap(){
  const entries=[{url:`${BASE}/marketplace`,changeFrequency:'daily',priority:1,lastModified:new Date()}];
  try{
    const url=`${APPROVED_SUPABASE_URL}/rest/v1/socialmarket_marketplace200_public_v?select=id,run_date&order=affinity_score.desc&limit=1000`;
    const r=await fetch(url,{headers:{apikey:APPROVED_PUBLISHABLE_KEY,Authorization:`Bearer ${APPROVED_PUBLISHABLE_KEY}`},next:{revalidate:900}});
    if(!r.ok)return entries;
    const rows=await r.json();
    for(const row of rows||[]){
      if(!row?.id)continue;
      entries.push({url:`${BASE}/marketplace/${encodeURIComponent(String(row.id))}`,changeFrequency:'weekly',priority:.78,lastModified:row.run_date?new Date(`${row.run_date}T00:00:00Z`):new Date()});
    }
  }catch{}
  return entries;
}
