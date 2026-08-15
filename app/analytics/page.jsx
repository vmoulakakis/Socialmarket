'use client';

import {useEffect,useMemo,useState} from 'react';
import {motion} from 'motion/react';
import {supabase} from '@/lib/supabase';
import EChart from '@/components/analytics/EChart';
import styles from './analytics.module.css';

const valid=v=>v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v));
const fmt=(v,d=0)=>valid(v)?Number(v).toLocaleString('el-GR',{maximumFractionDigits:d}):'—';
const age=v=>{if(!v)return 'not collected';const ms=Date.now()-new Date(v).getTime();if(ms<0)return 'now';const h=ms/3600000;if(h<1)return `${Math.round(h*60)}m ago`;if(h<48)return `${h.toFixed(1)}h ago`;return `${(h/24).toFixed(1)}d ago`};
const colors={text:'#edf2fa',muted:'#7f8ba0',line:'rgba(148,163,184,.14)',violet:'#8b5cf6',cyan:'#22d3ee',emerald:'#34d399',amber:'#fbbf24',red:'#fb7185'};
function Tile({label,value,meta,tone='violet'}){return <div className={styles.tile}><span>{label}</span><strong data-tone={tone}>{value}</strong><small>{meta}</small></div>}
function Empty({title,children}){return <div className={styles.empty}><b>{title}</b><p>{children}</p></div>}
function Panel({eyebrow,title,aside,children,className=''}){return <section className={`${styles.panel} ${className}`}><header className={styles.panelHead}><div><span>{eyebrow}</span><h2>{title}</h2></div>{aside}</header>{children}</section>}

