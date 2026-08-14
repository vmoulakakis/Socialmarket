'use client';

import {useEffect,useMemo,useState} from 'react';
import Link from 'next/link';
import {supabase} from '@/lib/supabase';

const PLATFORMS=['instagram','tiktok','facebook','linkedin'];
const LABEL={instagram:'Instagram',tiktok:'TikTok',facebook:'Facebook',linkedin:'LinkedIn'};

export default function SessionPublishingPage(){
  const [accounts,setAccounts]=useState([]);
  const [jobs,setJobs]=useState([]);
  const [posts,setPosts]=useState([]);
  const [busy,setBusy]=useState('');
  const [msg,setMsg]=useState('');
  const [linkedin,setLinkedin]=useState({caption:'',tracking_url:''});

  useEffect(()=>{load()},[]);

  async function load(){
    setMsg('');
    const [a,j,p]=await Promise.all([
      supabase.from('social_session_accounts').select('*').order('updated_at',{ascending:false}),
      supabase.from('social_publish_jobs').select('*').order('created_at',{ascending:false}).limit(100),
      supabase.from('social_posts').select('id,platform,status,approval_status,title,caption,hashtags,tracking_url,source_image_url,media_url,scheduled_at,products(product_name,brand_name)').order('created_at',{ascending:false}).limit(100)
    ]);
    const err=a.error||j.error||p.error;
    if(err)setMsg(err.message);
    setAccounts(a.data||[]);setJobs(j.data||[]);setPosts(p.data||[]);
  }

  const eligible=useMemo(()=>posts.filter(p=>p.approval_status==='approved'&&PLATFORMS.includes(p.platform)),[posts]);

  function accountFor(platform){return accounts.find(a=>a.platform===platform)}

  async function queuePost(post){
    setBusy(post.id);setMsg('');
    const account=accountFor(post.platform);
    const key=`assisted:${post.id}:${post.platform}:${post.scheduled_at||'now'}`;
    const {error}=await supabase.from('social_publish_jobs').upsert({
      post_id:post.id,
      account_id:account?.id||null,
      platform:post.platform,
      publish_mode:'assisted',
      status:'queued',
      scheduled_at:post.scheduled_at||new Date().toISOString(),
      idempotency_key:key,
      payload:{
        title:post.title,
        caption:post.caption,
        hashtags:post.hashtags,
        tracking_url:post.tracking_url,
        media_url:post.media_url,
        source_image_url:post.source_image_url
      }
    },{onConflict:'idempotency_key'});
    setMsg(error?error.message:`Queued ${LABEL[post.platform]} assisted publish.`);
    setBusy('');await load();
  }

  async function queueLinkedIn(e){
    e.preventDefault();
    if(!linkedin.caption.trim())return setMsg('Γράψε πρώτα το LinkedIn post.');
    setBusy('linkedin');
    const account=accountFor('linkedin');
    const {error}=await supabase.from('social_publish_jobs').insert({
      account_id:account?.id||null,
      platform:'linkedin',
      publish_mode:'assisted',
      status:'queued',
      scheduled_at:new Date().toISOString(),
      idempotency_key:`linkedin:${Date.now()}`,
      payload:{caption:linkedin.caption.trim(),tracking_url:linkedin.tracking_url.trim()||null}
    });
    if(!error)setLinkedin({caption:'',tracking_url:''});
    setMsg(error?error.message:'LinkedIn draft queued.');setBusy('');await load();
  }

  async function copy(text){
    try{await navigator.clipboard.writeText(text||'');setMsg('Caption copied.')}catch{setMsg('Copy failed — select the text manually.')}
  }

  return <main style={S.page}>
    <header style={S.hero}>
      <div><div style={S.eye}>SOCIALMARKET · NO-APP ROUTE</div><h1 style={S.h1}>Session Publishing</h1><p style={S.lead}>Pair accounts once, verify the saved session, prepare media + caption, then finish the final Publish action yourself. Official OAuth/API routes remain available for unattended publishing.</p></div>
      <div style={S.actions}><Link href="/scheduler" style={S.linkBtn}>← Scheduler</Link><button style={S.btn} onClick={load}>↻ Refresh</button></div>
    </header>

    {msg?<div style={S.toast}>{msg}</div>:null}

    <section style={S.grid4}>
      {PLATFORMS.map(platform=>{
        const a=accountFor(platform);
        return <article key={platform} style={S.card}>
          <div style={S.row}><b>{LABEL[platform]}</b><span style={{...S.badge,background:a?.status==='connected'||a?.status==='paired'?'#163d2c':'#3b2b16'}}>{a?.status||'not paired'}</span></div>
          <h3 style={S.cardTitle}>{a?.account_label||'No session account'}</h3>
          <p style={S.muted}>{a?.account_handle||'Pair from a trusted local browser.'}</p>
          <p style={S.small}>Last worker: {a?.worker_last_seen_at?new Date(a.worker_last_seen_at).toLocaleString('el-GR'):'—'}</p>
          {a?.last_error?<p style={S.error}>{a.last_error}</p>:null}
        </article>
      })}
    </section>

    <section style={S.panel}>
      <div style={S.rowWrap}>
        <div><div style={S.eye}>ONE-TIME PAIRING</div><h2 style={S.h2}>Login once from your own machine</h2><p style={S.muted}>The helper opens the real platform login page. Complete login/MFA yourself; SocialMarket stores only encrypted browser session state.</p></div>
      </div>
      <pre style={S.code}>pip install -r workers/social_publisher/requirements.txt{`\n`}python -m playwright install chromium{`\n`}python -m workers.social_publisher.bootstrap_session instagram --label "SocialMarket Instagram"</pre>
      <p style={S.small}>Required local environment: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SOCIAL_SESSION_KEY. Never paste those values into GitHub source files.</p>
    </section>

    <section style={S.panel}>
      <div style={S.rowWrap}><div><div style={S.eye}>APPROVED CONTENT</div><h2 style={S.h2}>Queue existing campaign posts</h2><p style={S.muted}>Only already-approved posts are shown here.</p></div><span style={S.counter}>{eligible.length}</span></div>
      <div style={S.list}>
        {eligible.length?eligible.map(p=><article key={p.id} style={S.item}>
          <div style={S.thumbWrap}>{p.media_url||p.source_image_url?<img src={p.media_url||p.source_image_url} alt="" style={S.thumb}/>:<div style={S.thumbEmpty}>no media</div>}</div>
          <div style={{flex:1,minWidth:0}}><div style={S.row}><b>{LABEL[p.platform]}</b><span style={S.status}>{p.status}</span></div><h3 style={S.itemTitle}>{p.products?.product_name||p.title||'Untitled'}</h3><p style={S.caption}>{p.caption||'No caption'}</p></div>
          <button style={S.primary} disabled={busy===p.id} onClick={()=>queuePost(p)}>{busy===p.id?'Queueing…':'Queue assisted'}</button>
        </article>):<div style={S.empty}>No approved posts available.</div>}
      </div>
    </section>

    <section style={S.panel}>
      <div style={S.eye}>LINKEDIN</div><h2 style={S.h2}>Quick assisted post</h2>
      <form onSubmit={queueLinkedIn} style={S.form}>
        <textarea style={S.textarea} rows={7} value={linkedin.caption} onChange={e=>setLinkedin({...linkedin,caption:e.target.value})} placeholder="LinkedIn post text…"/>
        <input style={S.input} value={linkedin.tracking_url} onChange={e=>setLinkedin({...linkedin,tracking_url:e.target.value})} placeholder="Optional URL"/>
        <button style={S.primary} disabled={busy==='linkedin'}>{busy==='linkedin'?'Queueing…':'Queue LinkedIn draft'}</button>
      </form>
    </section>

    <section style={S.panel}>
      <div style={S.rowWrap}><div><div style={S.eye}>READY / HISTORY</div><h2 style={S.h2}>Publishing jobs</h2></div><span style={S.counter}>{jobs.length}</span></div>
      <div style={S.list}>{jobs.length?jobs.map(job=>{
        const r=job.result||{};
        return <article key={job.id} style={S.item}>
          <div style={{flex:1}}><div style={S.row}><b>{LABEL[job.platform]||job.platform}</b><span style={S.status}>{job.status}</span></div><p style={S.caption}>{r.caption||job.payload?.caption||'—'}</p>{job.last_error?<p style={S.error}>{job.last_error}</p>:null}</div>
          <div style={S.actions}>
            {(r.caption||job.payload?.caption)?<button style={S.btn} onClick={()=>copy(r.caption||job.payload?.caption)}>Copy caption</button>:null}
            {r.open_url?<a style={S.primaryLink} href={r.open_url} target="_blank" rel="noreferrer">Open composer →</a>:null}
          </div>
        </article>
      }):<div style={S.empty}>No no-app jobs yet.</div>}</div>
    </section>
  </main>
}

