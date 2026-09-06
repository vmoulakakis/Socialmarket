'use client';

import Link from 'next/link';
import {useEffect,useMemo,useState} from 'react';
import {supabase} from '@/lib/supabase';
import AffinityCommerceModal from '@/components/affinity/AffinityCommerceModal';
import styles from './marketplace.module.css';

const arr=v=>Array.isArray(v)?v:[];
const money=v=>Number(v||0).toLocaleString('el-GR',{style:'currency',currency:'EUR',maximumFractionDigits:2});
const score=v=>Math.max(0,Math.min(100,Math.round(Number(v||0))));
const slug=id=>encodeURIComponent(String(id||''));

function badge(item){
 if(score(item.whitespace_score)>=86)return 'Rare Find';
 if(score(item.viral_score)>=84)return 'Trending';
 if(score(item.demand_score)>=86)return 'Bestseller Fit';
 return 'Staff Pick';
}
function benefit(item){return item.solution_statement||item.job_to_be_done||'Μια πιο έξυπνη λύση για την καθημερινότητα.'}

function ProductCard({item,onOffer}){
 return <article className={styles.productCard}>
  <Link href={`/marketplace/${slug(item.id)}`} className={styles.productImage}>
   {item.image_url?<img src={item.image_url} alt={item.product_name} loading="lazy"/>:<div className={styles.productFallback}>A<br/>BETTER<br/>EVERYDAY</div>}
   <span>{badge(item)}</span>
  </Link>
  <div className={styles.productCopy}>
   <small>{item.subniche||item.niche||'AFFINITY FIND'}</small>
   <Link href={`/marketplace/${slug(item.id)}`}><h3>{item.product_name}</h3></Link>
   <p>{benefit(item)}</p>
   <div className={styles.productMeta}>{Number(item.sale_price_eur)>0&&<strong>{money(item.sale_price_eur)}</strong>}<em>✦ curated solution</em></div>
   <div className={styles.productActions}><Link href={`/marketplace/${slug(item.id)}`}>Δες το case</Link><button onClick={()=>onOffer(item)}>Δες προσφορά ↗</button></div>
  </div>
 </article>
}

