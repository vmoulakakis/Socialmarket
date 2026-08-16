'use client';

import Link from 'next/link';
import {useEffect,useMemo,useState} from 'react';
import {supabase} from '@/lib/supabase';

const valid=v=>v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v));
const fmt=(v,d=0)=>valid(v)?Number(v).toLocaleString('el-GR',{maximumFractionDigits:d}):'—';
function Kpi({label,value,sub}){return <div className="semanticKpi"><span>{label}</span><strong>{value}</strong><small>{sub}</small></div>}
function Step({n,title,status,href,children}){const good=status==='READY'||status==='COMPLETE'||status==='LIVE';return <div className="semanticPanel"><div className="semanticPanelHead"><div><span>STEP {n}</span><h2>{title}</h2></div><span className={good?'semanticGood':'semanticWarn'}>{status}</span></div><p>{children}</p><Link href={href}>Open {title} →</Link></div>}

async function adminRequest(path){
 const {data:{session}}=await supabase.auth.getSession();
 const token=session?.access_token;
 if(!token)throw new Error('Admin session expired. Sign in again.');
 const r=await fetch(path,{headers:{authorization:`Bearer ${token}`},cache:'no-store'});
 const text=await r.text();let j=null;try{j=text?JSON.parse(text):null}catch{j={error:text||`HTTP ${r.status}`}}
 if(!r.ok||j?.error)throw new Error(j?.detail||j?.error||`HTTP ${r.status}`);
 return j;
}

export default function ProductionControlTower(){
 const [data,setData]=useState(null),[top,setTop]=useState([]),[outbox,setOutbox]=useState([]),[loading,setLoading]=useState(true),[error,setError]=useState('');
 async function load(){
  setLoading(true);setError('');
  try{
   const [dashboard,ranked,out]=await Promise.all([
    adminRequest('/api/admin-dashboard'),
    supabase.rpc('admin_top_ranked_products',{p_limit:100,p_band:null}),
    supabase.from('socialmarket_publishing_outbox').select('id,status,scheduled_for,last_error,created_at').order('created_at',{ascending:false}).limit(250)
   ]);
   if(ranked.error)throw ranked.error;if(out.error)throw out.error;
   setData(dashboard);setTop(ranked.data||[]);setOutbox(out.data||[]);
  }catch(e){setError(String(e.message||e));setData(null);setTop([]);setOutbox([])}finally{setLoading(false)}
 }
 useEffect(()=>{load()},[]);
 const categories=data?.category_market||[],merchants=data?.merchants||[];
 const waiting=useMemo(()=>outbox.filter(x=>['queued','ready','pending','scheduled'].includes(String(x.status||'').toLowerCase())).length,[outbox]);
 const failed=useMemo(()=>outbox.filter(x=>['failed','blocked','error'].includes(String(x.status||'').toLowerCase())).length,[outbox]);
 const topReady=top.length>=100;
 if(loading)return <main className="semanticConsole"><div className="semanticLoading">Loading SocialMarket production control tower…</div></main>;
 return <main className="semanticConsole">
  <header className="semanticHero"><div><span>PRODUCTION · WEEKLY AI PIPELINE</span><h1>SocialMarket Control Tower</h1><p>One operational flow: Demand → Merchants → Products → Full AI Ranking → Top 100 → Content/Outbox. The heavy intelligence pipeline runs every 7 days; SocialScheduler remains the independent execution layer.</p></div><div><button onClick={load}>↻ Refresh</button><Link className="semanticPrimary" href="/configuration">Configuration</Link></div></header>
  {error&&<div className="semanticError">{error}</div>}

  <section className="semanticKpis">
   <Kpi label="Demand markets" value={fmt(categories.length)} sub="canonical Greek market rows"/>
   <Kpi label="Merchants" value={fmt(merchants.length)} sub="merchant intelligence available"/>
   <Kpi label="Ranked products" value={fmt(top.length)} sub={topReady?'Top 100 contract visible':'waiting for complete ranking run'}/>
   <Kpi label="Outbox active" value={fmt(waiting)} sub="queued / ready / scheduled"/>
   <Kpi label="Outbox errors" value={fmt(failed)} sub={failed?'needs attention':'no current failures'}/>
   <Kpi label="AI cadence" value="7 days" sub="weekly canonical intelligence chain"/>
  </section>

  <section className="semanticPanel"><div className="semanticPanelHead"><div><span>CANONICAL OPERATING FLOW</span><h2>From market evidence to publishable inventory</h2></div><b>Weekly</b></div><p className="semanticNote">The scheduled chain is fail-closed: each AI stage starts only after the previous stage succeeds. Manual workflow dispatch remains available for maintenance or an intentional re-run.</p></section>

  <section className="semanticGrid2">
   <Step n="1" title="Demand" status={categories.length?'READY':'WAITING'} href="/demand">Category demand, competition, evidence, pain signals and Deep Demand context. Missing data stays unknown rather than becoming a favorable score.</Step>
   <Step n="2" title="Merchants" status={merchants.length?'READY':'WAITING'} href="/merchants">Merchant identity, trust, commercial program context, opportunity/whitespace and promotion eligibility.</Step>
   <Step n="3" title="Products" status="LIVE" href="/products">Direct Linkwise product universe, hard commercial gates, €10 minimum expected commission, merchant trust and deterministic preselection.</Step>
   <Step n="4" title="Full AI Process" status={top.length?'COMPLETE':'WAITING'} href="/analytics">Deterministic ranking → RAG/context → DeepSeek strategist → independent skeptic → SEO → Top 20 creative audit and durable assets.</Step>
   <Step n="5" title="Top 100" status={topReady?'COMPLETE':'WAITING'} href="/forecast-products">The highest ranked promotion candidates from the latest canonical production run. Minimum production contract: 100 fully ranked products.</Step>
   <Step n="6" title="Outbox" status={failed?'CHECK':'READY'} href="/scheduler">Approved canonical content and publishing intent. SocialScheduler executes approved jobs toward Buffer; SocialMarket does not publish directly.</Step>
  </section>

  <section className="semanticGrid2">
   <div className="semanticPanel"><span>WEEKLY AI JOB</span><h2>Execution order</h2><div className="semanticAction"><b>1 · Merchant Intelligence</b><p>Refresh merchant and affiliate-program evidence.</p></div><div className="semanticAction"><b>2 · Category Pain + Demand</b><p>Refresh Greek consumer evidence and canonical market context.</p></div><div className="semanticAction"><b>3 · Deep Demand</b><p>Run modeled demand only where evidence is sufficient; otherwise WITHHOLD.</p></div><div className="semanticAction"><b>4 · Product Ranking</b><p>Scan full Linkwise universe, rank 100–200, generate SEO, audit Top 20 and persist content.</p></div></div>
   <div className="semanticPanel"><span>QUICK ACCESS</span><h2>What you normally need</h2><div className="semanticAction"><b>Inspect the final choices</b><p>See rank, commission, network baseline, AI confidence, skeptic risk and SEO.</p><Link href="/forecast-products">Open Top 100 →</Link></div><div className="semanticAction"><b>Check what will publish</b><p>See canonical content, scheduled jobs and executor errors.</p><Link href="/scheduler">Open Outbox →</Link></div><div className="semanticAction"><b>Change decision thresholds</b><p>Adjust configurable scoring/gates without changing safety invariants.</p><Link href="/configuration">Open Configuration →</Link></div></div>
  </section>

  <footer className="semanticFooter">Generated {data?.generated_at?new Date(data.generated_at).toLocaleString('el-GR'):'—'} · Production data only · Heavy AI every 7 days · Missing ≠ zero</footer>
 </main>
}
