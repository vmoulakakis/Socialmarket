'use client';

import Link from 'next/link';
import {useEffect,useState} from 'react';
import {supabase} from '@/lib/supabase';

const fmt=(v,d=0)=>v===null||v===undefined?'—':Number(v).toLocaleString('el-GR',{maximumFractionDigits:d});
const money=v=>v===null||v===undefined?'—':`€${Number(v).toLocaleString('el-GR',{minimumFractionDigits:2,maximumFractionDigits:2})}`;

export default function Products(){
 const [pipe,setPipe]=useState(null),[config,setConfig]=useState(null),[top,setTop]=useState([]),[loading,setLoading]=useState(true),[error,setError]=useState('');
 async function load(){
  setLoading(true);setError('');
  const [a,b,c]=await Promise.all([
   supabase.rpc('admin_product_pipeline_analytics'),
   supabase.rpc('admin_get_product_config'),
   supabase.rpc('admin_top_ranked_products',{p_limit:20,p_band:null})
  ]);
  const e=a.error||b.error||c.error;if(e)setError(e.message);else{setPipe(a.data);setConfig(b.data);setTop(c.data||[])}setLoading(false)
 }
 useEffect(()=>{load()},[]);
 const cfg=config?.config||{},a=pipe?.latest_phase_a;const exclusions=Array.isArray(pipe?.phase_a_exclusions)?pipe.phase_a_exclusions:[];
 return <main>
  <div className="hero"><div><div className="eyebrow">FULL LINKWISE PRODUCT UNIVERSE</div><h1>Products</h1><p className="sub">Commercial universe → hard eligibility → deterministic preselection → market/RAG context → DeepSeek ranking + independent skeptic. Pain is additive evidence, not a mandatory product gate.</p></div><div style={{display:'flex',gap:10}}><button className="button" onClick={load}>↻ Refresh</button><Link className="button" href="/forecast-products">Top 100 →</Link></div></div>
  {error&&<div className="card"><p className="bad">{error}</p></div>}
  {loading?<div className="card"><p className="muted">Loading production product pipeline…</p></div>:<>
   <div className="card" style={{marginBottom:16}}><h2>Active commercial gates · config v{config?.version??'—'}</h2><div className="grid4">
    <div className="metric"><span>Minimum commission</span><strong>€{fmt(cfg.min_expected_commission_eur,2)}</strong></div>
    <div className="metric"><span>Merchant trust</span><strong>{fmt(cfg.min_merchant_trust)}/100</strong></div>
    <div className="metric"><span>AI candidates</span><strong>{fmt(cfg.ai_max_candidates)}</strong></div>
    <div className="metric"><span>Thinking mode</span><strong>{cfg.ai_thinking_mode||'auto'}</strong></div>
   </div><p className="muted">Hard safety invariants still reject unresolved/blocked merchants, invalid price/currency, out-of-stock offers, missing tracking/image and expected commission below €10. Missing pain or competition does not become a favorable assumption.</p></div>

   <div className="grid2" style={{marginBottom:16}}><div className="card"><h2>Latest full-feed scan</h2>{a?<><p><b>{fmt(a.records_seen)}</b> Linkwise records scanned</p><p><b>{fmt(a.commission_eligible_records??a.commission_eligible_offers)}</b> commercial-eligible offers</p><p><b>{fmt(a.unique_commission_eligible_products)}</b> unique eligible products</p><p className="muted">Runtime config v{a.runtime_config_version??'—'} · {a.runtime_profile_name||cfg.profile_name||'Adaptive Ranking'}</p></>:<p className="muted">No persisted full-feed profile yet. The weekly production run will create it.</p>}</div><div className="card"><h2>What happens next</h2><p><b>1.</b> Cheap deterministic ranking over every eligible product.</p><p><b>2.</b> High-recall market/RAG context on the strongest candidates.</p><p><b>3.</b> DeepSeek strategist + independent ranking skeptic.</p><p><b>4.</b> Persist 100–200 final rankings, SEO for all saved rows and audited Top 20 creatives.</p><Link className="button" href="/">Open Full AI Process →</Link></div></div>

   <div className="card" style={{marginBottom:16}}><h2>Latest exclusion reasons</h2>{exclusions.length?<table className="table"><thead><tr><th>Hard filter</th><th>Rejected records</th></tr></thead><tbody>{exclusions.map(([reason,count])=><tr key={reason}><td>{String(reason).replaceAll('_',' ')}</td><td><b>{fmt(count)}</b></td></tr>)}</tbody></table>:<p className="muted">No exclusion profile persisted yet.</p>}</div>

   <div className="card"><div style={{display:'flex',justifyContent:'space-between',gap:16,alignItems:'center'}}><div><h2 style={{marginBottom:4}}>Current leading products</h2><p className="muted">Preview from the latest canonical ranking. Full operational list is Top 100.</p></div><Link className="button" href="/forecast-products">Open Top 100 →</Link></div>{top.length===0?<p className="muted">No canonical product ranking is currently available.</p>:<table className="table"><thead><tr><th>#</th><th>Product</th><th>Merchant</th><th>Price</th><th>Commission</th><th>Rank</th><th>Band</th></tr></thead><tbody>{top.map(x=><tr key={`${x.run_id}-${x.source_record_hash}`}><td><b>#{x.global_rank}</b></td><td><strong>{x.product_name}</strong><div className="muted">{x.category||''}</div></td><td>{x.merchant_name}</td><td>{money(x.effective_price)}</td><td>{money(x.expected_commission_eur)}</td><td className="score good">{fmt(x.rank_score,1)}</td><td>{String(x.rank_band||'—').replaceAll('_',' ')}</td></tr>)}</tbody></table>}</div>
  </>}
 </main>
}
