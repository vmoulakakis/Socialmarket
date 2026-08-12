'use client';

import {useEffect,useMemo,useState} from 'react';
import Link from 'next/link';
import {supabase} from '@/lib/supabase';
import styles from './scheduler.module.css';

const PLATFORMS=['facebook','instagram','tiktok'];
const names={facebook:'Facebook',instagram:'Instagram',tiktok:'TikTok'};
const icons={facebook:'f',instagram:'◎',tiktok:'♪'};
function money(v){return v==null?'—':new Intl.NumberFormat('el-GR',{style:'currency',currency:'EUR'}).format(Number(v))}
function dt(v){return v?new Date(v).toLocaleString('el-GR',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}):'—'}
function cls(s){return `${styles.status} ${['published','scheduled','approved','connected'].includes(s)?styles.good:['failed','blocked','error'].includes(s)?styles.bad:styles.warn}`}

export default function SocialScheduler(){
  const [campaigns,setCampaigns]=useState([]),[posts,setPosts]=useState([]),[connections,setConnections]=useState([]),[ttConnections,setTTConnections]=useState([]),[metaHealth,setMetaHealth]=useState(null),[bufferHealth,setBufferHealth]=useState(null),[bufferChannels,setBufferChannels]=useState([]);
  const [tab,setTab]=useState('queue'),[platform,setPlatform]=useState('all'),[busy,setBusy]=useState(''),[msg,setMsg]=useState('');
  const [form,setForm]=useState({count:20,postsPerDay:3,start:'',platforms:['facebook','instagram','tiktok']});
  useEffect(()=>{try{const cached=JSON.parse(localStorage.getItem('socialmarket_buffer_channels')||'[]');if(Array.isArray(cached))setBufferChannels(cached)}catch{}load()},[]);
  async function load(){
    setMsg('');
    const [{data:c},{data:p},{data:a},{data:t}]=await Promise.all([
      supabase.from('social_campaigns').select('*').order('created_at',{ascending:false}).limit(30),
      supabase.from('social_posts').select('id,campaign_id,product_id,platform,status,title,caption,hashtags,tracking_url,source_image_url,media_url,media_type,scheduled_at,published_at,external_permalink,last_error_message,approval_status,metadata,products(product_name,brand_name,merchant_name,price,full_price,discount_pct)').order('created_at',{ascending:false}).limit(500),
      supabase.from('social_connections').select('*').order('updated_at',{ascending:false}),
      supabase.from('tiktok_connections').select('id,username,nickname,status,can_direct_post,audited,avatar_url,updated_at').order('updated_at',{ascending:false}).limit(5)
    ]);
    setCampaigns(c||[]);setPosts(p||[]);setConnections(a||[]);setTTConnections(t||[]);
    const base=process.env.NEXT_PUBLIC_SUPABASE_URL;if(base){
      try{const r=await fetch(`${base}/functions/v1/meta-oauth/health`,{cache:'no-store'});setMetaHealth(await r.json())}catch{setMetaHealth({configured:false})}
      try{const r=await fetch(`${base}/functions/v1/buffer-sync/health`,{cache:'no-store'});setBufferHealth(await r.json())}catch{setBufferHealth({configured:false})}
    }
  }
  const current=campaigns[0];
  const visible=useMemo(()=>posts.filter(p=>(platform==='all'||p.platform===platform)&&(!current||p.campaign_id===current.id)),[posts,platform,current]);
  const k=useMemo(()=>({total:posts.length,draft:posts.filter(x=>!['scheduled','published'].includes(x.status)).length,scheduled:posts.filter(x=>x.status==='scheduled').length,published:posts.filter(x=>x.status==='published').length,approved:posts.filter(x=>x.approval_status==='approved').length}),[posts]);
  const calendar=useMemo(()=>{const m={};for(const p of posts.filter(x=>x.scheduled_at)){const d=new Date(p.scheduled_at).toLocaleDateString('el-GR',{weekday:'short',day:'2-digit',month:'short'});(m[d]??=[]).push(p)}return m},[posts]);
  function togglePlatform(x){setForm(f=>({...f,platforms:f.platforms.includes(x)?f.platforms.filter(p=>p!==x):[...f.platforms,x]}))}
  async function createCampaign(e){e.preventDefault();if(!form.platforms.length)return setMsg('Διάλεξε τουλάχιστον μία πλατφόρμα.');setBusy('create');
    const {data,error}=await supabase.rpc('create_social_campaign',{p_name:`Smart Sales · Top ${form.count}`,p_count:Number(form.count),p_platforms:form.platforms,p_posts_per_day:Number(form.postsPerDay),p_scheduled_from:form.start?new Date(form.start).toISOString():null,p_strategy:'conversion'});
    setMsg(error?error.message:`Created ${data?.created||0} drafts.`);setBusy('');await load();
  }
  async function approvePost(p){setBusy(p.id);const media=p.platform==='tiktok'?p.media_url:(p.media_url||p.source_image_url);const {error}=await supabase.rpc('approve_social_post',{p_post_id:p.id,p_media_url:media||null});setMsg(error?error.message:`Approved ${names[p.platform]} post.`);setBusy('');await load()}
  async function approveFBIG(){if(!current)return;setBusy('bulk');const rows=posts.filter(p=>p.campaign_id===current.id&&['facebook','instagram'].includes(p.platform));for(const p of rows){await supabase.rpc('approve_social_post',{p_post_id:p.id,p_media_url:p.media_url||p.source_image_url})}setMsg(`Approved ${rows.length} Facebook/Instagram posts.`);setBusy('');await load()}
  async function schedule(){if(!current)return;setBusy('schedule');const {data,error}=await supabase.rpc('schedule_social_campaign',{p_campaign_id:current.id});setMsg(error?error.message:`Scheduled ${data?.scheduled||0} posts.`);setBusy('');await load()}
  async function connectTikTok(){const base=process.env.NEXT_PUBLIC_SUPABASE_URL;if(!base)return setMsg('Supabase URL missing');setBusy('tiktok');try{const r=await fetch(`${base}/functions/v1/tiktok-oauth/start?return_to=${encodeURIComponent(window.location.href)}`),d=await r.json();if(!r.ok||!d.authorize_url)throw new Error(d.error||'TikTok OAuth not configured');window.location.href=d.authorize_url}catch(e){setMsg(String(e.message||e));setBusy('')}}
  async function connectMeta(){const base=process.env.NEXT_PUBLIC_SUPABASE_URL;if(!base)return setMsg('Supabase URL missing');setBusy('meta');try{const r=await fetch(`${base}/functions/v1/meta-oauth/start?return_to=${encodeURIComponent(window.location.href)}`),d=await r.json();if(!r.ok||!d.authorize_url)throw new Error(d.error==='meta_oauth_not_configured'?`Meta OAuth needs: ${(d.missing||[]).join(', ')}`:(d.error||'Meta OAuth unavailable'));window.location.href=d.authorize_url}catch(e){setMsg(String(e.message||e));setBusy('')}}
  async function syncBufferAccounts(){const base=process.env.NEXT_PUBLIC_SUPABASE_URL;if(!base)return setMsg('Supabase URL missing');setBusy('buffer');try{const r=await fetch(`${base}/functions/v1/buffer-sync/sync`,{method:'POST',headers:{'content-type':'application/json'}}),d=await r.json();if(!r.ok||!d.ok)throw new Error(d.error==='buffer_not_configured'?'Buffer API key is not configured yet.':(d.error||'Buffer sync failed'));const rows=Array.isArray(d.channels)?d.channels:[];setBufferChannels(rows);try{localStorage.setItem('socialmarket_buffer_channels',JSON.stringify(rows))}catch{}setBufferHealth(h=>({...h,configured:true}));setMsg(`Buffer synced: ${rows.length} Facebook / Instagram / TikTok channel${rows.length===1?'':'s'}.`)}catch(e){setMsg(String(e.message||e))}finally{setBusy('')}}

  return <main className={styles.page}>
    <section className={styles.hero}><div><div className="eyebrow">SOCIALMARKET · PUBLISHING CONTROL</div><h1>Social Scheduler</h1><p>Facebook + Instagram + TikTok σε ένα approval queue, calendar και publishing workspace.</p></div><div className={styles.heroActions}><button onClick={load}>↻ Refresh</button><button className={styles.primary} onClick={()=>setTab('new')}>＋ New campaign</button></div></section>
    {msg?<div className={styles.toast}>{msg}</div>:null}
    <nav className={styles.tabs}>{[['queue','Queue'],['calendar','Calendar'],['accounts','Accounts'],['new','New campaign']].map(([id,label])=><button key={id} className={tab===id?styles.active:''} onClick={()=>setTab(id)}>{label}</button>)}</nav>
    <section className={styles.kpis}><Kpi label="Total drafts" value={k.total} sub={`${k.approved} approved`}/><Kpi label="Needs action" value={k.draft} sub="creative / approval"/><Kpi label="Scheduled" value={k.scheduled} sub="publishing calendar"/><Kpi label="Published" value={k.published} sub="live posts"/></section>

    {tab==='queue'?<>
      <section className={styles.sectionHead}><div><div className="eyebrow">CURRENT CAMPAIGN</div><h2>{current?.name||'No campaign'}</h2><p>{current?`${current.requested_products} products · ${current.posts_per_day}/day · ${dt(current.scheduled_from)}`:'Create a campaign first.'}</p></div><div className={styles.actions}><button onClick={approveFBIG} disabled={!current||busy==='bulk'}>Approve FB + IG</button><button className={styles.primary} onClick={schedule} disabled={!current||busy==='schedule'}>Schedule approved</button></div></section>
      <div className={styles.platformFilters}><button className={platform==='all'?styles.selected:''} onClick={()=>setPlatform('all')}>All {visible.length}</button>{PLATFORMS.map(x=><button key={x} className={platform===x?styles.selected:''} onClick={()=>setPlatform(x)}>{icons[x]} {names[x]} {posts.filter(p=>p.campaign_id===current?.id&&p.platform===x).length}</button>)}</div>
      <section className={styles.grid}>{visible.map(p=><PostCard key={p.id} p={p} busy={busy===p.id} approve={()=>approvePost(p)}/>)}</section>
    </>:null}

    {tab==='calendar'?<section className={styles.calendar}>{Object.keys(calendar).length?Object.entries(calendar).map(([day,items])=><article key={day}><header><b>{day}</b><span>{items.length}</span></header>{items.map(p=><div className={styles.calItem} key={p.id}>{p.media_url||p.source_image_url?<img src={p.media_url||p.source_image_url} alt=""/>:<span/>}<div><b>{p.products?.brand_name||p.title}</b><small>{names[p.platform]} · {new Date(p.scheduled_at).toLocaleTimeString('el-GR',{hour:'2-digit',minute:'2-digit'})}</small></div><i className={cls(p.status)}>{p.status}</i></div>)}</article>):<div className={styles.empty}>Δεν υπάρχουν scheduled posts ακόμη. Approve → Schedule.</div>}</section>:null}

    {tab==='accounts'?<section className={styles.accountGrid}>
      <article className={`${styles.account} ${styles.wide}`}>
        <div className={styles.accountTop}><span className={styles.platformIcon}>B</span><div><small>BUFFER SOCIAL HUB</small><h2>Sync Buffer Accounts</h2></div><i className={cls(bufferHealth?.configured?'connected':'disconnected')}>{bufferHealth?.configured?'API ready':'needs key'}</i></div>
        <p>Connect your social accounts once in Buffer, then sync Facebook, Instagram and TikTok into Socialmarket from one place.</p>
        <div className={styles.actions}><button className={styles.primary} onClick={syncBufferAccounts} disabled={busy==='buffer'||bufferHealth?.configured===false}>{busy==='buffer'?'Syncing…':'↻ Sync Buffer Accounts'}</button><a className={styles.deepLink} href="https://account.buffer.com/channels" target="_blank" rel="noreferrer">Open Buffer Channels →</a></div>
        <div className={styles.rules}>{bufferChannels.length?bufferChannels.map(ch=><span key={ch.id}>{icons[ch.service]||'•'} {names[ch.service]||ch.service} · {ch.displayName||ch.name}{ch.organizationName?` · ${ch.organizationName}`:''}{ch.isDisconnected?' · disconnected':''}{ch.isLocked?' · locked':''}</span>):<span>{bufferHealth?.configured?'Buffer API is ready. Click Sync Buffer Accounts to load connected channels.':'Add BUFFER_API_KEY to Supabase Edge Function secrets, then refresh this page.'}</span>}</div>
      </article>
      <Account platform="facebook" title="Facebook Page" conn={connections.find(x=>x.platform==='facebook')} onConnect={connectMeta} busy={busy==='meta'} configured={metaHealth?.configured}/>
      <Account platform="instagram" title="Instagram Professional" conn={connections.find(x=>x.platform==='instagram')} onConnect={connectMeta} busy={busy==='meta'} configured={metaHealth?.configured}/>
      <article className={styles.account}><div className={styles.accountTop}><span className={styles.platformIcon}>♪</span><div><small>TIKTOK</small><h2>{ttConnections[0]?.nickname||'Not connected'}</h2></div><i className={cls(ttConnections[0]?.status||'disconnected')}>{ttConnections[0]?.status||'disconnected'}</i></div><p>{ttConnections[0]?`@${ttConnections[0].username||'—'} · Direct Post ${ttConnections[0].can_direct_post?'enabled':'not granted'}`:'Connect your TikTok creator/business account.'}</p><button className={styles.primary} onClick={connectTikTok} disabled={busy==='tiktok'}>{ttConnections[0]?'Reconnect TikTok':'Connect TikTok'}</button><Link className={styles.deepLink} href="/tiktok">Open TikTok Studio →</Link></article>
      <article className={`${styles.account} ${styles.wide}`}><h2>Publishing routes</h2><div className={styles.rules}><span>Buffer: preferred unified account gateway for Facebook, Instagram and TikTok while direct platform integrations remain available as fallback.</span><span>Meta OAuth: {metaHealth?.configured?'configured':'needs app credentials / graph version'}.</span><span>TikTok Direct Post: app authorization required; unaudited clients are restricted by TikTok.</span><span>Scheduler never publishes until account connection + approval + media readiness are all green.</span></div></article>
    </section>:null}

    {tab==='new'?<section className={styles.builder}><form onSubmit={createCampaign}><div><div className="eyebrow">CAMPAIGN BUILDER</div><h2>Create from Top Opportunities</h2><p>Automatically selects preferred, market-eligible, non-travel products.</p></div><label>Products<input type="number" min="1" max="1000" value={form.count} onChange={e=>setForm({...form,count:e.target.value})}/></label><label>Posts / day<input type="number" min="1" max="15" value={form.postsPerDay} onChange={e=>setForm({...form,postsPerDay:e.target.value})}/></label><label>Start<input type="datetime-local" value={form.start} onChange={e=>setForm({...form,start:e.target.value})}/></label><div className={styles.platformSelect}>{PLATFORMS.map(x=><button type="button" key={x} className={form.platforms.includes(x)?styles.selected:''} onClick={()=>togglePlatform(x)}>{icons[x]} {names[x]}</button>)}</div><button className={styles.primary} disabled={busy==='create'}>{busy==='create'?'Creating…':'Generate campaign →'}</button></form></section>:null}
  </main>
}

