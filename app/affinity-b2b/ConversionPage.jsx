'use client';

import { useMemo, useState } from 'react';
import { motion } from 'motion/react';
import Link from 'next/link';

const fade = { hidden:{opacity:0,y:24}, show:{opacity:1,y:0,transition:{duration:.55}} };

export default function ConversionPage({ product, record }) {
  const base = Number(record?.salePrice || 0);
  const offer = record?.promotionLink || record?.detailUrl || '#';
  const image = record?.mainImage;
  const shop = record?.shopName || 'Marketplace seller';
  const [reference,setReference] = useState('');
  const [extras,setExtras] = useState('0');
  const landed = base + (Number(extras)||0);
  const saving = useMemo(()=>Math.max(0,(Number(reference)||0)-landed),[reference,landed]);
  const savingPct = Number(reference)>0 ? saving/Number(reference)*100 : 0;
  const benchmark = product.slug==='dz400-double-chamber-vacuum'
    ? 'Στην ελληνική αγορά εμφανίζονται συγκρίσιμα DZ-400 vacuum συστήματα περίπου από €2.039 έως €2.250. Δεν θεωρούνται απαραίτητα ίδιο SKU ή ίδιο configuration.'
    : product.slug==='greenhouse-hmi-plc-controller'
    ? 'Στην ευρωπαϊκή αγορά υπάρχουν 7″ HMI/PLC λύσεις περίπου €425–€552, επομένως εδώ η σωστή απόφαση εξαρτάται περισσότερο από I/O, sensors, integration και support παρά μόνο από την τιμή.'
    : 'Δεν χρησιμοποιούμε μη επαληθευμένη “τοπική τιμή” ως τεχνητό anchor. Ζήτησε 1–2 συγκρίσιμες προσφορές και βάλε τις στον calculator πριν αποφασίσεις.';

  return <div className="b2b" style={{'--accent':product.accent}}>
    <header className="topbar">
      <Link href="/affinity-b2b" className="brand"><span className="logo">A</span><span>AFFINITY <small>SMART B2B BUYING</small></span></Link>
      <nav><a href="#economics">Κέρδος</a><a href="#risk">Έλεγχος</a><a href="#faq">FAQ</a></nav>
      <a className="topCta" href={offer} target="_blank" rel="sponsored nofollow noopener">Έλεγχος προσφοράς ↗</a>
    </header>

    <main>
      <section className="hero">
        <motion.div initial="hidden" animate="show" variants={fade}>
          <div className="eyebrow">{product.eyebrow}</div>
          <h1>{product.headline}</h1>
          <p className="lead">{product.subheadline}</p>
          <div className="promise"><b>Το μήνυμα είναι απλό:</b> αγόρασε σωστά, μείωσε το συνολικό κόστος και κράτησε περισσότερο περιθώριο στην επιχείρηση.</div>
          <div className="ctaRow">
            <a className="primary" href={offer} target="_blank" rel="sponsored nofollow noopener">Δες τρέχουσα τιμή & όρους <span>→</span></a>
            <a className="secondary" href="#economics">Υπολόγισε το όφελος</a>
          </div>
          <p className="fine">Η τελική τιμή, αποστολή, ΦΠΑ, τελωνείο, warranty και return policy επιβεβαιώνονται πάντα στη σελίδα του πωλητή πριν την αγορά.</p>
        </motion.div>

        <motion.div initial={{opacity:0,scale:.95}} animate={{opacity:1,scale:1}} transition={{duration:.7}} className="visual">
          {image && <img src={image} alt={product.shortName}/>} 
          <div className="price"><small>Τιμή snapshot</small><strong>€{base.toLocaleString('el-GR',{minimumFractionDigits:2,maximumFractionDigits:2})}</strong><span>{shop}</span></div>
          <div className="badge">B2B VALUE CHECK</div>
        </motion.div>
      </section>

      <section className="economics" id="economics">
        <div className="sectionTitle"><span>ECONOMICS FIRST</span><h2>Ο έξυπνος έμπορος δεν κοιτάζει μόνο τιμή. Κοιτάζει landed cost και περιθώριο.</h2><p>{benchmark}</p></div>
        <div className="calc">
          <div className="calcInputs">
            <label>Τιμή προϊόντος<input value={base.toFixed(2)} readOnly/></label>
            <label>Μεταφορικά / δασμοί / λοιπά €<input value={extras} onChange={e=>setExtras(e.target.value)} inputMode="decimal"/></label>
            <label>Συγκρίσιμη τοπική/ευρωπαϊκή προσφορά €<input value={reference} onChange={e=>setReference(e.target.value)} placeholder="π.χ. 2200" inputMode="decimal"/></label>
          </div>
          <div className="calcResult">
            <small>Εκτιμώμενο landed cost</small><strong>€{landed.toLocaleString('el-GR',{minimumFractionDigits:2,maximumFractionDigits:2})}</strong>
            <div className="divider"/>
            <small>Πιθανή εξοικονόμηση έναντι δικής σου προσφοράς</small><b>{Number(reference)>0 ? `€${saving.toLocaleString('el-GR',{minimumFractionDigits:2,maximumFractionDigits:2})} • ${savingPct.toFixed(1)}%` : 'Βάλε συγκρίσιμη τιμή'}</b>
          </div>
        </div>
      </section>

      <section className="pain">
        <div className="sectionTitle"><span>PROFIT GAP</span><h2>Το κέρδος χάνεται συνήθως σε τέσσερα σημεία.</h2><p>{product.pain}</p></div>
        <div className="grid4">{product.roiLabels.map((x,i)=><motion.article key={x} whileHover={{y:-6}}><i>0{i+1}</i><h3>{x}</h3><p>Υπολόγισε το πραγματικό κόστος αυτού του σημείου στην επιχείρησή σου πριν συγκρίνεις λύσεις.</p></motion.article>)}</div>
      </section>

      <section className="specBand">{product.benefits.map((b,i)=><div key={b}><span>{['◉','↗','⌁','✓'][i]}</span><b>{b}</b></div>)}</section>

      <section className="risk" id="risk">
        <div className="sectionTitle"><span>SMART BUYER CHECK</span><h2>Εμπιστοσύνη δεν σημαίνει “πίστεψέ μας”. Σημαίνει ότι ξέρεις ακριβώς τι πρέπει να ελέγξεις.</h2></div>
        <div className="checkGrid">
          <article><b>01 • Seller</b><p>Πωλητής που εμφανίζεται στο offer: <strong>{shop}</strong>. Έλεγξε rating, χρόνια λειτουργίας, πρόσφατες κριτικές και αριθμό παραγγελιών.</p></article>
          <article><b>02 • Europe / warehouse</b><p>Δεν δηλώνουμε “πιστοποιημένο ευρωπαϊκό seller” χωρίς ανεξάρτητη επιβεβαίωση. Έλεγξε Ship From, χώρα αποστολής και πραγματικό ETA στο checkout.</p></article>
          <article><b>03 • Taxes & landed cost</b><p>Επιβεβαίωσε ΦΠΑ, δασμούς, μεταφορικά και τυχόν έξοδα εκτελωνισμού. Η φθηνότερη τιμή προϊόντος δεν σημαίνει πάντα χαμηλότερο landed cost.</p></article>
          <article><b>04 • Warranty & service</b><p>Ζήτησε γραπτά warranty terms, ανταλλακτικά, τεχνική υποστήριξη, manuals και διαδικασία επιστροφής πριν πληρώσεις.</p></article>
          <article><b>05 • Exact configuration</b><p>Σύγκρινε SKU, ισχύ, τάση, διαστάσεις, accessories, sensors, connectors και συμβατότητα. Μην συγκρίνεις διαφορετικά bundles σαν να είναι ίδια.</p></article>
          <article><b>06 • Payment protection</b><p>Ολοκλήρωσε την αγορά μόνο μέσα από την πλατφόρμα και κράτησε όλη την επικοινωνία και τις τεχνικές συμφωνίες γραπτώς.</p></article>
        </div>
      </section>

      <section className="buyer">
        <div><span>WHO THIS IS FOR</span><h2>Για επαγγελματίες που αγοράζουν με αριθμούς — όχι με ενθουσιασμό.</h2><p>{product.buyer}</p></div>
        <aside><small>Decision rule</small><strong>Αν το πλήρες landed cost είναι χαμηλότερο και οι όροι/τεχνική κάλυψη είναι επαρκείς, τότε η διαφορά γίνεται πραγματικό περιθώριο κέρδους.</strong></aside>
      </section>

      <section className="faq" id="faq">
        <div className="sectionTitle"><span>DUE DILIGENCE FAQ</span><h2>Οι ερωτήσεις που κάνει ο σοβαρός B2B αγοραστής.</h2></div>
        <div className="faqGrid">{product.faq.map(([q,a],i)=><details key={q}><summary><span>0{i+1}</span>{q}</summary><p>{a}</p></details>)}</div>
      </section>

      <section className="final">
        <div><span>FINAL CHECK</span><h2>Το deal αξίζει μόνο όταν βγαίνει το συνολικό κόστος.</h2><p>Άνοιξε την τρέχουσα προσφορά, επιβεβαίωσε ακριβές configuration, seller, warehouse, μεταφορικά, φόρους και warranty. Μετά βάλε το τελικό ποσό στον calculator.</p></div>
        <a href={offer} target="_blank" rel="sponsored nofollow noopener">Έλεγξε την πραγματική προσφορά <b>↗</b></a>
      </section>
    </main>

    <footer><Link href="/affinity-b2b">← Όλες οι B2B ευκαιρίες</Link><span>Smart sourcing • Cost discipline • Margin protection</span></footer>

    <style jsx global>{`
      :root{color-scheme:dark}*{box-sizing:border-box}.b2b{min-height:100vh;background:#06101b;color:#f5f8fc;font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}.topbar{height:76px;position:sticky;top:0;z-index:40;display:flex;align-items:center;justify-content:space-between;padding:0 max(24px,calc((100vw - 1220px)/2));background:rgba(6,16,27,.86);backdrop-filter:blur(18px);border-bottom:1px solid #ffffff12}.brand{display:flex;align-items:center;gap:10px;color:white;text-decoration:none;font-weight:900;letter-spacing:.08em}.brand small{display:block;font-size:8px;letter-spacing:.18em;color:#8092a5}.logo{width:38px;height:38px;border-radius:12px;background:var(--accent);display:grid;place-items:center;color:#06101b}.topbar nav{display:flex;gap:26px}.topbar nav a{color:#c6d0dc;text-decoration:none;font-size:14px}.topCta,.primary{background:var(--accent);color:#06101b!important;text-decoration:none;font-weight:900;padding:14px 20px;border-radius:13px}.b2b main{max-width:1220px;margin:auto;padding:42px 24px 90px}.hero{min-height:640px;display:grid;grid-template-columns:1.06fr .94fr;gap:46px;align-items:center}.eyebrow,.sectionTitle span,.buyer>div>span,.final span{font-size:12px;letter-spacing:.2em;font-weight:900;color:var(--accent)}h1{font-size:clamp(46px,6.2vw,82px);line-height:.95;letter-spacing:-.055em;margin:17px 0 22px}.lead{font-size:20px;line-height:1.55;color:#b5c2d0}.promise{margin-top:24px;padding:18px 20px;border-left:4px solid var(--accent);background:#ffffff08;border-radius:0 14px 14px 0;color:#d8e1eb;line-height:1.5}.ctaRow{display:flex;gap:12px;flex-wrap:wrap;margin-top:28px}.primary,.secondary{display:inline-flex;align-items:center;gap:12px;padding:17px 21px}.secondary{border:1px solid #ffffff26;border-radius:13px;color:white;text-decoration:none}.fine{font-size:12px;color:#74879a;line-height:1.5;max-width:650px}.visual{min-height:520px;position:relative;display:grid;place-items:center;background:radial-gradient(circle at 50% 45%,color-mix(in srgb,var(--accent) 18%,transparent),transparent 62%)}.visual img{max-width:92%;max-height:430px;object-fit:contain;filter:drop-shadow(0 34px 54px #0009)}.price{position:absolute;left:0;bottom:38px;background:#0b1b2bdc;border:1px solid #ffffff1c;border-radius:18px;padding:17px 20px;backdrop-filter:blur(18px)}.price small,.price span{display:block;color:#889bad;font-size:11px}.price strong{display:block;font-size:31px;margin:3px 0}.badge{position:absolute;right:10px;top:42px;padding:10px 13px;border:1px solid color-mix(in srgb,var(--accent) 42%,transparent);border-radius:999px;color:var(--accent);font-size:11px;font-weight:900;letter-spacing:.15em}.sectionTitle{max-width:880px}.sectionTitle h2,.buyer h2,.final h2{font-size:clamp(34px,4vw,56px);line-height:1.03;letter-spacing:-.04em;margin:12px 0 14px}.sectionTitle p,.buyer p,.final p{font-size:17px;line-height:1.65;color:#97a9ba}.economics,.pain,.risk,.faq{padding:90px 0}.calc{margin-top:34px;display:grid;grid-template-columns:1.1fr .9fr;border:1px solid #ffffff13;border-radius:24px;overflow:hidden;background:#091727}.calcInputs{padding:26px;display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.calcInputs label{font-size:12px;color:#8fa1b5}.calcInputs input{width:100%;margin-top:8px;background:#06101b;border:1px solid #ffffff18;color:white;border-radius:12px;padding:14px;font-size:16px}.calcResult{padding:28px;background:linear-gradient(145deg,color-mix(in srgb,var(--accent) 14%,#0b1b2b),#0b1b2b)}.calcResult small{display:block;color:#8fa1b5}.calcResult strong{display:block;font-size:35px;margin:5px 0 18px}.calcResult b{display:block;font-size:24px;color:var(--accent);margin-top:5px}.divider{height:1px;background:#ffffff15;margin:18px 0}.grid4,.checkGrid{display:grid;grid-template-columns:repeat(4,1fr);gap:15px;margin-top:34px}.grid4 article,.checkGrid article{padding:24px;border:1px solid #ffffff10;border-radius:20px;background:linear-gradient(145deg,#ffffff09,#ffffff03)}.grid4 i{font-style:normal;color:var(--accent);font-weight:900}.grid4 h3{font-size:21px;margin:38px 0 8px}.grid4 p,.checkGrid p{color:#879aab;line-height:1.55}.specBand{display:grid;grid-template-columns:repeat(4,1fr);border:1px solid #ffffff10;border-radius:20px;overflow:hidden;background:#ffffff0d;gap:1px}.specBand>div{padding:27px;background:#0a1827;display:flex;align-items:center;gap:13px}.specBand span{color:var(--accent);font-size:24px}.checkGrid{grid-template-columns:repeat(3,1fr)}.checkGrid b{color:#e8eef5}.checkGrid strong{color:white}.buyer{padding:92px 0;display:grid;grid-template-columns:1.1fr .9fr;gap:45px;align-items:center}.buyer aside{padding:30px;border-radius:24px;border:1px solid color-mix(in srgb,var(--accent) 30%,transparent);background:linear-gradient(145deg,color-mix(in srgb,var(--accent) 12%,#0a1827),#0a1827)}.buyer aside small{color:#8ea0b2}.buyer aside strong{display:block;font-size:25px;line-height:1.3;margin-top:12px}.faqGrid{display:grid;gap:11px;margin-top:30px}.faqGrid details{border:1px solid #ffffff12;border-radius:16px;background:#ffffff06;padding:0 20px}.faqGrid summary{cursor:pointer;padding:19px 0;font-weight:800}.faqGrid summary span{color:var(--accent);margin-right:14px}.faqGrid p{color:#91a4b6;padding:0 0 18px 34px;line-height:1.55}.final{margin-top:40px;padding:44px;border-radius:28px;background:linear-gradient(135deg,color-mix(in srgb,var(--accent) 18%,#0a1727),#0a1727);border:1px solid color-mix(in srgb,var(--accent) 28%,transparent);display:grid;grid-template-columns:1fr auto;gap:28px;align-items:center}.final a{background:var(--accent);color:#06101b;text-decoration:none;font-weight:900;padding:18px 22px;border-radius:14px;white-space:nowrap}.b2b footer{max-width:1220px;margin:auto;border-top:1px solid #ffffff10;padding:28px 24px 50px;display:flex;justify-content:space-between;color:#74879a;font-size:13px}.b2b footer a{color:#b9c6d3;text-decoration:none}@media(max-width:900px){.topbar nav{display:none}.hero,.calc,.buyer,.final{grid-template-columns:1fr}.visual{min-height:400px}.calcInputs{grid-template-columns:1fr}.grid4,.checkGrid,.specBand{grid-template-columns:repeat(2,1fr)}.final a{white-space:normal;text-align:center}}@media(max-width:600px){.topCta{display:none}.b2b main{padding-inline:18px}.hero{padding-top:20px}h1{font-size:48px}.visual{min-height:350px}.grid4,.checkGrid,.specBand{grid-template-columns:1fr}.economics,.pain,.risk,.faq{padding:65px 0}.b2b footer{flex-direction:column;gap:12px}}
    `}</style>
  </div>;
}