export default function Analytics(){
 const [bi,setBi]=useState(null),[pipe,setPipe]=useState(null),[loading,setLoading]=useState(true),[error,setError]=useState(''),[brief,setBrief]=useState(null),[aiBusy,setAiBusy]=useState(false);
 async function load(){setLoading(true);setError('');const [a,b]=await Promise.all([supabase.rpc('admin_business_intelligence_snapshot'),supabase.rpc('admin_product_pipeline_analytics')]);if(a.error||b.error)setError(a.error?.message||b.error?.message);else{setBi(a.data);setPipe(b.data)}setLoading(false)}
 useEffect(()=>{load()},[]);
 const p=bi?.pipeline||{},fresh=bi?.freshness||{},qa=bi?.queue_alerts||{},ai=bi?.ai_summary||{};
 const phaseA=pipe?.latest_phase_a||null,phaseB=pipe?.latest_phase_b||null;
 const stages=useMemo(()=>phaseA?[['Feed records',phaseA.records_seen],['Commercial eligible',phaseA.commission_eligible_records??phaseA.commission_eligible_offers],['Unique eligible',phaseA.unique_commission_eligible_products],['AI reviewed',phaseB?.ai_offers_submitted],['Validated',phaseB?.saved]]:[],[phaseA,phaseB]);
 const alerts=Number(qa.research_failed||0)+Number(qa.collection_failed||0)+Number(qa.research_stuck_running||0)+Number(qa.collection_stuck_running||0);
 const headline=Number(p.validated_products||0)>0?'Validated product opportunities are flowing through the intelligence stack':Number(p.validated_pain_clusters||0)>0?'Validated demand exists; product conversion is the current execution frontier':'The system is protecting quality before monetization';
 const subhead=Number(p.validated_pain_clusters||0)===0?'No clean validated pains are being promoted. That is a deliberate fail-closed production state, not an empty-dashboard defect.':'This overview preserves observed, derived and modeled states and resolves each decision back to production evidence.';
 const funnel=useMemo(()=>({backgroundColor:'transparent',tooltip:{trigger:'item',backgroundColor:'#0b1220',borderColor:colors.line,textStyle:{color:colors.text},formatter:p=>`${p.name}: <b>${fmt(p.value)}</b>`},series:[{type:'funnel',left:'3%',top:12,bottom:12,width:'94%',minSize:'24%',maxSize:'100%',sort:'none',gap:5,label:{show:true,position:'inside',color:'#f8fafc',fontSize:11,formatter:p=>`${p.name}\n${fmt(p.value)}`},labelLine:{show:false},itemStyle:{borderColor:'#09101a',borderWidth:3},emphasis:{label:{fontSize:12}},data:stages.map(([name,value],i)=>({name,value:Number(value||0),itemStyle:{color:[colors.cyan,'#3b82f6',colors.violet,'#a855f7',colors.emerald][i]}}))}]}),[stages]);
 const sourceMix=useMemo(()=>{const rows=(bi?.evidence_by_source||[]).slice(0,10);return {rows,option:{backgroundColor:'transparent',grid:{left:115,right:24,top:10,bottom:28},xAxis:{type:'value',axisLabel:{color:colors.muted},splitLine:{lineStyle:{color:'rgba(148,163,184,.07)'}}},yAxis:{type:'category',inverse:true,data:rows.map(x=>x.source_kind||'unknown'),axisLabel:{color:'#aeb9ca',fontSize:10},axisLine:{show:false},axisTick:{show:false}},tooltip:{trigger:'axis',axisPointer:{type:'shadow'},backgroundColor:'#0b1220',borderColor:colors.line,textStyle:{color:colors.text}},series:[{type:'bar',data:rows.map(x=>Number(x.observations||0)),barMaxWidth:16,itemStyle:{color:colors.cyan,borderRadius:[0,7,7,0]}}]}}},[bi]);
 async function analyze(){if(!bi)return;setAiBusy(true);setError('');try{const {data:{session}}=await supabase.auth.getSession();const r=await fetch('https://rpfadpdnnxequgvdcfoq.supabase.co/functions/v1/admin-intelligence-gateway',{method:'POST',headers:{'content-type':'application/json','authorization':`Bearer ${session?.access_token||''}`},body:JSON.stringify({action:'business_brief',bi})});const j=await r.json();if(!r.ok||j.error)throw new Error(j.error||`HTTP ${r.status}`);setBrief(j.brief)}catch(e){setError(String(e.message||e))}finally{setAiBusy(false)}}
 if(loading)return <main className={styles.page}><div className={styles.loading}>Loading production business intelligence…</div></main>;
 return <main className={styles.page}>
  <motion.header className={styles.hero} initial={{opacity:0,y:10}} animate={{opacity:1,y:0}}>
   <div><span className={styles.kicker}>EXECUTIVE INTELLIGENCE · PRODUCTION</span><h1>{headline}</h1><p>{subhead}</p></div>
   <aside><button onClick={load}>Refresh</button><button className={styles.primary} onClick={analyze} disabled={aiBusy}>{aiBusy?'Analyzing…':'AI Business Brief'}</button></aside>
  </motion.header>
  {error&&<div className={styles.error}>{error}</div>}
  <section className={styles.tiles}>
   <Tile label="Evidence" value={fmt(p.evidence_observations)} meta={`${fmt(p.validated_observations)} validated`} tone="cyan"/>
   <Tile label="Validated pains" value={fmt(p.validated_pain_clusters)} meta={`${fmt(p.embedded_clusters)} embedded`} tone="amber"/>
   <Tile label="Merchant programs" value={fmt(p.merchant_programs)} meta={`${fmt(p.merchants)} merchants`} tone="violet"/>
   <Tile label="Validated products" value={fmt(p.validated_products)} meta={`${fmt(p.eligible_offers)} eligible offers`} tone="emerald"/>
   <Tile label="AI calls · 7d" value={fmt(ai.calls_7d)} meta={`$${fmt(ai.estimated_cost_usd_7d,4)} estimated`} tone="violet"/>
   <Tile label="Operational alerts" value={fmt(alerts)} meta="failed + stuck queues" tone={alerts?'red':'emerald'}/>
  </section>

  <div className={styles.gridPrimary}>
   <Panel eyebrow="INTELLIGENCE FUNNEL" title="Where commercial candidates are lost" aside={<a href="/configuration">Tune gates →</a>} className={styles.funnelPanel}>{stages.length?<EChart option={funnel} height={390} ariaLabel="Product intelligence funnel"/>:<Empty title="No persisted Phase A profile">The next Product Intelligence run will populate the real funnel.</Empty>}</Panel>
   <Panel eyebrow="OPERATING FRESHNESS" title="Can we trust the current picture?">
    <div className={styles.freshness}><div><span>Evidence</span><b>{age(fresh.latest_evidence_at)}</b><small>{fmt(fresh.evidence_24h)} new / 24h</small></div><div><span>Skeptic audit</span><b>{age(fresh.latest_audit_at)}</b><small>latest verdict</small></div><div><span>Semantic layer</span><b>{age(fresh.latest_semantic_cluster_at)}</b><small>{fmt(fresh.stale_clusters_7d)} stale &gt;7d</small></div><div><span>Product AI</span><b>{age(fresh.latest_product_intelligence_at)}</b><small>latest snapshot</small></div></div>
    <a className={styles.demandCta} href="/demand"><span>Flagship workspace</span><b>Open Demand Intelligence</b><small>Opportunity landscape · signal matrix · evidence footprint →</small></a>
   </Panel>
  </div>

  <div className={styles.grid3}>
   <Panel eyebrow="EVIDENCE MIX" title="Source coverage">{sourceMix.rows.length?<EChart option={sourceMix.option} height={330} ariaLabel="Evidence observations by source"/>:<Empty title="No source coverage">No evidence source distribution is available.</Empty>}</Panel>
   <Panel eyebrow="AI OPERATIONS" title="Cost and reliability"><div className={styles.metricList}><div><span>Input tokens · 7d</span><b>{fmt(ai.input_tokens_7d)}</b></div><div><span>Output tokens · 7d</span><b>{fmt(ai.output_tokens_7d)}</b></div><div><span>Remote requests · 7d</span><b>{fmt(ai.remote_requests_7d)}</b></div><div><span>Remote failures · 7d</span><b data-risk={Number(ai.remote_failures_7d)>0}>{fmt(ai.remote_failures_7d)}</b></div><div><span>Average AI latency</span><b>{valid(ai.avg_remote_latency_seconds_7d)?`${fmt(ai.avg_remote_latency_seconds_7d,1)}s`:'—'}</b></div></div></Panel>
   <Panel eyebrow="QUEUE HEALTH" title="Execution risk"><div className={styles.queue}><div><span>Research failed</span><b>{fmt(qa.research_failed)}</b></div><div><span>Research stuck</span><b>{fmt(qa.research_stuck_running)}</b></div><div><span>Research queued &gt;6h</span><b>{fmt(qa.research_queued_over_6h)}</b></div><div><span>Collection failed</span><b>{fmt(qa.collection_failed)}</b></div><div><span>Collection stuck</span><b>{fmt(qa.collection_stuck_running)}</b></div><div><span>Collection queued &gt;6h</span><b>{fmt(qa.collection_queued_over_6h)}</b></div></div></Panel>
  </div>

  <div className={styles.grid2}>
   <Panel eyebrow="VALIDATED UNMET NEED" title="Top pain opportunities">{(bi?.top_pain_clusters||[]).length?<div className={styles.rankList}>{bi.top_pain_clusters.slice(0,10).map((x,i)=><div key={x.id}><em>{String(i+1).padStart(2,'0')}</em><span><b>{x.canonical_text}</b><small>{x.category||'Unclassified'} · {fmt(x.evidence_count)} evidence · {fmt(x.source_diversity)} sources</small></span><strong>{fmt(x.opportunity_index,1)}</strong></div>)}</div>:<Empty title="0 clean validated pains">The hardened validation layer is intentionally blocking contaminated demand claims.</Empty>}</Panel>
   <Panel eyebrow="MERCHANT WHITESPACE" title="Best current solution environments">{(bi?.merchant_opportunities||[]).length?<div className={styles.rankList}>{bi.merchant_opportunities.slice(0,10).map((x,i)=><div key={x.merchant_id}><em>{String(i+1).padStart(2,'0')}</em><span><b>{x.canonical_name}</b><small>{x.taxonomy_name||'—'} · trust {fmt(x.trust_score)}</small></span><strong>{fmt(x.solution_whitespace_score,1)}</strong></div>)}</div>:<Empty title="No trusted merchant whitespace yet">Merchant intelligence remains fail-closed until trusted taxonomy and market context align.</Empty>}</Panel>
  </div>

  {brief&&<motion.section className={styles.aiPanel} initial={{opacity:0,y:12}} animate={{opacity:1,y:0}}><div><span>AI INTELLIGENCE ANALYST</span><h2>{brief.executive_summary||'Evidence-grounded executive brief'}</h2></div><div className={styles.aiGrid}><section><h3>Priority actions</h3>{(brief.recommended_actions||[]).slice(0,6).map((x,i)=><div key={i}><b>{x.priority} · {x.action}</b><p>{x.reason}</p><small>Watch: {x.metric_to_watch}</small></div>)}</section><section><h3>Operational risks</h3>{(brief.operational_risks||[]).slice(0,6).map((x,i)=><div key={i}><b>{x.severity} · {x.risk}</b><p>{x.action}</p></div>)}</section></div></motion.section>}
  <footer className={styles.footer}>Generated {bi?.generated_at?new Date(bi.generated_at).toLocaleString('el-GR'):'—'} · Production truth only · Missing ≠ zero</footer>
 </main>
}
