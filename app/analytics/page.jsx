'use client';

import {useEffect,useMemo,useState} from 'react';
import {supabase} from '@/lib/supabase';
import styles from './analytics.module.css';

const n=(v,d=0)=>v===null||v===undefined?'—':Number(v).toLocaleString('el-GR',{maximumFractionDigits:d});
const pct=(a,b)=>!b?'—':`${((Number(a||0)/Number(b))*100).toFixed(1)}%`;
const age=(v)=>{if(!v)return 'not collected';const ms=Date.now()-new Date(v).getTime();if(ms<0)return 'now';const h=ms/3600000;if(h<1)return `${Math.round(h*60)}m ago`;if(h<48)return `${h.toFixed(1)}h ago`;return `${(h/24).toFixed(1)}d ago`};
const tone=(v,good=80,warn=55)=>Number(v)>=good?styles.good:Number(v)>=warn?styles.warn:styles.bad;

function Card({label,value,sub,accent}){return <div className={styles.kpi} style={{'--accent':accent||'#8b5cf6'}}><span>{label}</span><strong>{value}</strong><small>{sub}</small></div>}
function Bar({label,value,max=100,meta}){const width=Math.max(0,Math.min(100,max?Number(value||0)/Number(max)*100:0));return <div className={styles.barRow}><div className={styles.barHead}><span>{label}</span><b>{n(value,1)}</b></div><div className={styles.bar}><i style={{width:`${width}%`}}/></div>{meta&&<small>{meta}</small>}</div>}
function Empty({children}){return <div className={styles.empty}>{children||'No production data collected yet.'}</div>}

