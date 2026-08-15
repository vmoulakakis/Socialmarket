'use client';

import {useEffect,useState} from 'react';
import {supabase} from '@/lib/supabase';

const fmt=(v,d=0)=>v===null||v===undefined?'—':Number(v).toLocaleString('el-GR',{maximumFractionDigits:d});

export default function Products(){
 const [bi,setBi]=useState(null),[pipe,setPipe]=useState(null),[config,setConfig]=useState(null),[loading,setLoading]=useState(true),[error,setError]=useState('');
 async function load(){setLoading(true);const [a,b,c]=await Promise.all([supabase.rpc('admin_business_intelligence_snapshot'),supabase.rpc('admin_product_pipeline_analytics'),supabase.rpc('admin_get_product_config')]);const e=a.error||b.error||c.error;if(e)setError(e.message);else{setBi(a.data);setPipe(b.data);setConfig(c.data)}setLoading(false)}
 useEffect(()=>{load()},[]);
 const cfg=config?.config||{},products=bi?.product_opportunities||[],a=pipe?.latest_phase_a,b=pipe?.latest_phase_b;
 const exclusions=Array.isArray(pipe?.phase_a_exclusions)?pipe.phase_a_exclusions:[];
 return <main>
  <div className="hero"><div><div className="eyebrow">Validated Product Intelligence</div><h1>Products</h1><p className="sub">Real pipeline: deterministic commercial gates → validated pain RAG → Product Research AI → independent Skeptic Audit → VALIDATED-only persistence. No €150 minimum and no legacy HIGO selection.</p></div><div style={{display:'flex',gap:10}}><a className="button" href="/analytics">Analytics</a><a className="button" href="/configuration">Configuration</a></div></div>
  {error&&<div className="card"><p className="bad">{error}</p></div>}
  {loading?<div className="card"><p className="muted">Loading production Product Intelligence…</p></div>:<>
   <div className="card" style={{marginBottom:16}}><h2>Active selection policy · v{config?.version??'—'}</h2><div className="grid4">
    <div className="metric"><span>Commission gate</span><strong>€{fmt(cfg.min_expected_commission_eur,2)}</strong></div>
    <div className="metric"><span>Merchant trust</span><strong>{fmt(cfg.min_merchant_trust)}/100</strong></div>
    <div className="metric"><span>Skeptic overall</span><strong>{fmt(cfg.min_audit_overall)}/100</strong></div>
    <div className="metric"><span>Pain fit</span><strong>{fmt(cfg.min_pain_fit)}/100</strong></div>
    <div className="metric"><span>Evidence confidence</span><strong>{fmt(cfg.min_product_evidence)}/100</strong></div>
    <div className="metric"><span>Min pain evidence</span><strong>{fmt(cfg.min_pain_evidence_count)}</strong></div>
    <div className="metric"><span>Min source diversity</span><strong>{fmt(cfg.min_pain_source_diversity)}</strong></div>
    <div className="metric"><span>Max competition</span><strong>{fmt(cfg.max_competition)}/100</strong></div>
   </div><p className="muted">Profile: {cfg.profile_name||'Custom'} · AI candidates/run: {fmt(cfg.ai_max_candidates)} · Pain RAG: {fmt(cfg.pain_rag_limit)} · Thinking: {cfg.ai_thinking_mode||'auto'}.</p></div>

   <div className="grid2" style={{marginBottom:16}}><div className="card"><h2>Latest Phase A funnel</h2>{a?<><p><b>{fmt(a.records_seen)}</b> feed records scanned</p><p><b>{fmt(a.commission_eligible_records??a.commission_eligible_offers)}</b> commercial-eligible offers</p><p><b>{fmt(a.unique_commission_eligible_products)}</b> unique eligible products</p><p className="muted">Runtime config v{a.runtime_config_version??'—'} · {a.runtime_profile_name||'—'}</p></>:<p className="muted">No persisted Phase A profile yet. The next run will write it automatically.</p>}</div><div className="card"><h2>Latest Phase B AI</h2>{b?<><p><b>{fmt(b.ai_offers_submitted)}</b> offers submitted to AI</p><p><b>{fmt(b.audited_validated)}</b> AI verdict VALIDATED</p><p><b>{fmt(b.saved)}</b> persisted products</p><p className="muted">Non-validated {fmt(b.not_persisted_nonvalidated)} · no pain {fmt(b.not_persisted_no_validated_pain)} · low audit {fmt(b.not_persisted_audit_score)} · low fit {fmt(b.not_persisted_pain_fit)} · low evidence {fmt(b.not_persisted_evidence_confidence)}</p></>:<p className="muted">No persisted Phase B profile yet.</p>}</div></div>

   <div className="card" style={{marginBottom:16}}><h2>Actual deterministic exclusion reasons</h2>{exclusions.length?<table className="table"><thead><tr><th>Reason</th><th>Rejected records</th></tr></thead><tbody>{exclusions.map(([reason,count])=><tr key={reason}><td>{String(reason).replaceAll('_',' ')}</td><td><b>{fmt(count)}</b></td></tr>)}</tbody></table>:<p className="muted">No Phase A rejection profile has been persisted yet.</p>}</div>

   <div className="card"><h2>Promotion-ready products</h2>{products.length===0?<><p className="muted">There are currently <b>0 validated persisted products</b> in the production Product Intelligence layer. This is a real pipeline state, not demo content.</p><p className="muted">Use Analytics to find the bottleneck and Configuration to tune thresholds. Safety invariants remain non-configurable.</p></>:<table className="table"><thead><tr><th>Product</th><th>Merchant</th><th>Price</th><th>Expected commission</th><th>Pain fit</th><th>Demand</th><th>Competition</th><th>Trust</th><th>Evidence</th><th>Final score</th></tr></thead><tbody>{products.map(x=><tr key={`${x.product_id}-${x.offer_id}`}><td><strong>{x.canonical_title}</strong><div className="muted">{x.category||''} {x.subcategory?`› ${x.subcategory}`:''}</div></td><td>{x.merchant_name}</td><td>€{fmt(x.effective_price,2)}</td><td>€{fmt(x.expected_commission_eur,2)}</td><td>{fmt(x.pain_gap_fit_score)}</td><td>{fmt(x.greek_demand_score)}</td><td>{fmt(x.competition_score)}</td><td>{fmt(x.merchant_trust_score)}</td><td>{fmt(x.evidence_count)}</td><td className="score good">{fmt(x.final_opportunity_score,1)}</td></tr>)}</tbody></table>}</div>
  </>}
 </main>
}
