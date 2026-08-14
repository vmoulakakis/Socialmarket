'use client';

import {useEffect,useMemo,useState} from 'react';
import {supabase} from '@/lib/supabase';

const statusClass=(status)=>['published','scheduled'].includes(status)?'good':['failed','cancelled'].includes(status)?'bad':'warn';
const dt=(v)=>v?new Date(v).toLocaleString('el-GR',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}):'—';

export default function PublishingOutbox(){
  const [jobs,setJobs]=useState([]);
  const [loading,setLoading]=useState(true);
  const [msg,setMsg]=useState('');

  async function load(){
    setLoading(true);setMsg('');
    const {data,error}=await supabase
      .from('publishing_outbox')
      .select('id,platform,status,caption,format,media_url,tracking_url,scheduled_for,external_post_id,external_permalink,published_at,last_error,attempt_count,created_at,content_items(id,title,brand_sites(name,slug))')
      .order('created_at',{ascending:false})
      .limit(300);
    if(error)setMsg(error.message); else setJobs(data||[]);
    setLoading(false);
  }
  useEffect(()=>{load()},[]);

  const k=useMemo(()=>({
    ready:jobs.filter(x=>x.status==='approved').length,
    leased:jobs.filter(x=>x.status==='leased').length,
    scheduled:jobs.filter(x=>x.status==='scheduled').length,
    published:jobs.filter(x=>x.status==='published').length,
    failed:jobs.filter(x=>x.status==='failed').length,
  }),[jobs]);

  return <main>
    <section className="hero"><div><div className="eyebrow">SOCIALMARKET → SOCIALSCHEDULER</div><h1>Publishing Outbox</h1><p className="sub">Αυτό δεν είναι δεύτερος scheduler. Το SocialMarket δημιουργεί και εγκρίνει το content. Ο SocialScheduler κάνει claim μόνο από αυτό το outbox και είναι ο μοναδικός owner του Buffer scheduling/publishing.</p></div><button className="button" onClick={load}>↻ Refresh</button></section>

    <div className="grid">
      <article className="card"><div className="eyebrow">READY</div><h2>{k.ready}</h2><p className="muted">Approved jobs που περιμένουν executor.</p></article>
      <article className="card"><div className="eyebrow">LEASED</div><h2>{k.leased}</h2><p className="muted">Τα έχει προσωρινά κάνει claim ο executor.</p></article>
      <article className="card"><div className="eyebrow">SCHEDULED</div><h2>{k.scheduled}</h2><p className="muted">Έχουν Buffer post id.</p></article>
      <article className="card"><div className="eyebrow">PUBLISHED</div><h2>{k.published}</h2><p className="muted">Επιβεβαιωμένα sent/published.</p></article>
      <article className="card"><div className="eyebrow">FAILED</div><h2>{k.failed}</h2><p className="muted">Χρειάζονται διάγνωση· δεν γίνεται blind retry.</p></article>
    </div>

    {msg?<div className="card"><b>{msg}</b></div>:null}
    {loading?<div className="muted">Loading…</div>:null}
    {!loading&&jobs.length===0?<div className="card"><h2>Outbox empty</h2><p className="muted">Approved content θα εμφανίζεται εδώ αφού γίνει queue από το SocialMarket.</p></div>:null}

    <div className="creative-grid">
      {jobs.map(job=><article className="card creative-card" key={job.id}>
        {job.media_url?<img className="creative-image" src={job.media_url} alt="Publishing creative"/>:<div className="creative-placeholder">No media</div>}
        <div className="eyebrow">{job.content_items?.brand_sites?.name||'Brand'} · {job.platform}</div>
        <h3>{job.content_items?.title||'Content item'}</h3>
        <p>{job.caption}</p>
        <div className="creative-meta"><span className={statusClass(job.status)}>{job.status}</span><span>{job.format}</span><span>{dt(job.scheduled_for)}</span></div>
        <p className="muted">Attempts: {job.attempt_count||0}{job.external_post_id?` · Buffer ${job.external_post_id}`:''}</p>
        {job.last_error?<p className="muted"><b>Error:</b> {job.last_error}</p>:null}
        {job.external_permalink?<a href={job.external_permalink} target="_blank" rel="noreferrer">Open published post →</a>:null}
      </article>)}
    </div>
  </main>;
}
