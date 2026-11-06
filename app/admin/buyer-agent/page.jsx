'use client';
import {useState} from 'react';
import Link from 'next/link';
import {supabase} from '@/lib/supabase';
import styles from './lab.module.css';

const euro=value=>Number(value).toLocaleString('el-GR',{style:'currency',currency:'EUR'});
const reasons={
 live_stock:'Δεν υπάρχει επιβεβαίωση διαθεσιμότητας',validity_window:'Δεν υπάρχει καταγεγραμμένο όριο ισχύος',
 freshness:'Η πηγή δεν είναι αρκετά πρόσφατη',skeptic_evidence:'Απουσιάζει ανεξάρτητο evidence audit',
};

export default function BuyerAgentLab(){
 const [query,setQuery]=useState('Γωνιακός καναπές για μικρό σπίτι');
 const [budget,setBudget]=useState('');
 const [result,setResult]=useState(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 async function run(useModel=false){
  if(busy)return;
  setBusy(true);setError('');
  try{
   const {data:{session}}=await supabase.auth.getSession();
   if(!session?.access_token)throw Error('Απαιτείται σύνδεση διαχειριστή.');
   const response=await fetch('/api/admin/buyer-agent',{
    method:'POST',headers:{'content-type':'application/json',authorization:'Bearer '+session.access_token},
    cache:'no-store',body:JSON.stringify({query,budget:budget?Number(budget):null,run_model:useModel})
   });
   const data=await response.json();
   if(!response.ok)throw Error(data.detail||data.error||'Πρόβλημα επικοινωνίας.');
   setResult(data);
  }catch(e){setError(e.message||'Αποτυχία ελέγχου.');}
  finally{setBusy(false);}
 }
 const items=result?.verified?.length?result.verified:result?.candidates||[];
 const insights=new Map((result?.research||[]).map(r=>[r.id,r]));
 const audits=new Map((result?.critic||[]).map(r=>[r.id,r]));
 return <main className={styles.wrap}>
  <header className={styles.hero}><div><span className={styles.eyebrow}>MYAGENTICTEAM / SOCIALMARKET</span>
   <h1>Buyer Agent Laboratory</h1>
   <p>Δοκιμή του πραγματικού decision pipeline: ανάγκη → προϊόντα → affiliate έλεγχος → Product Fit → ανεξάρτητος Skeptic. Καμία αυτόματη δημοσίευση.</p></div>
   <Link href="/marketplace/advisor" className={styles.public}>Άνοιγμα δημόσιου Advisor ↗</Link>
  </header>
  <section className={styles.panel} aria-label="Αίτημα ανάλυσης">
   <form onSubmit={e=>{e.preventDefault();void run(false);}} className={styles.form}>
    <label>Ανάγκη αγοραστή<input type="search" required minLength={3} maxLength={180} value={query} onChange={e=>setQuery(e.target.value)} placeholder="Περιέγραψε ανάγκη ή προϊόν"/></label>
    <label>Προϋπολογισμός (€)<input type="number" min="1" max="100000" step="1" value={budget} onChange={e=>setBudget(e.target.value)} placeholder="Χωρίς όριο"/></label>
    <div className={styles.actions}>
     <button type="submit" disabled={busy||query.trim().length<3}>{busy?'Έλεγχος…':'1. Έλεγχος προϊόντων'}</button>
     <button type="button" onClick={()=>run(true)} disabled={busy||query.trim().length<3||result?.model_enabled===false}>
      2. Product Fit + Skeptic
     </button>
    </div>
   </form>
   <p className={styles.hint}>Οι κλήσεις LLM εκτελούνται μόνο μετά από ενεργοποίηση του owner cost gate και χρησιμοποιούν τους υπάρχοντες περιορισμούς AI budget.</p>
  </section>
  {error&&<div className={styles.error} role="alert">{error}</div>}
  {result&&<div aria-live="polite" className={styles.outcomes}>
   <section className={styles.status}>
    <span>ΚΑΤΑΣΤΑΣΗ ΕΚΤΕΛΕΣΗΣ</span><h2>{result.crew_status||result.status}</h2>
    <p>{result.diagnostic}</p>
    <div className={styles.facts}>
     <span><strong>{result.searched??0}</strong> εγγραφές εξετάστηκαν</span>
     <span><strong>{result.verified?.length??0}</strong> επαληθευμένες</span>
     <span><strong>{result.candidates?.length??0}</strong> ερευνητικές αντιστοιχίσεις</span>
     <span><strong>{result.ai_model_executed?'Ναι':'Όχι'}</strong> εκτελέστηκε μοντέλο</span>
    </div>
    {!result.model_enabled&&<p className={styles.disabled}>Η live AI λειτουργία είναι κλειδωμένη από την πολιτική κόστους. Οι υπάρχοντες έλεγχοι είναι λειτουργικοί· δεν δημιουργούνται πλασματικά AI αποτελέσματα.</p>}
   </section>
   {items.length? <section className={styles.cards} aria-label="Ερευνητικές αντιστοιχίσεις">
    {items.map(p=><article className={styles.card} key={p.id}>
     <div className={styles.cardTop}><strong>{p.title}</strong><span>{euro(p.price_eur)}</span></div>
     <p>{p.merchant} · {p.category||'Χωρίς κατηγορία'}</p>
     <span className={styles.tag}>{p.verification==='VERIFIED'?'Source verified':'Needs evidence'}</span>
     {p.missing_checks?.length>0&&<ul>{p.missing_checks.map(check=><li key={check}>{reasons[check]||check}</li>)}</ul>}
     {insights.has(p.id)&&<div className={styles.insight}><strong>Product Fit (μοντελοποιημένη υπόθεση)</strong><p>{insights.get(p.id).reason}</p></div>}
     {audits.has(p.id)&&<div className={styles.insight}><strong>Skeptic: {audits.get(p.id).final_verdict}</strong><p>{audits.get(p.id).critic_reason}</p></div>}
     <a href={p.tracking_url} target="_blank" rel="sponsored noopener noreferrer">Έλεγχος αρχικής προσφοράς ↗</a>
    </article>)}
   </section>:<div className={styles.panel}>Δεν βρέθηκαν υποψήφια προϊόντα στη διαθέσιμη συλλογή. Δεν θα δημιουργηθούν τεχνητές εγγραφές.</div>}
  </div>}
  <footer className={styles.footer}>Εσωτερική λειτουργία δοκιμών · Καμία έγκριση αποστολής, δημοσίευσης ή αγοράς · Το Source Truth υπερισχύει κάθε μοντέλου.</footer>
 </main>;
}
