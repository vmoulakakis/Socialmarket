import Link from 'next/link';
import {getLuxeTop100,money,productPath} from '@/lib/luxecorner';
import styles from './luxecorner.module.css';

const BASE='https://socialmarket-theta.vercel.app';
const TITLE='LuxeCorner | Premium Γωνιακοί Καναπέδες & Luxury Sofa Edit';
const DESCRIPTION='Curated premium γωνιακοί καναπέδες, βελούδινα sofas και statement κομμάτια για elegant σαλόνια. Editorial επιλογές, guides και άμεση πρόσβαση στις κορυφαίες προτάσεις.';

export const metadata={
  title:TITLE,
  description:DESCRIPTION,
  alternates:{canonical:`${BASE}/luxecorner`},
  robots:{index:true,follow:true,googleBot:{index:true,follow:true,'max-image-preview':'large','max-snippet':-1,'max-video-preview':-1}},
  openGraph:{
    type:'website',locale:'el_GR',url:`${BASE}/luxecorner`,siteName:'LuxeCorner',
    title:'LuxeCorner — The sofa that changes the whole room',
    description:DESCRIPTION,
    images:[{url:`${BASE}/luxecorner/opengraph-image`,width:1200,height:630,alt:'LuxeCorner premium sofa editorial'}]
  },
  twitter:{card:'summary_large_image',title:'LuxeCorner — Curated Luxury Sofas',description:DESCRIPTION,images:[`${BASE}/luxecorner/opengraph-image`]}
};

const collections=[
 ['Statement Corners','Γωνιακοί καναπέδες που δίνουν ταυτότητα και αρχιτεκτονικό βάρος στον χώρο.','/luxecorner/collections/goniakoi-kanapedes'],
 ['Velvet Icons','Βελούδο, βαθιές υφές και editorial παρουσία για πιο cinematic σαλόνια.','/luxecorner/collections/veloudinoi-kanapedes'],
 ['Soft Luxury','Λινό, ουδέτερες αποχρώσεις και ήρεμη πολυτέλεια χωρίς υπερβολή.','/luxecorner/collections/premium-kanapedes'],
 ['Sofa Beds','Πρακτικότητα που δεν δείχνει πρακτική: sofa beds με premium αισθητική.','/luxecorner/collections/kanapedes-krevati']
];
const faqs=[
 ['Πώς επιλέγονται οι καναπέδες στη LuxeCorner;','Με editorial κριτήρια όπως κλίμακα, σιλουέτα, υλικό, οπτική παρουσία και suitability για premium living spaces.'],
 ['Οι τιμές είναι πάντα ίδιες;','Όχι. Οι τιμές και η διαθεσιμότητα μπορούν να αλλάζουν και επιβεβαιώνονται πάντα στο συνεργαζόμενο κατάστημα.'],
 ['Τι πρέπει να μετρήσω πριν αγοράσω μεγάλο γωνιακό καναπέ;','Το τελικό footprint, τα περάσματα, τις πόρτες, το ασανσέρ ή κλιμακοστάσιο και τις βασικές οπτικές γραμμές του σαλονιού.'],
 ['Τα links είναι affiliate;','Ορισμένοι σύνδεσμοι είναι affiliate links και μπορεί να αποφέρουν προμήθεια χωρίς πρόσθετη χρέωση για τον αγοραστή.']
];

