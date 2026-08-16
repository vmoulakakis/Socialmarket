'use client';

import {useEffect,useState} from 'react';
import {supabase} from '@/lib/supabase';
import styles from './analytics.module.css';

const n=(v,d=0)=>v===null||v===undefined||Number.isNaN(Number(v))?'—':Number(v).toLocaleString('el-GR',{maximumFractionDigits:d});
const money=v=>v===null||v===undefined?'—':`€${Number(v).toLocaleString('el-GR',{minimumFractionDigits:2,maximumFractionDigits:2})}`;
const obj=v=>v&&typeof v==='object'&&!Array.isArray(v)?v:{};
const age=v=>{if(!v)return 'no run yet';const h=(Date.now()-new Date(v).getTime())/3600000;if(h<1)return `${Math.max(1,Math.round(h*60))}m ago`;if(h<48)return `${h.toFixed(1)}h ago`;return `${(h/24).toFixed(1)}d ago`};
const tips={score:'Final promotion rank from market demand, whitespace, commission, network commercial performance, competition, merchant trust, product fit and creative fit, reduced by independent Skeptic risk.',network:'Observed Linkwise/program conversion baseline. It is not observed sales for this exact product.',forecast:'Deterministic expected approved commission per 100 clicks using network program CVR × approval × product commission. This is a modeled baseline, not observed revenue.',risk:'Independent Ranking Skeptic risk. Higher means more reasons to test carefully.',commission:'Expected affiliate commission per approved conversion using the deterministic merchant program rule.',band:'PROMOTE NOW = strongest current opportunity. HIGH POTENTIAL = strong candidate. TEST = controlled experiment. WATCHLIST = keep observing.'};
function Tip({text}){return <span className={styles.tip} title={text}>?</span>}
function KPI({label,value,help,meta}){return <div className={styles.kpi}><span>{label}{help&&<Tip text={help}/>}</span><b>{value}</b>{meta&&<small>{meta}</small>}</div>}

