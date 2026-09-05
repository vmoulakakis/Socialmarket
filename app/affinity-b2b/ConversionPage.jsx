'use client';

import { motion } from 'motion/react';
import Link from 'next/link';

const fade = { hidden: { opacity: 0, y: 26 }, show: { opacity: 1, y: 0, transition: { duration: .65 } } };

export default function ConversionPage({ product, record }) {
  const price = Number(record?.salePrice || 0);
  const rate = parseFloat(String(record?.commissionRate || '0').replace('%','')) || 0;
  const commission = price * rate / 100;
  const affiliate = record?.promotionLink || record?.detailUrl || '#';
  const image = record?.mainImage;
  const shop = record?.shopName || 'Marketplace seller';

  return <div className="affinity" style={{'--accent': product.accent}}>
    <div className="noise" />
    <header className="nav">
      <Link href="/affinity-b2b" className="brand"><span className="mark">A</span><span>AFFINITY<small>B2B PAIN-GAP ENGINE</small></span></Link>
      <nav><a href="#value">Αξία</a><a href="#proof">Αξιοπιστία</a><a href="#faq">FAQ</a></nav>
      <a className="navCta" href={affiliate} target="_blank" rel="sponsored nofollow noopener">Δες την προσφορά ↗</a>
    </header>

    <main>
      <section className="hero">
        <motion.div initial="hidden" animate="show" variants={fade} className="heroCopy">
          <div className="eyebrow">{product.eyebrow}</div>
          <h1>{product.headline}</h1>
          <p className="lead">{product.subheadline}</p>
          <div className="ctaRow">
            <a className="primary" href={affiliate} target="_blank" rel="sponsored nofollow noopener">Έλεγχος τιμής & διαθεσιμότητας <span>→</span></a>
            <a className="secondary" href="#value">Δες γιατί αξίζει</a>
          </div>
          <div className="micro">Affiliate offer • Τρέχουσα τιμή/διαθεσιμότητα επιβεβαιώνεται στον merchant</div>
        </motion.div>

        <motion.div initial={{opacity:0,scale:.94}} animate={{opacity:1,scale:1}} transition={{duration:.8}} className="visual">
          <div className="orb one"/><div className="orb two"/>
          {image ? <img src={image} alt={product.shortName} /> : null}
          <div className="priceCard"><small>Τιμή βάσης</small><strong>€{price.toLocaleString('el-GR',{minimumFractionDigits:2,maximumFractionDigits:2})}</strong><span>{shop}</span></div>
          <div className="commissionCard"><small>Affiliate KPI</small><strong>~€{commission.toFixed(2)}</strong><span>θεωρητική προμήθεια βάσει {rate}%</span></div>
        </motion.div>
      </section>

      <section className="pain" id="value">
        <motion.div initial="hidden" whileInView="show" viewport={{once:true,amount:.2}} variants={fade} className="sectionHead">
          <span>THE PAIN GAP</span><h2>Το κόστος δεν είναι το προϊόν. Είναι το πρόβλημα που μένει άλυτο.</h2><p>{product.pain}</p>
        </motion.div>
        <div className="metricGrid">{product.roiLabels.map((x,i)=><motion.div key={x} whileHover={{y:-8,scale:1.02}} className="metric"><b>0{i+1}</b><h3>{x}</h3><p>Βάλε το δικό σου πραγματικό κόστος και σύγκρινε πριν αποφασίσεις.</p></motion.div>)}</div>
      </section>

      <section className="featureBand">
        {product.benefits.map((b,i)=><motion.div key={b} initial={{opacity:0,y:20}} whileInView={{opacity:1,y:0}} transition={{delay:i*.08}} viewport={{once:true}} className="feature"><span>{['◉','↗','⌁','✓'][i%4]}</span><b>{b}</b></motion.div>)}
      </section>

      <section className="buyer">
        <div><span className="kicker">WHO BUYS THIS?</span><h2>Χτισμένο για επαγγελματίες που μετρούν κόστος, χρόνο και ρίσκο.</h2><p>{product.buyer}</p></div>
        <div className="roiBox"><div className="pulse"/><small>Decision rule</small><strong>Αν το pain κοστίζει περισσότερο από τη λύση, η συζήτηση αλλάζει.</strong><p>Χρησιμοποίησε τη σελίδα ως decision aid — όχι ως υπόσχεση αποτελεσμάτων.</p></div>
      </section>

      <section className="proof" id="proof">
        <div className="sectionHead"><span>TRUST BEFORE CLICK</span><h2>Αξιοπιστία χωρίς fake persuasion.</h2></div>
        <div className="trustGrid">
          <div><i>01</i><b>Affiliate tracking</b><p>Το CTA χρησιμοποιεί το promotion link που υπάρχει στη SocialMarket βάση.</p></div>
          <div><i>02</i><b>Seller transparency</b><p>Merchant: {shop}. Έλεγξε rating, αποστολή, returns και warranty πριν την πληρωμή.</p></div>
          <div><i>03</i><b>No fake reviews</b><p>Δεν δημοσιεύουμε ανύπαρκτες αξιολογήσεις, stock counters ή ψεύτικα countdowns.</p></div>
          <div><i>04</i><b>Buyer protection</b><p>Ισχύουν οι όροι της πλατφόρμας/merchant που εμφανίζονται κατά το checkout.</p></div>
        </div>
      </section>

      <section className="faq" id="faq">
        <div className="sectionHead"><span>OBJECTION HANDLING</span><h2>Οι σωστές ερωτήσεις πριν το checkout.</h2></div>
        <div className="faqGrid">{product.faq.map(([q,a],i)=><motion.details key={q} whileHover={{scale:1.01}}><summary><span>0{i+1}</span>{q}</summary><p>{a}</p></motion.details>)}</div>
      </section>

      <section className="finalCta">
        <div><span>READY TO VALIDATE?</span><h2>Μην αγοράσεις από το headline. Άνοιξε το offer και έλεγξε το πραγματικό configuration.</h2><p>Τιμή, μεταφορικά, warehouse, ΦΠΑ, warranty, returns και συμβατότητα μπορεί να αλλάζουν ανά SKU και χώρα.</p></div>
        <a href={affiliate} target="_blank" rel="sponsored nofollow noopener">Άνοιξε το affiliate offer <b>↗</b></a>
      </section>
    </main>

    <footer><Link href="/affinity-b2b">← Όλα τα AFFINITY B2B προϊόντα</Link><span>Evidence-first affiliate experience • Greece / EU</span></footer>

    <style jsx global>{`
      :root{color-scheme:dark}.affinity{min-height:100vh;background:#07111f;color:#f7fbff;font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;overflow:hidden;position:relative}.affinity *{box-sizing:border-box}.noise{position:fixed;inset:0;pointer-events:none;opacity:.035;background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 180 180' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.9'/%3E%3C/svg%3E")}.nav{height:78px;position:sticky;top:0;z-index:50;display:flex;align-items:center;justify-content:space-between;padding:0 max(28px,calc((100vw - 1240px)/2));backdrop-filter:blur(18px);background:rgba(7,17,31,.78);border-bottom:1px solid rgba(255,255,255,.08)}.brand{display:flex;gap:10px;align-items:center;color:#fff;text-decoration:none;font-weight:900;letter-spacing:.08em}.brand .mark{display:grid;place-items:center;width:38px;height:38px;background:var(--accent);clip-path:polygon(50% 0,100% 100%,78% 100%,50% 48%,22% 100%,0 100%);font-size:0}.brand small{display:block;font-size:8px;opacity:.55;letter-spacing:.18em;margin-top:2px}.nav nav{display:flex;gap:26px}.nav nav a{color:#cbd7e5;text-decoration:none;font-size:14px}.navCta,.primary{background:var(--accent);color:#07111f!important;text-decoration:none;font-weight:900;border-radius:14px;padding:14px 20px;box-shadow:0 12px 40px color-mix(in srgb,var(--accent) 32%,transparent);transition:.25s}.navCta:hover,.primary:hover{transform:translateY(-2px);box-shadow:0 18px 50px color-mix(in srgb,var(--accent) 48%,transparent)}main{max-width:1240px;margin:auto;padding:54px 28px 90px}.hero{min-height:680px;display:grid;grid-template-columns:1.02fr .98fr;align-items:center;gap:48px;position:relative}.eyebrow,.sectionHead span,.kicker,.finalCta span{font-size:12px;letter-spacing:.22em;font-weight:900;color:var(--accent)}h1{font-size:clamp(48px,6vw,86px);line-height:.94;letter-spacing:-.055em;margin:18px 0 24px;max-width:760px}.lead{font-size:20px;line-height:1.55;color:#b8c6d8;max-width:700px}.ctaRow{display:flex;gap:14px;margin-top:32px;flex-wrap:wrap}.primary,.secondary{padding:17px 22px;border-radius:14px;display:inline-flex;align-items:center;gap:16px}.secondary{border:1px solid rgba(255,255,255,.18);color:#fff;text-decoration:none;background:rgba(255,255,255,.04)}.micro{font-size:12px;color:#718096;margin-top:18px}.visual{min-height:560px;position:relative;display:grid;place-items:center}.visual img{position:relative;z-index:2;max-width:92%;max-height:480px;object-fit:contain;filter:drop-shadow(0 35px 60px rgba(0,0,0,.55));animation:float 5s ease-in-out infinite}.orb{position:absolute;border-radius:50%;filter:blur(10px)}.orb.one{width:440px;height:440px;background:radial-gradient(circle,color-mix(in srgb,var(--accent) 26%,transparent),transparent 68%);animation:pulse 4s ease-in-out infinite}.orb.two{width:240px;height:240px;background:radial-gradient(circle,#4f8cff33,transparent 70%);right:0;top:6%;animation:pulse 5s 1s ease-in-out infinite}.priceCard,.commissionCard{position:absolute;z-index:4;padding:18px 20px;border:1px solid rgba(255,255,255,.14);background:rgba(8,21,38,.82);backdrop-filter:blur(18px);border-radius:18px;box-shadow:0 24px 50px #0007}.priceCard{left:0;bottom:56px}.commissionCard{right:0;top:60px}.priceCard small,.commissionCard small{display:block;color:#8fa1b5}.priceCard strong,.commissionCard strong{display:block;font-size:30px;margin:4px 0}.priceCard span,.commissionCard span{font-size:11px;color:#90a0b0}.pain{padding:110px 0 80px}.sectionHead{max-width:840px}.sectionHead h2,.buyer h2,.finalCta h2{font-size:clamp(34px,4vw,58px);line-height:1.02;letter-spacing:-.04em;margin:12px 0}.sectionHead p,.buyer p,.finalCta p{color:#93a6ba;font-size:18px;line-height:1.6}.metricGrid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-top:42px}.metric,.trustGrid>div{padding:26px;border:1px solid rgba(255,255,255,.08);border-radius:22px;background:linear-gradient(145deg,rgba(255,255,255,.055),rgba(255,255,255,.018));min-height:190px}.metric b{color:var(--accent);font-size:13px}.metric h3{font-size:22px;margin:48px 0 8px}.metric p,.trustGrid p{color:#8699ad;line-height:1.5}.featureBand{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.08);border-radius:22px;overflow:hidden}.feature{padding:30px;background:#0a1728;display:flex;align-items:center;gap:16px}.feature span{font-size:28px;color:var(--accent)}.buyer{padding:100px 0;display:grid;grid-template-columns:1.1fr .9fr;gap:50px;align-items:center}.roiBox{position:relative;padding:34px;border-radius:28px;background:linear-gradient(145deg,color-mix(in srgb,var(--accent) 15%,#0a1728),#0a1728);border:1px solid color-mix(in srgb,var(--accent) 24%,transparent)}.roiBox strong{display:block;font-size:26px;line-height:1.25;margin:16px 0}.pulse{position:absolute;right:26px;top:26px;width:12px;height:12px;border-radius:50%;background:var(--accent);box-shadow:0 0 0 0 color-mix(in srgb,var(--accent) 55%,transparent);animation:ring 1.8s infinite}.proof,.faq{padding:80px 0}.trustGrid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-top:38px}.trustGrid i{font-style:normal;color:var(--accent);font-weight:900}.trustGrid b{display:block;font-size:20px;margin:40px 0 8px}.faqGrid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-top:36px}.faq details{background:#0b1829;border:1px solid rgba(255,255,255,.09);border-radius:18px;padding:22px}.faq summary{cursor:pointer;font-weight:800;list-style:none}.faq summary span{color:var(--accent);margin-right:12px}.faq details p{color:#90a3b6;line-height:1.55}.finalCta{margin-top:70px;padding:42px;border-radius:30px;background:linear-gradient(120deg,color-mix(in srgb,var(--accent) 20%,#081525),#081525 62%);border:1px solid color-mix(in srgb,var(--accent) 28%,transparent);display:grid;grid-template-columns:1fr auto;gap:30px;align-items:center}.finalCta h2{font-size:38px}.finalCta a{display:flex;align-items:center;gap:22px;text-decoration:none;background:var(--accent);color:#07111f;padding:20px 24px;border-radius:16px;font-weight:900;white-space:nowrap}.finalCta a b{font-size:24px}footer{max-width:1240px;margin:auto;padding:30px 28px 48px;display:flex;justify-content:space-between;border-top:1px solid rgba(255,255,255,.08);color:#6f849a;font-size:13px}footer a{color:#fff;text-decoration:none}@keyframes float{50%{transform:translateY(-12px) rotate(-.6deg)}}@keyframes pulse{50%{transform:scale(1.12);opacity:.7}}@keyframes ring{70%{box-shadow:0 0 0 18px transparent}}@media(max-width:900px){.nav nav{display:none}.navCta{font-size:12px;padding:11px 13px}.hero,.buyer,.finalCta{grid-template-columns:1fr}.hero{padding-top:30px}.visual{min-height:460px}.metricGrid,.trustGrid{grid-template-columns:repeat(2,1fr)}.featureBand{grid-template-columns:repeat(2,1fr)}.faqGrid{grid-template-columns:1fr}.finalCta a{justify-content:center}.commissionCard{right:8px}.priceCard{left:8px}}@media(max-width:560px){main{padding-left:18px;padding-right:18px}.nav{padding:0 18px}.brand{font-size:13px}.metricGrid,.trustGrid,.featureBand{grid-template-columns:1fr}h1{font-size:48px}.lead{font-size:17px}.visual{min-height:390px}.priceCard,.commissionCard{position:relative;left:auto;right:auto;top:auto;bottom:auto;margin:8px;width:90%}.visual{align-content:center}.finalCta{padding:26px}.finalCta h2{font-size:31px}footer{flex-direction:column;gap:12px}}
    `}</style>
  </div>;
}
