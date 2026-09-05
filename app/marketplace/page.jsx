'use client';

import Link from 'next/link';
import {useEffect,useMemo,useState} from 'react';
import {supabase} from '@/lib/supabase';
import styles from './marketplace.module.css';

const arr=v=>Array.isArray(v)?v:[];
const money=v=>Number(v||0).toLocaleString('el-GR',{style:'currency',currency:'EUR',maximumFractionDigits:2});
const score=v=>Math.max(0,Math.min(100,Math.round(Number(v||0))));
const slug=id=>encodeURIComponent(String(id||''));

function mood(item){
 const d=score(item.demand_score),g=score(item.whitespace_score),v=score(item.viral_score);
 if(g>=86)return 'Rare find';
 if(v>=84)return 'Social pick';
 if(d>=86)return 'Worth a look';
 return 'Problem solver';
}

function promise(item){return item.solution_statement||item.job_to_be_done||'Μια πρακτική λύση για καθημερινή τριβή.'}

function SolutionCard({item,index}){
 return <article className={`${styles.card} ${index%5===0?styles.featured:''}`}>
  <Link className={styles.visual} href={`/marketplace/${slug(item.id)}`} aria-label={`Δες το case: ${item.product_name}`}>
   {item.image_url?<img src={item.image_url} alt={item.product_name} loading="lazy"/>:<div className={styles.imageFallback}>FIX<br/>WHAT<br/>BUGS YOU</div>}
   <div className={styles.visualShade}/>
   <span className={styles.discoveryBadge}>{mood(item)}</span>
   <span className={styles.saveBadge}>↗</span>
   <div className={styles.visualCopy}>
    <small>{item.subniche||item.niche||'REAL-LIFE SOLVER'}</small>
    <h2>{item.product_name}</h2>
   </div>
  </Link>
  <div className={styles.cardBody}>
   <p className={styles.promise}>{promise(item)}</p>
   <div className={styles.painLine}><span>ΓΙΑΤΙ ΕΧΕΙ ΝΟΗΜΑ</span><p>{item.pain_statement||'Σχεδιάστηκε για ένα συγκεκριμένο use case, όχι για αόριστη κατανάλωση.'}</p></div>
   <div className={styles.microSignals}>
    {score(item.whitespace_score)>=75&&<span>◉ δύσκολο να βρεθεί</span>}
    {score(item.semantic_fit_score)>=78&&<span>✦ δυνατό use-case fit</span>}
    {score(item.product_quality_score)>=75&&<span>✓ πέρασε evidence check</span>}
   </div>
   <div className={styles.tags}>{arr(item.semantic_tags).slice(0,4).map(t=><span key={t}>{t}</span>)}</div>
   <div className={styles.cardFoot}>
    <div>{Number(item.sale_price_eur)>0&&<><small>ένδειξη τιμής</small><strong>{money(item.sale_price_eur)}</strong></>}</div>
    <Link href={`/marketplace/${slug(item.id)}`}>Δες πώς λύνει το pain <b>→</b></Link>
   </div>
  </div>
 </article>
}

