'use client';

import Link from 'next/link';
import {useCallback,useEffect,useRef,useState} from 'react';
import {workspace} from '@/lib/workspace-client';
import styles from './CanonicalWorkspace.module.css';

const sections = {
  products: ['Products', 'Τα πραγματικά offers του feed. Η εμπορική επιλεξιμότητα δεν σημαίνει ολοκληρωμένη αξιολόγηση AI.'],
  curation: ['Social Curation', 'Τελικές επιλογές από το canonical product selection. Τα μη αξιολογημένα offers παραμένουν στη σελίδα Products.'],
  creatives: ['Creatives', 'Αποθηκευμένα social briefs, κοινό, κείμενα και αποτελέσματα ελέγχου.'],
  outbox: ['Publishing Control', 'Πραγματικές καταστάσεις παράδοσης στο SocialScheduler. Η δημοσίευση εκτελείται από το SocialScheduler.'],
  analytics: ['Pipeline Analytics', 'Αποθηκευμένες εκτελέσεις, εισαγωγές feed και πραγματική κατάσταση του pipeline.'],
  configuration: ['Product Policies', 'Οι ενεργές πολιτικές προϊόντων στη VMDB. Οι αλλαγές merchant, budget και app settings γίνονται στο Admin Control.'],
  optimization: ['Performance & Optimization', 'Calibration από πραγματικά conversion events. Χωρίς επαρκή δεδομένα δεν παρουσιάζεται ROI ως γεγονός.'],
};
export const number = value => value == null || value === '' ? '—' : Number(value).toLocaleString('el-GR',{maximumFractionDigits:2});
const date = value => value ? new Date(value).toLocaleString('el-GR') : '—';
const safeUrl = value => {try{const u = new URL(value);return ['https:','http:'].includes(u.protocol) ? u.href : null;}catch{return null;}};
const label = value => String(value || '').replaceAll('_',' ');
function Links({row}) {
  const offer = safeUrl(row.tracking_url || row.creative_brief?.tracking_url);
  const post = safeUrl(row.external_permalink);
  return <div className={styles.links}>{offer && <a href={offer} target="_blank" rel="sponsored noopener noreferrer">Προσφορά ↗</a>}{post && <a href={post} target="_blank" rel="noopener noreferrer">Δημοσιευμένο post ↗</a>}</div>;
}
function Item({row,section}) {
  const title = row.product_name || row.title || row.hook || row.stage_key || row.policy_key || row.entity_key || row.id;
  const image = safeUrl(row.image_url || row.media_url || row.creative_brief?.media_url);
  const status = row.status || row.selection_status || row.intelligence_status || row.critic_status;
  const metrics = section === 'products' ? [['Τιμή €',row.price_eur],['Προμήθεια €',row.expected_commission_eur]]
    : section === 'curation' ? [['Score',row.final_score],['Confidence',row.confidence]]
    : section === 'creatives' ? [['Confidence',row.confidence],['Model conversion score',row.predicted_conversion_score]] : [];
  return <article className={styles.item}>
    {image && <img className={styles.image} src={image} alt={title} loading="lazy"/>}
    <div className={styles.itemBody}><div className={styles.rowHead}><h2>{title}</h2>{status && <span className={styles.badge}>{label(status)}</span>}</div>
      <p className={styles.muted}>{row.program_name || row.brand_name || row.audience_key || row.pipeline_key || row.category || row.category_raw || ''}</p>
      {(row.caption || row.pain_statement || row.notes) && <p className={styles.copy}>{row.caption || row.pain_statement || row.notes}</p>}
      <div className={styles.metrics}>{metrics.map(([k,v])=><span key={k}>{k}<b>{number(v)}</b></span>)}</div>
      {section === 'products' && <p className={styles.muted}>Stock: {row.in_stock == null ? 'άγνωστο' : row.in_stock ? 'διαθέσιμο στο feed' : 'μη διαθέσιμο'} · Active: {row.is_active ? 'ναι' : 'όχι'} · Feed: {date(row.last_seen_at)}</p>}
      {section === 'outbox' && <p className={styles.muted}>{row.platform} · Πρόγραμμα: {date(row.scheduled_for)} · Published: {date(row.published_at)}</p>}
      {section === 'outbox' && row.scheduled_for && new Date(row.scheduled_for)<new Date() && !row.published_at && <p className={styles.error}>Η προγραμματισμένη ημερομηνία πέρασε χωρίς επιβεβαίωση δημοσίευσης. Χρειάζεται έλεγχος στο SocialScheduler.</p>}
      {section === 'creatives' && <p>{row.solution_statement}</p>}
      {row.error || row.last_error ? <p role="alert" className={styles.error}>{row.error || row.last_error}</p> : null}
      <Links row={row}/>
      <details><summary>Στοιχεία & τεκμηρίωση</summary><pre>{JSON.stringify(row,null,2)}</pre></details>
    </div>
  </article>;
}
export default function CanonicalWorkspace({section}) {
  const [data,setData]=useState(null),[loading,setLoading]=useState(true),[error,setError]=useState('');
  const [draft,setDraft]=useState(''),[query,setQuery]=useState(''),[offset,setOffset]=useState(0),[status,setStatus]=useState('all');
  const requestId=useRef(0);
  const load=useCallback(async()=>{
    const id=++requestId.current;setLoading(true);setError('');
    try {const next=await workspace(section,{query,offset});if(id===requestId.current)setData(next);}
    catch(e){if(id===requestId.current){setError(e.message);setData(null);}}
    finally{if(id===requestId.current)setLoading(false);}
  },[section,query,offset]);
  useEffect(()=>{void load();return()=>{requestId.current++;}},[load]);
  const rows=data?.rows || [],counts=data?.health?.counts || {};
  const statuses=[...new Set(rows.map(x=>x.status || x.critic_status || x.intelligence_status).filter(Boolean))];
  const visible=rows.filter(x=>(status==='all'||(x.status||x.critic_status||x.intelligence_status)===status)&&(section==='products'||!query||JSON.stringify(x).toLocaleLowerCase('el').includes(query.toLocaleLowerCase('el'))));
  const [title,description]=sections[section];
  const metrics=section==='products' ? [['Feed offers',data?.total],['Τελικές επιλογές',counts.selected_products],['Eligible merchants',counts.eligible_merchants]]
    : section==='outbox' ? [['Outbox jobs',data?.total],['Ανοικτά jobs',counts.publishing_jobs_open],['Approved briefs',counts.approved_social_presentations]]
    : section==='optimization' ? [['Feedback events',data?.feedback_events],['Calibrations',data?.total],['Τελικές επιλογές',counts.selected_products]]
    : [['Εγγραφές',data?.total],['Merchants',counts.active_merchants],['Τελικές επιλογές',counts.selected_products]];
  return <main className={styles.page}>
    <header className={styles.hero}><div><span className={styles.eyebrow}>SOCIALMARKET · CANONICAL VMDB</span><h1>{title}</h1><p>{description}</p></div><button onClick={load} disabled={loading}>↻ Ανανέωση</button></header>
    {error && <div className={styles.error} role="alert">{error}<button onClick={load}>Δοκιμή ξανά</button></div>}
    <section className={styles.kpis}>{metrics.map(([k,v])=><article key={k}><small>{k}</small><strong>{loading?'…':number(v)}</strong></article>)}</section>
    {data?.health?.pipeline_status==='blocked_by_gate' && <aside className={styles.notice}><b>Το AI pipeline χρειάζεται ενέργεια</b><p>{label(data.health.next_action)} · {counts.merchant_program_or_tracking_unverified} merchants με ανεπιβεβαίωτο program/tracking. Δεν έχει παραχθεί τελική επιλογή προϊόντων.</p><Link href="/admin">Admin Control →</Link></aside>}
    <form className={styles.filters} onSubmit={e=>{e.preventDefault();setOffset(0);setQuery(draft.trim());}}>
      <input aria-label="Αναζήτηση εγγραφών" placeholder="Αναζήτηση προϊόντος, merchant ή κειμένου…" value={draft} onChange={e=>setDraft(e.target.value)}/><button type="submit">Αναζήτηση</button>
      <select aria-label="Κατάσταση" value={status} onChange={e=>setStatus(e.target.value)}><option value="all">Όλες οι καταστάσεις</option>{statuses.map(x=><option key={x} value={x}>{label(x)}</option>)}</select>
    </form>
    {section==='configuration' && <div className={styles.notice}><Link href="/admin">Άνοιγμα Admin Control για merchant policies, budgets και app settings →</Link><p>Οι παρακάτω πολιτικές προϊόντων είναι read-only. Δεν συνδέονται με τον παλιό, ανενεργό editor.</p></div>}
    {loading ? <p role="status">Φόρτωση πραγματικών δεδομένων…</p> : data && <>
      {visible.length ? <section className={styles.list}>{visible.map((row,i)=><Item key={row.id || row.policy_key || i} row={row} section={section}/>)}</section>
        : <div className={styles.empty}><h2>{query || status!=='all' ? 'Δεν βρέθηκαν αποτελέσματα' : 'Δεν υπάρχουν ακόμη εγγραφές σε αυτό το στάδιο'}</h2><p>{section==='curation' ? 'Τα offers έχουν εισαχθεί, αλλά το canonical selection παραμένει κενό μέχρι να ολοκληρωθούν οι έλεγχοι.' : section==='optimization' ? 'Δεν έχουν καταγραφεί performance events για αξιόπιστο calibration.' : 'Δοκίμασε άλλη αναζήτηση ή έλεγξε την κατάσταση του pipeline.'}</p><Link href="/products">Προβολή feed προϊόντων →</Link></div>}
      <nav className={styles.pagination} aria-label="Σελιδοποίηση"><button disabled={offset===0} onClick={()=>setOffset(x=>Math.max(0,x-100))}>← Προηγούμενα</button><span>{data.total ? `${offset+1}–${Math.min(offset+100,data.total)} / ${number(data.total)}` : '0 εγγραφές'}</span><button disabled={offset+100>=data.total} onClick={()=>setOffset(x=>x+100)}>Επόμενα →</button></nav>
      {section==='analytics' && <details className={styles.notice}><summary>Ιστορικό εισαγωγών feed</summary><pre>{JSON.stringify(data.feed_runs,null,2)}</pre></details>}
      <footer className={styles.muted}>Ενημέρωση: {date(data.generated_at)} · Οι άγνωστες τιμές εμφανίζονται ως —.</footer>
    </>}
  </main>;
}