export default function Analytics(){
 const [data,setData]=useState(null),[loading,setLoading]=useState(true),[error,setError]=useState('');
 async function load(){setLoading(true);setError('');const {data,error}=await supabase.rpc('admin_ranking_dashboard');if(error)setError(error.message);else setData(data);setLoading(false)}
 useEffect(()=>{load()},[]);
 if(loading)return <main className={styles.page}><div className={styles.loading}>Loading promotion ranking…</div></main>;
 const counts=data?.product_counts||{},run=data?.latest_run||{},products=data?.top_products||[],merchants=data?.top_merchants||[],demand=data?.demand_summary||{},analytics=data?.analytics_status||{};
 return <main className={styles.page}>
  <header className={styles.hero}>
   <div><span className={styles.kicker}>SOCIALMARKET · DAILY DECISION BOARD</span><h1>Τι να προωθήσουμε τώρα</h1><p>Μόνο η απόφαση: ποια προϊόντα βγήκαν πρώτα, τι οικονομικό αποτέλεσμα υποστηρίζει το evidence και ποιος είναι ο κίνδυνος.</p></div>
   <div className={styles.actions}><button onClick={load}>↻ Refresh</button><a href="/forecast-products">Όλη η κατάταξη →</a></div>
  </header>
  {error&&<div className={styles.error}>{error}</div>}
  <section className={styles.kpis}>
   <KPI label="Ranked products" value={n(counts.ranked)} help="Products saved from the latest completed Ranking V3.3 run." meta={run.completed_at?`last run ${age(run.completed_at)}`:'waiting for first ranking run'}/>
   <KPI label="Promote now" value={n(counts.promote_now)} help={tips.band} meta={`${n(counts.high_potential)} high potential`}/>
   <KPI label="SEO ready" value={n(counts.with_seo)} help="Ranked products with evidence-constrained AI SEO title, meta description, description and keywords." meta={`${n(counts.with_network_kpi)} with network KPI baseline`}/>
   <KPI label="Observed conversions 30d" value={n(analytics.first_party_approved_conversions_30d)} help="Actual first-party approved conversions recorded by SocialMarket in the last 30 days." meta={`${n(analytics.first_party_clicks_30d)} observed clicks · no inference when zero`}/>
  </section>
  <section className={styles.mainPanel}>
   <div className={styles.panelHead}><div><span>TOP PRODUCTS TO PROMOTE</span><h2>Η τελική λίστα</h2></div><small title="Ranking uses deterministic market + commercial evidence, AI strategist and an independent skeptic. SEO is generated only after final ranking.">Market → Commercial → Product → AI → Skeptic → SEO</small></div>
   {products.length?<div className={styles.products}>{products.map(x=>{const k=obj(x.kpi_snapshot),net=obj(k.network_baseline),model=obj(k.modeled_product_economics);return <article className={styles.product} key={`${x.run_id}-${x.source_record_hash}`}>
    <div className={styles.rank}>#{x.global_rank}</div>
    <div className={styles.productBody}><div className={styles.productTitle}><b>{x.product_name}</b><span>{x.merchant_name}{x.brand_name?` · ${x.brand_name}`:''}</span></div><p>{x.promotion_angle||x.promotion_reason||'AI promotion angle will appear after the ranking run.'}</p><div className={styles.channels}>{(Array.isArray(x.recommended_channels)?x.recommended_channels:[]).map(c=><span key={c}>{c}</span>)}</div></div>
    <div className={styles.decision}><strong title={tips.score}>{n(x.rank_score,1)}</strong><em title={tips.band}>{x.rank_band?.replaceAll('_',' ')}</em><div><span title={tips.commission}>Commission <b>{money(x.expected_commission_eur)}</b></span><span title={tips.network}>Network CVR <b>{net.conversion_rate_pct===undefined?'—':`${n(net.conversion_rate_pct,2)}%`}</b></span><span title={tips.forecast}>Approved €/100 clicks <b>{money(model.expected_approved_commission_per_100_clicks_eur)}</b></span><span title={tips.risk}>Risk <b>{n(x.ai_risk_score,0)}</b></span></div>{x.tracking_url&&<a href={x.tracking_url} target="_blank" rel="noreferrer">Open affiliate link ↗</a>}</div>
   </article>})}</div>:<div className={styles.empty}><b>Η πρώτη ολοκληρωμένη ranking λίστα δεν έχει αποθηκευτεί ακόμη.</b><p>Το full product run τρέχει πάνω στο πραγματικό affiliate feed. Η επόμενη V3.3 εκτέλεση θα προσθέσει KPIs, product characteristics και SEO.</p></div>}
  </section>
  <section className={styles.bottomGrid}>
   <div className={styles.smallPanel}><div className={styles.panelHead}><div><span>MERCHANT CONTEXT</span><h2>Top merchants</h2></div><Tip text="Merchant ranking is supporting context. The final decision remains product-level."/></div>{merchants.slice(0,5).map(x=><div className={styles.merchant} key={x.merchant_id}><b>#{x.global_rank} {x.canonical_name}</b><span>{x.primary_category||'—'}</span><strong>{n(x.overall_opportunity_score,1)}</strong></div>)}</div>
   <div className={styles.smallPanel}><div className={styles.panelHead}><div><span>PIPELINE</span><h2>Τι έτρεξε</h2></div></div><div className={styles.pipeline}><div><b>1</b><span>Greek market + Deep Demand evidence</span></div><div><b>2</b><span>Merchant + Linkwise program conversion context</span></div><div><b>3</b><span>2.6M+ feed deterministic eligibility + economics</span></div><div><b>4</b><span>Conversion-aware shortlist + RAG</span></div><div><b>5</b><span>AI ranking strategist → independent skeptic</span></div><div><b>6</b><span>SEO enrichment → final Products to Promote</span></div></div></div>
  </section>
  <footer className={styles.footer}>Ranking V3.3 · {run.engine_version||'awaiting first run'} · {n(demand.analysis_runs)} demand analysis runs · observed and modeled KPIs remain explicitly separated</footer>
 </main>
}
