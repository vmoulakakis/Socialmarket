'use client';

import {useEffect,useMemo,useState} from 'react';
import {supabase} from '@/lib/supabase';
import styles from './forecast-products.module.css';

const num=(v,d=0)=>v===null||v===undefined||Number.isNaN(Number(v))?'—':Number(v).toLocaleString('el-GR',{maximumFractionDigits:d});
const money=v=>v===null||v===undefined?'—':`€${Number(v).toLocaleString('el-GR',{minimumFractionDigits:2,maximumFractionDigits:2})}`;
const arr=v=>Array.isArray(v)?v:[];
const stateLabel={selected_top100:'Selected',approved_for_social:'→ SocialScheduler',claimed_by_scheduler:'Claimed',scheduled_in_provider:'Buffer scheduled',published:'Published'};

export default function ForecastProducts(){
 const [rows,setRows]=useState([]),[history,setHistory]=useState([]),[loading,setLoading]=useState(true),[error,setError]=useState(''),[query,setQuery]=useState(''),[category,setCategory]=useState('');
 async function load(){
  setLoading(true);setError('');
  const [current,old]=await Promise.all([
   supabase.from('socialmarket_top100_current_v').select('*').order('rank',{ascending:true}),
   supabase.from('socialmarket_top100_history_v').select('source_record_hash,category,published,passed_to_socialscheduler,claimed_by_socialscheduler,scheduled_in_provider,last_published_at').eq('run_status','completed').order('last_published_at',{ascending:false}).limit(500),
  ]);
  if(current.error)setError(current.error.message);else setRows(current.data||[]);
  if(!old.error)setHistory(old.data||[]);
  setLoading(false);
 }
 useEffect(()=>{load()},[]);
 const categories=useMemo(()=>[...new Set(rows.map(x=>x.category).filter(Boolean))],[rows]);
 const filtered=useMemo(()=>{const q=query.trim().toLowerCase();return rows.filter(x=>(!category||x.category===category)&&(!q||`${x.product_name||''} ${x.shop_name||''} ${x.category||''} ${x.ai_reason||''} ${x.audience||''}`.toLowerCase().includes(q)))},[rows,query,category]);
 const uniquePublished=useMemo(()=>new Set(history.filter(x=>x.published).map(x=>x.source_record_hash)).size,[history]);
 const handed=rows.filter(x=>x.passed_to_socialscheduler).length;
 const scheduled=rows.filter(x=>x.scheduled_in_provider).length;
 const runDate=rows[0]?.run_date||'—';
 if(loading)return <main className={styles.wrap}><div className={styles.loading}>Loading autonomous Top 100…</div></main>;
 return <main className={styles.wrap}>
  <header className={styles.hero}><div><span className={styles.eyebrow}>AUTONOMOUS GREECE TOP100 V2 · DAILY</span><h1>Top 100</h1><p>Μόνο προϊόντα με αναμενόμενη προμήθεια &gt; €20, live evidence σπανιότητας/απουσίας από μεγάλα ελληνικά shopping surfaces, έως 5 κατηγορίες, AI demand + forecast synthesis και provider-confirmed lifecycle προς SocialScheduler.</p></div><div className={styles.heroActions}><a href="/">← AI Process</a><button onClick={load}>↻ Refresh</button></div></header>
  {error&&<div className={styles.error}>{error}</div>}
  <section className={styles.controls}><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search product, category, shop, AI reason…"/><select value={category} onChange={e=>setCategory(e.target.value)}><option value="">All categories ({categories.length}/5)</option>{categories.map(c=><option key={c} value={c}>{c}</option>)}</select><span>{filtered.length} active · run {runDate}</span></section>
  <section className={styles.controls}><span>Active <b>{rows.length}/100</b></span><span>Categories <b>{categories.length}/5</b></span><span>Passed to Scheduler <b>{handed}</b></span><span>Buffer scheduled <b>{scheduled}</b></span><span>Provider-confirmed published history <b>{uniquePublished}</b></span></section>
  {filtered.length?<section className={styles.list}>{filtered.map(x=><article className={styles.row} key={`${x.run_id}-${x.source_record_hash}`}>
   <div className={styles.pos}>#{x.rank}</div>
   <div className={styles.identity}><b>{x.product_name}</b><span>{x.shop_name||'AliExpress'} · {x.category}</span><small>{x.greece_scarcity_status} · confidence {num(x.greece_scarcity_confidence)}%</small><p>{x.ai_reason||x.hook||'—'}</p><div className={styles.tags}><span>{stateLabel[x.lifecycle_state]||x.lifecycle_state}</span>{x.landing_candidate&&<i>AFFINITY candidate</i>}{arr(x.published_platforms).map(p=><span key={p}>{p}</span>)}</div></div>
   <div className={styles.score}><strong>{num(x.opportunity_score,1)}</strong><em>OPPORTUNITY</em><span>Forecast <b>{num(x.forecast_score)}%</b></span></div>
   <div className={styles.metrics}><span>Commission / sale <b>{money(x.expected_commission_eur)}</b></span><span>Price <b>{money(x.sale_price_eur)}</b></span><span>Demand <b>{num(x.demand_score)}</b></span><span>Forecast <b>{num(x.forecast_score)}</b></span><span>Organic <b>{num(x.organic_score)}</b></span><span>Ads <b>{num(x.ads_score)}</b></span><span>Viral <b>{num(x.viral_score)}</b></span><span>Scarcity <b>{num(x.greece_scarcity_confidence)}</b></span></div>
   <div className={styles.action}><a href={x.tracking_url} target="_blank" rel="noreferrer">Tracking URL ↗</a>{x.detail_url&&<a href={x.detail_url} target="_blank" rel="noreferrer">Product ↗</a>}<small>{x.passed_to_socialscheduler?'✓ Passed to SocialScheduler':'Waiting for daily handoff'}</small><small>{x.claimed_by_socialscheduler?'✓ Claimed by executor':'Not claimed yet'}</small><small>{x.scheduled_in_provider?'✓ Provider scheduled':'Not scheduled yet'}</small></div>
   <details className={styles.details}><summary>AI decision & social copy</summary><div className={styles.detailGrid}><section><h4>Buyer</h4><p>{x.audience||'—'}</p><h4>Hook</h4><p>{x.hook||'—'}</p></section><section><h4>Caption</h4><p>{x.caption||'—'}</p><div className={styles.keywordList}>{arr(x.hashtags).map(h=><span key={h}>{h}</span>)}</div></section><section className={styles.wide}><h4>Lifecycle truth</h4><p>{x.lifecycle_state} · source hash {x.source_record_hash}</p>{arr(x.provider_post_ids).length>0&&<p>Provider IDs: {arr(x.provider_post_ids).join(', ')}</p>}</section></div></details>
  </article>)}</section>:<section className={styles.empty}><h3>Top 100 snapshot is rebuilding</h3><p>Δεν υπάρχει ακόμη ολοκληρωμένο evidence-qualified snapshot. Η σελίδα εμφανίζει μόνο επιτυχημένα runs και δεν παρουσιάζει partial ή failed AI αποτελέσματα ως έγκυρο Top 100. Τα hard gates παραμένουν: προμήθεια &gt; €20, Greece scarcity evidence και έως 5 κατηγορίες.</p></section>}
 </main>
}
