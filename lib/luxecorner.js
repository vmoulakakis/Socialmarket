import {APPROVED_PUBLISHABLE_KEY,APPROVED_SUPABASE_URL} from '@/lib/supabase-config';

const TABLE='luxecorner_top100_public_v';

async function api(path,revalidate=900){
  const r=await fetch(`${APPROVED_SUPABASE_URL}/rest/v1/${TABLE}?${path}`,{
    headers:{apikey:APPROVED_PUBLISHABLE_KEY,Authorization:`Bearer ${APPROVED_PUBLISHABLE_KEY}`},
    next:{revalidate}
  });
  if(!r.ok) throw new Error(`LuxeCorner feed HTTP ${r.status}`);
  return r.json();
}

export async function getLuxeTop100(){
  return api('select=*&order=rank.asc&limit=100');
}

export async function getLuxeProduct(id){
  const safe=encodeURIComponent(String(id));
  const rows=await api(`select=*&source_product_id=eq.${safe}&limit=1`);
  return rows?.[0]||null;
}

export function productPath(row){
  return `/luxecorner/product/${encodeURIComponent(String(row.source_product_id))}`;
}

export function money(value){
  return Number(value||0).toLocaleString('el-GR',{style:'currency',currency:'EUR',maximumFractionDigits:2});
}