export default function Marketplace(){
 const [rows,setRows]=useState([]),[loading,setLoading]=useState(true),[error,setError]=useState(''),[query,setQuery]=useState(''),[niche,setNiche]=useState('all');
 useEffect(()=>{let alive=true;(async()=>{const {data,error}=await supabase.from('socialmarket_marketplace200_public_v').select('*').order('affinity_score',{ascending:false}).limit(240);if(!alive)return;if(error)setError(error.message);else setRows(data||[]);setLoading(false)})();return()=>{alive=false}},[]);
 const niches=useMemo(()=>[...new Set(rows.map(x=>x.niche).filter(Boolean))].slice(0,12),[rows]);
 const filtered=useMemo(()=>{const q=query.trim().toLowerCase();return rows.filter(x=>{if(niche!=='all'&&x.niche!==niche)return false;if(!q)return true;const hay=[x.product_name,x.niche,x.subniche,x.job_to_be_done,x.pain_statement,x.gap_statement,x.solution_statement,...arr(x.semantic_tags)].join(' ').toLowerCase();return q.split(/\s+/).filter(Boolean).every(t=>hay.includes(t))})},[rows,query,niche]);
 const featured=filtered.slice(0,3);

 return <main className={styles.page}>
  <nav className={styles.nav}>
   <Link href="/marketplace" className={styles.brand}><span>S</span><div><b>SocialMarket</b><small>Find what fixes it</small></div></Link>
   <div className={styles.navLinks}><a href="#discover">Ανακάλυψε</a><a href="#how">Η λογική</a><a href="#fresh">Fresh finds</a></div>
   <a className={styles.navCta} href="#discover">Βρες λύση ↓</a>
  </nav>

  <div className={styles.ticker} aria-hidden="true"><div>FIX THE FRICTION ✦ SAVE TIME ✦ LIVE SMARTER ✦ FIND THE GAP ✦ SHARE THE SOLUTION ✦ FIX THE FRICTION ✦ SAVE TIME ✦ LIVE SMARTER ✦</div></div>

  <header className={styles.hero}>
   <div className={styles.heroGlow}/>
   <div className={styles.heroCopy}>
    <span className={styles.kicker}>SOCIAL GAP-FILLER · CURATED FOR REAL LIFE</span>
    <h1>Κάτι σε<br/>δυσκολεύει;<br/><em>Βρες αυτό που το λύνει.</em></h1>
    <p>Δεν ξεκινάμε από ράφια και κατηγορίες. Ξεκινάμε από μικρές και μεγάλες τριβές της καθημερινότητας και ψάχνουμε λύσεις που αξίζουν πραγματικά την προσοχή σου.</p>
    <div className={styles.heroActions}><a href="#discover">Ξεκίνα από το pain</a><a href="#fresh" className={styles.ghost}>Δες τι ξεχωρίζει ✦</a></div>
   </div>
   <div className={styles.heroStack} aria-hidden="true">
    {featured.length?featured.map((x,i)=><div key={x.id} className={styles.stackCard} style={{'--i':i}}><img src={x.image_url} alt=""/><span>{x.subniche||x.niche}</span></div>):<><div className={styles.stackPlaceholder}>SAVE<br/>TIME</div><div className={styles.stackPlaceholder}>FIX<br/>FRICTION</div><div className={styles.stackPlaceholder}>LIVE<br/>SMARTER</div></>}
   </div>
  </header>

  <section className={styles.problemSearch} id="discover">
   <div className={styles.searchIntro}><small>START WITH THE PAIN</small><h2>Τι θέλεις να γίνει πιο εύκολο;</h2></div>
   <div className={styles.searchControl}><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="π.χ. οργάνωση, καθάρισμα, ύπνος, γραφείο, κατοικίδιο…"/><button onClick={()=>document.getElementById('fresh')?.scrollIntoView({behavior:'smooth'})}>Βρες λύσεις</button></div>
   <div className={styles.quickChips}><button onClick={()=>setQuery('χρόνο')}>⏱ Κερδίζω χρόνο</button><button onClick={()=>setQuery('οργάνωση')}>▦ Οργανώνω καλύτερα</button><button onClick={()=>setQuery('άνεση')}>☁ Περισσότερη άνεση</button><button onClick={()=>setQuery('εργασία')}>⌁ Δουλεύω εξυπνότερα</button><button onClick={()=>setQuery('καθαρισ')}>✦ Λιγότερος κόπος</button></div>
  </section>

  <section className={styles.manifesto} id="how">
   <div className={styles.manifestoTitle}><small>NO FILLER. ONLY USEFUL.</small><h2>Το προϊόν είναι το τέλος της ιστορίας. <em>Το pain είναι η αρχή.</em></h2></div>
   <div className={styles.steps}>
    <article><b>PAIN</b><h3>Βλέπουμε την τριβή.</h3><p>Καταστάσεις που κοστίζουν χρόνο, ενέργεια, άνεση ή συγκέντρωση.</p></article>
    <article><b>GAP</b><h3>Ψάχνουμε τι λείπει.</h3><p>Δεν μας αρκεί να υπάρχει κάτι· πρέπει να εξυπηρετεί ουσιαστικά το use case.</p></article>
    <article><b>PROOF</b><h3>Κρατάμε ό,τι αντέχει.</h3><p>Χωρίζουμε τα πραγματικά σήματα από το hype και τις αβάσιμες υποσχέσεις.</p></article>
    <article><b>SHARE</b><h3>Το κάνουμε social.</h3><p>Κάθε λύση γίνεται case που καταλαβαίνεις γρήγορα, αποθηκεύεις και μοιράζεσαι.</p></article>
   </div>
  </section>

  <section className={styles.discovery} id="fresh">
   <div className={styles.discoveryHead}><div><small>FRESH FINDS · MADE TO SOLVE</small><h2>Ανακαλύψεις με λόγο ύπαρξης.</h2></div><div className={styles.discoveryMeta}><span>Curated continuously · no filler drops</span><select value={niche} onChange={e=>setNiche(e.target.value)}><option value="all">Όλες οι ανάγκες</option>{niches.map(n=><option value={n} key={n}>{n}</option>)}</select></div></div>
   {loading?<div className={styles.state}><span className={styles.loader}/>Χαρτογραφούμε problem-solvers…</div>:error?<div className={styles.state}>Δεν ήταν δυνατή η φόρτωση αυτή τη στιγμή.</div>:filtered.length?<div className={styles.grid}>{filtered.map((x,i)=><SolutionCard key={x.id} item={x} index={i}/>)}</div>:<div className={styles.empty}><small>CURATION IN PROGRESS</small><h3>Δεν γεμίζουμε το feed με filler.</h3><p>Νέα cases εμφανίζονται μόνο όταν έχουν αρκετό context για να εξηγούν καθαρά ποιο pain λύνουν και τι πρέπει να ελέγξεις πριν αγοράσεις.</p></div>}
  </section>

  <section className={styles.shareBand}><div><small>SEE IT · SAVE IT · SHARE IT</small><h2>Μια καλή ανακάλυψη αξίζει περισσότερο όταν φτάνει στον σωστό άνθρωπο.</h2></div><a href="#fresh">Βρες το επόμενο fix ↗</a></section>

  <footer className={styles.footer}><div><div className={styles.footerBrand}>SocialMarket</div><p>Problem-solvers για πιο έξυπνη καθημερινότητα.</p></div><div><b>Η αρχή μας</b><p>Δεν δημοσιεύουμε claims που δεν στηρίζονται στα διαθέσιμα στοιχεία. Τιμή, διαθεσιμότητα, συμβατότητα και όροι επιβεβαιώνονται πάντα στον τελικό προορισμό.</p></div><div><b>Διαφάνεια</b><p>Ορισμένοι εξωτερικοί σύνδεσμοι μπορεί να υποστηρίζουν οικονομικά το SocialMarket, χωρίς επιπλέον κόστος για εσένα.</p></div></footer>
 </main>
}
