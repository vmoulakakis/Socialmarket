'use client';
import Link from 'next/link';
import {useMemo,useState} from 'react';
import styles from './catalog.module.css';

const money=(amount)=>Number(amount).toLocaleString('el-GR',{style:'currency',currency:'EUR',maximumFractionDigits:0});
const budgets=[{label:'Όλες οι τιμές',max:Infinity},{label:'Έως 200 €',max:200},{label:'Έως 500 €',max:500},{label:'Έως 1.500 €',max:1500}];

export default function Catalog({products=[],error=false}){
 const [query,setQuery]=useState('');
 const [category,setCategory]=useState('all');
 const [budget,setBudget]=useState(Infinity);
 const [sort,setSort]=useState('price-asc');
 const categories=useMemo(()=>[...new Set(products.map(x=>x.category_raw).filter(Boolean))], [products]);
 const rows=useMemo(()=>products
  .filter(x=>Number.isFinite(Number(x.price_eur))&&Number(x.price_eur)>0)
  .filter(x=>(category==='all'||x.category_raw===category)&&Number(x.price_eur)<=budget)
  .filter(x=>!query||[x.product_name,x.program_name,x.category_raw].join(' ').toLocaleLowerCase('el-GR').includes(query.toLocaleLowerCase('el-GR').trim()))
  .sort((a,b)=>sort==='price-desc'?Number(b.price_eur)-Number(a.price_eur):Number(a.price_eur)-Number(b.price_eur)),
  [products,query,category,budget,sort]);
 const hasProducts=products.length>0;
 function reset(){setQuery('');setCategory('all');setBudget(Infinity);setSort('price-asc');}
 return <main className={styles.page}>
  <header className={styles.nav}><Link href="/marketplace" aria-label="SocialMarket marketplace">SOCIALMARKET<span>Επιλεγμένα προϊόντα και οδηγός αγοράς</span></Link><Link href="/luxecorner">Premium συλλογή ↗</Link></header>
  <section className={styles.hero}>
   <small>ΠΡΟΪΟΝΤΑ ΜΕ ΣΑΦΕΙΣ ΠΛΗΡΟΦΟΡΙΕΣ</small>
   <h1>Επίλεξε με βάση <br/>την ανάγκη σου.</h1>
   <p>Σύγκρινε τις διαθέσιμες επιλογές με βάση την τιμή και την κατηγορία. Αυτή η συλλογή περιέχει κυρίως premium είδη σπιτιού· δεν αποτελεί σύγκριση ολόκληρης της αγοράς.</p>
   <a className={styles.heroLink} href="#catalog-results">Δες τις επιλογές ↓</a>
  </section>
  <section className={styles.buyerGuide} aria-label="Πώς να αγοράσεις με σιγουριά">
   <span><b>01 · Ανάγκη</b> Επιβεβαίωσε διαστάσεις και χρήση.</span>
   <span><b>02 · Κόστος</b> Υπολόγισε μεταφορικά και τελική τιμή.</span>
   <span><b>03 · Κατάστημα</b> Δες εγγύηση και όρους επιστροφής.</span>
  </section>
  <section className={styles.filters} aria-label="Φίλτρα καταλόγου">
   <label>Αναζήτηση<input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Προϊόν, ανάγκη ή κατάστημα…" type="search"/></label>
   <label>Κατηγορία<select value={category} onChange={e=>setCategory(e.target.value)}><option value="all">Όλες οι κατηγορίες</option>{categories.map(c=><option key={c} value={c}>{c}</option>)}</select></label>
   <label>Προϋπολογισμός<select value={String(budget)} onChange={e=>setBudget(Number(e.target.value))}>{budgets.map(x=><option key={x.label} value={String(x.max)}>{x.label}</option>)}</select></label>
   <label>Ταξινόμηση<select value={sort} onChange={e=>setSort(e.target.value)}><option value="price-asc">Τιμή: χαμηλότερη πρώτα</option><option value="price-desc">Τιμή: υψηλότερη πρώτα</option></select></label>
  </section>
  <section id="catalog-results" className={styles.resultsHeading} aria-live="polite"><p><b>{rows.length}</b> εμφανιζόμενες επιλογές</p><span>Οι τιμές και η διαθεσιμότητα επιβεβαιώνονται στον merchant.</span></section>
  {error&&<div className={styles.notice} role="alert">Η ενημέρωση του καταλόγου δεν είναι διαθέσιμη αυτή τη στιγμή. <Link href="/marketplace">Δοκίμασε ξανά</Link>.</div>}
  <section className={styles.grid} aria-label="Προϊόντα">{rows.map(p=><article className={styles.card} key={p.source_product_id}>
   <Link href={'/marketplace/'+encodeURIComponent(p.source_product_id)} aria-label={'Πληροφορίες για '+p.product_name}>
    {p.image_url?<img src={p.image_url} alt={p.product_name||'Προϊόν'} loading="lazy" onError={e=>{e.currentTarget.style.visibility='hidden';}}/>:<div className={styles.imageMissing}>Η φωτογραφία δεν είναι διαθέσιμη</div>}
   </Link>
   <div><small>{p.program_name||'Συνεργαζόμενο κατάστημα'}</small><h2><Link href={'/marketplace/'+encodeURIComponent(p.source_product_id)}>{p.product_name}</Link></h2>
    <strong>{money(p.price_eur)}</strong><p className={styles.merchantNote}>Έλεγξε τελική τιμή, διαθεσιμότητα και μεταφορικά.</p>
    <Link className={styles.button} href={'/marketplace/'+encodeURIComponent(p.source_product_id)}>Δες χαρακτηριστικά και κατάστημα →</Link></div>
  </article>)}</section>
  {!error&&!rows.length&&<div className={styles.notice} role="status"><b>{hasProducts?'Δεν υπάρχουν προϊόντα με αυτά τα φίλτρα.':'Δεν υπάρχουν επαληθευμένες επιλογές αυτή τη στιγμή.'}</b><p>{hasProducts?'Δοκίμασε άλλο όριο τιμής. Η διαθέσιμη συλλογή περιλαμβάνει premium προϊόντα.':'Επισκέψου ξανά τη σελίδα όταν ενημερωθεί ο κατάλογος.'}</p>{hasProducts&&<button className={styles.reset} onClick={reset}>Καθαρισμός φίλτρων</button>}</div>}
  <footer className={styles.footer}>Διαφάνεια: Ορισμένοι σύνδεσμοι είναι affiliate. Μπορεί να λάβουμε προμήθεια χωρίς πρόσθετο κόστος για εσένα. Δεν πραγματοποιούνται αγορές σε αυτό το site. Οι τελικοί όροι καθορίζονται από το κατάστημα.</footer>
 </main>;
}
