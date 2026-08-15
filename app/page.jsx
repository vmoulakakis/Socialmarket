'use client';

import Link from 'next/link';
import {useEffect,useMemo,useState} from 'react';
import {supabase} from '@/lib/supabase';
import CategoryMarketScatter from '@/components/analytics/CategoryMarketScatter';

const valid=v=>v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v));
const fmt=(v,d=0)=>valid(v)?Number(v).toLocaleString('el-GR',{maximumFractionDigits:d}):'—';
const pct=(v,d=0)=>valid(v)?`${fmt(Number(v)*100,d)}%`:'—';
const score=v=>valid(v)?Math.max(0,Math.min(100,Number(v))):null;

function Kpi({label,value,sub}){return <div className="semanticKpi"><span>{label}</span><strong>{value}</strong><small>{sub}</small></div>}
function Meter({label,value,sub}){const s=score(value);return <div className="semanticMeter"><div><b>{label}</b><span>{s===null?'—':fmt(s,0)}</span></div><i>{s!==null&&<em style={{width:`${s}%`}}/>}</i>{sub&&<small>{sub}</small>}</div>}
function Empty({title,children}){return <div className="semanticEmpty"><b>{title}</b><p>{children}</p></div>}

export default function SemanticConsole(){
 const [data,setData]=useState(null),[loading,setLoading]=useState(true),[error,setError]=useState(''),[aiBusy,setAiBusy]=useState(false),[forecast,setForecast]=useState(null);
 async function load(){setLoading(true);setError('');const {data,error}=await supabase.rpc('admin_dashboard_snapshot');if(error)setError(error.message);else setData(data);setLoading(false)}
 useEffect(()=>{load()},[]);
 const categories=useMemo(()=>[...(data?.category_market||[])].sort((a,b)=>Number(b.opportunity_score??-1)-Number(a.opportunity_score??-1)||Number(b.demand_score??-1)-Number(a.demand_score??-1)),[data]);
 const pains=data?.pain_gaps||[];const merchants=data?.merchants||[];const products=data?.products||[];const tax=data?.taxonomy_health||{};
 const completeMarket=categories.filter(x=>valid(x.demand_score)&&valid(x.competition_score));
 const incompleteMarket=categories.filter(x=>!valid(x.competition_score)||!valid(x.demand_score));
 async function runForecast(){setAiBusy(true);setError('');try{const {data:{session}}=await supabase.auth.getSession();const r=await fetch('https://rpfadpdnnxequgvdcfoq.supabase.co/functions/v1/admin-intelligence-gateway',{method:'POST',headers:{'content-type':'application/json','authorization':`Bearer ${session?.access_token||''}`},body:JSON.stringify({action:'forecast',generated_at:data?.generated_at,category_market:categories,pain_gaps:pains,merchants,social:data?.social||[]})});const j=await r.json();if(!r.ok||j.error)throw new Error(j.error||`HTTP ${r.status}`);setForecast(j.forecast)}catch(e){setError(String(e.message||e))}finally{setAiBusy(false)}}
 if(loading)return <main className="semanticConsole"><div className="semanticLoading">Loading production semantic intelligence…</div></main>;
 return <main className="semanticConsole">
  <header className="semanticHero"><div><span>PRODUCTION · SEMANTIC INTELLIGENCE V1</span><h1>AI Evidence Console</h1><p>Canonical taxonomy, real evidence, affiliate economics and audited forecasts. Missing data remains missing — never converted to a favorable score.</p></div><div><button onClick={load}>↻ Refresh</button><button className="semanticPrimary" onClick={runForecast} disabled={aiBusy}>{aiBusy?'Forecasting…':'✦ AI Forecast'}</button></div></header>
  {error&&<div className="semanticError">{error}</div>}

  <section className="semanticKpis">
   <Kpi label="Evidence observations" value={fmt(data?.kpis?.evidence_observations)} sub="normalized production evidence"/>
   <Kpi label="Validated pain gaps" value={fmt(data?.kpis?.validated_pains)} sub={pains.length?'audited solver needs':'contaminated legacy pains removed'}/>
   <Kpi label="Validated products" value={fmt(data?.kpis?.validated_products)} sub={`${fmt(data?.kpis?.offers)} persisted offers`}/>
   <Kpi label="Canonical taxonomy" value={fmt(tax.validated)} sub={`${fmt(tax.mapped)} mapped · ${fmt(tax.rejected)} rejected`}/>
   <Kpi label="Market rows with competition" value={fmt(completeMarket.length)} sub={`${fmt(incompleteMarket.length)} missing competition evidence`}/>
   <Kpi label="Merchant programs" value={fmt(data?.kpis?.merchant_programs)} sub="affiliate commercial universe"/>
  </section>

  <section className="semanticGrid2">
   <div className="semanticPanel"><div className="semanticPanelHead"><div><span>SEMANTIC MARKET MAP</span><h2>Demand × Competition × Pain</h2></div><Link href="/analytics">Full Analytics →</Link></div><CategoryMarketScatter items={categories}/><p className="semanticNote">Only rows with both demand and competition evidence are plotted. Missing competition is excluded rather than shown as zero.</p></div>
   <div className="semanticPanel"><span>TAXONOMY HEALTH</span><h2>What the system trusts</h2><div className="semanticTaxGrid"><div><b>{fmt(tax.validated)}</b><small>validated canonical nodes</small></div><div><b>{fmt(tax.mapped)}</b><small>legacy aliases mapped</small></div><div><b>{fmt(tax.rejected)}</b><small>navigation/brand/theme/noise rejected</small></div><div><b>{fmt(tax.pending)}</b><small>inactive labels awaiting review</small></div></div><p className="semanticNote">Brand, theme, location, language, promotion, navigation and service-policy labels cannot become product subcategories.</p></div>
  </section>

  <section className="semanticPanel"><div className="semanticPanelHead"><div><span>CATEGORY DEMAND / COMPETITION</span><h2>Canonical market intelligence</h2></div><small>{categories.length} semantic rows</small></div>
   {categories.length?<div className="semanticTableWrap"><table><thead><tr><th>Category</th><th>Subcategory</th><th>Demand</th><th>Competition</th><th>Pain</th><th>Opportunity</th><th>Confidence</th><th>Evidence entities</th><th>State</th></tr></thead><tbody>{categories.slice(0,100).map((x,i)=>{const complete=valid(x.competition_score)&&valid(x.demand_score);return <tr key={x.id||i}><td><b>{x.category_name||x.taxonomy_name||'—'}</b></td><td>{x.subcategory_name||'Category level'}</td><td>{fmt(x.demand_score,0)}</td><td>{fmt(x.competition_score,0)}</td><td>{fmt(x.pain_gap_score,0)}</td><td>{fmt(x.opportunity_score,0)}</td><td>{pct(x.confidence,0)}</td><td>{fmt(x.evidence_entities)}</td><td><span className={complete?'semanticGood':'semanticWarn'}>{complete?'comparable':'competition missing'}</span></td></tr>})}</tbody></table></div>:<Empty title="No trusted market rows">Canonical category research needs a fresh evidence run.</Empty>}
  </section>

  <section className="semanticGrid2">
   <div className="semanticPanel"><div className="semanticPanelHead"><div><span>VALIDATED PAINS</span><h2>Evidence-backed unmet needs</h2></div><b>{pains.length}</b></div>{pains.length?pains.slice(0,12).map(p=><div className="semanticPain" key={p.id}><div><b>{p.canonical_text}</b><small>{p.category}{p.subcategory?` / ${p.subcategory}`:''} · {fmt(p.evidence_count)} evidence · {fmt(p.source_diversity)} sources</small></div><strong>{fmt(p.pain_severity,0)}</strong></div>):<Empty title="0 clean validated pains">Four legacy “validated” clusters were semantically unrelated and are now stale. Product Intelligence will not promote products until clean pain evidence passes the hardened audit.</Empty>}</div>
   <div className="semanticPanel"><span>AFFILIATE DECISION LAYER</span><h2>Production actions</h2><div className="semanticAction"><b>Optimize merchant programs</b><p>Use observed network CVR/EPC/approval and scenario economics.</p><Link href="/optimization">Open Optimize →</Link></div><div className="semanticAction"><b>Top forecasted products</b><p>Validated products + tracking URLs + keywords + low-competition tag hypotheses + unique promotion copy.</p><Link href="/forecast-products">Open Forecast Products →</Link></div><div className="semanticAction"><b>Product gates</b><p>Change commission, trust, pain-fit, audit thresholds and score weights without code edits.</p><Link href="/configuration">Open Configuration →</Link></div></div>
  </section>

  <section className="semanticGrid2">
   <div className="semanticPanel"><span>MERCHANT WHITESPACE</span><h2>Highest current signals</h2>{merchants.slice(0,10).map(m=><Meter key={m.merchant_id} label={m.canonical_name} value={m.solution_whitespace_score} sub={`Demand ${fmt(m.demand_score)} · Competition ${fmt(m.competition_score)} · Trust ${fmt(m.trust_score)}`}/>)}{!merchants.length&&<Empty title="No merchant signals">Merchant intelligence is not available.</Empty>}</div>
   <div className="semanticPanel"><span>AI FORECAST</span><h2>Evidence-bounded outlook</h2>{forecast?<><p className="semanticSummary">{forecast.market_outlook||forecast.executive_summary||'Forecast generated.'}</p><div className="semanticForecastMeta"><b>Confidence {fmt(forecast.confidence_0_100,0)}%</b><small>{forecast.methodology_note||'Directional indices only.'}</small></div>{(forecast.affiliate_actions||[]).slice(0,6).map((a,i)=><div className="semanticForecastItem" key={i}>{typeof a==='string'?a:JSON.stringify(a)}</div>)}</>:<Empty title="Run AI Forecast">The forecast receives only semantic-taxonomy rows and currently validated pains. It cannot invent missing search volume, competition or conversions.</Empty>}</div>
  </section>

  <footer className="semanticFooter">Generated {data?.generated_at?new Date(data.generated_at).toLocaleString('el-GR'):'—'} · Production data only · Missing ≠ zero</footer>
 </main>
}
