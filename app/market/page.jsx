'use client';

import { useEffect, useMemo, useState } from 'react';
import { supabase } from '@/lib/supabase';

const avg=a=>a.length?a.reduce((s,n)=>s+n,0)/a.length:0;
const clamp=n=>Math.max(0,Math.min(100,Number(n)||0));

export default function Market(){
  const [signals,setSignals]=useState([]);const [forecasts,setForecasts]=useState([]);const [loading,setLoading]=useState(true);const [runAt,setRunAt]=useState(null);
  useEffect(()=>{(async()=>{
    const [rr,fr]=await Promise.all([
      supabase.from('market_research_runs').select('id,finished_at').eq('status','completed').order('finished_at',{ascending:false}).limit(1).maybeSingle(),
      supabase.from('forecast_runs').select('id,finished_at').eq('status','completed').order('finished_at',{ascending:false}).limit(1).maybeSingle()
    ]);
    if(!rr.data?.id){setLoading(false);return}
    setRunAt(rr.data.finished_at);
    const queries=[supabase.from('market_signals').select('taxonomy_id,signal_type,normalized_score,direction,confidence,taxonomy(name,slug,taxonomy_type)').eq('research_run_id',rr.data.id).not('taxonomy_id','is',null)];
    if(fr.data?.id)queries.push(supabase.from('forecasts').select('taxonomy_id,growth_pct,direction,confidence,forecast_date,taxonomy(name,slug,taxonomy_type)').eq('forecast_run_id',fr.data.id).not('taxonomy_id','is',null));
    const result=await Promise.all(queries);setSignals(result[0]?.data||[]);setForecasts(result[1]?.data||[]);setLoading(false);
  })()},[]);

  const rows=useMemo(()=>{
    const map=new Map();
    for(const s of signals){
      const key=s.taxonomy_id;if(!key)continue;
      if(!map.has(key))map.set(key,{id:key,name:s.taxonomy?.name||'Unknown',type:s.taxonomy?.taxonomy_type||'',demand:[],seller:[],ad:[],adConf:[],organic:[]});
      const r=map.get(key);const type=(s.signal_type||'').toLowerCase();const val=Number(s.normalized_score||0);
      if(type==='seller_competition')r.seller.push(val);
      else if(type==='ad_pressure_proxy'){r.ad.push(val);r.adConf.push(Number(s.confidence||0))}
      else if(type.includes('competition')||type.includes('saturation'))r.organic.push(val);
      else if(type.includes('demand')||type.includes('search')||type.includes('trend')||type.includes('purchase'))r.demand.push(val);
    }
    const forecastByTax=new Map();
    for(const f of forecasts){if(!f.taxonomy_id)continue;const old=forecastByTax.get(f.taxonomy_id);if(!old||String(f.forecast_date)>String(old.forecast_date))forecastByTax.set(f.taxonomy_id,f)}
    return [...map.values()].map(r=>{
      const demand=avg(r.demand),seller=avg(r.seller),ad=avg(r.ad),adConfidence=avg(r.adConf),organic=avg(r.organic);const fc=forecastByTax.get(r.id);const growth=Number(fc?.growth_pct||0);const forecastScore=clamp(50+growth);
      const killed=seller>=82||(ad>=92&&adConfidence>=.65);const competition=clamp(seller*.7+(organic||seller)*.3);const marketScore=killed?0:clamp(demand*.50+forecastScore*.25+(100-competition)*.25);
      return {...r,demand,seller,ad,adConfidence,organic,growth,marketScore,killed,direction:fc?.direction||'—'};
    }).sort((a,b)=>Number(a.killed)-Number(b.killed)||b.marketScore-a.marketScore);
  },[signals,forecasts]);

  return <main><div className="hero"><div><div className="eyebrow">Market Intelligence</div><h1>Greece Opportunity Map</h1><p className="sub">Μόνο το τελευταίο completed research run. Seller saturation και Ad Pressure Proxy λειτουργούν ως kill-switch, όχι απλώς ως αρνητικό weight.</p>{runAt&&<p className="muted">Latest run: {new Date(runAt).toLocaleString('el-GR')}</p>}</div></div><div className="grid"><div className="card full">{loading?<p className="muted">Loading market evidence…</p>:rows.length===0?<p className="muted">Δεν υπάρχουν ακόμη market signals. Το πρώτο research run θα δημιουργήσει πραγματικές κατηγορίες και forecasts.</p>:<table className="table"><thead><tr><th>Category</th><th>Demand</th><th>Forecast</th><th>Seller Comp.</th><th>Ad Pressure*</th><th>Status</th><th>Market score</th></tr></thead><tbody>{rows.map(c=><tr key={c.id}><td><strong>{c.name}</strong><div className="muted">{c.type}</div></td><td>{c.demand.toFixed(0)}<div className="bar"><i style={{width:`${clamp(c.demand)}%`}}/></div></td><td className={c.growth>=0?'good':'bad'}>{c.growth>=0?'+':''}{c.growth.toFixed(1)}%</td><td className={c.seller>=82?'bad':''}>{c.seller.toFixed(0)}</td><td className={c.ad>=92&&c.adConfidence>=.65?'bad':''}>{c.ad?c.ad.toFixed(0):'—'}<div className="muted">{c.ad?`${Math.round(c.adConfidence*100)}% evidence`:''}</div></td><td><span className="pill">{c.killed?'EXCLUDED':c.direction}</span></td><td className={c.killed?'score bad':c.marketScore>=80?'score good':'score warn'}>{c.killed?'KILL':c.marketScore.toFixed(1)}</td></tr>)}</tbody></table>}<p className="muted" style={{marginTop:14}}>* Ad Pressure is an evidence-labelled commercial-pressure proxy until a direct paid-ad source is connected; it is never presented as observed ad spend or impression volume.</p></div></div></main>
}
