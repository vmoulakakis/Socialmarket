'use client';

import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';

export default function Products(){
  const [rows,setRows]=useState([]);
  const [loading,setLoading]=useState(true);
  useEffect(()=>{(async()=>{
    const {data}=await supabase.from('opportunity_scores')
      .select('id,higo_adjusted,higo_raw,confidence,demand_score,forecast_momentum_score,attention_gap_score,purchase_ease_score,offer_score,decision,skeptic_status,seller_competition_score,ad_pressure_score,competition_kill,validity_runway_score,products(id,product_name,price,full_price,discount_pct,category_raw,brand_name,program_name,image_url,tracking_url,purchase_friction,valid_to,validity_days_remaining,market_eligible)')
      .neq('decision','DROP').eq('competition_kill',false).order('higo_adjusted',{ascending:false}).limit(250);
    setRows((data||[]).filter(x=>x.products?.market_eligible!==false));setLoading(false);
  })()},[]);
  return <main><div className="hero"><div><div className="eyebrow">Opportunity selection</div><h1>Product Candidates</h1><p className="sub">Μόνο πραγματικές ευκαιρίες: €150+, valid_to &gt; 20 ημέρες με ώρα Ελλάδας, χωρίς travel/travel goods και χωρίς seller/ad-pressure competition kill.</p></div></div><div className="card">{loading?<p className="muted">Loading candidates…</p>:rows.length===0?<p className="muted">Δεν υπάρχουν candidates ακόμη. Πρέπει πρώτα να ολοκληρωθούν feed import και market-research run με τους νέους κανόνες.</p>:<table className="table"><thead><tr><th>Product</th><th>Price</th><th>Validity</th><th>Demand</th><th>Forecast</th><th>Seller Comp.</th><th>Ad Pressure*</th><th>Confidence</th><th>HIGO</th><th>Decision</th></tr></thead><tbody>{rows.map(o=><tr key={o.id}><td>{o.products?.product_name||'—'}<div className="muted">{o.products?.category_raw||o.products?.brand_name||''}</div></td><td>{o.products?.price?`€${Number(o.products.price).toFixed(2)}`:'—'}<div className="muted">{o.products?.discount_pct!=null?`${Number(o.products.discount_pct).toFixed(0)}% off`:''}</div></td><td>{o.products?.validity_days_remaining!=null?`${o.products.validity_days_remaining}d`:'—'}<div className="muted">runway {Number(o.validity_runway_score||0).toFixed(0)}</div></td><td>{Number(o.demand_score).toFixed(0)}</td><td>{Number(o.forecast_momentum_score).toFixed(0)}</td><td>{Number(o.seller_competition_score||0).toFixed(0)}</td><td>{Number(o.ad_pressure_score||0).toFixed(0)}</td><td>{Math.round(Number(o.confidence)*100)}%</td><td className={Number(o.higo_adjusted)>=92?'score good':Number(o.higo_adjusted)>=85?'score warn':'score'}>{Number(o.higo_adjusted).toFixed(1)}</td><td><span className="pill">{o.decision}</span></td></tr>)}</tbody></table>}<p className="muted" style={{marginTop:14}}>* Ad Pressure είναι evidence-labelled proxy μέχρι να συνδεθεί direct paid-ad source· δεν παρουσιάζεται ως πραγματικός αριθμός διαφημίσεων.</p></div></main>
}
