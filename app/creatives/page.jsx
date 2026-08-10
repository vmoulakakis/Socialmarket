'use client';

import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';

export default function Creatives(){
  const [assets,setAssets]=useState([]);
  const [loading,setLoading]=useState(true);
  useEffect(()=>{load()},[]);
  async function load(){
    const {data}=await supabase.from('creative_assets').select('id,asset_type,storage_path,quality_score,qr_payload,copy,created_at,creative_jobs(id,status,platform_target,concept_type,products(product_name,price,category_raw))').order('created_at',{ascending:false}).limit(100);
    const rows=[];
    for(const a of (data||[])){
      const {data:urlData}=await supabase.storage.from('creatives').createSignedUrl(a.storage_path,3600);
      rows.push({...a,url:urlData?.signedUrl||null});
    }
    setAssets(rows);setLoading(false);
  }
  async function review(assetId,action){
    await supabase.from('approvals').insert({creative_asset_id:assetId,action});
    await load();
  }
  return <main><div className="hero"><div><div className="eyebrow">Creative Control</div><h1>Creative Approval Queue</h1><p className="sub">Μόνο προϊόντα που επιβιώνουν HIGO + Evidence Auditor μπαίνουν εδώ. Δεν υπάρχει ακόμη automatic publishing.</p></div></div>{loading?<div className="muted">Loading…</div>:null}<div className="creative-grid">{!loading&&assets.length===0?<div className="card full"><h2>No assets yet</h2><p className="muted">Το intelligence layer είναι έτοιμο. Τα creatives θα εμφανίζονται εδώ με private signed URLs μόλις ενεργοποιηθεί ο renderer.</p></div>:assets.map(a=><article className="card creative-card" key={a.id}>{a.url?<img className="creative-image" src={a.url} alt="Generated creative"/>:<div className="creative-placeholder">Asset unavailable</div>}<div className="eyebrow">{a.creative_jobs?.concept_type||a.asset_type}</div><h3>{a.creative_jobs?.products?.product_name||'Creative'}</h3><p className="muted">{a.creative_jobs?.products?.category_raw||''}</p><div className="creative-meta"><span>Quality {a.quality_score??'—'}</span><span>{a.creative_jobs?.platform_target||'generic'}</span></div><div className="creative-actions"><button className="button" onClick={()=>review(a.id,'approved')}>Approve</button><button className="link-button" onClick={()=>review(a.id,'rejected')}>Reject</button><button className="link-button" onClick={()=>review(a.id,'regenerate')}>Regenerate</button></div></article>)}</div></main>
}
