'use client';
import Link from 'next/link';
import { useState } from 'react';
import styles from './buyer-advisor.module.css';

const examples = [
  'Γωνιακός καναπές για μικρό σαλόνι',
  'Καναπές κρεβάτι για επισκέπτες',
  'Άνετος καναπές από ύφασμα',
];
const eu = v => Number(v).toLocaleString('el-GR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 2 });

export default function BuyerAdvisor() {
  const [query, setQuery] = useState('');
  const [budget, setBudget] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  async function research(need) {
    const clean = need.trim();
    if (clean.length < 3 || loading) return;
    setLoading(true); setError(''); setResult(null);
    try {
      const r = await fetch('/api/marketplace/advisor', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: clean, budget: budget === '' ? null : Number(budget) }),
        cache: 'no-store',
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || 'Η έρευνα δεν ήταν διαθέσιμη.');
      setResult(data);
    } catch (e) { setError(e.message || 'Παρουσιάστηκε σφάλμα.'); }
    finally { setLoading(false); }
  }

  const rows = result?.verified?.length ? result.verified : result?.candidates || [];
  const onlyResearch = !!result && !result.verified.length;
  return <main className={styles.page}>
    <header className={styles.top}>
      <Link href="/marketplace" className={styles.identity} aria-label="SocialMarket AI — κατάλογος">
        <span className={styles.symbol}>S</span>
        <span><strong>SOCIALMARKET AI</strong><small>Shopping intelligence · Ελλάδα</small></span>
      </Link>
      <Link href="/marketplace" className={styles.back}>Κατάλογος <span aria-hidden="true">↗</span></Link>
    </header>
    <section className={styles.hero}>
      <div className={styles.heroText}>
        <span className={styles.eyebrow}>ΑΝΑΓΚΗ ΠΡΩΤΑ · ΠΡΟΪΟΝ ΜΕΤΑ</span>
        <h1>Πες τι χρειάζεσαι.<br/><em>Μάθε τι αξίζει να εξετάσεις.</em></h1>
        <p>Αντί για έναν ατελείωτο κατάλογο, ξεκινάμε από το πρόβλημά σου. Συνδέουμε πραγματικές προσφορές με το αίτημα και ξεχωρίζουμε τι έχει επαληθευτεί από τι χρειάζεται ακόμη έλεγχο.</p>
        <div className={styles.source}>Πιλοτική κάλυψη: premium προϊόντα σπιτιού · Τα αποτελέσματα δεν καλύπτουν όλη την ελληνική αγορά.</div>
      </div>
      <div className={styles.illustration} aria-hidden="true">
        <div className={styles.orbit}><span>Ανάγκη</span><span>Πηγή</span><span>Έλεγχος</span></div>
        <div className={styles.heroGlyph}>S<span>AI</span></div>
        <div className={styles.orbitCaption}>Evidence before recommendation</div>
      </div>
    </section>
    <section className={styles.searchWrap} aria-labelledby="search-title">
      <div className={styles.searchIntro}><div><span className={styles.eyebrow}>01 / DISCOVERY</span><h2 id="search-title">Τι ψάχνεις;</h2></div><span className={styles.stepTag}>Read-only έρευνα</span></div>
      <form className={styles.form} onSubmit={e => { e.preventDefault(); void research(query); }}>
        <label className={styles.need}>
          <span>Περιέγραψε το προϊόν ή την ανάγκη σου</span>
          <input type="search" value={query} onChange={e => setQuery(e.target.value)} minLength={3} maxLength={180}
            placeholder="π.χ. καναπές κρεβάτι για μικρό σπίτι" autoComplete="off" required/>
        </label>
        <label className={styles.budget}>
          <span>Μέγιστος προϋπολογισμός (€)</span>
          <input type="number" inputMode="decimal" min="1" max="100000" step="1" value={budget}
            onChange={e => setBudget(e.target.value)} placeholder="Προαιρετικά"/>
        </label>
        <button type="submit" disabled={loading || query.trim().length < 3}>{loading ? 'Ερευνώ…' : 'Έλεγξε επιλογές'} <span aria-hidden="true">↗</span></button>
      </form>
      <div className={styles.suggestions}><span>Δοκίμασε:</span>{examples.map(s =>
        <button type="button" key={s} disabled={loading} onClick={() => { setQuery(s); void research(s); }}>{s}</button>)}</div>
    </section>
    <section className={styles.results} aria-live="polite" aria-busy={loading}>
      {loading && <div className={styles.notice} role="status">Ανάλυση ανάγκης, έλεγχος feed, αντιστοίχιση προϊόντων…</div>}
      {error && <div className={styles.error} role="alert"><b>Η έρευνα δεν ολοκληρώθηκε.</b><p>{error}</p><button onClick={() => research(query)} disabled={loading}>Επανάληψη</button></div>}
      {result && <>
        <div className={styles.heading}><div><span className={styles.eyebrow}>02 / EVIDENCE REPORT</span><h2>{onlyResearch ? 'Υποψήφιες αντιστοιχίσεις' : 'Επαληθευμένες επιλογές'}</h2></div><span className={styles.count}>{rows.length} καταχωρίσεις</span></div>
        <div className={onlyResearch ? styles.pending : styles.confirmed} role="status">
          <strong>{onlyResearch ? 'Δεν υπάρχουν ακόμη επαληθευμένες AI προτάσεις' : 'Οι εμφανιζόμενες επιλογές πέρασαν τους ελέγχους'}</strong>
          <p>{result.diagnostic} Η προμήθεια δεν καθορίζει την κατάταξη των αποτελεσμάτων. Κανένα προϊόν δεν αγοράζεται αυτόματα.</p>
        </div>
        <div className={styles.steps} aria-label="Στάδια επαλήθευσης">{(result.stages || []).map((s, i) =>
          <div key={s.name} className={styles.stage}><span className={styles.stageNumber}>0{i+1}</span><b>{s.name}</b><small>{s.status === 'DONE' ? 'Ολοκληρώθηκε' : 'Απαιτεί στοιχεία'}</small></div>)}</div>
        {rows.length ? <div className={styles.cards}>{rows.map(p => <article key={p.id} className={styles.card}>
          <div className={styles.media}>{p.image_url && <img src={p.image_url} alt={p.title} loading="lazy" referrerPolicy="no-referrer"/>}<span className={styles.reviewTag}>{p.verification === 'VERIFIED' ? 'Επαληθευμένο' : 'Απαιτεί επαλήθευση'}</span></div>
          <div className={styles.cardBody}><small>{p.merchant}</small><h3>{p.title}</h3><p className={styles.category}>{p.category || 'Προϊόν σπιτιού'}</p>
            <div className={styles.cardFooter}><strong>{eu(p.price_eur)}</strong><Link href={'/marketplace/' + encodeURIComponent(p.id)}>Δες στοιχεία <span aria-hidden="true">↗</span></Link></div>
            <p className={styles.disclaimer}>Η διαθεσιμότητα, η τελική τιμή, τα μεταφορικά και οι όροι αγοράς ελέγχονται στο κατάστημα.</p></div>
        </article>)}</div> :
        <div className={styles.notice}>Δεν βρέθηκε τεκμηριωμένη αντιστοίχιση στην τρέχουσα περιορισμένη συλλογή. Δοκίμασε άλλο προϊόν ή κατηγορία.</div>}
      </>}
      {!result && !loading && !error && <div className={styles.initial}><span className={styles.eyebrow}>ΠΩΣ ΛΕΙΤΟΥΡΓΕΙ</span><h2>Όχι άλλη λίστα «top προϊόντων» χωρίς αιτιολόγηση.</h2><p>Το SocialMarket ελέγχει τη συνάφεια με την ανάγκη, την προέλευση του affiliate link και τις διαθέσιμες αποδείξεις. Όταν λείπει έγκυρος έλεγχος αποθέματος ή έρευνας, το αναφέρει αντί να εφευρίσκει βεβαιότητα.</p></div>}
    </section>
    <footer className={styles.footer}>Διαφάνεια: Οι σύνδεσμοι καταστημάτων μπορεί να είναι affiliate και να αποφέρουν προμήθεια χωρίς επιπλέον χρέωση σε εσένα. Τρέχουσα λειτουργία: περιορισμένη ανάκτηση και έλεγχος στοιχείων, όχι ενεργοποιημένο generative AI ή live επιβεβαίωση απόθεματος.</footer>
  </main>;
}
