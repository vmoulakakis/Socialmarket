'use client';

import {useEffect,useMemo,useState} from 'react';
import {supabase} from '@/lib/supabase';
import styles from './product-to-post.module.css';

const PLATFORMS=['facebook','instagram','tiktok','linkedin'];
const LABELS={facebook:'Facebook',instagram:'Instagram',tiktok:'TikTok',linkedin:'LinkedIn'};
const statusClass=s=>`${styles.status} ${['completed','scheduled','published','approved'].includes(s)?styles.good:['failed','cancelled'].includes(s)?styles.bad:styles.warn}`;
const dt=v=>v?new Date(v).toLocaleString('el-GR',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}):'—';

export default function ProductToPost(){
  const [runs,setRuns]=useState([]),[candidates,setCandidates]=useState([]),[calendar,setCalendar]=useState([]),[busy,setBusy]=useState(false),[msg,setMsg]=useState(''),[err,setErr]=useState('');
  const [form,setForm]=useState({mode:'auto',productId:'',count:5,horizon:30,platforms:[...PLATFORMS],strategy:'conversion',audience:''});
  useEffect(()=>{load()},[]);
  async function load(){
    setErr('');
    const [{data:r,error:re},{data:c},{data:cal}]=await Promise.all([
      supabase.from('product_to_post_runs').select('*').order('created_at',{ascending:false}).limit(30),
      supabase.from('opportunity_scores').select('id,higo_adjusted,confidence,products(id,product_name,brand_name,merchant_name,price,discount_pct,tracking_url,image_url,market_eligible,is_preferred_offer)').neq('decision','DROP').order('higo_adjusted',{ascending:false}).limit(100),
      supabase.from('social_content_calendar').select('id,run_id,platform,scheduled_at,status,tracking_url,creative_asset_id,social_post_variants(headline,hook,caption),product_to_post_items(products(product_name,brand_name))').order('scheduled_at',{ascending:true}).limit(500)
    ]);
    if(re)setErr(re.message);setRuns(r||[]);
    setCandidates((c||[]).filter(x=>x.products?.tracking_url&&x.products?.image_url&&x.products?.market_eligible!==false&&x.products?.is_preferred_offer!==false).slice(0,50));
    setCalendar(cal||[]);
  }
  function toggle(p){setForm(f=>({...f,platforms:f.platforms.includes(p)?f.platforms.filter(x=>x!==p):[...f.platforms,p]}))}
  async function createRun(e){
    e.preventDefault();setMsg('');setErr('');if(!form.platforms.length)return setErr('Διάλεξε τουλάχιστον μία πλατφόρμα.');if(form.mode==='manual'&&!form.productId)return setErr('Διάλεξε προϊόν.');
    setBusy(true);
    const payload={mode:form.mode,product_id:form.mode==='manual'?form.productId:null,requested_count:form.mode==='manual'?1:Number(form.count),platforms:form.platforms,horizon_days:Number(form.horizon),strategy:form.strategy,audience_context:form.audience?{notes:form.audience}:{},status:'queued'};
    const {data,error}=await supabase.from('product_to_post_runs').insert(payload).select().single();
    if(error)setErr(error.message);else setMsg(`Run ${data.id.slice(0,8)} queued. Ο worker θα το μετατρέψει σε evidence → angles → creatives → 30-day calendar.`);
    setBusy(false);await load();
  }
  const latest=runs[0];
  const latestCal=useMemo(()=>latest?calendar.filter(x=>x.run_id===latest.id):[],[calendar,latest]);
  const grouped=useMemo(()=>{const m={};for(const x of latestCal){const day=new Date(x.scheduled_at).toLocaleDateString('el-GR',{weekday:'short',day:'2-digit',month:'short'});(m[day]??=[]).push(x)}return m},[latestCal]);
  const k={runs:runs.length,queued:runs.filter(x=>['queued','processing'].includes(x.status)).length,review:runs.filter(x=>x.status==='needs_approval').length,slots:latestCal.length};
  return <main className={styles.page}>
    <section className={styles.hero}><div><div className="eyebrow">SOCIALMARKET · CONVERSION FACTORY</div><h1>Product → Post Engine</h1><p className={styles.muted}>Verified affiliate product → evidence → marketing angles → native social copy → professional product creative + QR → 30-day calendar.</p></div><button onClick={load}>↻ Refresh</button></section>
    {err?<div className={styles.error}>{err}</div>:null}{msg?<div className="card">{msg}</div>:null}
    <section className={styles.kpis}><div className={styles.kpi}><small>Runs</small><strong>{k.runs}</strong></div><div className={styles.kpi}><small>In pipeline</small><strong>{k.queued}</strong></div><div className={styles.kpi}><small>Needs approval</small><strong>{k.review}</strong></div><div className={styles.kpi}><small>Latest calendar</small><strong>{k.slots}</strong></div></section>
    <section className={styles.grid}>
      <article className={styles.card}><div className="eyebrow">NEW RUN</div><h2>Manual ή AI auto-selection</h2><form className={styles.form} onSubmit={createRun}>
        <div className={styles.row}><label>Mode<select value={form.mode} onChange={e=>setForm({...form,mode:e.target.value})}><option value="auto">AI auto — top DB opportunities</option><option value="manual">Manual — επιλέγω προϊόν</option></select></label><label>{form.mode==='auto'?'Products':'Product'}{form.mode==='auto'?<input type="number" min="1" max="30" value={form.count} onChange={e=>setForm({...form,count:e.target.value})}/>:<select value={form.productId} onChange={e=>setForm({...form,productId:e.target.value})}><option value="">Choose product…</option>{candidates.map(x=><option key={x.products.id} value={x.products.id}>{Number(x.higo_adjusted||0).toFixed(0)} · {x.products.product_name} · {x.products.merchant_name}</option>)}</select>}</label></div>
        <div className={styles.row}><label>Calendar horizon<input type="number" min="7" max="90" value={form.horizon} onChange={e=>setForm({...form,horizon:e.target.value})}/></label><label>Strategy<select value={form.strategy} onChange={e=>setForm({...form,strategy:e.target.value})}><option value="conversion">Conversion</option><option value="qualified_click">Qualified clicks</option><option value="launch">Launch / discovery</option></select></label></div>
        <label>Audience / campaign context<textarea rows="3" placeholder="π.χ. γονείς 35–50, πρακτικές λύσεις, όχι κραυγαλέα διαφήμιση" value={form.audience} onChange={e=>setForm({...form,audience:e.target.value})}/></label>
        <div><small>Platforms</small><div className={styles.platforms}>{PLATFORMS.map(p=><button type="button" key={p} className={form.platforms.includes(p)?styles.on:''} onClick={()=>toggle(p)}>{LABELS[p]}</button>)}</div></div>
        <div className={styles.actions}><button className={styles.primary} disabled={busy}>{busy?'Queuing…':'Create Product-to-Post run →'}</button></div>
      </form></article>
      <article className={styles.card}><div className="eyebrow">PIPELINE</div><h2>Recent runs</h2><div className={styles.runs}>{runs.length?runs.map(r=><div className={styles.run} key={r.id}><div><strong>{r.mode==='auto'?`Auto · ${r.requested_count} products`:'Manual product'}</strong><small className={styles.muted}>{dt(r.created_at)} · {(r.platforms||[]).map(x=>LABELS[x]).join(' / ')}</small>{r.error?<small className={styles.muted}>{String(r.error).slice(0,180)}</small>:null}</div><span className={statusClass(r.status)}>{r.status}</span></div>):<p className={styles.muted}>No runs yet.</p>}</div></article>
    </section>
    <section className={styles.card}><div className="eyebrow">30-DAY PLAN</div><h2>{latest?`Latest run · ${latest.status}`:'No calendar yet'}</h2>{Object.keys(grouped).length?<div className={styles.calendar}>{Object.entries(grouped).map(([day,items])=><article className={styles.day} key={day}><strong>{day}</strong>{items.map(x=><div className={styles.slot} key={x.id}><b>{LABELS[x.platform]}</b><span>{x.product_to_post_items?.products?.product_name||x.social_post_variants?.headline||'Post'}</span><small className={styles.muted}>{dt(x.scheduled_at)} · {x.status}</small></div>)}</article>)}</div>:<p className={styles.muted}>Μόλις ολοκληρωθεί ένα run, εδώ εμφανίζονται τα platform-specific slots προς approval.</p>}</section>
  </main>
}
