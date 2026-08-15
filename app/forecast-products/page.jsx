'use client';

import {useEffect,useMemo,useState} from 'react';
import {supabase} from '@/lib/supabase';
import styles from './forecast-products.module.css';

const num=(v,d=1)=>v===null||v===undefined||Number.isNaN(Number(v))?'—':Number(v).toLocaleString('el-GR',{maximumFractionDigits:d});
const money=v=>v===null||v===undefined?'—':`€${Number(v).toLocaleString('el-GR',{minimumFractionDigits:2,maximumFractionDigits:2})}`;
const arr=v=>Array.isArray(v)?v:[];
const help={rank:'Final Ranking V3 score. Combines observed market/merchant/commercial signals with AI product and creative fit, then applies independent Skeptic risk.',demand:'Greek demand signal from current market intelligence; not sales volume.',competition:'Competition evidence. Missing stays unknown and never gets a low-competition bonus.',pain:'Optional semantic pain/JTBD support. Zero does not reject a product.',creative:'AI estimate of how clearly the product can be communicated and demonstrated in content.',risk:'Independent ranking skeptic risk: higher means greater promotion uncertainty.'};

export default function ForecastProducts(){
 const [rows,setRows]=useState([]),[loading,setLoading]=useState(true),[error,setError]=useState(''),[query,setQuery]=useState(''),[band,setBand]=useState('');
 async function load(){setLoading(true);setError('');const {data,error}=await supabase.rpc('admin_top_ranked_products',{p_limit:500,p_band:band||null});if(error)setError(error.message);else setRows(data||[]);setLoading(false)}
 useEffect(()=>{load()},[band]);
 const filtered=useMemo(()=>{const q=query.trim().toLowerCase();return q?rows.filter(x=>`${x.product_name||''} ${x.merchant_name||''} ${x.brand_name||''} ${x.category||''} ${x.promotion_angle||''}`.toLowerCase().includes(q)):rows},[rows,query]);
 if(loading)return <main className={styles.wrap}><div className={styles.loading}>Loading product ranking…</div></main>;
 return <main className={styles.wrap}>
  <header className={styles.hero}><div><span className={styles.eyebrow}>Ranking V3 · Promotion Decision Engine</span><h1>Products to Promote</h1><p>Από το affiliate universe στην τελική λίστα: demand, merchant context, economics, product fit, creative potential και independent AI risk check.</p></div><div className={styles.heroActions}><a href="/analytics">← Dashboard</a><button onClick={load}>↻ Refresh</button></div></header>
  {error&&<div className={styles.error}>{error}</div>}
  <section className={styles.controls}><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search product, merchant, category…"/><select value={band} onChange={e=>setBand(e.target.value)}><option value="">All ranked</option><option value="PROMOTE_NOW">Promote now</option><option value="HIGH_POTENTIAL">High potential</option><option value="TEST">Test</option><option value="WATCHLIST">Watchlist</option></select><span>{filtered.length} products</span></section>
  {filtered.length?<section className={styles.list}>{filtered.map(x=><article className={styles.row} key={`${x.run_id}-${x.source_record_hash}`}>
   <div className={styles.pos}>#{x.global_rank}</div>
   <div className={styles.identity}><b>{x.product_name}</b><span>{x.merchant_name}{x.brand_name?` · ${x.brand_name}`:''}</span><small>{x.category||'—'}{x.subcategory?` › ${x.subcategory}`:''}</small><p>{x.promotion_angle||x.promotion_reason||'—'}</p><div className={styles.tags}>{arr(x.recommended_channels).map(c=><span key={c}>{c}</span>)}{arr(x.risk_flags).slice(0,2).map(r=><i key={r}>{r}</i>)}</div></div>
   <div className={styles.score}><strong title={help.rank}>{num(x.rank_score,1)}</strong><em>{x.rank_band?.replaceAll('_',' ')}</em><span>AI confidence <b>{num(x.ai_confidence,0)}%</b></span></div>
   <div className={styles.metrics}><span title={help.demand}>Demand <b>{num(x.merchant_demand_score,0)}</b></span><span title={help.competition}>Competition <b>{num(x.competition_score,0)}</b></span><span title={help.pain}>Pain signal <b>{num(x.pain_signal_score,0)}</b></span><span title={help.creative}>Creative <b>{num(x.ai_creative_score,0)}</b></span><span title={help.risk}>Risk <b>{num(x.ai_risk_score,0)}</b></span><span>Commission <b>{money(x.expected_commission_eur)}</b></span><span>Price <b>{money(x.effective_price)}</b></span><span>Discount <b>{num(x.discount_pct,0)}%</b></span></div>
   <div className={styles.action}>{x.tracking_url?<a href={x.tracking_url} target="_blank" rel="noreferrer">Promote link ↗</a>:<span>No link</span>}<small>{x.promotion_reason||x.ai_summary||''}</small></div>
  </article>)}</section>:<section className={styles.empty}><h3>No ranking results yet</h3><p>The first Ranking V3 run will populate this list. Missing validated pain no longer blocks a product from competing.</p></section>}
 </main>
}
