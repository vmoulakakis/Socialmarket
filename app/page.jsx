'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';

export default function Home(){
  const [stats,setStats]=useState({priority:0,rising:0,screened:0,creatives:0});const [top,setTop]=useState([]);const [loading,setLoading]=useState(true);
  useEffect(()=>{load()},[]);
  async function load(){
    setLoading(true);
    const [screenedQ,priorityQ,creativeQ,risingQ,topQ]=await Promise.all([
      supabase.from('products').select('*',{count:'exact',head:true}).eq('hard_gate_pass',true).eq('travel_related',false),
      supabase.from('opportunity_scores').select('*',{count:'exact',head:true}).eq('competition_kill',false).gte('higo_adjusted',92).gte('confidence',0.70).neq('decision','DROP'),
      supabase.from('creative_assets').select('*',{count:'exact',head:true}),
      supabase.from('forecasts').select('scope_key,growth_pct').eq('scope_type','taxonomy').gt('growth_pct',0).limit(2000),
      supabase.from('opportunity_scores').select('id,higo_adjusted,confidence,demand_score,forecast_momentum_score,attention_gap_score,decision,competition_kill,validity_runway_score,products(product_name,price,discount_pct,category_raw,brand_name,validity_days_remaining,market_eligible)').eq('competition_kill',false).neq('decision','DROP').order('higo_adjusted',{ascending:false}).limit(20)
    ]);
    const rising=new Set((risingQ.data||[]).map(x=>x.scope_key)).size;setStats({priority:priorityQ.count||0,rising,screened:screenedQ.count||0,creatives:creativeQ.count||0});setTop((topQ.data||[]).filter(x=>x.products?.market_eligible!==false).slice(0,10));setLoading(false);
  }
  return <main><section className="hero"><div><div className="eyebrow">Greek Hidden Opportunity Engine</div><h1>Find demand before everyone promotes it.</h1><p className="sub">€150+ is only the first gate. Products also need valid_to &gt; 20 days in Greece time, no travel/travel goods, acceptable purchase friction and no seller/ad-pressure competition kill.</p></div><Link className="button" href="/market">Open Market Map</Link></section><div className="grid">
    <div className="card kpi"><span className="muted">Priority opportunities</span><strong>{loading?'—':stats.priority}</strong><span className="good">HIGO ≥ 92</span></div><div className="card kpi"><span className="muted">Categories rising</span><strong>{loading?'—':stats.rising}</strong><span className="good">positive forecast</span></div><div className="card kpi"><span className="muted">Feed-gate survivors</span><strong>{loading?'—':stats.screened.toLocaleString('el-GR')}</strong><span className="muted">before market kill-switch</span></div><div className="card kpi"><span className="muted">Creative assets</span><strong>{loading?'—':stats.creatives}</strong><span className="muted">approval library</span></div>
    <div className="card full"><h2>Top product opportunities</h2>{top.length===0?<p className="muted">Δεν υπάρχουν ακόμη πραγματικά scores. Το import και το market-intelligence workflow πρέπει να ολοκληρωθούν με τους νέους κανόνες.</p>:<table className="table"><thead><tr><th>Product</th><th>Price</th><th>Validity</th><th>Demand</th><th>Forecast</th><th>Gap</th><th>Confidence</th><th>HIGO</th></tr></thead><tbody>{top.map(o=><tr key={o.id}><td>{o.products?.product_name||'—'}<div className="muted">{o.products?.category_raw||o.products?.brand_name||''}</div></td><td>{o.products?.price?`€${Number(o.products.price).toFixed(2)}`:'—'}</td><td>{o.products?.validity_days_remaining!=null?`${o.products.validity_days_remaining}d`:'—'}<div className="muted">runway {Number(o.validity_runway_score||0).toFixed(0)}</div></td><td>{Number(o.demand_score).toFixed(0)}</td><td>{Number(o.forecast_momentum_score).toFixed(0)}</td><td>{Number(o.attention_gap_score).toFixed(0)}</td><td>{Math.round(Number(o.confidence)*100)}%</td><td className={Number(o.higo_adjusted)>=92?'score good':'score warn'}>{Number(o.higo_adjusted).toFixed(1)}</td></tr>)}</tbody></table>}</div>
    <div className="card wide"><h2>System status</h2><p className="muted">Evidence-first selection. Competition can veto an opportunity regardless of price, discount or forecast. No evidence means no promotion claim.</p></div><div className="card side"><h2>Selection policy</h2><p className="muted">Rolling validity, travel exclusion, seller saturation, Ad Pressure Proxy, demand, forecast and purchase friction.</p><Link className="button" href="/products">View candidates</Link></div>
  </div></main>
}
