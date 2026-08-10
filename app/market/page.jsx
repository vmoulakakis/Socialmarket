'use client';

import { useEffect, useMemo, useState } from 'react';
import { supabase } from '@/lib/supabase';

const avg=a=>a.length?a.reduce((s,n)=>s+n,0)/a.length:0;
const clamp=n=>Math.max(0,Math.min(100,n));

export default function Market(){
  const [signals,setSignals]=useState([]);
  const [forecasts,setForecasts]=useState([]);
  const [loading,setLoading]=useState(true);

  useEffect(()=>{(async()=>{
    const [s,f]=await Promise.all([
      supabase.from('market_signals').select('taxonomy_id,signal_type,normalized_score,direction,confidence,taxonomy(name,slug,taxonomy_type)').not('taxonomy_id','is',null).order('observed_at',{ascending:false}).limit(5000),
      supabase.from('forecasts').select('taxonomy_id,growth_pct,direction,confidence,forecast_date,taxonomy(name,slug,taxonomy_type)').not('taxonomy_id','is',null).order('forecast_date',{ascending:false}).limit(3000)
    ]);
    setSignals(s.data||[]);setForecasts(f.data||[]);setLoading(false);
  })()},[]);

  const rows=useMemo(()=>{
    const map=new Map();
    for(const s of signals){
      const key=s.taxonomy_id;if(!key)continue;
      if(!map.has(key))map.set(key,{id:key,name:s.taxonomy?.name||'Unknown',type:s.taxonomy?.taxonomy_type||'',demand:[],competition:[],other:[]});
      const r=map.get(key);const type=(s.signal_type||'').toLowerCase();const val=Number(s.normalized_score||0);
      if(type.includes('competition')||type.includes('saturation'))r.competition.push(val);
      else if(type.includes('demand')||type.includes('search')||type.includes('trend')||type.includes('purchase'))r.demand.push(val);
      else r.other.push(val);
    }
    const latestForecast=new Map();
    for(const f of forecasts){if(!f.taxonomy_id)continue;if(!latestForecast.has(f.taxonomy_id))latestForecast.set(f.taxonomy_id,f)}
    return [...map.values()].map(r=>{
      const demand=avg(r.demand);const competition=avg(r.competition);const fc=latestForecast.get(r.id);
      const growth=Number(fc?.growth_pct||0);const forecastScore=clamp(50+growth);
      const marketScore=clamp(demand*.55+forecastScore*.25+(100-competition)*.20);
      return {...r,demand,competition,growth,marketScore,direction:fc?.direction||'—',confidence:Number(fc?.confidence||0)};
    }).sort((a,b)=>b.marketScore-a.marketScore);
  },[signals,forecasts]);

  return <main><div className="hero"><div><div className="eyebrow">Market Intelligence</div><h1>Greece Opportunity Map</h1><p className="sub">Category/subcategory demand, competition saturation and statistical momentum. Το market score είναι ξεχωριστό από το product-level HIGO.</p></div></div><div className="grid"><div className="card full">{loading?<p className="muted">Loading market evidence…</p>:rows.length===0?<p className="muted">Δεν υπάρχουν ακόμη market signals. Το πρώτο research run θα δημιουργήσει τις πραγματικές κατηγορίες και forecasts.</p>:<table className="table"><thead><tr><th>Category</th><th>Demand</th><th>Forecast</th><th>Competition</th><th>Direction</th><th>Market score</th></tr></thead><tbody>{rows.map(c=><tr key={c.id}><td><strong>{c.name}</strong><div className="muted">{c.type}</div></td><td>{c.demand.toFixed(0)}<div className="bar"><i style={{width:`${clamp(c.demand)}%`}}/></div></td><td className={c.growth>=0?'good':'bad'}>{c.growth>=0?'+':''}{c.growth.toFixed(1)}%</td><td>{c.competition.toFixed(0)}</td><td><span className="pill">{c.direction}</span></td><td className={c.marketScore>=80?'score good':'score warn'}>{c.marketScore.toFixed(1)}</td></tr>)}</tbody></table>}</div></div></main>
}
