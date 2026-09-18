import Link from 'next/link';
import {notFound} from 'next/navigation';
import {getLuxeProduct,money} from '@/lib/luxecorner';
import styles from '../../luxecorner.module.css';

const BASE='https://socialmarket-theta.vercel.app';

export async function generateMetadata({params}){
  const {id}=await params;
  let p=null;try{p=await getLuxeProduct(id)}catch{}
  if(!p)return {title:'Product | LuxeCorner',robots:{index:false,follow:false}};
  const title=`${p.product_name} | LuxeCorner`;
  const description=`${p.product_name}: curated premium επιλογή για statement σαλόνι. Δες τιμή, διαθεσιμότητα και editorial buying context.`;
  const canonical=`${BASE}/luxecorner/product/${encodeURIComponent(String(p.source_product_id))}`;
  return {
    title,description,alternates:{canonical},
    robots:{index:true,follow:true,googleBot:{index:true,follow:true,'max-image-preview':'large'}},
    openGraph:{type:'website',locale:'el_GR',url:canonical,siteName:'LuxeCorner',title,description,images:p.image_url?[{url:p.image_url,alt:p.product_name}]:[{url:`${BASE}/luxecorner/opengraph-image`}]},
    twitter:{card:'summary_large_image',title,description,images:p.image_url?[p.image_url]:[`${BASE}/luxecorner/opengraph-image`]}
  };
}

export default async function LuxeProductPage({params}){
  const {id}=await params;
  let p=null;try{p=await getLuxeProduct(id)}catch{}
  if(!p)notFound();

  const url=`${BASE}/luxecorner/product/${encodeURIComponent(String(p.source_product_id))}`;
  const schema={
    '@context':'https://schema.org',
    '@graph':[
      {
        '@type':'Product',
        '@id':`${url}#product`,
        name:p.product_name,
        image:p.image_url?[p.image_url]:undefined,
        category:p.category_raw||'Premium sofas',
        brand:{'@type':'Brand',name:p.program_name||'LuxeCorner curated partner'},
        offers:{
          '@type':'Offer',url:p.tracking_url,priceCurrency:'EUR',price:Number(p.price_eur),
          availability:'https://schema.org/InStock',
          seller:{'@type':'Organization',name:p.program_name||'Partner store'}
        }
      },
      {
        '@type':'BreadcrumbList',
        itemListElement:[
          {'@type':'ListItem',position:1,name:'LuxeCorner',item:`${BASE}/luxecorner`},
          {'@type':'ListItem',position:2,name:p.product_name,item:url}
        ]
      }
    ]
  };

  return <main className={styles.site}>
    <script type="application/ld+json" dangerouslySetInnerHTML={{__html:JSON.stringify(schema)}}/>
    <header className={styles.nav}>
      <Link href="/luxecorner" className={styles.brand}>LUXE<span>CORNER</span></Link>
      <nav><Link href="/luxecorner#edit">The Edit</Link><Link href="/luxecorner#moods">Shop by Mood</Link><Link href="/luxecorner#guide">Guide</Link></nav>
      <Link className={styles.navCta} href="/luxecorner">Back to edit</Link>
    </header>

    <section className={styles.productHero}>
      <div className={styles.detailMedia}>{p.image_url?<img src={p.image_url} alt={p.product_name}/>:<div className={styles.productFallback}/>}</div>
      <div className={styles.detailCopy}>
        <span className={styles.eyebrow}>CURATED PICK · #{p.rank}</span>
        <h1>{p.product_name}</h1>
        <p className={styles.detailLead}>Ένα statement piece με premium κλίμακα και strong visual presence — για σαλόνι που θέλει να χτίσει όλη την αισθητική του γύρω από ένα κεντρικό έπιπλο.</p>
        <div className={styles.detailPrice}>{money(p.price_eur)}</div>
        <a className={styles.detailCta} href={p.tracking_url} target="_blank" rel="sponsored noopener">See current price & availability ↗</a>
        <small>Η τελική τιμή, διαθεσιμότητα και όροι αγοράς επιβεβαιώνονται στο κατάστημα.</small>
      </div>
    </section>

    <section className={styles.detailEditorial}>
      <article><span>WHY IT WORKS</span><h2>Room-defining scale.</h2><p>Η μεγάλη κλίμακα λειτουργεί καλύτερα όταν ο καναπές αντιμετωπίζεται ως αρχιτεκτονικό στοιχείο: αφήνεις καθαρές οπτικές γραμμές, περιορίζεις τα ανταγωνιστικά statement pieces και χτίζεις το styling γύρω από την υφή του.</p></article>
      <article><span>STYLE DIRECTION</span><h2>Keep the rest intentional.</h2><p>Συνδύασε με ήσυχα υλικά, χαμηλά τραπεζάκια, layered φωτισμό και περιορισμένη χρωματική παλέτα. Έτσι το αποτέλεσμα δείχνει curated και όχι φορτωμένο.</p></article>
      <article><span>BUYING NOTE</span><h2>Measure before desire wins.</h2><p>Έλεγξε είσοδο, ασανσέρ, πόρτες, διάδρομο και τελικό footprint. Σε high-ticket oversized έπιπλα, η πραγματική πρόσβαση στον χώρο είναι μέρος της αγοράς.</p></article>
    </section>

    <section className={styles.finalCta}>
      <span>THE DECISION</span>
      <h2>If it defines the room,<br/>it deserves the space.</h2>
      <a className={styles.primary} href={p.tracking_url} target="_blank" rel="sponsored noopener">View at {p.program_name||'partner store'} ↗</a>
    </section>

    <footer className={styles.footer}><div><b>LUXECORNER</b><p>Curated premium living.</p></div><p>Affiliate disclosure: ενδέχεται να λαμβάνουμε προμήθεια όταν πραγματοποιείται αγορά μέσω επιλεγμένων συνδέσμων, χωρίς πρόσθετη χρέωση για εσένα.</p></footer>
  </main>;
}
