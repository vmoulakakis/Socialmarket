export const API='https://rpfadpdnnxequgvdcfoq.supabase.co/functions/v1/affinity-b2b-public';
export const SITE='https://affinity-b2b-greece.vercel.app';
export async function inventory(limit=42){const r=await fetch(`${API}?limit=${limit}`,{next:{revalidate:3600}});if(!r.ok)throw new Error('inventory');const j=await r.json();return j.inventory||[]}
export const slugify=s=>String(s||'').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'').slice(0,88);