export default async function LuxeCornerPage(){
  let products=[];
  try{products=await getLuxeTop100()}catch{}
  const hero=products[0];
  const featured=products.slice(0,12);
  const schema={
    '@context':'https://schema.org',
    '@graph':[
      {'@type':'WebSite','@id':`${BASE}/luxecorner#website`,url:`${BASE}/luxecorner`,name:'LuxeCorner',inLanguage:'el-GR'},
      {'@type':'CollectionPage','@id':`${BASE}/luxecorner#page`,url:`${BASE}/luxecorner`,name:TITLE,description:DESCRIPTION,isPartOf:{'@id':`${BASE}/luxecorner#website`}},
      {'@type':'ItemList',name:'LuxeCorner Premium Sofa Edit',numberOfItems:featured.length,itemListElement:featured.map((p,i)=>({
        '@type':'ListItem',position:i+1,url:`${BASE}${productPath(p)}`,name:p.product_name
      }))},
      {'@type':'FAQPage',mainEntity:faqs.map(([q,a])=>({'@type':'Question',name:q,acceptedAnswer:{'@type':'Answer',text:a}}))}
    ]
  };

  return <main className={styles.site}>
    <script type="application/ld+json" dangerouslySetInnerHTML={{__html:JSON.stringify(schema)}}/>
    <header className={styles.nav}>
      <Link href="/luxecorner" className={styles.brand}>LUXE<span>CORNER</span></Link>
      <nav><a href="#edit">The Edit</a><a href="#moods">Shop by Mood</a><a href="#guide">Guide</a></nav>
      <a className={styles.navCta} href="#edit">Explore</a>
    </header>

    <section className={styles.hero}>
      <div className={styles.heroMedia}>
        {hero?.image_url?<img src={hero.image_url} alt={hero.product_name}/>:<div className={styles.heroFallback}/>}
        <div className={styles.scrim}/>
      </div>
      <div className={styles.heroCopy}>
        <span className={styles.eyebrow}>CURATED LUXURY SOFA EDIT</span>
        <h1>The sofa that changes<br/>the whole room.</h1>
        <p>Premium γωνιακοί καναπέδες και statement pieces επιλεγμένα για χώρους που θέλουν παρουσία, υφή και χαρακτήρα.</p>
        <div className={styles.heroActions}><a href="#edit" className={styles.primary}>Explore the Edit</a><a href="#guide" className={styles.secondary}>Find your style</a></div>
      </div>
      <div className={styles.heroNote}>Editorial curation · Live availability · Affiliate links</div>
    </section>

    <section className={styles.intro}>
      <span>DESIGN, NOT JUST FURNITURE</span>
      <h2>Δεν ψάχνεις απλώς καναπέ.<br/>Ψάχνεις το κομμάτι που ορίζει τον χώρο.</h2>
      <p>Η LuxeCorner οργανώνει premium επιλογές με βάση σιλουέτα, υλικό, κλίμακα και οπτικό impact — ώστε η έρευνα να μοιάζει περισσότερο με interior edit και λιγότερο με κατάλογο.</p>
    </section>

    <section id="moods" className={styles.moods}>
      {collections.map(([title,copy,href],i)=><article key={title} className={styles.moodCard}>
        <span>0{i+1}</span><h3>{title}</h3><p>{copy}</p><Link href={href}>Discover →</Link>
      </article>)}
    </section>

    <section id="edit" className={styles.edit}>
      <div className={styles.sectionHead}><div><span>THE MOST WANTED</span><h2>Statement pieces worth building a room around.</h2></div><p>Live curated selection από το current product universe. Κάθε CTA οδηγεί μέσω του affiliate tracking route στο merchant.</p></div>
      <div className={styles.productGrid}>
        {featured.map((p,i)=><article key={`${p.program_id}-${p.source_product_id}`} className={styles.productCard}>
          <Link href={productPath(p)} className={styles.productImage}>
            {p.image_url?<img src={p.image_url} alt={p.product_name} loading={i<4?'eager':'lazy'}/>:<div className={styles.productFallback}/>}
            <span className={styles.rank}>#{p.rank}</span>
          </Link>
          <div className={styles.productBody}>
            <span className={styles.merchant}>{p.program_name||'Curated partner'}</span>
            <h3><Link href={productPath(p)}>{p.product_name}</Link></h3>
            <div className={styles.productMeta}><strong>{money(p.price_eur)}</strong><span>Curated premium pick</span></div>
            <div className={styles.cardActions}><Link href={productPath(p)}>View editorial</Link><a href={p.tracking_url} target="_blank" rel="sponsored noopener">See price & availability ↗</a></div>
          </div>
        </article>)}
      </div>
    </section>

    <section id="guide" className={styles.guide}>
      <div><span>SOFA FIT GUIDE</span><h2>Buy for the room you want to create.</h2></div>
      <div className={styles.guideGrid}>
        <article><b>01 · Scale</b><h3>Ξεκίνα από τον χώρο.</h3><p>Μέτρα πραγματικά περάσματα, ανοίγματα και οπτικές γραμμές — όχι μόνο το μήκος του τοίχου.</p></article>
        <article><b>02 · Texture</b><h3>Διάλεξε την αίσθηση.</h3><p>Βελούδο για drama, λινό για soft luxury, μπουκλέ για tactile modern χαρακτήρα.</p></article>
        <article><b>03 · Presence</b><h3>Άφησε τον καναπέ να ηγηθεί.</h3><p>Σε premium σαλόνια, η σωστή σιλουέτα μπορεί να λειτουργήσει σαν το βασικό αρχιτεκτονικό στοιχείο.</p></article>
      </div>
    </section>

    <section className={styles.faq}><div><span>BUYING QUESTIONS</span><h2>Know before you choose.</h2></div><div>{faqs.map(([q,a])=><details key={q}><summary>{q}</summary><p>{a}</p></details>)}</div></section>

    <section className={styles.finalCta}>
      <span>MAKE THE ROOM</span>
      <h2>Choose the piece that gives<br/>your living room its character.</h2>
      <a href="#edit" className={styles.primary}>See the premium edit</a>
    </section>

    <footer className={styles.footer}>
      <div><b>LUXECORNER</b><p>Curated premium living.</p></div>
      <p>Οι σύνδεσμοι προϊόντων μπορεί να είναι affiliate links. Η τελική τιμή και διαθεσιμότητα επιβεβαιώνονται στο κατάστημα.</p>
    </footer>
  </main>
}