export default function Analytics(){
 const [bi,setBi]=useState(null),[pipe,setPipe]=useState(null),[loading,setLoading]=useState(true),[error,setError]=useState('');
 const [brief,setBrief]=useState(null),[aiBusy,setAiBusy]=useState(false);
 async function load(){setLoading(true);setError('');const [a,b]=await Promise.all([supabase.rpc('admin_business_intelligence_snapshot'),supabase.rpc('admin_product_pipeline_analytics')]);if(a.error||b.error)setError(a.error?.message||b.error?.message);else{setBi(a.data);setPipe(b.data)}setLoading(false)}
 useEffect(()=>{load()},[]);
 async function analyze(){if(!bi)return;setAiBusy(true);setError('');try{const {data:{session}}=await supabase.auth.getSession();const r=await fetch('https://rpfadpdnnxequgvdcfoq.supabase.co/functions/v1/admin-intelligence-gateway',{method:'POST',headers:{'content-type':'application/json','authorization':`Bearer ${session?.access_token||''}`},body:JSON.stringify({action:'business_brief',bi})});const j=await r.json();if(!r.ok||j.error)throw new Error(j.error||`HTTP ${r.status}`);setBrief(j.brief)}catch(e){setError(String(e.message||e))}finally{setAiBusy(false)}}
 const p=bi?.pipeline||{},fresh=bi?.freshness||{},qa=bi?.queue_alerts||{},ai=bi?.ai_summary||{};
 const sourceMax=Math.max(1,...(bi?.evidence_by_source||[]).map(x=>Number(x.observations||0)));
 const phaseA=pipe?.latest_phase_a||null,phaseB=pipe?.latest_phase_b||null;
 const exclusions=Array.isArray(pipe?.phase_a_exclusions)?pipe.phase_a_exclusions:[];
 const pipelineSteps=useMemo(()=>phaseA?[['Feed records',phaseA.records_seen],['Commercial eligible',phaseA.commission_eligible_records??phaseA.commission_eligible_offers],['Unique eligible products',phaseA.unique_commission_eligible_products],['AI submitted',phaseB?.ai_offers_submitted],['Persisted VALIDATED',phaseB?.saved]]:[],[phaseA,phaseB]);
 const maxPipe=Math.max(1,...pipelineSteps.map(x=>Number(x[1]||0)));
 if(loading)return <main className={styles.wrap}><div className={styles.loading}>Loading production BI…</div></main>;
 return <main className={styles.wrap}>
  <header className={styles.hero}><div><span className={styles.eyebrow}>Production Business Intelligence</span><h1>SocialMarket Analytics</h1><p>Real Supabase intelligence, audit, pipeline, AI-cost and freshness metrics. Missing data stays missing — never mocked.</p></div><div className={styles.actions}><button onClick={load}>↻ Refresh</button><button className={styles.primary} onClick={analyze} disabled={aiBusy}>{aiBusy?'AI analyzing…':'✦ AI Business Brief'}</button></div></header>
  {error&&<div className={styles.error}>{error}</div>}
  <section className={styles.kpis}>
   <Card label="Evidence" value={n(p.evidence_observations)} sub={`${n(p.validated_observations)} validated`} accent="#38bdf8"/>
   <Card label="Validated pains" value={n(p.validated_pain_clusters)} sub={`${n(p.embedded_clusters)} embedded clusters`} accent="#fb923c"/>
   <Card label="Merchants" value={n(p.merchants)} sub={`${n(p.merchant_programs)} programs`} accent="#a78bfa"/>
   <Card label="Products" value={n(p.validated_products)} sub={`${n(p.eligible_offers)} eligible offers`} accent="#34d399"/>
   <Card label="AI calls · 7d" value={n(ai.calls_7d)} sub={`$${n(ai.estimated_cost_usd_7d,4)} estimated`} accent="#f472b6"/>
   <Card label="Queue alerts" value={n(Number(qa.research_failed||0)+Number(qa.collection_failed||0)+Number(qa.research_stuck_running||0)+Number(qa.collection_stuck_running||0))} sub="failed + stuck" accent="#f87171"/>
  </section>

  <section className={styles.grid2}>
   <div className={styles.panel}><div className={styles.panelHead}><div><span className={styles.eyebrow}>Product funnel</span><h2>Where candidates are lost</h2></div><a href="/configuration">Tune criteria →</a></div>
    {pipelineSteps.length?pipelineSteps.map(([label,value])=><Bar key={label} label={label} value={value} max={maxPipe} meta={label==='Commercial eligible'&&phaseA?.records_seen?`${pct(value,phaseA.records_seen)} of feed`:undefined}/>):<Empty>No Phase A run profile has been persisted yet. The next Product Intelligence run will populate this funnel.</Empty>}
    {p.products===0&&<div className={styles.blocker}><b>Current blocker</b><span>0 persisted products / 0 offers. Product selection has not completed end-to-end yet.</span></div>}
   </div>
   <div className={styles.panel}><span className={styles.eyebrow}>Data freshness</span><h2>Is the intelligence current?</h2><div className={styles.freshGrid}>
    <div><span>Evidence</span><b>{age(fresh.latest_evidence_at)}</b><small>{n(fresh.evidence_24h)} new / 24h</small></div>
    <div><span>Audit</span><b>{age(fresh.latest_audit_at)}</b><small>latest skeptic verdict</small></div>
    <div><span>Semantic</span><b>{age(fresh.latest_semantic_cluster_at)}</b><small>{n(fresh.stale_clusters_7d)} validated &gt;7d old</small></div>
    <div><span>Product AI</span><b>{age(fresh.latest_product_intelligence_at)}</b><small>latest persisted snapshot</small></div>
   </div></div>
  </section>

  <section className={styles.grid3}>
   <div className={styles.panel}><span className={styles.eyebrow}>Phase A exclusions</span><h2>Deterministic rejection reasons</h2>{exclusions.length?exclusions.slice(0,12).map(([reason,count])=><div className={styles.reason} key={reason}><span>{String(reason).replaceAll('_',' ')}</span><b>{n(count)}</b></div>):<Empty>Run Phase A to collect real exclusion counts.</Empty>}</div>
   <div className={styles.panel}><span className={styles.eyebrow}>Evidence mix</span><h2>Source coverage</h2>{(bi?.evidence_by_source||[]).slice(0,10).map(x=><Bar key={x.source_kind||'unknown'} label={x.source_kind||'unknown'} value={x.observations} max={sourceMax} meta={`${n(x.validated)} validated · conf ${x.avg_confidence===null?'—':n(Number(x.avg_confidence)*100,0)+'%'}`}/>)}</div>
   <div className={styles.panel}><span className={styles.eyebrow}>AI operations</span><h2>Cost & reliability</h2><div className={styles.metricList}><div><span>Input tokens · 7d</span><b>{n(ai.input_tokens_7d)}</b></div><div><span>Output tokens · 7d</span><b>{n(ai.output_tokens_7d)}</b></div><div><span>Remote requests · 7d</span><b>{n(ai.remote_requests_7d)}</b></div><div><span>Remote failures · 7d</span><b className={Number(ai.remote_failures_7d)>0?styles.bad:''}>{n(ai.remote_failures_7d)}</b></div><div><span>Avg AI latency</span><b>{ai.avg_remote_latency_seconds_7d===null?'—':`${n(ai.avg_remote_latency_seconds_7d,1)}s`}</b></div></div></div>
  </section>

  <section className={styles.grid2}>
   <div className={styles.panel}><div className={styles.panelHead}><div><span className={styles.eyebrow}>Validated unmet need</span><h2>Top pain opportunities</h2></div><span className={styles.note}>derived index from stored metrics</span></div>{(bi?.top_pain_clusters||[]).slice(0,10).map(x=><div className={styles.opportunity} key={x.id}><div><b>{x.canonical_text}</b><small>{x.category||'Unclassified'} · {n(x.evidence_count)} evidence · {n(x.source_diversity)} sources</small></div><div><strong>{n(x.opportunity_index,1)}</strong><small>D {n(x.demand_score)} · C {n(x.competition_score)}</small></div></div>)}{!(bi?.top_pain_clusters||[]).length&&<Empty/>}</div>
   <div className={styles.panel}><span className={styles.eyebrow}>Merchant whitespace</span><h2>Best solution environments</h2>{(bi?.merchant_opportunities||[]).slice(0,10).map(x=><div className={styles.opportunity} key={x.merchant_id}><div><b>{x.canonical_name}</b><small>{x.taxonomy_name||'—'} · trust {n(x.trust_score)}</small></div><div><strong>{n(x.solution_whitespace_score,1)}</strong><small>D {n(x.demand_score)} · C {n(x.competition_score)}</small></div></div>)}{!(bi?.merchant_opportunities||[]).length&&<Empty/>}</div>
  </section>

  <section className={styles.grid2}>
   <div className={styles.panel}><span className={styles.eyebrow}>Audit quality</span><h2>Skeptic verdicts</h2>{(bi?.audit_distribution||[]).map(x=><div className={styles.audit} key={x.verdict}><span className={tone(x.avg_overall)}>{x.verdict||'unknown'}</span><b>{n(x.audits)}</b><small>avg overall {n(x.avg_overall,1)} · source quality {n(x.avg_source_quality,1)} · pain validation {n(x.avg_pain_validation,1)}</small></div>)}{!(bi?.audit_distribution||[]).length&&<Empty/>}</div>
   <div className={styles.panel}><span className={styles.eyebrow}>Pipeline operations</span><h2>Queue health</h2><div className={styles.alertGrid}><div><span>Research failed</span><b className={Number(qa.research_failed)>0?styles.bad:''}>{n(qa.research_failed)}</b></div><div><span>Research stuck</span><b className={Number(qa.research_stuck_running)>0?styles.bad:''}>{n(qa.research_stuck_running)}</b></div><div><span>Research queued &gt;6h</span><b>{n(qa.research_queued_over_6h)}</b></div><div><span>Collection failed</span><b className={Number(qa.collection_failed)>0?styles.bad:''}>{n(qa.collection_failed)}</b></div><div><span>Collection stuck</span><b className={Number(qa.collection_stuck_running)>0?styles.bad:''}>{n(qa.collection_stuck_running)}</b></div><div><span>Collection queued &gt;6h</span><b>{n(qa.collection_queued_over_6h)}</b></div></div></div>
  </section>

  <section className={styles.panel}><div className={styles.panelHead}><div><span className={styles.eyebrow}>Promotion-ready output</span><h2>Validated product opportunities</h2></div><a href="/products">Products →</a></div>{(bi?.product_opportunities||[]).length?<div className={styles.tableWrap}><table><thead><tr><th>Product</th><th>Merchant</th><th>Price</th><th>Commission</th><th>Pain</th><th>Demand</th><th>Competition</th><th>Trust</th><th>Final</th></tr></thead><tbody>{bi.product_opportunities.slice(0,30).map(x=><tr key={`${x.product_id}-${x.offer_id}`}><td>{x.canonical_title}</td><td>{x.merchant_name}</td><td>€{n(x.effective_price,2)}</td><td>€{n(x.expected_commission_eur,2)}</td><td>{n(x.pain_gap_fit_score)}</td><td>{n(x.greek_demand_score)}</td><td>{n(x.competition_score)}</td><td>{n(x.merchant_trust_score)}</td><td><b>{n(x.final_opportunity_score,1)}</b></td></tr>)}</tbody></table></div>:<Empty>No validated products exist in production yet. This is a real pipeline state, not a UI placeholder.</Empty>}</section>

  {brief&&<section className={`${styles.panel} ${styles.aiPanel}`}><div className={styles.panelHead}><div><span className={styles.eyebrow}>AI Business Intelligence</span><h2>Evidence-grounded executive brief</h2></div><button onClick={()=>setBrief(null)}>Clear</button></div><p className={styles.summary}>{brief.executive_summary}</p><div className={styles.grid2}><div><h3>P0/P1/P2 actions</h3>{(brief.recommended_actions||[]).map((x,i)=><div className={styles.aiItem} key={i}><b>{x.priority} · {x.action}</b><span>{x.reason}</span><small>Watch: {x.metric_to_watch}</small></div>)}</div><div><h3>Operational risks</h3>{(brief.operational_risks||[]).map((x,i)=><div className={styles.aiItem} key={i}><b>{x.severity} · {x.risk}</b><span>{x.action}</span></div>)}</div></div></section>}
  <footer className={styles.footer}>Generated {bi?.generated_at?new Date(bi.generated_at).toLocaleString('el-GR'):'—'} · Production data only · No mock fallback</footer>
 </main>
}