function Kpi({label,value,sub}){return <article><small>{label}</small><strong>{value}</strong><em>{sub}</em></article>}
function PostCard({p,busy,approve}){const x=p.products||{},img=p.media_url||p.source_image_url;return <article className={styles.card}><div className={styles.media}>{img?<img src={img} alt=""/>:<div className={styles.mediaEmpty}>No media</div>}<span className={styles.platformBadge}>{icons[p.platform]} {names[p.platform]}</span>{x.discount_pct?<b>-{Math.round(Number(x.discount_pct))}%</b>:null}</div><div className={styles.cardBody}><small>{x.brand_name||'Product'} · {x.merchant_name||''}</small><h3>{x.product_name||p.title}</h3><div className={styles.price}>{money(x.price)} {x.full_price&&Number(x.full_price)>Number(x.price)?<del>{money(x.full_price)}</del>:null}</div><p>{p.caption}</p><div className={styles.cardFooter}><i className={cls(p.approval_status)}>{p.approval_status}</i><button onClick={approve} disabled={busy||p.approval_status==='approved'}>{p.approval_status==='approved'?'Approved':'Approve'}</button></div></div></article>}
function Account({platform,title,conn,onConnect,busy,configured}){return <article className={styles.account}><div className={styles.accountTop}><span className={styles.platformIcon}>{icons[platform]}</span><div><small>{names[platform].toUpperCase()}</small><h2>{conn?.display_name||title}</h2></div><i className={cls(conn?.status||'disconnected')}>{conn?.status||'disconnected'}</i></div><p>{conn?.username?`@${conn.username}`:configured===false?'Meta adapter installed; credentials still need configuration.':'Connect the Meta Page/Instagram account.'}</p><button className={styles.primary} onClick={onConnect} disabled={busy}>{conn?'Reconnect Meta':`Connect ${names[platform]}`}</button><small className={styles.note}>One Meta authorization can discover both the Facebook Page and linked Instagram professional account.</small></article>}
