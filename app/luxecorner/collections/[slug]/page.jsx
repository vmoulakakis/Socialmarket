import Link from 'next/link';
import {notFound} from 'next/navigation';
import {getLuxeTop100,money,productPath} from '@/lib/luxecorner';
import styles from '../../luxecorner.module.css';

const BASE='https://socialmarket-theta.vercel.app';
const CONFIG={
  'goniakoi-kanapedes':{
    title:'Γωνιακοί Καναπέδες Πολυτελείας | LuxeCorner',
    h1:'Γωνιακοί καναπέδες που ορίζουν τον χώρο.',
    description:'Curated premium γωνιακοί καναπέδες για μεγάλα και statement σαλόνια. Επιλογές με έμφαση σε υφή, κλίμακα και αρχιτεκτονική παρουσία.',
    match:(p)=>/γωνιακ/i.test(p.product_name||'')
  },
  'veloudinoi-kanapedes':{
    title:'Βελούδινοι Καναπέδες & Velvet Sofas | LuxeCorner',
    h1:'Velvet with presence.',
    description:'Βελούδινοι καναπέδες και premium velvet επιλογές για cinematic, elegant και statement interiors.',
    match:(p)=>/βελούδ/i.test(p.product_name||'')
  },
  'kanapedes-krevati':{
    title:'Premium Καναπέδες-Κρεβάτι | LuxeCorner',
    h1:'Sofa beds that still feel designed.',
    description:'Premium καναπέδες-κρεβάτι με editorial αισθητική, για χώρους που χρειάζονται λειτουργικότητα χωρίς να χάνουν χαρακτήρα.',
    match:(p)=>/κρεβάτι|πτυσσόμεν/i.test(p.product_name||'')
  },
  'premium-kanapedes':{
    title:'Premium Καναπέδες Σαλονιού | LuxeCorner',
    h1:'The premium sofa edit.',
    description:'Curated premium καναπέδες σαλονιού με έμφαση σε statement design, υλικά, αναλογίες και υψηλή αισθητική.',
    match:()=>true
  }
};

export function generateStaticParams(){return Object.keys(CONFIG).map(slug=>({slug}));}

export async function generateMetadata({params}){
  const {slug}=await params;const c=CONFIG[slug];
  if(!c)return {robots:{index:false,follow:false}};
  const url=`${BASE}/luxecorner/collections/${slug}`;
  return {
    title:c.title,description:c.description,
    alternates:{canonical:url},
    robots:{index:true,follow:true},
    openGraph:{type:'website',locale:'el_GR',url,siteName:'LuxeCorner',title:c.title,description:c.description,images:[{url:`${BASE}/luxecorner/opengraph-image`,width:1200,height:630}]},
    twitter:{card:'summary_large_image',title:c.title,description:c.description,images:[`${BASE}/luxecorner/opengraph-image`]}
  };
}

export default async function CollectionPage({params}){
  const {slug}=await params;const c=CONFIG[slug];if(!c)notFound();
  let all=[];try{all=await getLuxeTop100()}catch{}
  const products=all.filter(c.match).slice(0,30);
  const url=`${BASE}/luxecorner/collections/${slug}`;
  const schema={'@context':'https://schema.org','@graph':[
    {'@type':'CollectionPage',url,name:c.title,description:c.description,inLanguage:'el-GR'},
    {'@type':'ItemList',name:c.h1,numberOfItems:products.length,itemListElement:products.map((p,i)=>({'@type':'ListItem',position:i+1,url:`${BASE}${productPath(p)}`,name:p.product_name}))}
  ]};
  return <main className={styles.site}>
    <script type="application/ld+json" dangerouslySetInnerHTML={{__html:JSON.stringify(schema)}}/>
    <header className={styles.nav}><Link href="/luxecorner" className={styles.brand}>LUXE<span>CORNER</span></Link><nav><Link href="/luxecorner#edit">The Edit</Link><Link href="/luxecorner#moods">Shop by Mood</Link><Link href="/luxecorner#guide">Guide</Link></nav><Link className={styles.navCta} href="/luxecorner">Home</Link></header>
    <section className={styles.collectionHero}><span>CURATED COLLECTION</span><h1>{c.h1}</h1><p>{c.description}</p></section>
    <section className={styles.collectionSeo}><h2>Πώς επιλέγουμε</h2><p>Η συλλογή δίνει βάρος σε προϊόντα που λειτουργούν ως βασικό design element του σαλονιού: σωστή κλίμακα, καθαρή σιλουέτα, υλικό με οπτική ποιότητα και παρουσία που μπορεί να στηρίξει ολόκληρο interior concept.</p><p>Πριν την αγορά, έλεγξε διαστάσεις, πραγματικό footprint, πρόσβαση στον χώρο και τις τρέχουσες πληροφορίες διαθεσιμότητας στο κατάστημα.</p></section>
    <section className={styles.edit}><div className={styles.sectionHead}><div><span>THE COLLECTION</span><h2>{products.length} curated pieces.</h2></div><p>Κάθε προϊόν οδηγεί σε editorial detail page και από εκεί στο current merchant offer.</p></div><div className={styles.productGrid}>{products.map(p=><article key={`${p.program_id}-${p.source_product_id}`} className={styles.productCard}><Link href={productPath(p)} className={styles.productImage}>{p.image_url?<img src={p.image_url} alt={p.product_name} loading="lazy"/>:<div className={styles.productFallback}/>}<span className={styles.rank}>#{p.rank}</span></Link><div className={styles.productBody}><span className={styles.merchant}>{p.program_name}</span><h3><Link href={productPath(p)}>{p.product_name}</Link></h3><div className={styles.productMeta}><strong>{money(p.price_eur)}</strong><span>Premium edit</span></div><div className={styles.cardActions}><Link href={productPath(p)}>View editorial</Link><a href={p.tracking_url} target="_blank" rel="sponsored noopener">Availability ↗</a></div></div></article>)}</div></section>
    <footer className={styles.footer}><div><b>LUXECORNER</b><p>Curated premium living.</p></div><p>Affiliate disclosure: ορισμένοι σύνδεσμοι μπορεί να αποφέρουν προμήθεια χωρίς πρόσθετη χρέωση για εσένα.</p></footer>
  </main>;
}
