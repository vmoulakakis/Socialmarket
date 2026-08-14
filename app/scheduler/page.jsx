'use client';

import { useEffect, useMemo, useState } from 'react';
import { supabase } from '@/lib/supabase';
import styles from './scheduler.module.css';

const PLATFORMS = ['facebook', 'instagram', 'tiktok', 'linkedin'];
const names = { facebook: 'Facebook', instagram: 'Instagram', tiktok: 'TikTok', linkedin: 'LinkedIn' };

function dt(v) {
  return v ? new Date(v).toLocaleString('el-GR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : '—';
}

function statusClass(s) {
  return `${styles.status} ${['published', 'scheduled', 'completed', 'approved'].includes(s) ? styles.good : ['failed', 'blocked', 'error'].includes(s) ? styles.bad : styles.warn}`;
}

export default function PublishingControl() {
  const [outbox, setOutbox] = useState([]);
  const [content, setContent] = useState([]);
  const [platform, setPlatform] = useState('all');
  const [tab, setTab] = useState('outbox');
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');

  useEffect(() => { load(); }, []);

  async function load() {
    setLoading(true);
    setMessage('');
    const [{ data: o, error: oe }, { data: c, error: ce }] = await Promise.all([
      supabase.from('socialmarket_publishing_outbox').select('*').order('created_at', { ascending: false }).limit(500),
      supabase.from('socialmarket_content_items').select('*').order('created_at', { ascending: false }).limit(500)
    ]);
    if (oe || ce) setMessage(oe?.message || ce?.message || 'Failed to load publishing data.');
    setOutbox(o || []);
    setContent(c || []);
    setLoading(false);
  }

  const visible = useMemo(() => outbox.filter(x => platform === 'all' || x.platform === platform), [outbox, platform]);
  const kpis = useMemo(() => ({
    content: content.length,
    queued: outbox.filter(x => ['queued', 'ready', 'pending'].includes(x.status)).length,
    scheduled: outbox.filter(x => x.status === 'scheduled').length,
    published: outbox.filter(x => x.status === 'published').length,
    failed: outbox.filter(x => ['failed', 'blocked', 'error'].includes(x.status)).length
  }), [outbox, content]);

  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <div>
          <div className="eyebrow">SOCIALMARKET AI · SOURCE OF TRUTH</div>
          <h1>Publishing Control</h1>
          <p>SocialMarket δημιουργεί, εγκρίνει και παραδίδει immutable publishing intent. Η εκτέλεση ανήκει αποκλειστικά στο SocialScheduler.</p>
        </div>
        <div className={styles.heroActions}><button onClick={load} disabled={loading}>↻ Refresh</button></div>
      </section>

      {message ? <div className={styles.toast}>{message}</div> : null}

      <section className={styles.kpis}>
        <Kpi label="Canonical content" value={kpis.content} sub="SocialMarket owned" />
        <Kpi label="Waiting execution" value={kpis.queued} sub="outbox jobs" />
        <Kpi label="Scheduled" value={kpis.scheduled} sub="executor state" />
        <Kpi label="Published" value={kpis.published} sub={`${kpis.failed} failed / blocked`} />
      </section>

      <section className={styles.sectionHead}>
        <div>
          <div className="eyebrow">OWNERSHIP BOUNDARY</div>
          <h2>Research → Decide → Create → Approve → Outbox</h2>
          <p>Το SocialMarket δεν συνδέει Buffer/Meta/TikTok accounts και δεν κάνει publish/retry. Ο SocialScheduler βλέπει την ίδια Supabase και εκτελεί μόνο τα approved outbox jobs.</p>
        </div>
      </section>

      <nav className={styles.tabs}>
        <button className={tab === 'outbox' ? styles.active : ''} onClick={() => setTab('outbox')}>Publishing Outbox</button>
        <button className={tab === 'content' ? styles.active : ''} onClick={() => setTab('content')}>Canonical Content</button>
      </nav>

      {tab === 'outbox' ? <>
        <div className={styles.platformFilters}>
          <button className={platform === 'all' ? styles.selected : ''} onClick={() => setPlatform('all')}>All {outbox.length}</button>
          {PLATFORMS.map(p => <button key={p} className={platform === p ? styles.selected : ''} onClick={() => setPlatform(p)}>{names[p]} {outbox.filter(x => x.platform === p).length}</button>)}
        </div>
        <section className={styles.grid}>
          {visible.length ? visible.map(job => <OutboxCard key={job.id} job={job} />) : <div className={styles.empty}>{loading ? 'Loading…' : 'No publishing jobs yet.'}</div>}
        </section>
      </> : null}

      {tab === 'content' ? <section className={styles.grid}>
        {content.length ? content.map(item => <ContentCard key={item.id} item={item} />) : <div className={styles.empty}>{loading ? 'Loading…' : 'No canonical content yet.'}</div>}
      </section> : null}
    </main>
  );
}

function Kpi({ label, value, sub }) {
  return <article><small>{label}</small><strong>{value}</strong><em>{sub}</em></article>;
}

function OutboxCard({ job }) {
  const image = job.media_url;
  return <article className={styles.card}>
    <div className={styles.media}>{image ? <img src={image} alt="" /> : <div className={styles.mediaEmpty}>No media</div>}<span className={styles.platformBadge}>{names[job.platform] || job.platform}</span></div>
    <div className={styles.cardBody}>
      <small>{job.brand_name || job.brand_slug || 'Brand'} · {dt(job.created_at)}</small>
      <h3>{job.title || 'Publishing job'}</h3>
      <p>{job.caption || 'No caption'}</p>
      <div className={styles.cardFoot}><i className={statusClass(job.status)}>{job.status}</i><span>{dt(job.scheduled_for)}</span></div>
      {job.last_error ? <small>{job.last_error}</small> : null}
      {job.external_permalink ? <a href={job.external_permalink} target="_blank" rel="noreferrer">Published post →</a> : null}
    </div>
  </article>;
}

function ContentCard({ item }) {
  return <article className={styles.card}>
    <div className={styles.cardBody}>
      <small>{item.brand_name || item.brand_slug || 'Brand'} · {item.source_key || 'content'}</small>
      <h3>{item.title}</h3>
      <p>{item.angle || item.core_copy || 'No content body'}</p>
      <div className={styles.cardFoot}><i className={statusClass(item.status)}>{item.status}</i><span>{item.approved_at ? `Approved ${dt(item.approved_at)}` : `Created ${dt(item.created_at)}`}</span></div>
      {item.tracking_url ? <a href={item.tracking_url} target="_blank" rel="noreferrer">Tracking URL →</a> : null}
    </div>
  </article>;
}
