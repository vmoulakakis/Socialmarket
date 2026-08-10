'use client';

import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';

export default function Products(){
  const [rows,setRows]=useState([]);
  const [loading,setLoading]=useState(true);
  useEffect(()=>{(async()=>{
    const {data}=await supabase.from('opportunity_scores').select('id,higo_adjusted,higo_raw,confidence,demand_score,forecast_momentum_score,attention_gap_score,purchase_ease_score,offer_score,decision,skeptic_status,products(id,product_name,price,full_price,discount_pct,category_raw,brand_name,program_name,image_url,tracking_url,purchase_friction)').order('higo_adjusted',{ascending:false}).limit(250);
    setRows(data||[]);setLoading(false);
  })()},[]);
  return <main><div className="hero"><div><div className="eyebrow">High-ticket selection</div><h1>Product Candidates</h1><p className="sub">Μόνο πραγματικά scored προϊόντα. Price €150+, active/in-stock offer, tracking URL, usable image και purchase-friction gate πριν από το AI ranking.</p></div></div><div className="card">{loading?<p className="muted">Loading candidates…</p>:rows.length===0?<p className="muted">Δεν υπάρχουν candidates ακόμη. Το feed import και τα market-research runs πρέπει να ολοκληρωθούν πρώτα.</p>:<table className="table"><thead><tr><th>Product</th><th>Price</th><th>Discount</th><th>Demand</th><th>Forecast</th><th>Gap</th><th>Ease</th><th>Confidence</th><th>HIGO</th><th>Audit</th></tr></thead><tbody>{rows.map(o=><tr key={o.id}><td>{o.products?.product_name||'—'}<div className="muted">{o.products?.category_raw||o.products?.brand_name||''}</div></td><td>{o.products?.price?`€${Number(o.products.price).toFixed(2)}`:'—'}</td><td>{o.products?.discount_pct!=null?`${Number(o.products.discount_pct).toFixed(0)}%`:'—'}</td><td>{Number(o.demand_score).toFixed(0)}</td><td>{Number(o.forecast_momentum_score).toFixed(0)}</td><td>{Number(o.attention_gap_score).toFixed(0)}</td><td>{Number(o.purchase_ease_score).toFixed(0)}</td><td>{Math.round(Number(o.confidence)*100)}%</td><td className={Number(o.higo_adjusted)>=92?'score good':Number(o.higo_adjusted)>=85?'score warn':'score'}>{Number(o.higo_adjusted).toFixed(1)}</td><td><span className="pill">{o.skeptic_status}</span></td></tr>)}</tbody></table>}</div></main>
}
