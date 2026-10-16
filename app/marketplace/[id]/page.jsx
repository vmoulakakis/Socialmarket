import Link from 'next/link';
import {notFound} from 'next/navigation';
import {getLuxeProduct,money} from '@/lib/luxecorner';
import styles from '@/components/catalog/catalog.module.css';
function safeUrl(v){try{const u=new URL(v);return ['https:','http:'].includes(u.protocol)?u.href:null;}catch{return null;}}
export default async function Page({params}){
 const {id}=await params;
 const product=await getLuxeProduct(id);
 if(!product)notFound();
 const offer=safeUrl(product.tracking_url);
 return <main className={styles.page}><header className={styles.nav}><Link href="/marketplace">SOCIALMARKET</Link><Link href="/marketplace">← Κατάλογος</Link></header><section className={styles.detail}><img src={product.image_url} alt={product.product_name}/><div><small>{product.program_name}</small><h1>{product.product_name}</h1><p>{product.category_raw}</p><strong>{product.price_eur==null?'Τιμή στο κατάστημα':money(product.price_eur)}</strong><p>Στοιχεία από τον κατάλογο του συνεργαζόμενου καταστήματος. Επιβεβαίωσε διαστάσεις, χαρακτηριστικά, τελική τιμή, μεταφορικά και διαθεσιμότητα πριν από την αγορά.</p>{offer&&<a className={styles.button} href={offer} target="_blank" rel="sponsored noopener noreferrer">Δες στο κατάστημα ↗</a>}<p>Affiliate σύνδεσμος: ενδέχεται να λάβουμε προμήθεια χωρίς επιπλέον χρέωση για εσένα.</p></div></section></main>;
}
