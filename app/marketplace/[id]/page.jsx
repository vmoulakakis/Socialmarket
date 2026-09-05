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
const uniq=a=>[...new Set(a.filter(Boolean))];

function signal(value,strong='Ισχυρό σήμα',medium='Θετικό σήμα'){
 const n=score(value);return n>=85?strong:n>=72?medium:'Υπό έλεγχο';
}

export default function Solver(){
 const {id}=useParams();
 const [item,setItem]=useState(null),[related,setRelated]=useState([]),[loading,setLoading]=useState(true),[copied,setCopied]=useState(false);
 useEffect(()=>{let alive=true;(async()=>{const {data}=await supabase.from('socialmarket_marketplace200_public_v').select('*').eq('id',decodeURIComponent(String(id))).maybeSingle();if(!alive)return;setItem(data||null);if(data){const {data:r}=await supabase.from('socialmarket_marketplace200_public_v').select('*').eq('niche',data.niche).neq('id',data.id).order('affinity_score',{ascending:false}).limit(3);if(alive)setRelated(r||[])}setLoading(false)})();return()=>{alive=false}},[id]);
 const target=clean(item?.tracking_url);
 const qr=useMemo(()=>target?`https://api.qrserver.com/v1/create-qr-code/?size=420x420&margin=18&data=${encodeURIComponent(target)}`:'',[target]);
 const social=item?.social_copy&&typeof item.social_copy==='object'?item.social_copy:{};
 const creativeImages=useMemo(()=>uniq([...arr(social.creative_images),...arr(item?.creative_images),item?.image_url]).slice(0,4),[item,social]);
 const share=async()=>{const url=location.href,title=item?.product_name||'SocialMarket';if(navigator.share){try{await navigator.share({title,text:item?.solution_statement||'',url});return}catch{}}await navigator.clipboard?.writeText(url);setCopied(true);setTimeout(()=>setCopied(false),1800)};
 const shareWhatsApp=()=>{const txt=encodeURIComponent(`${item?.product_name||'SocialMarket'} — ${item?.solution_statement||''}\n${location.href}`);window.open(`https://wa.me/?text=${txt}`,'_blank','noopener,noreferrer')};
 if(loading)return <main className={styles.loading}>Χτίζουμε το case…</main>;
 if(!item)return <main className={styles.loading}><h1>Αυτό το case δεν είναι διαθέσιμο.</h1><Link href="/marketplace">← Πίσω στις ανακαλύψεις</Link></main>;

 const evidence=arr(social.quality_evidence||item.quality_evidence).slice(0,4);
 const unknowns=arr(social.quality_unknowns||item.quality_unknowns).slice(0,4);
 const tags=arr(item.semantic_tags).slice(0,6);
 const objections=arr(social.objections).slice(0,4);
 const whyNow=clean(social.urgency_angle)||'Η τιμή, η διαθεσιμότητα και οι παραλλαγές μπορεί να αλλάξουν στον τελικό προορισμό. Αν το use case είναι δικό σου, έλεγξέ τα πριν αποφασίσεις.';
 const audience=clean(social.audience)||item.job_to_be_done||'Για όσους αναγνωρίζουν αυτό το pain και θέλουν μια πιο πρακτική λύση.';
 const hook=clean(social.hook)||item.solution_statement||'Ένα μικρό fix που μπορεί να αφαιρέσει καθημερινή τριβή.';

 return <main className={styles.page}>
  <nav className={styles.nav}><Link href="/marketplace" className={styles.brand}><span>S</span><b>SocialMarket</b></Link><div className={styles.navActions}><button onClick={shareWhatsApp}>WhatsApp</button><button onClick={share}>{copied?'Αντιγράφηκε ✓':'Μοιράσου ↗'}</button></div></nav>
  <div className={styles.liveStrip}><span>FRESH CASE</span><p>Από pain → gap → solution. Έλεγξε τα σημερινά δεδομένα πριν αγοράσεις.</p></div>

  <header className={styles.hero}>
   <div className={styles.heroVisual}>{creativeImages[0]?<img src={creativeImages[0]} alt={item.product_name}/>:<div className={styles.fallback}>SOLVE<br/>THE GAP</div>}<div className={styles.gradient}/><div className={styles.badge}>CASE SOLVER · {item.subniche||item.niche}</div><div className={styles.heroStamp}>WORTH<br/>A LOOK</div></div>
   <div className={styles.heroCopy}>
    <div className={styles.path}>{item.niche}<span>→</span>{item.subniche||'solution'}</div>
    <h1>{item.product_name}</h1>
    <p className={styles.lead}>{hook}</p>
    <div className={styles.heroTags}>{tags.map(t=><span key={t}>{t}</span>)}</div>
    <div className={styles.fastProof}><span>✓ {signal(item.semantic_fit_score,'Πολύ δυνατό use-case fit','Δυνατό use-case fit')}</span><span>✦ {signal(item.whitespace_score,'Μεγάλο κενό','Υπαρκτό κενό')}</span><span>◉ {signal(item.product_quality_score,'Ισχυρά στοιχεία','Επαρκή στοιχεία')}</span></div>
    <div className={styles.buyRow}>{Number(item.sale_price_eur)>0&&<div><small>ένδειξη τιμής</small><strong>{money(item.sale_price_eur)}</strong></div>}{target&&<a href={target} target="_blank" rel="sponsored noreferrer">Δες αν σε συμφέρει σήμερα <b>↗</b></a>}</div>
    <p className={styles.micro}>Η τελική τιμή, διαθεσιμότητα, μεταφορικά, συμβατότητα και όροι επιβεβαιώνονται στον τελικό προορισμό.</p>
   </div>
  </header>

  <section className={styles.story}>
   <article className={styles.pain}><span>THE FRICTION</span><h2>Το πρόβλημα που τρώει χρόνο ή ενέργεια.</h2><p>{item.pain_statement}</p></article>
   <article className={styles.gap}><span>THE GAP</span><h2>Γιατί το συνηθισμένο workaround δεν είναι αρκετό.</h2><p>{item.gap_statement}</p></article>
   <article className={styles.solution}><span>THE FIX</span><h2>Τι αλλάζει στην πράξη.</h2><p>{item.solution_statement}</p></article>
  </section>

  <section className={styles.visualStory}>
   <div className={styles.visualStoryCopy}><small>SEE THE USE CASE</small><h2>Δεν πουλάμε το αντικείμενο.<br/><em>Δείχνουμε το αποτέλεσμα.</em></h2><p>{item.job_to_be_done}</p></div>
   <div className={styles.visualMosaic}>
    <figure className={styles.mosaicA}>{creativeImages[0]&&<img src={creativeImages[0]} alt={`${item.product_name} — product view`}/>}<figcaption>THE OBJECT</figcaption></figure>
    <figure className={styles.mosaicB}>{(creativeImages[1]||creativeImages[0])&&<img src={creativeImages[1]||creativeImages[0]} alt={`${item.product_name} — detail`}/>}<figcaption>THE DETAIL</figcaption></figure>
    <figure className={styles.mosaicC}>{(creativeImages[2]||creativeImages[0])&&<img src={creativeImages[2]||creativeImages[0]} alt={`${item.product_name} — use case`}/>}<figcaption>THE FIX</figcaption></figure>
   </div>
  </section>

  <section className={styles.whyNow}>
   <div><small>WHY NOW?</small><h2>Αν το pain είναι δικό σου, <em>μην το αφήσεις για “κάποια στιγμή”.</em></h2></div><p>{whyNow}</p>{target&&<a href={target} target="_blank" rel="sponsored noreferrer">Έλεγξε τώρα τι ισχύει ↗</a>}
  </section>

  <section className={styles.proof}>
   <div className={styles.proofTitle}><small>WHY IT MADE THE CUT</small><h2>Όχι hype. <em>Σήματα που έχουν νόημα.</em></h2><p>Τα εσωτερικά scores δεν είναι πιστοποίηση και δεν τα χρησιμοποιούμε σαν marketing claim. Μεταφράζουμε τα στοιχεία σε απλές ενδείξεις για να καταλάβεις αν αξίζει να συνεχίσεις.</p></div>
   <div className={styles.proofGrid}>
    <div><b>USE CASE</b><strong>{signal(item.semantic_fit_score,'Πολύ ισχυρό','Ισχυρό')}</strong><span>Η λύση ταιριάζει στο συγκεκριμένο job-to-be-done.</span></div>
    <div><b>MARKET GAP</b><strong>{signal(item.whitespace_score,'Μεγάλο','Υπαρκτό')}</strong><span>Υπάρχει λόγος να ψάξεις πέρα από τις προφανείς επιλογές.</span></div>
    <div><b>INTEREST</b><strong>{signal(item.demand_score,'Υψηλό','Θετικό')}</strong><span>Το pain δείχνει ότι δεν αφορά μόνο έναν μεμονωμένο χρήστη.</span></div>
    <div><b>EVIDENCE</b><strong>{signal(item.product_quality_score,'Ισχυρό','Επαρκές')}</strong><span>Υπάρχουν αρκετά στοιχεία για να παρουσιαστεί υπεύθυνα το case.</span></div>
   </div>
  </section>

  <section className={styles.fit}>
   <div><small>BEST FOR</small><h2>Για ποιον έχει νόημα;</h2><p>{audience}</p></div>
   <div><small>BEFORE YOU BUY</small><h2>Τι να ελέγξεις.</h2>{unknowns.length?<ul>{unknowns.map((x,i)=><li key={i}>{x}</li>)}</ul>:<p>Διαστάσεις, συμβατότητα, παραλλαγή, όρους επιστροφής, χρόνο παράδοσης και τελική τιμή.</p>}</div>
  </section>

  <section className={styles.objections}>
   <div className={styles.objectionTitle}><small>OBJECTION CHECK</small><h2>Μην το πάρεις επειδή απλώς φαίνεται ωραίο.</h2><p>Πέρασε πρώτα από αυτά τα checks.</p></div>
   <div className={styles.objectionGrid}>{(objections.length?objections:['Το pain είναι πραγματικό και επαναλαμβανόμενο για εσένα;','Η λύση ταιριάζει στις διαστάσεις/συμβατότητα που χρειάζεσαι;','Η τελική τιμή εξακολουθεί να βγάζει νόημα μετά τα μεταφορικά;','Οι όροι επιστροφής σε καλύπτουν;']).map((x,i)=><article key={i}><b>0{i+1}</b><p>{typeof x==='string'?x:x?.objection||JSON.stringify(x)}</p></article>)}</div>
  </section>

  <section className={styles.evidence}>
   <div className={styles.evidenceHead}><small>CASE NOTES</small><h2>Τι μας έπεισε να το κρατήσουμε.</h2></div>
   <div className={styles.evidenceCards}>{evidence.length?evidence.map((x,i)=><article key={i}><b>0{i+1}</b><p>{typeof x==='string'?x:JSON.stringify(x)}</p></article>):<><article><b>01</b><p>Υπάρχει σαφής σύνδεση ανάμεσα στο προϊόν και στο συγκεκριμένο pain/use case.</p></article><article><b>02</b><p>Το case πέρασε ανεξάρτητο relevance και evidence check πριν εμφανιστεί δημόσια.</p></article></>}</div>
  </section>

  <section className={styles.action}>
   <div className={styles.actionCopy}><small>ONE LAST CHECK</small><h2>Αν λύνει το δικό σου pain,<br/><em>τότε αξίζει να το δεις τώρα.</em></h2><p>Μπες στον τελικό προορισμό, επιβεβαίωσε τιμή, παραλλαγή, παράδοση και όρους. Η σωστή αγορά δεν είναι impulse· είναι η σωστή λύση στο σωστό πρόβλημα.</p>{target&&<a href={target} target="_blank" rel="sponsored noreferrer">Δες τη σημερινή διαθεσιμότητα ↗</a>}<div className={styles.shareActions}><button onClick={shareWhatsApp}>Στείλ' το στο WhatsApp</button><button onClick={share}>{copied?'Link copied ✓':'Αντέγραψε το case link'}</button></div></div>
   {qr&&<div className={styles.qr}><div className={styles.qrTop}><span>SCAN TO CHECK</span><b>↗</b></div><img src={qr} alt="QR code για τον τελικό προορισμό"/><b>Σκάναρέ το από άλλη συσκευή</b><span>Ο QR κωδικός οδηγεί ακριβώς στον ίδιο εξωτερικό προορισμό με το CTA.</span></div>}
  </section>

  {related.length>0&&<section className={styles.related}><div><small>KEEP EXPLORING</small><h2>Παρόμοια pains. Διαφορετικά fixes.</h2></div><div className={styles.relatedGrid}>{related.map(x=><Link key={x.id} href={`/marketplace/${encodeURIComponent(String(x.id))}`}><div>{x.image_url&&<img src={x.image_url} alt=""/>}</div><span>{x.subniche||x.niche}</span><h3>{x.product_name}</h3><p>{x.solution_statement}</p></Link>)}</div></section>}

  <div className={styles.sticky}>{Number(item.sale_price_eur)>0&&<div><small>ένδειξη τιμής</small><b>{money(item.sale_price_eur)}</b></div>}{target?<a href={target} target="_blank" rel="sponsored noreferrer">Δες αν σε συμφέρει ↗</a>:<Link href="/marketplace">Πίσω στο SocialMarket</Link>}</div>
  <footer className={styles.footer}><Link href="/marketplace">← SocialMarket</Link><p>Ορισμένοι εξωτερικοί σύνδεσμοι μπορεί να υποστηρίζουν οικονομικά το SocialMarket χωρίς επιπλέον κόστος για εσένα. Πάντα επιβεβαίωσε τα τελικά στοιχεία πριν την αγορά.</p></footer>
 </main>
}
