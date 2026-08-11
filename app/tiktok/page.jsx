'use client';

import { useEffect, useMemo, useState } from 'react';
import { supabase } from '@/lib/supabase';

const EDGE=process.env.NEXT_PUBLIC_SUPABASE_URL;
const tabs=[['studio','Studio'],['queue','Queue'],['calendar','Calendar'],['account','Account']];
const good=['connected','published','scheduled','completed','approved','draft'];
const bad=['failed','blocked','error','revoked','expired'];
function cls(status){return `tt-status ${good.includes(status)?'is-good':bad.includes(status)?'is-bad':'is-warn'}`}
function money(v){return v==null?'—':new Intl.NumberFormat('el-GR',{style:'currency',currency:'EUR'}).format(Number(v))}
function dt(v){return v?new Date(v).toLocaleString('el-GR',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}):'—'}
function pct(v){return v?`${Math.round(Number(v))}%`:null}
function mediaOf(p){return Array.isArray(p.media_urls)&&p.media_urls[0]?p.media_urls[0]:null}
function dayKey(v){if(!v)return 'Unscheduled';return new Date(v).toLocaleDateString('el-GR',{weekday:'short',day:'2-digit',month:'short'})}

export default function TikTokStudio(){
  const [connections,setConnections]=useState([]),[batches,setBatches]=useState([]),[posts,setPosts]=useState([]),[health,setHealth]=useState(null);
  const [tab,setTab]=useState('studio'),[busy,setBusy]=useState(''),[msg,setMsg]=useState('');
  const [form,setForm]=useState({count:10,postsPerDay:5,strategy:'conversion',start:''});
  useEffect(()=>{load()},[]);

  async function load(){
    setMsg('');
    const [{data:c},{data:b},{data:p}]=await Promise.all([
      supabase.from('tiktok_connections').select('id,label,username,nickname,avatar_url,status,audited,can_direct_post,privacy_level_options,max_video_post_duration_sec,last_creator_info_at,last_error,updated_at').order('updated_at',{ascending:false}),
      supabase.from('tiktok_batches').select('id,name,strategy,requested_count,scheduled_from,posts_per_day,status,created_at,updated_at').order('created_at',{ascending:false}).limit(20),
      supabase.from('tiktok_posts').select('id,batch_id,status,media_type,strategy,hook,title,caption,hashtags,scheduled_at,published_at,publish_id,last_error_code,last_error_message,media_urls,metadata,creative_spec,products(product_name,brand_name,merchant_name,merchant_trust_score,category_raw,price,full_price,discount_pct)').order('created_at',{ascending:false}).limit(200)
    ]);
    setConnections(c||[]);setBatches(b||[]);setPosts(p||[]);
    if(EDGE){try{const r=await fetch(`${EDGE}/functions/v1/tiktok-oauth/health`,{cache:'no-store'});setHealth(await r.json())}catch{setHealth({ok:false})}}
  }

  async function connectTikTok(){
    if(!EDGE)return setMsg('NEXT_PUBLIC_SUPABASE_URL λείπει.');
    setBusy('connect');setMsg('');
    try{const r=await fetch(`${EDGE}/functions/v1/tiktok-oauth/start?return_to=${encodeURIComponent(window.location.href)}`,{cache:'no-store'}),d=await r.json();if(!r.ok||!d.authorize_url)throw new Error(d.error||'TikTok OAuth unavailable');window.location.href=d.authorize_url}catch(e){setMsg(String(e.message||e));setBusy('')}
  }
  async function createBatch(e){
    e.preventDefault();setBusy('batch');setMsg('');
    const start=form.start?new Date(form.start).toISOString():null;
    const {data,error}=await supabase.rpc('create_tiktok_batch',{p_name:`TikTok Top ${form.count}`,p_count:Number(form.count),p_posts_per_day:Number(form.postsPerDay),p_scheduled_from:start,p_strategy:form.strategy});
    setMsg(error?error.message:`Δημιουργήθηκαν ${data?.created||0} νέα TikTok drafts.`);setBusy('');await load();
  }
  async function aiRefine(batchId){
    setBusy(`ai-${batchId}`);setMsg('');
    try{
      const rows=posts.filter(p=>p.batch_id===batchId).slice(0,25).map(p=>({id:p.id,strategy:p.strategy,product:{...p.products,selection_score:p.metadata?.selection_score}}));
      if(!rows.length)throw new Error('No posts in batch');
      const r=await fetch('/api/tiktok/refine',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({posts:rows})}),d=await r.json();
      if(!r.ok)throw new Error(d.error||'AI refine failed');
      for(const x of d.posts||[])await supabase.from('tiktok_posts').update({hook:x.hook,title:x.title,caption:x.caption,hashtags:x.hashtags||[],strategy:x.strategy||undefined,creative_spec:x.creative_spec||{}}).eq('id',x.id);
      setMsg(`AI refined ${d.posts?.length||0} posts · ${d.provider}${d.model?` / ${d.model}`:''}`);
    }catch(e){setMsg(String(e.message||e))}
    setBusy('');await load();
  }
  async function queueCreatives(batchId){setBusy(`creative-${batchId}`);const {data,error}=await supabase.rpc('queue_tiktok_creatives',{p_batch_id:batchId});setMsg(error?error.message:`Queued ${data?.creative_jobs_queued||0} TikTok-safe creatives.`);setBusy('');await load()}
  async function scheduleBatch(batchId){setBusy(`schedule-${batchId}`);const {data,error}=await supabase.rpc('approve_and_schedule_tiktok_batch',{p_batch_id:batchId});setMsg(error?error.message:`Scheduled ${data?.scheduled||0} · waiting media ${data?.waiting_for_creative||0}`);setBusy('');await load()}

  const conn=connections[0];
  const k=useMemo(()=>({all:posts.length,draft:posts.filter(x=>['draft','needs_creative'].includes(x.status)).length,scheduled:posts.filter(x=>x.status==='scheduled').length,published:posts.filter(x=>x.status==='published').length,failed:posts.filter(x=>['failed','blocked'].includes(x.status)).length,media:posts.filter(x=>mediaOf(x)).length}),[posts]);
  const activeBatch=batches[0];
  const activePosts=activeBatch?posts.filter(p=>p.batch_id===activeBatch.id):posts.slice(0,10);
  const progress=activeBatch?Math.round((activePosts.filter(p=>mediaOf(p)).length/Math.max(1,activeBatch.requested_count))*100):0;
  const calendar=useMemo(()=>{const m={};for(const p of posts){const key=dayKey(p.scheduled_at);(m[key]??=[]).push(p)}return m},[posts]);

  return <main className="tt-page">
    <section className="tt-hero">
      <div><div className="eyebrow">SOCIALMARKET · CREATOR ENGINE</div><h1>TikTok Studio</h1><p>Από opportunity → creative → approval → schedule → publish, σε ένα workspace.</p></div>
      <div className="tt-hero-actions"><button className="tt-btn ghost" onClick={load}>↻ Refresh</button><button className="tt-btn primary" onClick={()=>setTab('studio')}>＋ New batch</button></div>
    </section>
    {msg?<div className="tt-toast">{msg}</div>:null}

    <nav className="tt-tabs">{tabs.map(([id,label])=><button key={id} onClick={()=>setTab(id)} className={tab===id?'active':''}>{label}{id==='queue'&&k.draft?<span>{k.draft}</span>:null}</button>)}</nav>

    <section className="tt-kpis">
      <article><div className="tt-kpi-icon">◫</div><div><small>Total posts</small><strong>{k.all}</strong><em>{k.media} media ready</em></div></article>
      <article><div className="tt-kpi-icon">✦</div><div><small>Drafts</small><strong>{k.draft}</strong><em>ready to review</em></div></article>
      <article><div className="tt-kpi-icon">◷</div><div><small>Scheduled</small><strong>{k.scheduled}</strong><em>in publishing queue</em></div></article>
      <article><div className="tt-kpi-icon">✓</div><div><small>Published</small><strong>{k.published}</strong><em>{k.failed} blocked / failed</em></div></article>
    </section>

    {tab==='studio'?<>
      <section className="tt-layout">
        <aside className="tt-panel tt-builder">
          <div className="tt-panel-head"><div><div className="eyebrow">MASS CREATOR</div><h2>Build a campaign</h2></div><span className="tt-ai-dot">AI</span></div>
          <form onSubmit={createBatch}>
            <label>How many products?<div className="tt-stepper"><button type="button" onClick={()=>setForm({...form,count:Math.max(1,Number(form.count)-5)})}>−</button><input value={form.count} type="number" min="1" max="1000" onChange={e=>setForm({...form,count:e.target.value})}/><button type="button" onClick={()=>setForm({...form,count:Math.min(1000,Number(form.count)+5)})}>＋</button></div></label>
            <label>Posting strategy<select value={form.strategy} onChange={e=>setForm({...form,strategy:e.target.value})}><option value="conversion">Conversion</option><option value="deal">Deal Reveal</option><option value="problem_solution">Problem → Solution</option><option value="lifestyle">Lifestyle</option><option value="curiosity">Curiosity</option></select></label>
            <div className="tt-form-row"><label>Posts / day<input type="number" min="1" max="15" value={form.postsPerDay} onChange={e=>setForm({...form,postsPerDay:e.target.value})}/></label><label>Start<input type="datetime-local" value={form.start} onChange={e=>setForm({...form,start:e.target.value})}/></label></div>
            <div className="tt-policy"><b>Smart selection ON</b><span>Active · market eligible · preferred merchant · no travel</span></div>
            <button className="tt-btn primary big" disabled={busy==='batch'}>{busy==='batch'?'Generating…':'Generate TikTok batch →'}</button>
          </form>
        </aside>

        <section className="tt-panel tt-current">
          <div className="tt-panel-head"><div><div className="eyebrow">CURRENT CAMPAIGN</div><h2>{activeBatch?.name||'No campaign yet'}</h2></div>{activeBatch?<span className={cls(activeBatch.status)}>{activeBatch.status}</span>:null}</div>
          {activeBatch?<>
            <div className="tt-progress-row"><div><strong>{activePosts.filter(p=>mediaOf(p)).length}/{activeBatch.requested_count}</strong><span>media ready</span></div><div><strong>{activeBatch.posts_per_day}/day</strong><span>cadence</span></div><div><strong>{progress}%</strong><span>production</span></div></div>
            <div className="tt-progress"><i style={{width:`${Math.min(100,progress)}%`}}/></div>
            <div className="tt-batch-actions"><button className="tt-btn ghost" onClick={()=>aiRefine(activeBatch.id)} disabled={busy===`ai-${activeBatch.id}`}>✦ AI Refine</button><button className="tt-btn ghost" onClick={()=>queueCreatives(activeBatch.id)} disabled={busy===`creative-${activeBatch.id}`}>◫ Queue creatives</button><button className="tt-btn primary" onClick={()=>scheduleBatch(activeBatch.id)} disabled={busy===`schedule-${activeBatch.id}`}>Approve & Schedule</button></div>
          </>:<div className="tt-empty">Δημιούργησε το πρώτο batch από τα Top Opportunities.</div>}
        </section>
      </section>

      <section className="tt-section-head"><div><div className="eyebrow">VISUAL QUEUE</div><h2>Ready to review</h2></div><button className="tt-text-btn" onClick={()=>setTab('queue')}>View all →</button></section>
      <section className="tt-post-grid">{activePosts.slice(0,8).map(p=><PostCard key={p.id} p={p}/>)}</section>
    </>:null}

    {tab==='queue'?<>
      <section className="tt-section-head"><div><div className="eyebrow">CONTENT QUEUE</div><h2>{posts.length} TikTok posts</h2></div><div className="tt-filter-pills"><span className="active">All</span><span>Draft {k.draft}</span><span>Scheduled {k.scheduled}</span><span>Published {k.published}</span></div></section>
      <section className="tt-post-grid large">{posts.map(p=><PostCard key={p.id} p={p}/>)}</section>
    </>:null}

    {tab==='calendar'?<>
      <section className="tt-section-head"><div><div className="eyebrow">PUBLISHING PLAN</div><h2>Schedule calendar</h2></div><span className="tt-mini-note">Timezone · Europe/Athens</span></section>
      <section className="tt-calendar">{Object.entries(calendar).map(([day,items])=><article key={day}><header><strong>{day}</strong><span>{items.length} posts</span></header><div>{items.slice(0,8).map(p=><div className="tt-calendar-item" key={p.id}>{mediaOf(p)?<img src={mediaOf(p)} alt=""/>:<span className="tt-cal-placeholder"/>}<div><b>{p.products?.brand_name||'Product'}</b><small>{p.scheduled_at?new Date(p.scheduled_at).toLocaleTimeString('el-GR',{hour:'2-digit',minute:'2-digit'}):'Not scheduled'}</small></div><span className={cls(p.status)}>{p.status}</span></div>)}</div></article>)}</section>
    </>:null}

    {tab==='account'?<section className="tt-account-grid">
      <article className="tt-panel">
        <div className="tt-panel-head"><div><div className="eyebrow">TIKTOK ACCOUNT</div><h2>{conn?.nickname||'Not connected'}</h2></div><span className={cls(conn?.status||'disconnected')}>{conn?.status||'disconnected'}</span></div>
        {conn?<div className="tt-account-row">{conn.avatar_url?<img src={conn.avatar_url} alt=""/>:<div className="tt-avatar-placeholder">♪</div>}<div><strong>@{conn.username||'—'}</strong><p>Direct Post: {conn.can_direct_post?'enabled':'not granted'} · Audit: {conn.audited?'approved':'pending'}</p><p>Creator info: {dt(conn.last_creator_info_at)}</p></div></div>:<p className="muted">Σύνδεσε TikTok creator account για Direct Post.</p>}
        <button className="tt-btn primary big" onClick={connectTikTok} disabled={busy==='connect'}>{conn?'Reconnect TikTok':'Connect TikTok'}</button>
      </article>
      <article className="tt-panel"><div className="eyebrow">SYSTEM STATUS</div><h2>Publishing infrastructure</h2><div className="tt-system-list"><div><span>OAuth configuration</span><b className={health?.configured?'good':'warn'}>{health?.configured?'Ready':'Needs client key/secret'}</b></div><div><span>Media pipeline</span><b className="good">Active</b></div><div><span>Publisher cron</span><b className="good">Every minute</b></div><div><span>TikTok media compliance</span><b className="good">Enforced</b></div></div></article>
      <article className="tt-panel tt-compliance"><div className="eyebrow">COMPLIANCE</div><h2>Native TikTok rules</h2><ul><li>✓ No QR inside media</li><li>✓ No baked tracking URL</li><li>✓ No promotional watermark</li><li>✓ Fresh creator privacy check before publish</li><li>✓ Unaudited API forces SELF_ONLY</li></ul></article>
    </section>:null}
  </main>
}

function PostCard({p}){
  const media=mediaOf(p),product=p.products||{};
  return <article className="tt-post-card">
    <div className="tt-media">{media?<img src={media} alt={product.product_name||'TikTok creative'}/>:<div className="tt-media-empty">♪<span>creative pending</span></div>}<div className="tt-media-top"><span className={cls(p.status)}>{p.status}</span><span className="tt-format">{p.media_type||'PHOTO'}</span></div>{product.discount_pct?<div className="tt-discount">−{pct(product.discount_pct)}</div>:null}</div>
    <div className="tt-card-body"><div className="tt-product-line"><div><small>{product.brand_name||product.merchant_name||'Product'}</small><h3>{product.product_name||'TikTok post'}</h3></div><strong>{money(product.price)}</strong></div><p className="tt-hook">“{p.hook||'AI hook pending'}”</p><div className="tt-card-meta"><span>{p.strategy}</span><span>{p.scheduled_at?dt(p.scheduled_at):'Not scheduled'}</span></div></div>
  </article>
}