export default function Marketplace(){
 const [rows,setRows]=useState([]),[loading,setLoading]=useState(true),[error,setError]=useState(''),[query,setQuery]=useState(''),[niche,setNiche]=useState('all'),[offer,setOffer]=useState(null);
 useEffect(()=>{let alive=true;(async()=>{const {data,error}=await supabase.from('socialmarket_marketplace200_public_v').select('*').order('affinity_score',{ascending:false}).limit(240);if(!alive)return;if(error)setError(error.message);else setRows(data||[]);setLoading(false)})();return()=>{alive=false}},[]);
 const niches=useMemo(()=>[...new Set(rows.map(x=>x.niche).filter(Boolean))].slice(0,10),[rows]);
 const filtered=useMemo(()=>{const q=query.trim().toLowerCase();return rows.filter(x=>{if(niche!=='all'&&x.niche!==niche)return false;if(!q)return true;const hay=[x.product_name,x.niche,x.subniche,x.job_to_be_done,x.pain_statement,x.gap_statement,x.solution_statement,...arr(x.semantic_tags)].join(' ').toLowerCase();return q.split(/\s+/).filter(Boolean).every(t=>hay.includes(t))})},[rows,query,niche]);
 const hero=filtered[0]||rows[0];
 const featured=filtered.slice(0,5);

 return <main className={styles.page}>
  <div className={styles.topBar}>A MORE THOUGHTFUL EVERYDAY <span>✦</span> CURATED SOLUTIONS FOR REAL LIFE</div>
  <nav className={styles.nav}>
   <Link href="/marketplace" className={styles.brand}><b>AFFINITY</b><span>Small Solutions.<br/>A Better You.</span></Link>
   <div className={styles.navLinks}><a href="#shop">Shop</a><a href="#solutions">Solutions</a><a href="#new">New In</a><a href="#shop">Bestsellers</a><a href="#story">Our Story</a></div>
   <div className={styles.navTools}><label><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search for a better everyday…"/><span>⌕</span></label><button aria-label="Account">♙</button><button aria-label="Saved finds">♡</button></div>
  </nav>

  <header className={styles.hero}>
   <div className={styles.heroMedia}>{hero?.image_url&&<img src={hero.image_url} alt=""/>}<div className={styles.heroVeil}/></div>
   <div className={styles.heroCopy}>
    <small>REAL PEOPLE · REAL SOLUTIONS</small>
    <h1>Discover products<br/>that solve <em>real problems.</em></h1>
    <p>Έξυπνες, curated λύσεις για μία πιο εύκολη, όμορφη και οργανωμένη καθημερινότητα — με το pain και το αποτέλεσμα πριν από το ίδιο το προϊόν.</p>
    <div className={styles.heroActions}><a href="#shop">Discover Solutions →</a>{hero&&<button onClick={()=>setOffer(hero)}>Shop This Find ↗</button>}</div>
    <div className={styles.heroTrust}><span>◇ Curated with purpose</span><span>◇ Evidence before hype</span><span>◇ Better everyday</span></div>
   </div>
   <div className={styles.heroNote}>Good products.<br/><em>Brighter days.</em> ♡</div>
  </header>

  <section className={styles.featured} id="shop">
   <div className={styles.sectionIntro}><small>FEATURED SOLUTIONS</small><h2>Real Problems.<br/>Beautiful Solutions.</h2><p>Κάθε επιλογή έχει λόγο ύπαρξης: συγκεκριμένο use case, σαφές pain και ξεκάθαρη διαδρομή προς τη λύση.</p></div>
   <div className={styles.productRail}>{featured.map(item=><ProductCard key={item.id} item={item} onOffer={setOffer}/>)}{!featured.length&&!loading&&<div className={styles.empty}>Το curation feed γεμίζει μόνο με validated finds.</div>}</div>
  </section>

  <section className={styles.problemFinder} id="solutions">
   <div><small>SHOP BY PROBLEM</small><h2>Τι θέλεις να γίνει πιο εύκολο;</h2></div>
   <div className={styles.finderControl}><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="π.χ. ύπνος, οργάνωση, γραφείο, κατοικίδιο…"/><button onClick={()=>document.getElementById('new')?.scrollIntoView({behavior:'smooth'})}>Find My Fix →</button></div>
   <div className={styles.chips}>{niches.map(n=><button key={n} onClick={()=>setNiche(n)} className={niche===n?styles.activeChip:''}>{n}</button>)}<button onClick={()=>{setNiche('all');setQuery('')}}>Όλα</button></div>
  </section>

  <section className={styles.how} id="story">
   <div className={styles.howIntro}><small>HOW AFFINITY WORKS</small><h2>From everyday problems<br/>to a better you.</h2></div>
   <div className={styles.howSteps}>
    <article><b>01</b><span>THE PAIN</span><h3>Βλέπουμε την τριβή.</h3><p>Τι σε καθυστερεί, σε κουράζει ή κάνει μία απλή καθημερινή εργασία πιο δύσκολη απ’ όσο πρέπει.</p></article>
    <article><b>02</b><span>THE GAP</span><h3>Ψάχνουμε τι λείπει.</h3><p>Δεν αρκεί να υπάρχει “ένα προϊόν”. Θέλουμε καλύτερο fit για το πραγματικό job-to-be-done.</p></article>
    <article><b>03</b><span>THE SOLUTION</span><h3>Κρατάμε ό,τι αξίζει.</h3><p>Το case περνά evidence και relevance checks πριν γίνει δημόσιο AFFINITY find.</p></article>
   </div>
  </section>

  <section className={styles.trustBand}>
   <div><small>CURATED WITH PURPOSE</small><h3>Trust the method, then verify the offer.</h3></div>
   <span>✓ Evidence-first curation</span><span>✓ Clear buyer checks</span><span>✓ Transparent affiliate disclosure</span><span>✓ Shareable case pages</span>
  </section>

  <section className={styles.discovery} id="new">
   <div className={styles.discoveryHead}><div><small>NEW IN · FRESH FINDS</small><h2>Shop the solutions.</h2></div><select value={niche} onChange={e=>setNiche(e.target.value)}><option value="all">Όλες οι ανάγκες</option>{niches.map(n=><option key={n} value={n}>{n}</option>)}</select></div>
   {loading?<div className={styles.state}>Curating better finds…</div>:error?<div className={styles.state}>Δεν ήταν δυνατή η φόρτωση αυτή τη στιγμή.</div>:filtered.length?<div className={styles.grid}>{filtered.map(item=><ProductCard key={item.id} item={item} onOffer={setOffer}/>)}</div>:<div className={styles.state}>Δεν βρέθηκε case για αυτό το pain ακόμη.</div>}
  </section>

  <section className={styles.offerBand}>
   <div><small>TODAY'S WINDOW</small><h2>A good fix is worth checking <em>while it still fits.</em></h2><p>Δεν χρησιμοποιούμε fake countdowns. Οι πραγματικές τιμές, διαθεσιμότητα και όροι αλλάζουν — γι’ αυτό έλεγξε τη σημερινή προσφορά όταν βρεις λύση που ταιριάζει στο δικό σου pain.</p></div><a href="#new">Shop today’s finds →</a>
  </section>

  <section className={styles.shareBand}><div><small>SEE IT · SAVE IT · SHARE IT</small><h2>Good finds are better shared.</h2><p>Κάθε AFFINITY case έχει share buttons, branded preview και QR προς την ενεργή προσφορά.</p></div><a href="#shop">Find something useful ↗</a></section>

  <footer className={styles.footer}>
   <div><b>AFFINITY</b><p>Small Solutions. A Better You.</p></div>
   <div><strong>Shop</strong><a href="#shop">Featured</a><a href="#new">New In</a><a href="#solutions">By Problem</a></div>
   <div><strong>About</strong><a href="#story">Our Method</a><span>Evidence-first</span><span>Made for Greece</span></div>
   <div><strong>Transparency</strong><p>Ορισμένοι εξωτερικοί σύνδεσμοι είναι affiliate links. Μπορεί να υποστηρίζουν το AFFINITY χωρίς επιπλέον κόστος για εσένα.</p></div>
  </footer>

  <AffinityCommerceModal item={offer} open={Boolean(offer)} onClose={()=>setOffer(null)}/>
 </main>
}
