# Editorial draft — Ελληνικός οδηγός επιλογής ελαστικών (HOLD)

**Change:** CHG-AWIN-20261028 · **Publisher:** 3060863 · **Campaign:** `awin:3060863:9837:tyre-compatibility:editorial-v1` · **Research:** 2026-11-01 (Europe/Athens) · **State:** EDITORIAL ONLY, not approved for publication.

## Why / audience / promise
Οδηγός για Έλληνες οδηγούς που χρειάζονται ελαστικά αλλά δυσκολεύονται να συγκρίνουν διαστάσεις, δείκτες φορτίου/ταχύτητας, επιδόσεις σε βρεγμένο, θόρυβο και επιλογή εποχής. Δεν υποκαθιστά οδηγίες κατασκευαστή ή επαγγελματία. Στόχος: ο αναγνώστης να καταλήγει σε ελέγξιμη λίστα απαιτήσεων, όχι να οδηγείται σε τυχαία αγορά.

## Market and affiliate evidence (not product endorsement)
- Awin advertiser **Elastika-Online GR (9837)**: `Not joined` as of 2026-11-01, publisher 3060863. Official public profile advertises **3% per sale**, **60-day cookie** and validation/release approximately 4–6 weeks after dispatch/return window; **merchant-specific exclusions, eligible VAT/shipping base, channel permissions and publisher contract remain unverified**. Source: https://ui.awin.com/merchant-profile/9837 (checked 2026-11-01).
- At an *illustrative* 3% on a fully eligible net commission basis, **€10 requires >€333.33** in eligible sale value. This is NOT a minimum cart price, product claim, guaranteed payout or a confirmed publisher rate.
- Public Greek competitors/supply examples: https://protires.gr/gr/elastika-gia-autokinita/2026 (search by dimensions, brand, season) and https://cars.elastikaleader.gr/elastiko/jeep/compass/compass-5206/42808 (vehicle-fitment filters, dimension verification disclaimer). These are supply observations, not measured market share, search volume or evidence of a low-competition niche.
- Demand, conversion, seasonality, current stock and price: **UNKNOWN** until first-party or verified search-volume and offer evidence exists. Autumn wet-road relevance is a **hypothesis**, not measured uplift.

## User flow (mobile-first, editorial-only)
**Screen 1 — Το πρόβλημά σου.** One question: «Τι χρειάζεσαι;» choices «Αλλαγή φθαρμένων», «Οδήγηση σε βροχή», «Συχνά ταξίδια», «Θέλω να ελέγξω διαστάσεις». No automatic purchase recommendation.

**Screen 2 — Βρες τη σωστή διάσταση.** Ask user to read the vehicle handbook / registration documentation and approved tyre specifications. Explain the markings with a non-vehicle-specific example `205/55 R16 91V` (width, profile, radial, rim, load and speed index). Never infer fitment from an example, license plate, or an unverified vehicle database. Clarify front/rear staggered sizes when relevant.

**Screen 3 — Χρήση & συμβιβασμοί.** Choose city/highway, wet-road emphasis, seasonal conditions, budget; compare EU tyre-label wet grip, rolling resistance and external noise using product-specific evidence only. Discuss seasonal/snow certification (3PMSF) as a product attribute, not a universal requirement in all Greek regions. For replacement, check age, condition, tread and safety with a tyre professional.

**Screen 4 — Check-list before purchase.** Correct homologated dimensions, load/speed ratings, tyre type, fitting/delivery costs, DOT/production age where documented, return policy, invoice and fitment appointment. Explicitly show `Δεν υπάρχουν ακόμη επαληθευμένες προσφορές` when no approved merchant/offer.

**Screen 5 — Next action.** Printable copyable checklist; if merchant is unapproved, provide non-commercial next action: verify vehicle specs and ask a fitter for an itemized quote. No fake “best price” or empty offer cards.

## SEO / content (do not publish yet)
- Candidate title: «Πώς να επιλέξεις σωστά ελαστικά αυτοκινήτου: διαστάσεις, δείκτες και χρήση».
- Candidate description: «Πρακτικός οδηγός για διαστάσεις, δείκτες φορτίου και ταχύτητας, επιδόσεις στη βροχή και κόστος τοποθέτησης — πριν αγοράσεις».
- Candidate slug **for later review only**: `/odigos-elastikon`. Do not add to the SocialMarket admin app: it is private and `noindex` by contract. Public destination must be an independently verified owned consumer-facing property.
- When later deployed: semantic H1/H2, FAQ only where actually answered, valid canonical URL, OG image with license/provenance, accessible buttons, responsive typography, keyboard support, low-motion fallback and mobile/desktop browser QA. Avoid inflated claims and invented review schema.
- Conditional affiliate disclosure (only if/when live links exist): «Ορισμένοι σύνδεσμοι μπορεί να είναι διαφημιστικοί. Αν αγοράσετε μέσω αυτών, ενδέχεται να λάβουμε προμήθεια χωρίς πρόσθετη χρέωση για εσάς.» All verified affiliate anchors `rel="sponsored noopener noreferrer"`. Before activation, verify actual merchant rules and tracked links; no affiliate links in this draft.

## Experiment / stop rules
- **Primary KPI after eligible activation:** approved commission EUR per qualified outbound click (requires attribution + validation evidence).
- **Diagnostic:** outbound CTR, merchant conversion rate, EPC, reversals and link health. Missing values stay null.
- **One experiment only:** order of «fitment checklist» versus «compare attributes» after sufficient qualified observations; predefine minimum evidence and duration before interpreting; no “winner” from a tiny sample.
- **Keep:** evidence supports qualified traffic and positive validated unit economics.
- **Repair:** broken links, low eligible clicks, bad fitment explanations or missing tracking evidence.
- **Stop:** programme approval withdrawn, safety/fitment concerns, unverified offer facts, repeated reversals, or noncompliant merchant channel.

## Gates and handoff
- Merchant `Joined`: **NO**; no tracked links, prices, stock, products, posts, or deployment.
- Authenticated Awin Join: requires originating browser context / approved action-time workflow; never use metered TinyFish.
- Source-of-truth: `data/awin/operations-ledger.json` and `data/awin/application-queue.json`; do not duplicate an already prepared Buffer idea `6ae2faea86828dc765d02378`.
- Review/acceptance: real merchant approval + publisher site verification + complete terms + 1–5 real offers with timestamps + build/mobile/desktop QA + independently reviewed publishing permissions. This file is an editorial brief, **not** a live mini site or a passed build.
