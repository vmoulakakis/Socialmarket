'use client';

import {useEffect,useMemo,useState} from 'react';
import {supabase} from '@/lib/supabase';
import styles from './marketplace.module.css';

const money=v=>Number(v||0).toLocaleString('el-GR',{style:'currency',currency:'EUR',maximumFractionDigits:2});
const score=v=>Math.max(0,Math.min(100,Math.round(Number(v||0))));
const arr=v=>Array.isArray(v)?v:[];

function ProductCard({item}){
 const copy=item.social_copy||{};
 return <article className={styles.card}>
  <div className={styles.imageWrap}>
   <img src={item.image_url} alt={item.product_name} loading="lazy"/>
   <div className={styles.sourceBadge}>{item.portfolio==='aliexpress'?'GLOBAL GAP':'GREEK MERCHANT'}</div>
   <div className={styles.qualityBadge}>QA {score(item.product_quality_score)}</div>
  </div>
  <div className={styles.cardBody}>
   <div className={styles.semanticPath}><span>{item.niche}</span><i>→</i><span>{item.subniche||'λύση'}</span></div>
   <h2>{item.product_name}</h2>
   <p className={styles.jtbd}>{item.job_to_be_done}</p>

   <div className={styles.story}>
    <section><small>01 · PAIN</small><p>{item.pain_statement}</p></section>
    <section><small>02 · GAP</small><p>{item.gap_statement}</p></section>
    <section><small>03 · SOLUTION</small><p>{item.solution_statement}</p></section>
   </div>

   <div className={styles.signalRow}>
    <div><b>{score(item.demand_score)}</b><span>Demand fit</span></div>
    <div><b>{score(item.whitespace_score)}</b><span>Market gap</span></div>
    <div><b>{score(item.semantic_fit_score)}</b><span>Semantic fit</span></div>
   </div>

   <div className={styles.tags}>{arr(item.semantic_tags).slice(0,5).map(t=><span key={t}>{t}</span>)}</div>

   <div className={styles.cardFoot}>
    <div><small>Τρέχουσα τιμή</small><strong>{money(item.sale_price_eur)}</strong>{item.merchant_name&&<span>{item.merchant_name}</span>}</div>
    <a href={item.tracking_url} target="_blank" rel="sponsored noreferrer">Δες τη λύση <b>↗</b></a>
   </div>
   <details><summary>Γιατί πέρασε το research</summary><p>{copy.research_reason||'Η επιλογή πέρασε semantic fit, quality evidence και ανεξάρτητο Skeptic audit.'}</p><small>Το QA score αξιολογεί την ποιότητα των διαθέσιμων αποδείξεων και όχι εργαστηριακή πιστοποίηση του προϊόντος.</small></details>
  </div>
 </article>
}

