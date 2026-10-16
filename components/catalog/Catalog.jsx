'use client';
import Link from 'next/link';
import {useMemo,useState} from 'react';
import styles from './catalog.module.css';
export function offerUrl(value){try{const u=new URL(value);return ['https:','http:'].includes(u.protocol)?u.href:null;}catch{return null;}}
export default function Catalog({products,error}){
 const [query,setQuery]=useState(''),[category,setCategory]=useState('all');
 const categories=[...new Set(products.map(x=>x.category_raw).filter(Boolean))];
 const rows=useMemo(()=>products.filter(x=>(category==='all'||x.category_raw===category)&&(!query||`${x.product_name} ${x.program_name} ${x.category_raw}`.toLocaleLowerCase('el').includes(query.toLocaleLowerCase('el')))),[products,query,category]);
 return <main className={styles.page}><header className={styles.nav}><Link href="/marketplace">SOCIALMARKET<span>Επιλογές για τον χώρο σου</span></Link><Link href="/luxecorner">LuxeCorner ↗</Link></header><section className={styles.hero}><small>THE HOME EDIT</small><h1>Βρες την επόμενη<br/>ιδέα για το σπίτι σου.</h1><p>Προϊόντα από τον διαθέσιμο κατάλογο LuxeCorner. Οι τιμές και η διαθεσιμότητα επιβεβαιώνονται στο συνεργαζόμενο κατάστημα.</p></section>
 <section className={styles.filters}><input aria-label="Αναζήτηση προϊόντων" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Αναζήτηση προϊόντος ή καταστήματος…"/><select aria-label="Κατηγορία" value={category} onChange={e=>setCategory(e.target.value)}><option value="all">Όλες οι κατηγορίες</option>{categories.map(c=><option key={c} value={c}>{c}</option>)}</select><span>{rows.length} προϊόντα</span></section>
 {error&&<div className={styles.notice} role="alert">Ο κατάλογος δεν είναι διαθέσιμος αυτή τη στιγμή. <a href="/marketplace">Δοκίμασε ξανά</a>.</div>}
 <section className={styles.grid}>{rows.map(p=><article className={styles.card} key={p.source_product_id}><Link href={`/marketplace/${encodeURIComponent(p.source_product_id)}`}><img src={p.image_url} alt={p.product_name} loading="lazy"/></Link><div><small>{p.program_name}</small><h2><Link href={`/marketplace/${encodeURIComponent(p.source_product_id)}`}>{p.product_name}</Link></h2><strong>{p.price_eur==null?'Τιμή στο κατάστημα':Number(p.price_eur).toLocaleString('el-GR',{style:'currency',currency:'EUR'})}</strong><Link className={styles.button} href={`/marketplace/${encodeURIComponent(p.source_product_id)}`}>Λεπτομέρειες →</Link></div></article>)}</section>
 {!error&&!rows.length&&<div className={styles.notice}>Δεν βρέθηκαν προϊόντα. Δοκίμασε διαφορετική αναζήτηση.</div>}
 <footer className={styles.footer}>Ορισμένοι σύνδεσμοι είναι affiliate: μπορεί να λάβουμε προμήθεια χωρίς πρόσθετο κόστος για εσένα. Δεν πραγματοποιούνται αγορές σε αυτό το site.</footer></main>;
}
