'use client';
import {useCallback,useEffect,useRef,useState} from 'react';
import Link from 'next/link';
import styles from './shop-experience.module.css';

const EXAMPLES=[
 {label:'Φωτισμός για σαλόνι',text:'φωτιστικό οροφής για σαλόνι μέχρι 300 ευρώ',icon:'✳'},
 {label:'Εργαλεία αυτοκινήτου',text:'διαγνωστικό εργαλείο για αυτοκίνητο',icon:'◈'},
 {label:'Έξυπνο σπίτι',text:'έξυπνες συσκευές για το σπίτι',icon:'◇'},
 {label:'Έπιπλα & διακόσμηση',text:'γωνιακός καναπές για μικρό σαλόνι',icon:'▦'},
];
const money=n=>Number(n).toLocaleString('el-GR',{style:'currency',currency:'EUR',maximumFractionDigits:2});
const short=n=>Number(n||0).toLocaleString('el-GR');
const safeDate=s=>{if(!s)return 'Δεν αναφέρεται';const d=new Date(s);return Number.isNaN(d.getTime())?'Άγνωστο':d.toLocaleDateString('el-GR',{day:'numeric',month:'short',year:'numeric'});};
function External({href,children,className='',onClick}){
 return <a className={className} href={href} target="_blank" rel="sponsored noopener noreferrer" onClick={onClick}>{children}</a>;
}
function ProductCard({item,index,saved,onSave,compared,onCompare}){
 const [imageError,setImageError]=useState(false);
 return <article className={styles.product}>
  <div className={styles.productVisual}>
   <span className={styles.productNumber}>{String(index+1).padStart(2,'0')}</span>
   {imageError||!item.image?<div className={styles.noPhoto}>Εικόνα μη διαθέσιμη</div>:<img src={item.image} alt={item.title} loading="lazy" referrerPolicy="no-referrer" onError={()=>setImageError(true)}/>}
   <button className={saved?styles.saveSelected:styles.save} type="button" aria-label={saved?'Αφαίρεση από αποθηκευμένα':'Αποθήκευση προϊόντος'} aria-pressed={saved} onClick={()=>onSave(item.id)}>
    <svg viewBox="0 0 24 24" width="19" height="19" fill={saved?'currentColor':'none'} stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round"><path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1-1.1a5.5 5.5 0 1 0-7.8 7.8l8.8 8.8 8.8-8.8a5.5 5.5 0 0 0 0-7.8Z"/></svg>
   </button>
   <span className={item.freshness==='recent'?styles.fresh:styles.unconfirmed}>{item.freshness==='recent'?'Πρόσφατο feed':'Έλεγχος στο κατάστημα'}</span>
  </div>
  <div className={styles.productContent}>
   <div className={styles.productMeta}><span>{item.category}</span><span>{item.source}</span></div>
   <h3 title={item.title}>{item.title}</h3>
   <p className={styles.shopName}>{item.merchant} <span aria-hidden="true">·</span> {item.availability==='unknown'?'Stock μη επιβεβαιωμένο':'Feed stock'}</p>
   <div className={styles.productBottom}>
    <div><span className={styles.priceLabel}>Τιμή feed</span><strong>{money(item.price)}</strong></div>
    <External className={styles.shopLink} href={item.href}>Στο κατάστημα <span aria-hidden="true">↗</span></External>
   </div>
   <button className={styles.compareToggle} type="button" aria-pressed={compared} onClick={()=>onCompare(item.id)}>
    <span aria-hidden="true">{compared?'☑':'□'}</span> {compared?'Στη σύγκριση':'Προσθήκη στη σύγκριση'}
   </button>
  </div>
 </article>;
}
function CompareBar({items,onRemove,onClose}){
 if(!items.length)return null;
 return <section className={styles.compareBar} aria-label="Σύγκριση προϊόντων">
   <div className={styles.compareTop}><div><span className={styles.eyebrow}>ΣΥΓΚΡΙΣΗ</span><h2>{items.length} προϊόντα</h2></div><button type="button" onClick={onClose} aria-label="Κλείσιμο σύγκρισης">✕</button></div>
   <div className={styles.compareGrid}>{items.map(p=><article key={p.id}>
    <div className={styles.compareName}>{p.title}</div><strong>{money(p.price)}</strong>
    <small>{p.merchant} · {p.source}</small>
    <p>Απόθεμα, μεταφορικά και τελική τιμή: προς επιβεβαίωση.</p>
    <div><External href={p.href}>Έλεγχος τιμής ↗</External><button type="button" onClick={()=>onRemove(p.id)}>Αφαίρεση</button></div>
   </article>)}</div>
  </section>;
}
function Message({row}){
 return <div className={row.role==='user'?styles.userBubble:styles.agentBubble}>
   {row.role==='assistant'&&<div className={styles.agentTag}><span className={styles.agentIndicator}/> {row.ai?'Product Fit + Skeptic':'Έρευνα από πηγές'}</div>}
   <p>{row.text}</p>
   {row.explanations?.length>0&&<div className={styles.aiReasons}>{row.explanations.map(e=><div key={e.id}><b>AI αιτιολόγηση · υπό επαλήθευση</b><span>{e.text}</span></div>)}</div>}
   {row.items?.length>0&&<div className={styles.inlineItems}>{row.items.slice(0,3).map(p=><External key={p.id} href={p.href}>{p.category} · {money(p.price)} ↗</External>)}</div>}
 </div>;
}
export default function ShopExperience({initialChat=false}){
 const [products,setProducts]=useState([]),[allCount,setAllCount]=useState(0),[total,setTotal]=useState(0);
 const [categories,setCategories]=useState(['Όλα']),[category,setCategory]=useState('Όλα');
 const [search,setSearch]=useState(''),[budget,setBudget]=useState(''),[sort,setSort]=useState('relevance');
 const [page,setPage]=useState(1),[hasMore,setHasMore]=useState(false),[loading,setLoading]=useState(true);
 const [error,setError]=useState(''),[sourceStatus,setSourceStatus]=useState('');
 const [saved,setSaved]=useState([]),[compare,setCompare]=useState([]);
 const [compareOpen,setCompareOpen]=useState(false),[chatOpen,setChatOpen]=useState(initialChat);
 const [draft,setDraft]=useState(''),[asking,setAsking]=useState(false);
 const [history,setHistory]=useState([{role:'assistant',text:'Γεια! Περιέγραψέ μου τι χρειάζεσαι και το budget σου. Θα ερευνήσω πραγματικά προϊόντα και θα ξεχωρίσω τι γνωρίζουμε από όσα χρειάζονται έλεγχο.',items:[],ai:false}]);
 const listAnchor=useRef(null),chatEnd=useRef(null);
 const relevant=compare;
 const load=useCallback(async(q,cat,max,order,current,append=false)=>{
  setLoading(true);setError('');
  try{
   const params=new URLSearchParams({q,category:cat,sort:order,page:String(current)});
   if(max!=='')params.set('budget',max);
   const r=await fetch('/api/shop/products?'+params.toString(),{cache:'no-store'});
   const data=await r.json();
   if(!r.ok)throw new Error(data.error||'Ο κατάλογος δεν είναι διαθέσιμος.');
   setProducts(old=>append?[...old,...data.items.filter(p=>!old.some(x=>x.id===p.id))]:data.items);
   setAllCount(data.catalogCount||0);setTotal(data.total||0);setCategories(data.categories||['Όλα']);
   setHasMore(Boolean(data.hasMore));setSourceStatus(data.sourceStatus||'');
  }catch(e){setError(e.message||'Αποτυχία φόρτωσης.');if(!append)setProducts([]);}
  finally{setLoading(false)}
 },[]);
 useEffect(()=>{
  const timer=setTimeout(()=>{setPage(1);void load(search,category,budget,sort,1);},240);
  return()=>clearTimeout(timer);
 },[search,category,budget,sort,load]);
 useEffect(()=>{if(chatOpen)chatEnd.current?.scrollIntoView({behavior:'smooth',block:'nearest'});},[history,chatOpen]);
 function pickExample(text){setSearch(text);setDraft(text);setChatOpen(true);listAnchor.current?.scrollIntoView({behavior:'smooth'});}
 function toggleSave(id){setSaved(v=>v.includes(id)?v.filter(x=>x!==id):[...v,id]);}
 function toggleCompare(id){const found=products.find(p=>p.id===id);if(!found)return;setCompare(v=>v.some(x=>x.id===id)?v.filter(x=>x.id!==id):v.length>=3?v:[...v,found]);setCompareOpen(true);}
 async function ask(raw){
  const message=String(raw||'').trim();if(message.length<3||asking)return;
  setDraft('');setChatOpen(true);setHistory(v=>[...v,{role:'user',text:message}]);
  setAsking(true);
  try{
   const r=await fetch('/api/shop/ask',{method:'POST',headers:{'content-type':'application/json'},
    body:JSON.stringify({message,budget:budget?Number(budget):null,category}),cache:'no-store'});
   const data=await r.json();
   if(!r.ok)throw new Error(data.message||data.error||'Η έρευνα απέτυχε.');
   setHistory(v=>[...v,{role:'assistant',text:data.message,items:data.items||[],ai:data.aiModelExecuted===true,explanations:data.explanations||[]}]);
   setSearch(message);
  }catch(e){setHistory(v=>[...v,{role:'assistant',text:(e.message||'Προέκυψε σφάλμα')+' Δοκίμασε ξανά.',items:[],ai:false}]);}
  finally{setAsking(false);}
 }
 function next(){if(loading||!hasMore)return;const n=page+1;setPage(n);void load(search,category,budget,sort,n,true);}
 return <div className={styles.site}>
  <header className={styles.nav}>
   <Link className={styles.brand} href="/marketplace" aria-label="SocialMarket AI αρχική"><span className={styles.brandIcon}>S<span>✳</span></span><span className={styles.brandWords}><strong>socialmarket<span>.ai</span></strong><small>INTELLIGENT SHOPPING · GR</small></span></Link>
   <nav className={styles.navLinks} aria-label="Βασική πλοήγηση"><a href="#discover">Ανακάλυψη</a><a href="#how">Πώς λειτουργεί</a><Link href="/luxecorner">Home collection</Link></nav>
   <button className={styles.topAssistant} type="button" onClick={()=>setChatOpen(true)}><span className={styles.littleSpark}>✳</span> Ρώτησε τον Advisor <span aria-hidden="true">↗</span></button>
  </header>
  <main>
   <section className={styles.hero} aria-labelledby="hero-title">
    <div className={styles.heroInner}>
     <div className={styles.heroCopy}><span className={styles.heroEyebrow}><span className={styles.liveDot}/> Η ΝΕΑ ΕΜΠΕΙΡΙΑ ΕΞΥΠΝΩΝ ΑΓΟΡΩΝ</span>
      <h1 id="hero-title">Λιγότερο ψάξιμο.<br/><em>Καλύτερες αποφάσεις.</em></h1>
      <p>Πες μας τι χρειάζεσαι. Ερευνούμε πραγματικά προϊόντα, συγκρίνουμε επιλογές και εξηγούμε τι γνωρίζουμε — και τι πρέπει να ελέγξεις πριν αγοράσεις.</p>
      <form className={styles.heroSearch} onSubmit={e=>{e.preventDefault();void ask(search||draft);}}>
       <label htmlFor="heroSearch" className={styles.srOnly}>Τι προϊόν ψάχνεις;</label>
       <span aria-hidden="true" className={styles.searchGlyph}>⌕</span>
       <input id="heroSearch" type="search" value={search} onChange={e=>setSearch(e.target.value)} placeholder="π.χ. φωτιστικό για μικρό σαλόνι..." maxLength={180}/>
       <button type="submit" disabled={asking||(search||draft).trim().length<3}>Αναζήτηση <span aria-hidden="true">↗</span></button>
      </form>
      <div className={styles.promptExamples}><span>ΔΟΚΙΜΑΣΕ</span>{EXAMPLES.slice(0,3).map(x=><button type="button" key={x.label} onClick={()=>pickExample(x.text)}>{x.label} <span aria-hidden="true">↗</span></button>)}</div>
     </div>
     <div className={styles.heroGraphic} aria-hidden="true"><div className={styles.heroOrbit}><div className={styles.circle1}/><div className={styles.circle2}/><div className={styles.centerGem}>✳</div><span className={styles.float1}>REAL PRODUCTS</span><span className={styles.float2}>HUMAN-FIRST AI</span><span className={styles.float3}>EVIDENCE LED</span></div><span className={styles.graphicCaption}>FIND · UNDERSTAND · DECIDE</span></div>
    </div>
   </section>
   <div className={styles.trustStrip} aria-label="Διαφάνεια πηγών"><span><b>01</b> Πραγματικές καταχωρίσεις</span><span><b>02</b> Πρωτότυπα affiliate URLs</span><span><b>03</b> Σαφή όρια αξιοπιστίας</span><span><b>04</b> Χωρίς αυτόματες αγορές</span></div>
   <section className={styles.discovery} id="discover" ref={listAnchor} aria-labelledby="discover-title">
    <div className={styles.sectionLead}><div><span className={styles.eyebrow}>ΕΞΕΡΕΥΝΗΣΗ / 001</span><h2 id="discover-title">Επιλογές για <em>διερεύνηση.</em></h2><p>Συγκεντρωμένες από πραγματικά feeds. Χωρίς ψεύτικα ratings, επινοημένες εκπτώσεις ή βεβαιότητα για stock.</p></div>
     <button type="button" className={styles.assistantPrompt} onClick={()=>setChatOpen(true)}><span>✳</span> Χρειάζεσαι καθοδήγηση; <b>Ρώτησε τον Advisor ↗</b></button>
    </div>
    <div className={styles.finderPanel}>
     <div className={styles.filters}><div className={styles.categoryScroller} aria-label="Κατηγορίες">{categories.map(cat=><button key={cat} type="button" className={cat===category?styles.categorySelected:styles.categoryButton} aria-pressed={cat===category} onClick={()=>setCategory(cat)}>{cat}</button>)}</div>
      <div className={styles.filterRow}><label>Μέγιστη τιμή (€)<input type="number" value={budget} min="1" max="100000" placeholder="Χωρίς όριο" onChange={e=>setBudget(e.target.value)}/></label>
       <label>Ταξινόμηση<select value={sort} onChange={e=>setSort(e.target.value)}><option value="relevance">Πιο σχετικά</option><option value="fresh">Πιο πρόσφατα</option><option value="price-asc">Χαμηλότερη τιμή</option><option value="price-desc">Υψηλότερη τιμή</option></select></label>
       <button type="button" className={styles.clearFilters} onClick={()=>{setSearch('');setCategory('Όλα');setBudget('');setSort('relevance');}}>Καθαρισμός ↺</button></div></div>
    </div>
    <div className={styles.resultsHead}><div><span className={styles.eyebrow}>LIVE FEED / CURATED RESEARCH</span><p><strong>{loading&&products.length===0?'…':short(total)}</strong> αποτελέσματα · {short(allCount)} διαθέσιμες προς διερεύνηση καταχωρίσεις</p></div><span className={styles.sourceState}>Πηγή: {sourceStatus==='vmdb-research'?'VMDB + Linkwise':sourceStatus==='limited-linkwise'?'Linkwise':'Έλεγχος σύνδεσης'}</span></div>
    {error&&<div className={styles.error} role="alert"><strong>Πρόβλημα φόρτωσης.</strong> {error}<button type="button" onClick={()=>load(search,category,budget,sort,page)}>Επανάληψη</button></div>}
    {loading&&products.length===0?<div className={styles.loading} role="status">Ανάκτηση πραγματικών προϊόντων…</div>:null}
    {!loading&&products.length===0&&!error?<div className={styles.empty}><span>⌕</span><h3>Δεν βρέθηκαν σχετικά προϊόντα.</h3><p>Δοκίμασε άλλη περιγραφή ή αφαίρεσε το όριο τιμής. Δεν συμπληρώνουμε τα αποτελέσματα με ανύπαρκτες προσφορές.</p><button onClick={()=>{setSearch('');setBudget('');setCategory('Όλα');}}>Επαναφορά φίλτρων</button></div>:null}
    <div className={styles.productGrid}>{products.map((item,index)=><ProductCard key={item.id} item={item} index={index} saved={saved.includes(item.id)} onSave={toggleSave} compared={compare.some(p=>p.id===item.id)} onCompare={toggleCompare}/>)}</div>
    {hasMore&&<div className={styles.moreWrap}><button className={styles.more} type="button" disabled={loading} onClick={next}>{loading?'Φόρτωση…':'Περισσότερες επιλογές'} <span aria-hidden="true">↗</span></button></div>}
    <div className={styles.dataCaveat}><span aria-hidden="true">ⓘ</span><p>Οι τιμές, η διαθεσιμότητα και οι χρόνοι παράδοσης μπορεί να αλλάξουν. Οι σύνδεσμοι είναι affiliate και ενδέχεται να αποφέρουν προμήθεια χωρίς επιπλέον χρέωση για σένα. Έλεγξε τα στοιχεία στο κατάστημα.</p></div>
   </section>
   <section id="how" className={styles.how} aria-labelledby="how-title"><div><span className={styles.eyebrow}>ΜΙΑ ΔΙΑΦΟΡΕΤΙΚΗ ΠΡΟΣΕΓΓΙΣΗ</span><h2 id="how-title">Πρώτα η ανάγκη σου.<br/><em>Μετά το προϊόν.</em></h2></div><div className={styles.howSteps}>
    <article><span>01 /</span><b>Περιέγραψε</b><p>Τι θέλεις να πετύχεις, για ποιον και με ποιο budget.</p></article>
    <article><span>02 /</span><b>Ερεύνησε</b><p>Αντιστοίχιση με πραγματικές εγγραφές, πηγές και συνδέσμους.</p></article>
    <article><span>03 /</span><b>Σύγκρινε</b><p>Τιμή και επιλογές. Τα στοιχεία που λείπουν παραμένουν εμφανή.</p></article>
   </div></section>
  </main>
  <footer className={styles.footer}><div className={styles.footerBrand}>socialmarket<span>.ai</span><p>Εξυπνότερη διερεύνηση. Χωρίς εικασίες.</p></div><div><Link href="/luxecorner">Home collection</Link><Link href="/marketplace/advisor">Shopping Advisor</Link><Link href="/">Control Tower</Link></div><p>© 2026 SocialMarket AI · Η αγορά ολοκληρώνεται μόνο στον έμπορο.</p></footer>
  {!chatOpen&&<button className={styles.chatFab} type="button" onClick={()=>setChatOpen(true)} aria-label="Άνοιγμα Shopping Advisor"><span>✳</span> Ρώτησε το AI</button>}
  {chatOpen&&<aside className={styles.chat} aria-label="Shopping Advisor"><div className={styles.chatTop}><div className={styles.chatAvatar}>✳</div><div><strong>Shopping Advisor</strong><span>Πραγματικά προϊόντα · τεκμηριωμένη αναζήτηση</span></div><button type="button" onClick={()=>setChatOpen(false)} aria-label="Κλείσιμο συνομιλίας">✕</button></div>
    <div className={styles.chatBody} aria-live="polite">{history.map((row,i)=><Message key={i} row={row}/>)}
      {asking&&<div className={styles.agentBubble} role="status">Αναζήτηση προϊόντων και έλεγχος πηγών…</div>}<div ref={chatEnd}/></div>
    <form className={styles.chatForm} onSubmit={e=>{e.preventDefault();void ask(draft);}}><label htmlFor="chatDraft" className={styles.srOnly}>Μήνυμα προς τον Advisor</label><textarea id="chatDraft" value={draft} maxLength={180} rows={2} onChange={e=>setDraft(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();void ask(draft);}}} placeholder="Πες μου τι ψάχνεις…"/><button type="submit" disabled={asking||draft.trim().length<3} aria-label="Αποστολή μηνύματος">↗</button></form>
    <p className={styles.chatFinePrint}>Η AI ανάλυση ενεργοποιείται μόνο με διαθέσιμη υπηρεσία. Οι προσφορές απαιτούν επιβεβαίωση εμπόρου.</p>
  </aside>}
  {compare.length>0&&<button type="button" className={styles.compareFab} onClick={()=>setCompareOpen(v=>!v)}>Σύγκριση <b>{compare.length}/3</b> {compareOpen?'−':'+'}</button>}
  {compareOpen&&<CompareBar items={relevant} onRemove={id=>setCompare(v=>v.filter(x=>x.id!==id))} onClose={()=>setCompareOpen(false)}/>}
 </div>;
}