export default function Marketplace(){
 const [rows,setRows]=useState([]),[loading,setLoading]=useState(true),[error,setError]=useState(''),[query,setQuery]=useState(''),[portfolio,setPortfolio]=useState('all'),[niche,setNiche]=useState('all');
 useEffect(()=>{let alive=true;(async()=>{const {data,error}=await supabase.from('socialmarket_marketplace200_public_v').select('*').order('affinity_score',{ascending:false}).limit(200);if(!alive)return;if(error)setError(error.message);else setRows(data||[]);setLoading(false)})();return()=>{alive=false}},[]);

 const niches=useMemo(()=>[...new Set(rows.map(x=>x.niche).filter(Boolean))].slice(0,14),[rows]);
 const filtered=useMemo(()=>{
  const q=query.trim().toLowerCase();
  return rows.filter(x=>{
   if(portfolio!=='all'&&x.portfolio!==portfolio)return false;
   if(niche!=='all'&&x.niche!==niche)return false;
   if(!q)return true;
   const hay=[x.product_name,x.niche,x.subniche,x.job_to_be_done,x.pain_statement,x.gap_statement,x.solution_statement,...arr(x.semantic_tags)].join(' ').toLowerCase();
   return q.split(/\s+/).filter(Boolean).every(t=>hay.includes(t));
  });
 },[rows,query,portfolio,niche]);

 const linkwise=rows.filter(x=>x.portfolio==='linkwise').length,ali=rows.filter(x=>x.portfolio==='aliexpress').length;
 const runDate=rows[0]?.run_date;

 return <main className={styles.page}>
  <nav className={styles.nav}><div className={styles.brand}><span>SM</span><div><b>SocialMarket</b><small>semantic solutions · Greece</small></div></div><div className={styles.navMeta}><span>{rows.length||'—'} curated λύσεις</span><a href="#solutions">Explore ↓</a></div></nav>

  <header className={styles.hero}>
   <div className={styles.heroGrid}>
    <div>
     <div className={styles.kicker}>AFFINITY · EVIDENCE-FIRST MARKETPLACE</div>
     <h1>Μην ψάχνεις<br/>προϊόν.<br/><em>Βρες τι λύνει.</em></h1>
     <p>Ξεκινάμε από το πρόβλημα, το κενό της ελληνικής αγοράς και το πραγματικό job-to-be-done. Τα προϊόντα εμφανίζονται μόνο αφού περάσουν merchant/seller quality, commission, semantic research και ανεξάρτητο Skeptic audit.</p>
    </div>
    <div className={styles.radar} aria-hidden="true"><div/><div/><div/><span>PAIN</span><span>GAP</span><span>SOLUTION</span><b>200</b></div>
   </div>
   <div className={styles.searchBox}>
    <label>Τι θέλεις να λύσεις;</label>
    <div><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="π.χ. λιγότερος χρόνος καθαρισμού, οργάνωση εργαστηρίου, καλύτερος ύπνος…"/><button onClick={()=>document.getElementById('solutions')?.scrollIntoView({behavior:'smooth'})}>Βρες λύσεις</button></div>
    <small>Semantic browsing πάνω σε pain · gap · use case · solution tags.</small>
   </div>
  </header>

  <section className={styles.proofStrip}>
   <div><small>PORTFOLIO</small><b>{rows.length}/200</b><span>μόνο validated</span></div>
   <div><small>LINKWISE</small><b>{linkwise}/100</b><span>max 3 / merchant</span></div>
   <div><small>ALIEXPRESS EXCLUSIVE</small><b>{ali}/100</b><span>Greek gap required</span></div>
   <div><small>LAST CURATION</small><b>{runDate||'building'}</b><span>AI + Skeptic QA</span></div>
  </section>

  <section className={styles.explainer}>
   <div><span>01</span><h3>Πρόβλημα</h3><p>Τι κοστίζει χρόνο, χρήμα, κόπο ή δημιουργεί πραγματική τριβή;</p></div>
   <div><span>02</span><h3>Κενό</h3><p>Τι λείπει, είναι σπάνιο ή εξυπηρετείται ανεπαρκώς στην ελληνική αγορά;</p></div>
   <div><span>03</span><h3>Evidence</h3><p>Merchant, product identity, market research, quality signals και Skeptic αντιπαράθεση.</p></div>
   <div><span>04</span><h3>Λύση</h3><p>Μόνο τότε εμφανίζεται το προϊόν και ο επαληθευμένος εμπορικός προορισμός.</p></div>
  </section>

  <section className={styles.market} id="solutions">
   <div className={styles.marketHead}><div><small>SEMANTIC MARKET MAP</small><h2>Λύσεις οργανωμένες γύρω από ανάγκες.</h2></div><p>{filtered.length} αποτελέσματα</p></div>
   <div className={styles.filters}>
    <button className={portfolio==='all'?styles.active:''} onClick={()=>setPortfolio('all')}>Όλα</button>
    <button className={portfolio==='linkwise'?styles.active:''} onClick={()=>setPortfolio('linkwise')}>Greek Merchant Finds</button>
    <button className={portfolio==='aliexpress'?styles.active:''} onClick={()=>setPortfolio('aliexpress')}>Global Gap Finds</button>
    <select value={niche} onChange={e=>setNiche(e.target.value)}><option value="all">Όλα τα semantic niches</option>{niches.map(n=><option value={n} key={n}>{n}</option>)}</select>
   </div>

   {loading?<div className={styles.state}>Χτίζεται ο semantic χάρτης…</div>:error?<div className={styles.state}>Δεν ήταν δυνατή η φόρτωση: {error}</div>:filtered.length?<div className={styles.grid}>{filtered.map(x=><ProductCard key={x.id} item={x}/>)}</div>:<div className={styles.empty}><small>QUALITY-FIRST CURATION</small><h3>Το portfolio χτίζεται χωρίς χαλάρωση των gates.</h3><p>Δεν εμφανίζουμε placeholder προϊόντα. Μόλις ένα προϊόν περάσει commission, merchant/seller quality, Greek-market evidence, Research Agent και Skeptic Agent, θα εμφανιστεί εδώ.</p></div>}
  </section>

  <footer className={styles.footer}><div><b>SocialMarket</b><p>Evidence-first product discovery για την Ελλάδα.</p></div><p>Ορισμένοι σύνδεσμοι είναι affiliate links. Αν πραγματοποιηθεί αγορά ενδέχεται να λάβουμε προμήθεια χωρίς πρόσθετη χρέωση για εσάς. Οι τιμές και η διαθεσιμότητα μπορούν να αλλάξουν στον τελικό έμπορο.</p></footer>
 </main>
}
