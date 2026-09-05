'use client';

import Link from 'next/link';
import {useEffect,useMemo,useState} from 'react';
import {useParams} from 'next/navigation';
import {supabase} from '@/lib/supabase';
import styles from './solver.module.css';

const arr=v=>Array.isArray(v)?v:[];
const money=v=>Number(v||0).toLocaleString('el-GR',{style:'currency',currency:'EUR',maximumFractionDigits:2});
const score=v=>Math.max(0,Math.min(100,Math.round(Number(v||0))));
const clean=s=>String(s||'').trim();

export default function Solver(){
 const {id}=useParams();
 const [item,setItem]=useState(null),[related,setRelated]=useState([]),[loading,setLoading]=useState(true),[copied,setCopied]=useState(false);
 useEffect(()=>{let alive=true;(async()=>{const {data}=await supabase.from('socialmarket_marketplace200_public_v').select('*').eq('id',decodeURIComponent(String(id))).maybeSingle();if(!alive)return;setItem(data||null);if(data){const {data:r}=await supabase.from('socialmarket_marketplace200_public_v').select('*').eq('niche',data.niche).neq('id',data.id).order('affinity_score',{ascending:false}).limit(3);if(alive)setRelated(r||[])}setLoading(false)})();return()=>{alive=false}},[id]);
 const target=clean(item?.tracking_url);
 const qr=useMemo(()=>target?`https://api.qrserver.com/v1/create-qr-code/?size=360x360&margin=18&data=${encodeURIComponent(target)}`:'',[target]);
 const share=async()=>{const url=location.href,title=item?.product_name||'SocialMarket';if(navigator.share){try{await navigator.share({title,text:item?.solution_statement||'',url});return}catch{}}await navigator.clipboard?.writeText(url);setCopied(true);setTimeout(()=>setCopied(false),1800)};
 if(loading)return <main className={styles.loading}>Χτίζουμε το case…</main>;
 if(!item)return <main className={styles.loading}><h1>Αυτό το case δεν είναι διαθέσιμο.</h1><Link href="/marketplace">← Πίσω στις ανακαλύψεις</Link></main>;

 const evidence=arr(item.social_copy?.quality_evidence||item.quality_evidence).slice(0,4);
 const unknowns=arr(item.social_copy?.quality_unknowns||item.quality_unknowns).slice(0,3);
 const tags=arr(item.semantic_tags).slice(0,6);

 return <main className={styles.page}>
  <nav className={styles.nav}><Link href="/marketplace" className={styles.brand}><span>S</span><b>SocialMarket</b></Link><button onClick={share}>{copied?'Αντιγράφηκε ✓':'Μοιράσου ↗'}</button></nav>

  <header className={styles.hero}>
   <div className={styles.heroVisual}>{item.image_url?<img src={item.image_url} alt={item.product_name}/>:<div className={styles.fallback}>SOLVE<br/>THE GAP</div>}<div className={styles.gradient}/><div className={styles.badge}>CASE SOLVER · {item.subniche||item.niche}</div></div>
   <div className={styles.heroCopy}>
    <div className={styles.path}>{item.niche}<span>→</span>{item.subniche||'λύση'}</div>
    <h1>{item.product_name}</h1>
    <p className={styles.lead}>{item.solution_statement||item.job_to_be_done}</p>
    <div className={styles.heroTags}>{tags.map(t=><span key={t}>{t}</span>)}</div>
    <div className={styles.buyRow}>{Number(item.sale_price_eur)>0&&<div><small>Τρέχουσα ένδειξη τιμής</small><strong>{money(item.sale_price_eur)}</strong></div>}{target&&<a href={target} target="_blank" rel="sponsored noreferrer">Έλεγξε τιμή & διαθεσιμότητα <b>↗</b></a>}</div>
    <p className={styles.micro}>Η τελική τιμή, διαθεσιμότητα, μεταφορικά και όροι επιβεβαιώνονται στον τελικό προορισμό.</p>
   </div>
  </header>

  <section className={styles.story}>
   <article className={styles.pain}><span>01 · THE FRICTION</span><h2>Το πρόβλημα που αξίζει να σταματήσεις να ανέχεσαι.</h2><p>{item.pain_statement}</p></article>
   <article className={styles.gap}><span>02 · THE GAP</span><h2>Γιατί οι συνηθισμένες επιλογές συχνά δεν αρκούν.</h2><p>{item.gap_statement}</p></article>
   <article className={styles.solution}><span>03 · THE FIX</span><h2>Τι αλλάζει αυτή η λύση.</h2><p>{item.solution_statement}</p></article>
  </section>

  <section className={styles.proof}>
   <div className={styles.proofTitle}><small>WHY IT MADE THE CUT</small><h2>Όχι hype. <em>Σήματα που αντέχουν σε έλεγχο.</em></h2><p>Δεν χρησιμοποιούμε ένα score ως «πιστοποίηση». Το case βασίζεται σε συνδυασμό καταλληλότητας, market gap και διαθέσιμων στοιχείων.</p></div>
   <div className={styles.proofGrid}>
    <div><strong>{score(item.semantic_fit_score)}</strong><span>Fit στο πραγματικό use case</span></div>
    <div><strong>{score(item.whitespace_score)}</strong><span>Ένταση του κενού</span></div>
    <div><strong>{score(item.demand_score)}</strong><span>Σήμα ενδιαφέροντος</span></div>
    <div><strong>{score(item.product_quality_score)}</strong><span>Ποιότητα διαθέσιμων στοιχείων</span></div>
   </div>
  </section>

  <section className={styles.fit}>
   <div><small>BEST FOR</small><h2>Για ποιον έχει νόημα;</h2><p>{item.social_copy?.audience||item.job_to_be_done||'Για όσους αναγνωρίζουν το συγκεκριμένο pain και θέλουν πρακτικότερη λύση.'}</p></div>
   <div><small>BEFORE YOU BUY</small><h2>Τι να ελέγξεις.</h2>{unknowns.length?<ul>{unknowns.map((x,i)=><li key={i}>{x}</li>)}</ul>:<p>Διαστάσεις, συμβατότητα, όρους επιστροφής, χρόνο παράδοσης και τελική τιμή στον προορισμό αγοράς.</p>}</div>
  </section>

  <section className={styles.evidence}>
   <div className={styles.evidenceHead}><small>CASE NOTES</small><h2>Τι μας έπεισε να το κρατήσουμε.</h2></div>
   <div className={styles.evidenceCards}>{evidence.length?evidence.map((x,i)=><article key={i}><b>0{i+1}</b><p>{typeof x==='string'?x:JSON.stringify(x)}</p></article>):<><article><b>01</b><p>Σαφής σύνδεση ανάμεσα στο προϊόν και στο pain/use case.</p></article><article><b>02</b><p>Το case πέρασε ανεξάρτητο quality/relevance έλεγχο πριν δημοσιευτεί.</p></article></>}</div>
  </section>

  <section className={styles.action}>
   <div className={styles.actionCopy}><small>READY TO CHECK IT?</small><h2>Μην αγοράζεις από περιέργεια.<br/><em>Αγόρασε μόνο αν λύνει το δικό σου πρόβλημα.</em></h2><p>Άνοιξε τον τελικό προορισμό, επιβεβαίωσε τιμή, παραλλαγή και όρους και αποφάσισε με τα πραγματικά δεδομένα μπροστά σου.</p>{target&&<a href={target} target="_blank" rel="sponsored noreferrer">Έλεγξε τη σημερινή προσφορά ↗</a>}</div>
   {qr&&<div className={styles.qr}><img src={qr} alt="QR code για τον εμπορικό προορισμό"/><b>Σκάναρέ το από άλλη συσκευή</b><span>Ο κωδικός οδηγεί στον ίδιο εξωτερικό προορισμό με το CTA.</span></div>}
  </section>

  {related.length>0&&<section className={styles.related}><div><small>KEEP EXPLORING</small><h2>Παρόμοια pains. Διαφορετικές λύσεις.</h2></div><div className={styles.relatedGrid}>{related.map(x=><Link key={x.id} href={`/marketplace/${encodeURIComponent(String(x.id))}`}><div>{x.image_url&&<img src={x.image_url} alt=""/>}</div><span>{x.subniche||x.niche}</span><h3>{x.product_name}</h3><p>{x.solution_statement}</p></Link>)}</div></section>}

  <div className={styles.sticky}>{Number(item.sale_price_eur)>0&&<div><small>ένδειξη τιμής</small><b>{money(item.sale_price_eur)}</b></div>}{target?<a href={target} target="_blank" rel="sponsored noreferrer">Δες διαθεσιμότητα ↗</a>:<Link href="/marketplace">Πίσω στο SocialMarket</Link>}</div>
  <footer className={styles.footer}><Link href="/marketplace">← SocialMarket</Link><p>Ορισμένοι εξωτερικοί σύνδεσμοι μπορεί να αποφέρουν αμοιβή στο SocialMarket χωρίς επιπλέον χρέωση για εσένα.</p></footer>
 </main>
}
