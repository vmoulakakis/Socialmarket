'use client';

import {useEffect,useState} from 'react';
import {supabase} from '@/lib/supabase';
import styles from './analytics.module.css';

const n=(v,d=0)=>v===null||v===undefined||Number.isNaN(Number(v))?'—':Number(v).toLocaleString('el-GR',{maximumFractionDigits:d});
const money=v=>v===null||v===undefined?'—':`€${Number(v).toLocaleString('el-GR',{minimumFractionDigits:2,maximumFractionDigits:2})}`;
const age=v=>{if(!v)return 'no run yet';const h=(Date.now()-new Date(v).getTime())/3600000;if(h<1)return `${Math.max(1,Math.round(h*60))}m ago`;if(h<48)return `${h.toFixed(1)}h ago`;return `${(h/24).toFixed(1)}d ago`};
const tips={score:'Final promotion rank from demand, whitespace, commission, competition, merchant trust, price/value, purchase signal, optional pain/seasonality and AI product/creative fit, reduced by Skeptic risk.',demand:'Observed/derived Greek demand signal from SocialMarket market intelligence. It is not sales volume.',confidence:'AI confidence in the promotion thesis based only on available evidence. Missing evidence lowers confidence; it does not automatically remove a product.',risk:'Independent Ranking Skeptic risk. Higher means more reasons to test carefully.',commission:'Expected affiliate commission per conversion using the deterministic merchant program rule.',band:'PROMOTE NOW = strongest current opportunity. HIGH POTENTIAL = strong candidate. TEST = worth controlled experimentation. WATCHLIST = keep observing.'};
function Tip({text}){return <span className={styles.tip} title={text}>?</span>}
function KPI({label,value,help,meta}){return <div className={styles.kpi}><span>{label}{help&&<Tip text={help}/>}</span><b>{value}</b>{meta&&<small>{meta}</small>}</div>}

export default function Analytics(){
 const [data,setData]=useState(null),[loading,setLoading]=useState(true),[error,setError]=useState('');
 async function load(){setLoading(true);setError('');const {data,error}=await supabase.rpc('admin_ranking_dashboard');if(error)setError(error.message);else setData(data);setLoading(false)}
 useEffect(()=>{load()},[]);
 if(loading)return <main className={styles.page}><div className={styles.loading}>Loading promotion ranking…</div></main>;
 const counts=data?.product_counts||{},run=data?.latest_run||{},products=data?.top_products||[],merchants=data?.top_merchants||[],demand=data?.demand_summary||{};
 return <main className={styles.page}>
  <header className={styles.hero}>
   <div><span className={styles.kicker}>SOCIALMARKET · DAILY DECISION BOARD</span><h1>Τι να προωθήσουμε τώρα</h1><p>Η μικρότερη δυνατή εικόνα: τι ανέλυσε το σύστημα, ποια προϊόντα βγήκαν πρώτα και γιατί.</p></div>
   <div className={styles.actions}><button onClick={load}>↻ Refresh</button><a href="/forecast-products">Όλη η κατάταξη →</a></div>
  </header>
  {error&&<div className={styles.error}>{error}</div>}
  <section className={styles.kpis}>
   <KPI label="Ranked products" value={n(counts.ranked)} help="Products saved from the latest completed Ranking V3 run." meta={run.completed_at?`last run ${age(run.completed_at)}`:'waiting for first ranking run'}/>
   <KPI label="Promote now" value={n(counts.promote_now)} help={tips.band} meta="highest-priority products"/>
   <KPI label="High potential" value={n(counts.high_potential)} help={tips.band} meta={`${n(counts.test)} additional TEST`}/>
   <KPI label="Demand freshness" value={age(demand.latest_observed_at)} help="Age of the latest canonical Greek category-market observation." meta={`${n(demand.active_themes)} active demand themes`}/>
  </section>
  <section className={styles.mainPanel}>
   <div className={styles.panelHead}><div><span>TOP PRODUCTS TO PROMOTE</span><h2>Η τελική AI λίστα</h2></div><small title="Ranking runs after market/demand intelligence. Pain is one optional signal, not an admission gate.">Demand → Merchant → Product → AI Strategy → Skeptic</small></div>
   {products.length?<div className={styles.products}>{products.map(x=><article className={styles.product} key={`${x.run_id}-${x.source_record_hash}`}>
    <div className={styles.rank}>#{x.global_rank}</div>
    <div className={styles.productBody}><div className={styles.productTitle}><b>{x.product_name}</b><span>{x.merchant_name}{x.brand_name?` · ${x.brand_name}`:''}</span></div><p>{x.promotion_angle||x.promotion_reason||'AI promotion angle will appear after the ranking run.'}</p><div className={styles.channels}>{(Array.isArray(x.recommended_channels)?x.recommended_channels:[]).map(c=><span key={c}>{c}</span>)}</div></div>
    <div className={styles.decision}><strong title={tips.score}>{n(x.rank_score,1)}</strong><em title={tips.band}>{x.rank_band?.replaceAll('_',' ')}</em><div><span title={tips.commission}>Commission <b>{money(x.expected_commission_eur)}</b></span><span title={tips.demand}>Demand <b>{n(x.merchant_demand_score,0)}</b></span><span title={tips.confidence}>AI confidence <b>{n(x.ai_confidence,0)}%</b></span><span title={tips.risk}>Risk <b>{n(x.ai_risk_score,0)}</b></span></div>{x.tracking_url&&<a href={x.tracking_url} target="_blank" rel="noreferrer">Open affiliate link ↗</a>}</div>
   </article>)}</div>:<div className={styles.empty}><b>Η πρώτη Ranking V3 λίστα δεν έχει ολοκληρωθεί ακόμη.</b><p>Το νέο pipeline δεν περιμένει validated pain. Με το επόμενο full product run θα εμφανίσει ranked προϊόντα από το πραγματικό affiliate feed.</p></div>}
  </section>
  <section className={styles.bottomGrid}>
   <div className={styles.smallPanel}><div className={styles.panelHead}><div><span>MERCHANT CONTEXT</span><h2>Top merchants</h2></div><Tip text="Merchant ranking is a supporting environment score. The final decision is product-level."/></div>{merchants.slice(0,5).map(x=><div className={styles.merchant} key={x.merchant_id}><b>#{x.global_rank} {x.canonical_name}</b><span>{x.primary_category||'—'}</span><strong>{n(x.overall_opportunity_score,1)}</strong></div>)}</div>
   <div className={styles.smallPanel}><div className={styles.panelHead}><div><span>PIPELINE</span><h2>Τι έτρεξε</h2></div></div><div className={styles.pipeline}><div><b>1</b><span>Greek market + category evidence</span></div><div><b>2</b><span>Deep Demand: GraphRAG, fuzzy, forecast lab, causal skeptic</span></div><div><b>3</b><span>Merchant intelligence + opportunity context</span></div><div><b>4</b><span>2.6M feed scan → deterministic shortlist</span></div><div><b>5</b><span>AI ranking strategist → independent ranking skeptic</span></div><div><b>6</b><span>Final Products to Promote</span></div></div></div>
  </section>
  <footer className={styles.footer}>Ranking V3 · {run.engine_version||'awaiting first run'} · {n(demand.analysis_runs)} demand analysis runs · hover ? or metrics for help</footer>
 </main>
}
