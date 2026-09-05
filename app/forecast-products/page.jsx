'use client';

import {useEffect,useMemo,useState} from 'react';
import {supabase} from '@/lib/supabase';
import styles from './forecast-products.module.css';

const num=(v,d=0)=>v===null||v===undefined||Number.isNaN(Number(v))?'—':Number(v).toLocaleString('el-GR',{maximumFractionDigits:d});
const money=v=>v===null||v===undefined?'—':`€${Number(v).toLocaleString('el-GR',{minimumFractionDigits:2,maximumFractionDigits:2})}`;
const arr=v=>Array.isArray(v)?v:[];

export default function Marketplace200Admin(){
 const [rows,setRows]=useState([]),[loading,setLoading]=useState(true),[error,setError]=useState(''),[query,setQuery]=useState(''),[portfolio,setPortfolio]=useState(''),[cluster,setCluster]=useState('');
 async function load(){
  setLoading(true);setError('');
  const res=await supabase.from('socialmarket_marketplace200_admin_v').select('*').order('portfolio',{ascending:true}).order('affinity_score',{ascending:false}).limit(250);
  if(res.error)setError(res.error.message);else setRows(res.data||[]);setLoading(false);
 }
 useEffect(()=>{load()},[]);

 const clusters=useMemo(()=>[...new Set(rows.map(x=>x.semantic_cluster_key).filter(Boolean))],[rows]);
 const filtered=useMemo(()=>{const q=query.trim().toLowerCase();return rows.filter(x=>(!portfolio||x.portfolio===portfolio)&&(!cluster||x.semantic_cluster_key===cluster)&&(!q||[x.product_name,x.merchant_name,x.niche,x.subniche,x.job_to_be_done,x.pain_statement,x.gap_statement,x.solution_statement,...arr(x.semantic_tags)].join(' ').toLowerCase().includes(q)))},[rows,query,portfolio,cluster]);
 const linkwise=rows.filter(x=>x.portfolio==='linkwise'),ali=rows.filter(x=>x.portfolio==='aliexpress');
 const handed=rows.filter(x=>x.passed_to_socialscheduler).length,scheduled=rows.filter(x=>x.scheduled_in_provider).length,published=rows.filter(x=>x.published).length;
 const qualityAvg=rows.length?rows.reduce((s,x)=>s+Number(x.product_quality_score||0),0)/rows.length:0;
 const merchantCounts=new Map();for(const x of linkwise){const k=x.merchant_id||x.merchant_name||'unknown';merchantCounts.set(k,(merchantCounts.get(k)||0)+1)}
 const sellerCounts=new Map();for(const x of ali){const k=x.merchant_name||'unknown';sellerCounts.set(k,(sellerCounts.get(k)||0)+1)}
 const merchantMax=Math.max(0,...merchantCounts.values()),sellerMax=Math.max(0,...sellerCounts.values());
 const runDate=rows[0]?.run_date||'—';

 if(loading)return <main className={styles.wrap}><div className={styles.loading}>Loading Semantic Marketplace 200…</div></main>;
 return <main className={styles.wrap}>
  <header className={styles.hero}><div><span className={styles.eyebrow}>AFFINITY · SEMANTIC SOCIAL MARKETPLACE 200</span><h1>Marketplace 200 Control</h1><p>100 Linkwise buried finds + 100 AliExpress Greek-gap products. Hard gates: commission &gt; €30, max 3 προϊόντα/merchant ή seller, merchant rank/trust quality, evidence-first semantic fit, Product Research Agent + independent Skeptic QA, provider-confirmed social lifecycle.</p></div><div className={styles.heroActions}><a href="/marketplace" target="_blank" rel="noreferrer">Public Marketplace ↗</a><button onClick={load}>↻ Refresh</button></div></header>
  {error&&<div className={styles.error}>{error}</div>}

  <section className={styles.controls}><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search pain, JTBD, product, merchant, semantic tag…"/><select value={portfolio} onChange={e=>setPortfolio(e.target.value)}><option value="">Both portfolios</option><option value="linkwise">Linkwise Discovery 100</option><option value="aliexpress">AliExpress Exclusive 100</option></select><select value={cluster} onChange={e=>setCluster(e.target.value)}><option value="">All semantic clusters ({clusters.length})</option>{clusters.map(c=><option key={c} value={c}>{c}</option>)}</select></section>

  <section className={styles.kpis}>
   <div><small>ACTIVE</small><b>{rows.length}/200</b><span>run {runDate}</span></div>
   <div><small>LINKWISE</small><b>{linkwise.length}/100</b><span>merchant max {merchantMax}/3</span></div>
   <div><small>ALIEXPRESS</small><b>{ali.length}/100</b><span>seller max {sellerMax}/3</span></div>
   <div><small>SEMANTIC CLUSTERS</small><b>{clusters.length}</b><span>niche → pain → solution</span></div>
   <div><small>AVG QUALITY</small><b>{num(qualityAvg,1)}</b><span>minimum 75</span></div>
   <div><small>SOCIAL</small><b>{handed} / {scheduled}</b><span>passed / scheduled</span></div>
  </section>

  {filtered.length?<section className={styles.list}>{filtered.map((x,index)=>{const copy=x.social_copy||{},evidence=x.evidence_summary||{};return <article className={styles.row} key={x.id}>
   <div className={styles.pos}>#{index+1}</div>
   <div className={styles.identity}><b>{x.product_name}</b><span>{x.portfolio==='linkwise'?'LINKWISE':'ALIEXPRESS'} · {x.merchant_name||'seller unknown'} · {x.semantic_cluster_key}</span><small>{x.niche}{x.subniche?` → ${x.subniche}`:''} · {x.lifecycle_state}</small><p><b>PAIN:</b> {x.pain_statement}<br/><b>GAP:</b> {x.gap_statement}<br/><b>SOLUTION:</b> {x.solution_statement}</p><div className={styles.tags}><span>QA {num(x.product_quality_score)}</span><span>AFFINITY {num(x.affinity_score)}</span><span>{x.skeptic_verdict}</span>{x.greek_availability&&<i>{x.greek_availability}</i>}{x.landing_candidate&&<i>AFFINITY PAGE</i>}</div></div>
   <div className={styles.score}><strong>{num(x.affinity_score,1)}</strong><em>AFFINITY</em><span>Quality <b>{num(x.product_quality_score)}</b></span><span>Semantic <b>{num(x.semantic_fit_score)}</b></span></div>
   <div className={styles.metrics}><span>Commission <b>{money(x.expected_commission_eur)}</b></span><span>Price <b>{money(x.sale_price_eur)}</b></span><span>Demand <b>{num(x.demand_score)}</b></span><span>Pain <b>{num(x.pain_score)}</b></span><span>Whitespace <b>{num(x.whitespace_score)}</b></span><span>Scarcity <b>{num(x.scarcity_score)}</b></span><span>Organic <b>{num(x.organic_score)}</b></span><span>Viral <b>{num(x.viral_score)}</b></span></div>
   <div className={styles.action}><a href={x.tracking_url} target="_blank" rel="noreferrer">Tracking ↗</a>{x.detail_url&&<a href={x.detail_url} target="_blank" rel="noreferrer">Product ↗</a>}<small>{x.portfolio==='linkwise'?`Merchant rank #${x.merchant_global_rank||'—'} · trust ${num(x.merchant_trust_score)} · research conf ${num(Number(x.merchant_research_confidence||0)*100)}%`:`Seller quality evidence ${num(x.seller_quality_score)}`}</small><small>{x.passed_to_socialscheduler?'✓ SocialScheduler':'Not handed off'} · {x.claimed_by_socialscheduler?'✓ claimed':'not claimed'} · {x.scheduled_in_provider?'✓ provider scheduled':'not scheduled'} · {x.published?'✓ published':'not published'}</small></div>
   <details className={styles.details}><summary>Semantic decision · QA · evidence · social copy</summary><div className={styles.detailGrid}>
    <section><h4>Job to be done</h4><p>{x.job_to_be_done}</p><h4>Semantic tags</h4><div className={styles.keywordList}>{arr(x.semantic_tags).map(t=><span key={t}>{t}</span>)}</div><h4>Greek market</h4><p>{x.greek_availability||'N/A for Linkwise'} · scarcity {num(x.scarcity_score)}</p></section>
    <section><h4>Social creative</h4><p><b>Audience:</b> {copy.audience||'—'}</p><p><b>Hook:</b> {copy.hook||'—'}</p><p>{copy.caption||'—'}</p><div className={styles.keywordList}>{arr(copy.hashtags).map(h=><span key={h}>{h}</span>)}</div></section>
    <section className={styles.wide}><h4>Quality evidence ledger</h4><pre>{JSON.stringify(evidence,null,2)}</pre><p><b>Research:</b> {copy.research_reason||'—'}</p>{arr(copy.skeptic_reasons).length>0&&<p><b>Skeptic:</b> {arr(copy.skeptic_reasons).join(' · ')}</p>}{arr(copy.quality_unknowns).length>0&&<p><b>Unknowns:</b> {arr(copy.quality_unknowns).join(' · ')}</p>}<p>source hash: {x.source_record_hash}</p></section>
   </div></details>
  </article>})}</section>:<section className={styles.empty}><h3>Marketplace 200 is building under the new quality contract</h3><p>Δεν μεταφέρουμε το παλιό Top-100 ούτε βάζουμε placeholders. Η λίστα θα γεμίσει μόνο από νέα runs που περνούν: commission &gt; €30, strict merchant/seller gate, max 3 ανά merchant/seller, semantic pain-gap fit, quality ≥75, AFFINITY ≥76 και Skeptic verdict = validated.</p></section>}
 </main>
}
