'use client';

import Link from 'next/link';
import {useEffect,useMemo,useState} from 'react';
import {useParams} from 'next/navigation';
import {supabase} from '@/lib/supabase';
import AffinityCommerceModal from '@/components/affinity/AffinityCommerceModal';
import styles from './solver.module.css';

const arr=v=>Array.isArray(v)?v:[];
const money=v=>Number(v||0).toLocaleString('el-GR',{style:'currency',currency:'EUR',maximumFractionDigits:2});
const clean=v=>String(v||'').trim();
const score=v=>Math.max(0,Math.min(100,Math.round(Number(v||0))));
const signal=(v,strong,good)=>score(v)>=85?strong:score(v)>=72?good:'Check fit';

export default function Solver(){
 const {id}=useParams();
 const [item,setItem]=useState(null),[related,setRelated]=useState([]),[loading,setLoading]=useState(true),[offerOpen,setOfferOpen]=useState(false),[copied,setCopied]=useState(false);
 useEffect(()=>{let alive=true;(async()=>{const {data}=await supabase.from('socialmarket_marketplace200_public_v').select('*').eq('id',decodeURIComponent(String(id))).maybeSingle();if(!alive)return;setItem(data||null);if(data){const {data:r}=await supabase.from('socialmarket_marketplace200_public_v').select('*').eq('niche',data.niche).neq('id',data.id).order('affinity_score',{ascending:false}).limit(3);if(alive)setRelated(r||[])}setLoading(false)})();return()=>{alive=false}},[id]);
 const social=item?.social_copy&&typeof item.social_copy==='object'?item.social_copy:{};
 const images=useMemo(()=>[...new Set([...arr(social.creative_images),...arr(item?.creative_images),item?.image_url].filter(Boolean))].slice(0,4),[item,social]);
 const target=clean(item?.tracking_url);
 const qr=target?`https://api.qrserver.com/v1/create-qr-code/?size=420x420&margin=18&data=${encodeURIComponent(target)}`:'';
 const share=async()=>{const url=location.href;if(navigator.share){try{await navigator.share({title:item.product_name,text:item.solution_statement||'',url});return}catch{}}await navigator.clipboard?.writeText(url);setCopied(true);setTimeout(()=>setCopied(false),1500)};
 if(loading)return <main className={styles.loading}>AFFINITY is building the case…</main>;
 if(!item)return <main className={styles.loading}><h1>Αυτό το AFFINITY case δεν είναι διαθέσιμο.</h1><Link href="/marketplace">← Back to shop</Link></main>;

 const hook=clean(social.hook)||item.solution_statement||'Μια πιο έξυπνη λύση για ένα πραγματικό καθημερινό pain.';
 const audience=clean(social.audience)||item.job_to_be_done||'Για όσους θέλουν λιγότερη τριβή στην καθημερινότητά τους.';
 const urgency=clean(social.urgency_angle)||'Η τιμή, η διαθεσιμότητα και οι όροι μπορεί να αλλάξουν στον τελικό προορισμό. Αν το fit είναι σωστό, έλεγξε τι ισχύει σήμερα.';
 const unknowns=arr(social.quality_unknowns||item.quality_unknowns).slice(0,4);
 const objections=arr(social.objections).slice(0,4);
 const evidence=arr(social.quality_evidence||item.quality_evidence).slice(0,4);
 const tags=arr(item.semantic_tags).slice(0,5);
 const faqs=[
  ['Ταιριάζει σε εμένα;',audience],
  ['Τι πρέπει να ελέγξω πριν αγοράσω;',unknowns.length?unknowns.join(' · '):'Διαστάσεις, συμβατότητα, παραλλαγή, χρόνο παράδοσης, επιστροφές και τελική τιμή.'],
  ['Γιατί το AFFINITY το κράτησε;',item.solution_statement||'Γιατί υπάρχει σαφής σύνδεση ανάμεσα στο pain, το use case και τη λύση.'],
  ['Η τιμή είναι εγγυημένη;', 'Όχι. Η τιμή που βλέπεις εδώ είναι ένδειξη. Η τελική τιμή και διαθεσιμότητα επιβεβαιώνονται στον τελικό προορισμό.']
 ];

 return <main className={styles.page}>
  <div className={styles.topBar}>AFFINITY · SMALL SOLUTIONS. A BETTER YOU.</div>
  <nav className={styles.nav}>
   <Link href="/marketplace" className={styles.brand}><b>AFFINITY</b><span>Shop better everyday</span></Link>
   <div className={styles.navActions}><button onClick={share}>{copied?'Copied ✓':'Share ↗'}</button><button onClick={()=>setOfferOpen(true)}>View Offer ↗</button></div>
  </nav>

  <header className={styles.hero}>
   <div className={styles.heroVisual}>{images[0]?<img src={images[0]} alt={item.product_name}/>:<div className={styles.fallback}>A<br/>BETTER<br/>EVERYDAY</div>}<div className={styles.heroShade}/><span className={styles.badge}>CURATED SOLUTION</span></div>
   <div className={styles.heroCopy}>
    <small>{item.niche}{item.subniche?` · ${item.subniche}`:''}</small>
    <h1>{item.product_name}</h1>
    <p className={styles.lead}>{hook}</p>
    <div className={styles.tags}>{tags.map(t=><span key={t}>{t}</span>)}</div>
    <div className={styles.proofPills}><span>✓ {signal(item.semantic_fit_score,'Strong use-case fit','Good use-case fit')}</span><span>✦ {signal(item.whitespace_score,'Distinct market gap','Useful market gap')}</span><span>◇ {signal(item.product_quality_score,'Strong evidence','Enough evidence')}</span></div>
    <div className={styles.buyRow}>{Number(item.sale_price_eur)>0&&<div><small>price indication</small><strong>{money(item.sale_price_eur)}</strong></div>}<button onClick={()=>setOfferOpen(true)}>Δες την προσφορά <b>↗</b></button></div>
    <p className={styles.micro}>Τελική τιμή, διαθεσιμότητα, συμβατότητα, μεταφορικά και όροι επιβεβαιώνονται στον τελικό προορισμό.</p>
   </div>
  </header>

  <section className={styles.benefits}>
   <article><span>01</span><b>THE PAIN</b><h2>Τι σε δυσκολεύει.</h2><p>{item.pain_statement}</p></article>
   <article><span>02</span><b>THE GAP</b><h2>Τι λείπει σήμερα.</h2><p>{item.gap_statement}</p></article>
   <article><span>03</span><b>THE SOLUTION</b><h2>Τι αλλάζει στην πράξη.</h2><p>{item.solution_statement}</p></article>
  </section>

  <section className={styles.editorial}>
   <div className={styles.editorialCopy}><small>SEE THE OUTCOME</small><h2>Don’t buy the object.<br/><em>Buy the better outcome.</em></h2><p>{item.job_to_be_done}</p><button onClick={()=>setOfferOpen(true)}>Check today’s offer →</button></div>
   <div className={styles.gallery}>{[0,1,2].map((n)=><figure key={n}>{images[n]||images[0]?<img src={images[n]||images[0]} alt={`${item.product_name} visual ${n+1}`}/>:null}<figcaption>{['THE PRODUCT','THE DETAIL','THE USE CASE'][n]}</figcaption></figure>)}</div>
  </section>

  <section className={styles.whyNow}>
   <div><small>WHY NOW</small><h2>Αν λύνει δικό σου pain, <em>έλεγξε τι ισχύει σήμερα.</em></h2></div><p>{urgency}</p><button onClick={()=>setOfferOpen(true)}>Open offer ↗</button>
  </section>

  <section className={styles.proofSection}>
   <div><small>WHY IT MADE THE CUT</small><h2>Evidence before hype.</h2><p>Τα internal scores δεν είναι διαφήμιση. Τα χρησιμοποιούμε για να ξεχωρίζουμε ποια cases αξίζουν πραγματικά να παρουσιαστούν.</p></div>
   <div className={styles.proofGrid}><article><b>USE CASE</b><strong>{signal(item.semantic_fit_score,'Strong','Good')}</strong><p>Fit με το συγκεκριμένο job-to-be-done.</p></article><article><b>MARKET GAP</b><strong>{signal(item.whitespace_score,'Distinct','Useful')}</strong><p>Υπάρχει λόγος να ψάξεις πέρα από τις προφανείς επιλογές.</p></article><article><b>INTEREST</b><strong>{signal(item.demand_score,'High','Positive')}</strong><p>Το pain έχει αρκετό ενδιαφέρον για να αξίζει curation.</p></article><article><b>EVIDENCE</b><strong>{signal(item.product_quality_score,'Strong','Enough')}</strong><p>Υπάρχουν αρκετά στοιχεία για υπεύθυνη παρουσίαση.</p></article></div>
  </section>

  <section className={styles.fit}>
   <div><small>BEST FOR</small><h2>Για ποιον έχει νόημα;</h2><p>{audience}</p></div>
   <div><small>BEFORE YOU BUY</small><h2>Τι να ελέγξεις.</h2>{unknowns.length?<ul>{unknowns.map((x,i)=><li key={i}>{x}</li>)}</ul>:<p>Διαστάσεις, συμβατότητα, variant, returns, shipping και τελική τιμή.</p>}</div>
  </section>

  <section className={styles.objections}><div><small>OBJECTION CHECK</small><h2>Μην το αγοράσεις επειδή απλώς φαίνεται ωραίο.</h2></div><div className={styles.objectionGrid}>{(objections.length?objections:['Το pain είναι πραγματικό για εσένα;','Ταιριάζει στις διαστάσεις ή στη συμβατότητα που χρειάζεσαι;','Η τελική τιμή εξακολουθεί να έχει νόημα μετά τα μεταφορικά;','Οι όροι επιστροφής σε καλύπτουν;']).map((x,i)=><article key={i}><b>0{i+1}</b><p>{typeof x==='string'?x:x?.objection||JSON.stringify(x)}</p></article>)}</div></section>

  <section className={styles.faq}><div><small>FAQ</small><h2>Questions before checkout.</h2></div><div>{faqs.map(([q,a])=><details key={q}><summary>{q}<span>+</span></summary><p>{a}</p></details>)}</div></section>

  <section className={styles.offerSection}>
   <div><small>SHOP THE SOLUTION</small><h2>One last check.<br/><em>Does it fit your life?</em></h2><p>{evidence.length?evidence.map(x=>typeof x==='string'?x:JSON.stringify(x)).join(' · '):'Το case πέρασε relevance και evidence checks πριν γίνει δημόσιο.'}</p><div className={styles.offerButtons}><button onClick={()=>setOfferOpen(true)}>Δες την προσφορά →</button><button onClick={share}>Share this find ↗</button></div></div>
   {qr&&<div className={styles.qr}><img src={qr} alt="QR προς την ενεργή προσφορά"/><b>SCAN & SHOP</b><span>QR → ενεργό affiliate tracking URL</span></div>}
  </section>

  {related.length>0&&<section className={styles.related}><small>YOU MAY ALSO LIKE</small><h2>More useful finds.</h2><div>{related.map(x=><Link key={x.id} href={`/marketplace/${encodeURIComponent(String(x.id))}`}><div>{x.image_url&&<img src={x.image_url} alt={x.product_name}/>}</div><span>{x.subniche||x.niche}</span><h3>{x.product_name}</h3><p>{x.solution_statement}</p></Link>)}</div></section>}

  <footer className={styles.footer}><Link href="/marketplace">AFFINITY</Link><p>Ορισμένοι εξωτερικοί σύνδεσμοι είναι affiliate links. Μπορεί να υποστηρίζουν το AFFINITY χωρίς επιπλέον κόστος για εσένα.</p></footer>
  <button className={styles.sticky} onClick={()=>setOfferOpen(true)}><span>{Number(item.sale_price_eur)>0?money(item.sale_price_eur):'Check today'}</span><b>View Offer ↗</b></button>
  <AffinityCommerceModal item={item} open={offerOpen} onClose={()=>setOfferOpen(false)} landingUrl={typeof window!=='undefined'?window.location.href:undefined}/>
 </main>
}