const S={
  page:{maxWidth:1280,margin:'0 auto',padding:'32px 22px 80px',color:'#f5f6f8'},
  hero:{display:'flex',justifyContent:'space-between',gap:24,alignItems:'flex-start',padding:'28px',border:'1px solid #29303a',borderRadius:24,background:'linear-gradient(135deg,#111821,#17131d)'},
  eye:{fontSize:12,letterSpacing:1.8,fontWeight:800,color:'#9aa7b7'},h1:{fontSize:42,margin:'8px 0 10px'},h2:{fontSize:25,margin:'5px 0 8px'},lead:{maxWidth:820,color:'#c3cad4',lineHeight:1.6},
  actions:{display:'flex',gap:10,flexWrap:'wrap',alignItems:'center'},btn:{border:'1px solid #394351',background:'#171d25',color:'#eef2f7',padding:'10px 14px',borderRadius:12,cursor:'pointer'},linkBtn:{textDecoration:'none',border:'1px solid #394351',background:'#171d25',color:'#eef2f7',padding:'10px 14px',borderRadius:12},primary:{border:0,background:'#f0f2f5',color:'#11151b',fontWeight:800,padding:'11px 15px',borderRadius:12,cursor:'pointer'},primaryLink:{textDecoration:'none',background:'#f0f2f5',color:'#11151b',fontWeight:800,padding:'11px 15px',borderRadius:12,whiteSpace:'nowrap'},
  toast:{marginTop:16,padding:'12px 16px',background:'#18212b',border:'1px solid #344252',borderRadius:12},grid4:{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(220px,1fr))',gap:14,marginTop:18},card:{padding:18,border:'1px solid #29313b',borderRadius:18,background:'#12171e'},row:{display:'flex',justifyContent:'space-between',gap:12,alignItems:'center'},rowWrap:{display:'flex',justifyContent:'space-between',gap:20,alignItems:'center',flexWrap:'wrap'},badge:{padding:'4px 8px',borderRadius:999,fontSize:11,fontWeight:800},cardTitle:{margin:'18px 0 5px',fontSize:18},muted:{color:'#aab4c0',lineHeight:1.5},small:{fontSize:12,color:'#818e9c'},error:{color:'#ff9e9e',fontSize:12,lineHeight:1.4},panel:{marginTop:18,padding:22,border:'1px solid #29313b',borderRadius:20,background:'#10151b'},code:{overflowX:'auto',padding:16,borderRadius:14,background:'#080b0f',border:'1px solid #252c35',color:'#bde0c6',lineHeight:1.6},counter:{minWidth:36,height:36,borderRadius:99,display:'grid',placeItems:'center',background:'#202832',fontWeight:800},list:{display:'grid',gap:10,marginTop:16},item:{display:'flex',alignItems:'center',gap:14,padding:14,border:'1px solid #252d36',borderRadius:16,background:'#0d1217'},thumbWrap:{width:68,height:68,flex:'0 0 68px'},thumb:{width:'100%',height:'100%',objectFit:'cover',borderRadius:12},thumbEmpty:{width:'100%',height:'100%',display:'grid',placeItems:'center',fontSize:10,color:'#6f7b88',background:'#191f26',borderRadius:12},status:{fontSize:11,color:'#9fb0bf',textTransform:'uppercase'},itemTitle:{fontSize:16,margin:'6px 0'},caption:{margin:0,color:'#aeb8c3',lineHeight:1.45,whiteSpace:'pre-wrap',overflowWrap:'anywhere'},empty:{padding:30,textAlign:'center',color:'#788593'},form:{display:'grid',gap:10,marginTop:14},textarea:{width:'100%',boxSizing:'border-box',border:'1px solid #303944',borderRadius:14,background:'#0c1117',color:'#eef2f6',padding:14,font:'inherit'},input:{width:'100%',boxSizing:'border-box',border:'1px solid #303944',borderRadius:12,background:'#0c1117',color:'#eef2f6',padding:12,font:'inherit'}
};
