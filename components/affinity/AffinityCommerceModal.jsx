'use client';

import {useEffect,useMemo} from 'react';
import styles from './AffinityCommerceModal.module.css';

const clean=v=>String(v||'').trim();
const money=v=>Number(v||0).toLocaleString('el-GR',{style:'currency',currency:'EUR',maximumFractionDigits:2});

export default function AffinityCommerceModal({item,open,onClose,landingUrl}){
 const target=clean(item?.tracking_url);
 const pageUrl=useMemo(()=>landingUrl||((typeof window!=='undefined'&&item?.id)?`${window.location.origin}/marketplace/${encodeURIComponent(String(item.id))}`:''),[landingUrl,item?.id]);
 const qr=target?`https://api.qrserver.com/v1/create-qr-code/?size=360x360&margin=14&data=${encodeURIComponent(target)}`:'';
 const shareText=clean(item?.solution_statement)||clean(item?.pain_statement)||`Δες το ${clean(item?.product_name)||'AFFINITY find'}`;

 useEffect(()=>{
  if(!open)return;
  const before=document.body.style.overflow;document.body.style.overflow='hidden';
  const key=e=>{if(e.key==='Escape')onClose?.()};window.addEventListener('keydown',key);
  return()=>{document.body.style.overflow=before;window.removeEventListener('keydown',key)};
 },[open,onClose]);

 if(!open||!item)return null;
 const shareTo=url=>window.open(url,'_blank','noopener,noreferrer,width=760,height=720');
 const encodedUrl=encodeURIComponent(pageUrl);const encodedText=encodeURIComponent(`${item.product_name} — ${shareText}`);
 const nativeShare=async()=>{if(navigator.share){try{await navigator.share({title:item.product_name,text:shareText,url:pageUrl});return}catch{}}await navigator.clipboard?.writeText(pageUrl)};
 const copyOffer=async()=>{if(target)await navigator.clipboard?.writeText(target)};

 return <div className={styles.backdrop} role="presentation" onMouseDown={e=>{if(e.target===e.currentTarget)onClose?.()}}>
  <section className={styles.modal} role="dialog" aria-modal="true" aria-label={`AFFINITY offer — ${item.product_name}`}>
   <button className={styles.close} onClick={onClose} aria-label="Κλείσιμο">×</button>
   <div className={styles.visual}>
    {item.image_url?<img src={item.image_url} alt={item.product_name}/>:<div className={styles.fallback}>AFFINITY<br/>BETTER<br/>EVERYDAY</div>}
    <span>CURATED SOLUTION</span>
   </div>
   <div className={styles.content}>
    <small className={styles.eyebrow}>AFFINITY · SHOP THE SOLUTION</small>
    <h2>{item.product_name}</h2>
    <p className={styles.promise}>{shareText}</p>
    {Number(item.sale_price_eur)>0&&<div className={styles.price}><span>ένδειξη τιμής</span><strong>{money(item.sale_price_eur)}</strong></div>}
    <div className={styles.actions}>
     {target&&<a href={target} target="_blank" rel="sponsored noreferrer">Δες την προσφορά <b>↗</b></a>}
     <button onClick={nativeShare}>Μοιράσου το case ↗</button>
    </div>
    <div className={styles.shareGrid}>
     <button onClick={()=>shareTo(`https://wa.me/?text=${encodedText}%0A${encodedUrl}`)}>WhatsApp</button>
     <button onClick={()=>shareTo(`https://www.facebook.com/sharer/sharer.php?u=${encodedUrl}`)}>Facebook</button>
     <button onClick={()=>shareTo(`https://www.linkedin.com/sharing/share-offsite/?url=${encodedUrl}`)}>LinkedIn</button>
     <button onClick={()=>shareTo(`https://twitter.com/intent/tweet?text=${encodedText}&url=${encodedUrl}`)}>X / Twitter</button>
    </div>
    <div className={styles.qrRow}>
     {qr&&<img src={qr} alt="QR προς την τρέχουσα προσφορά"/>}
     <div><b>Scan & shop</b><p>Το QR οδηγεί στο ενεργό tracking URL της προσφοράς. Για social sharing χρησιμοποιούμε τη branded AFFINITY case page.</p>{target&&<button onClick={copyOffer}>Αντιγραφή offer link</button>}</div>
    </div>
    <p className={styles.disclosure}>Τιμή, διαθεσιμότητα, μεταφορικά και όροι μπορεί να αλλάξουν στον τελικό προορισμό. Ορισμένοι σύνδεσμοι είναι affiliate links και μπορεί να υποστηρίζουν το AFFINITY χωρίς επιπλέον κόστος για εσένα.</p>
   </div>
  </section>
 </div>
}
