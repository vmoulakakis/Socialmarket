'use client';

import {useEffect,useMemo,useState} from 'react';
import {supabase} from '@/lib/supabase';
import EChart from '@/components/analytics/EChart';
import styles from './market.module.css';

const valid=v=>v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v));
const fmt=(v,d=0)=>valid(v)?Number(v).toLocaleString('el-GR',{maximumFractionDigits:d}):'—';
const pct=v=>valid(v)?`${fmt(Number(v)*100,0)}%`:'—';
const name=x=>x.subcategory_name||x.category_name||x.taxonomy_name||'Unclassified';
const colors={text:'#e9eef7',muted:'#7f8ba0',line:'rgba(148,163,184,.14)',cyan:'#22d3ee',violet:'#8b5cf6',emerald:'#34d399',amber:'#fbbf24'};

function Stat({label,value,meta,tone='violet'}){return <div className={styles.stat}><span>{label}</span><strong className={styles[tone]}>{value}</strong><small>{meta}</small></div>}

export default function Market(){
 const [data,setData]=useState(null),[loading,setLoading]=useState(true),[error,setError]=useState('');
 async function load(){
  setLoading(true);setError('');
  try{
   const {data:{session}}=await supabase.auth.getSession();
   if(!session?.access_token)throw new Error('Admin session expired. Sign in again.');
   const r=await fetch('/api/admin-dashboard',{headers:{authorization:`Bearer ${session.access_token}`},cache:'no-store'});
   const j=await r.json();
   if(!r.ok||j?.error)throw new Error(j?.message||j?.detail||j?.error||`HTTP ${r.status}`);
   setData(j);
  }catch(e){setError(String(e?.message||e));setData(null)}finally{setLoading(false)}
 }
 useEffect(()=>{load()},[]);
 const rows=useMemo(()=>[...(data?.category_market||[])].sort((a,b)=>Number(b.opportunity_score??-1)-Number(a.opportunity_score??-1)||Number(b.demand_score??-1)-Number(a.demand_score??-1)),[data]);
 const comparable=useMemo(()=>rows.filter(x=>valid(x.demand_score)&&valid(x.competition_score)),[rows]);
 const missingCompetition=rows.filter(x=>!valid(x.competition_score)).length;
 const top=comparable.find(x=>valid(x.opportunity_score))||null;
 const latestObserved=rows.reduce((best,x)=>!x.observed_at?best:(!best||String(x.observed_at)>String(best)?x.observed_at:best),null);
 const avgConfidence=rows.filter(x=>valid(x.confidence)).length?rows.filter(x=>valid(x.confidence)).reduce((s,x)=>s+Number(x.confidence),0)/rows.filter(x=>valid(x.confidence)).length:null;
 const painClusters=rows.reduce((s,x)=>s+Number(x.validated_pain_clusters||0),0);
 const scatter=useMemo(()=>({
  backgroundColor:'transparent',animationDuration:600,textStyle:{color:colors.text,fontFamily:'Inter,system-ui,sans-serif'},
  grid:{left:54,right:28,top:32,bottom:54},
  xAxis:{name:'Competition →',min:0,max:100,nameLocation:'middle',nameGap:34,axisLabel:{color:colors.muted},axisLine:{lineStyle:{color:colors.line}},splitLine:{lineStyle:{color:'rgba(148,163,184,.07)'}}},
  yAxis:{name:'Demand →',min:0,max:100,nameLocation:'middle',nameGap:40,axisLabel:{color:colors.muted},axisLine:{lineStyle:{color:colors.line}},splitLine:{lineStyle:{color:'rgba(148,163,184,.07)'}}},
  tooltip:{trigger:'item',backgroundColor:'#0b1220',borderColor:colors.line,textStyle:{color:colors.text},formatter:p=>{const v=p.value;return `<b>${v[5]}</b><br/>Demand ${fmt(v[1])}<br/>Competition ${fmt(v[0])}<br/>Pain ${fmt(v[2])}<br/>Opportunity ${fmt(v[3])}<br/>Confidence ${valid(v[4])?fmt(v[4]*100)+'%':'—'}`}},
  visualMap:{show:false,min:0,max:100,dimension:3,inRange:{color:['#475569',colors.cyan,colors.violet,colors.emerald]}},
  series:[{type:'scatter',data:comparable.map(x=>[Number(x.competition_score),Number(x.demand_score),Number(x.pain_gap_score||0),Number(x.opportunity_score||0),valid(x.confidence)?Number(x.confidence):null,name(x)]),symbolSize:v=>Math.max(12,Math.min(38,12+Number(v[2]||0)*.22)),itemStyle:{opacity:.82,borderColor:'rgba(255,255,255,.3)',borderWidth:1},emphasis:{scale:1.15,itemStyle:{opacity:1}},markArea:{silent:true,label:{color:'rgba(226,232,240,.48)',fontSize:10},itemStyle:{opacity:.045},data:[[{name:'HIGH DEMAND · LOWER COMP.',xAxis:0,yAxis:50,itemStyle:{color:colors.emerald}},{xAxis:50,yAxis:100}],[{name:'HIGH DEMAND · CROWDED',xAxis:50,yAxis:50,itemStyle:{color:colors.amber}},{xAxis:100,yAxis:100}],[{name:'EMERGING',xAxis:0,yAxis:0,itemStyle:{color:colors.cyan}},{xAxis:50,yAxis:50}]]}}]
 }),[comparable]);

 if(loading)return <main className={styles.page}><div className={styles.empty}><b>Loading Greece market intelligence…</b><span>Reading the current semantic production snapshot.</span></div></main>;
 return <main className={styles.page}>
  <header className={styles.hero}>
   <div className={styles.heroCopy}><span className={styles.kicker}>GREECE · SEMANTIC MARKET INTELLIGENCE</span><h1>{top?<>Opportunity leader: <em>{name(top)}</em></>:<>Greece Opportunity Map</>}</h1><p>{top?`Demand ${fmt(top.demand_score)} · Competition ${fmt(top.competition_score)} · Pain ${fmt(top.pain_gap_score)} · Opportunity ${fmt(top.opportunity_score)} · Confidence ${pct(top.confidence)}.`:'The map shows only evidence-backed semantic category intelligence. Missing competition remains missing.'}</p></div>
   <div className={styles.actions}><button onClick={load}>↻ Refresh</button></div>
  </header>
  {error&&<div className={styles.error}>{error}</div>}

  <section className={styles.stats}>
   <Stat label="Semantic market rows" value={fmt(rows.length)} meta="current production truth" tone="cyan"/>
   <Stat label="Comparable rows" value={fmt(comparable.length)} meta="demand + competition available" tone="violet"/>
   <Stat label="Competition missing" value={fmt(missingCompetition)} meta="preserved as NULL" tone="amber"/>
   <Stat label="Validated pain clusters" value={fmt(painClusters)} meta="category-level audited pain evidence" tone="emerald"/>
   <Stat label="Average confidence" value={avgConfidence===null?'—':pct(avgConfidence)} meta={latestObserved?`latest ${new Date(latestObserved).toLocaleString('el-GR')}`:'no observation timestamp'} tone="emerald"/>
  </section>

  <section className={styles.panel}>
   <div className={styles.panelHead}><div><span>OPPORTUNITY LANDSCAPE</span><h2>Demand × Competition × Pain</h2></div><span className={styles.legend}>Bubble size = pain-gap score · color = existing opportunity score</span></div>
   <div className={styles.chart}>{comparable.length?<EChart option={scatter} height={520} ariaLabel="Greece semantic market opportunity landscape"/>:<div className={styles.empty}><b>No comparable semantic rows</b><span>Rows require both evidence-derived demand and competition before they enter this map.</span></div>}</div>
   <p className={styles.note}><b>Important:</b> Seller saturation και Ad Pressure Proxy δεν αποτελούν πλέον category-market truth σε αυτή τη σελίδα. Αν υπάρχουν ως evidence-backed merchant/channel signals, χρησιμοποιούνται στο αντίστοιχο intelligence layer — όχι ως hard-coded category kill-switch. Το Competition εδώ είναι το production semantic competition index και παραμένει NULL όταν δεν υπάρχει επαρκές evidence.</p>
  </section>

  <section className={styles.panel}>
   <div className={styles.panelHead}><div><span>AUDITABLE MARKET TRUTH</span><h2>Canonical categories and subcategories</h2></div><span className={styles.legend}>{rows.length} rows · methodology {rows[0]?.methodology_version||'—'}</span></div>
   {rows.length?<div className={styles.tableWrap}><table className={styles.table}><thead><tr><th>Category</th><th>Subcategory</th><th>Demand</th><th>Competition</th><th>Pain</th><th>Opportunity</th><th>Confidence</th><th>Validated pains</th><th>Observed</th></tr></thead><tbody>{rows.slice(0,120).map((x,i)=><tr key={x.id||`${x.taxonomy_id}-${i}`}><td><b>{x.category_name||x.taxonomy_name||'—'}</b></td><td>{x.subcategory_name||'Category level'}</td><td className={styles.score}>{fmt(x.demand_score)}</td><td className={`${styles.score} ${!valid(x.competition_score)?styles.muted:''}`}>{fmt(x.competition_score)}</td><td className={styles.score}>{fmt(x.pain_gap_score)}</td><td className={`${styles.score} ${valid(x.opportunity_score)&&Number(x.opportunity_score)>=70?styles.good:styles.warn}`}>{fmt(x.opportunity_score)}</td><td>{pct(x.confidence)}</td><td>{fmt(x.validated_pain_clusters)}</td><td><small>{x.observed_at?new Date(x.observed_at).toLocaleString('el-GR'):'—'}</small></td></tr>)}</tbody></table></div>:<div className={styles.empty}><b>No semantic category rows</b><span>The evidence pipeline has not produced trusted category-market output.</span></div>}
  </section>
  <footer className={styles.footer}>Source: admin_dashboard_snapshot → api.semantic_category_market_v2 · Production truth only · Missing ≠ zero · Proxy ≠ observed paid-ad spend</footer>
 </main>;
}
