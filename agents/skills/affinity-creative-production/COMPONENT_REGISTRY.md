# AFFINITY Creative Component Registry

Version: 1.0
Last researched: 2026-09-07
Depends on: `skills/AFFINITY_SKILL.md`, `skills/AFFINITY_PAGE_ENGINE.md`

This registry is the reusable component grammar for AFFINITY creative production.

## Provenance labels

- `PP_VERIFIED` — component or functional block explicitly named in current PagePilot public pages/help docs.
- `MAG_VERIFIED_FORMAT` — page/content format or workflow explicitly named by Magnetic.ai publicly.
- `AFFINITY_DERIVED` — original AFFINITY component implementing a useful conversion/content function; not claimed to be a private PagePilot/Magnetic component.

Important: PagePilot publicly states 35+ CRO sections/blocks and elsewhere a 50+ component library, but the full private inventory is not publicly enumerated. Magnetic does not publish a full internal component list. This registry includes every public named PagePilot block/section verified in research plus a capability-complete AFFINITY superset for Magnetic-style outputs and AFFINITY-specific funnels.

---

# 1. PRODUCT / ABOVE-THE-FOLD BLOCKS

| ID | Component | Provenance | Primary job |
|---|---|---|---|
| PP-B01 | Review Numbers / Rating Summary | PP_VERIFIED | Put social proof near product title/hero |
| PP-B02 | Product Title | PP_VERIFIED | Identify product clearly |
| PP-B03 | Product Subtitle / USP | PP_VERIFIED | State key differentiator quickly |
| PP-B04 | Benefits Block | PP_VERIFIED | Translate product value into buyer outcomes |
| PP-B05 | Quantity Selector | PP_VERIFIED | Let shopper choose quantity / support AOV |
| PP-B06 | Variant Picker | PP_VERIFIED | Select size/color/configuration |
| PP-B07 | Buy Button / Add to Cart | PP_VERIFIED | Primary commerce action |
| PP-B08 | Divider | PP_VERIFIED | Visual grouping / hierarchy |
| PP-B09 | Guarantees | PP_VERIFIED | Reduce perceived risk |
| PP-B10 | Sticky Testimonial | PP_VERIFIED | Keep a real trust cue visible |
| PP-B11 | Expandable Text | PP_VERIFIED | Hide secondary shipping/returns/details until needed |
| PP-B12 | Custom Liquid / Custom Embed | PP_VERIFIED | Add justified custom functionality |
| PP-B13 | Product Gallery | PP_VERIFIED | Zoomable/swipeable visual product inspection |
| PP-B14 | Hero Section | PP_VERIFIED | Attention + value prop + primary action |
| PP-B15 | Sticky Add to Cart | PP_VERIFIED | Persistent mobile purchase action |
| PP-B16 | Trust Badges | PP_VERIFIED | Security/shipping/payment reassurance |
| PP-B17 | Countdown Timer | PP_VERIFIED | Real time-limited urgency only |
| AF-B18 | Price / Offer Block | AFFINITY_DERIVED | Show current price, compare-at only when real, offer terms |
| AF-B19 | Savings / Price-Gap Callout | AFFINITY_DERIVED | Explain verified economic advantage |
| AF-B20 | Shipping ETA Microcopy | AFFINITY_DERIVED | Reduce delivery uncertainty |
| AF-B21 | Returns Microcopy | AFFINITY_DERIVED | Reduce purchase-risk uncertainty |
| AF-B22 | Affiliate Destination CTA | AFFINITY_DERIVED | Send qualified visitor to verified merchant link |
| AF-B23 | Merchant Identity Strip | AFFINITY_DERIVED | Clarify who sells/fulfills the product |
| AF-B24 | Availability / Stock Status | AFFINITY_DERIVED | Show truthful availability only |
| AF-B25 | What’s Included Summary | AFFINITY_DERIVED | Prevent uncertainty about box contents |
| AF-B26 | Compatibility Summary | AFFINITY_DERIVED | Prevent wrong-product purchases |

### Selection notes
- Use one dominant primary action above the fold.
- Affiliate pages normally use `AF-B22`, not a fake cart.
- `PP-B17` is prohibited unless the deadline/timer is genuine and technically enforced or tied to a real published event.
- `PP-B10` requires a real, attributable testimonial; otherwise omit it.

---

# 2. NARRATIVE / CRO SECTIONS

| ID | Component | Provenance | Primary job |
|---|---|---|---|
| PP-S01 | Image with Text | PP_VERIFIED | Pair visual proof/context with persuasive copy |
| PP-S02 | Review Grid | PP_VERIFIED | Show multiple real reviews in grid/carousel/masonry |
| PP-S03 | Image with Benefits | PP_VERIFIED | Visually connect product with outcomes |
| PP-S04 | Competition Differences | PP_VERIFIED | Differentiate from alternatives |
| PP-S05 | Image with Percentages | PP_VERIFIED | Show quantified proof only when supported |
| PP-S06 | Frequently Asked Questions | PP_VERIFIED | Resolve objections late in decision path |
| PP-S07 | Call to Action Section | PP_VERIFIED | Final conversion push |
| PP-S08 | Recommended Products | PP_VERIFIED | Cross-sell / alternative route |
| PP-S09 | Custom Liquid Section | PP_VERIFIED | Advanced custom function |
| PP-S10 | Reviews & Testimonials | PP_VERIFIED | Social proof section |
| PP-S11 | Comparison Table | PP_VERIFIED | Side-by-side decision support |
| PP-S12 | Bundle & Upsell | PP_VERIFIED | Raise AOV with relevant package |
| PP-S13 | Feature Highlights | PP_VERIFIED | Fast-scanning feature/benefit grid |
| PP-S14 | Guarantee Strip | PP_VERIFIED | De-risk purchase |
| PP-S15 | Demo Video Slot | PP_VERIFIED | Demonstrate product behavior |
| PP-S16 | Lifestyle Visual Section | PP_VERIFIED | Show use context |
| PP-S17 | Product Description Section | PP_VERIFIED | Structured product explanation |
| AF-S18 | Pain / Problem Framing | AFFINITY_DERIVED | Make current friction concrete |
| AF-S19 | Cost of Inaction | AFFINITY_DERIVED | Quantify consequence when defensible |
| AF-S20 | Gap / Why Alternatives Fall Short | AFFINITY_DERIVED | Explain unresolved problem honestly |
| AF-S21 | Mechanism / How It Solves | AFFINITY_DERIVED | Explain why solution works |
| AF-S22 | How It Works Steps | AFFINITY_DERIVED | Reduce complexity through sequential explanation |
| AF-S23 | Use-Case Grid | AFFINITY_DERIVED | Show relevant buyer scenarios |
| AF-S24 | Audience Branch Selector | AFFINITY_DERIVED | Route materially different segments |
| AF-S25 | Honest Limitations | AFFINITY_DERIVED | Surface meaningful disadvantages |
| AF-S26 | Trust Stack | AFFINITY_DERIVED | Consolidate merchant, delivery, warranty, returns, service |
| AF-S27 | Economic Comparison | AFFINITY_DERIVED | Compare total solution cost |
| AF-S28 | ROI / Savings Summary | AFFINITY_DERIVED | Explain scenario economics |
| AF-S29 | Before / After Evidence | AFFINITY_DERIVED | Visual change only when real and supportable |
| AF-S30 | Specification Proof | AFFINITY_DERIVED | Present specs tied to buyer relevance |
| AF-S31 | Compatibility Matrix | AFFINITY_DERIVED | Show supported devices/environments/configurations |
| AF-S32 | Included vs Optional | AFFINITY_DERIVED | Clarify package boundaries |
| AF-S33 | Installation / Setup | AFFINITY_DERIVED | Explain burden, tools, professional requirements |
| AF-S34 | Delivery / Returns / Warranty | AFFINITY_DERIVED | Operational trust section |
| AF-S35 | Objection Cards | AFFINITY_DERIVED | Resolve 3–6 high-impact concerns |
| AF-S36 | Final Decision Summary | AFFINITY_DERIVED | Concise “who this is/isn’t for” |
| AF-S37 | Sticky Side Summary | AFFINITY_DERIVED | Keep key decision facts visible on long desktop pages |
| AF-S38 | Evidence Ledger View | AFFINITY_DERIVED | Public-facing citations/claim support when appropriate |

---

# 3. PRODUCT DESCRIPTION MICRO-COMPONENTS

PagePilot publicly describes a fixed description structure. AFFINITY preserves the useful discipline while adding evidence controls.

| ID | Component | Provenance | Primary job |
|---|---|---|---|
| PP-D01 | Opening Hook | PP_VERIFIED | Name problem + payoff quickly |
| PP-D02 | Benefit List | PP_VERIFIED | 3–5 outcome-oriented bullets |
| PP-D03 | Spec Table | PP_VERIFIED | Materials, sizing, box contents, care/specs |
| PP-D04 | Social Proof Line | PP_VERIFIED | Short trust cue mapped to real proof |
| AF-D05 | Limitation Line | AFFINITY_DERIVED | State critical caveat where needed |
| AF-D06 | Delivery/Returns Line | AFFINITY_DERIVED | Clarify operational purchase facts |
| AF-D07 | Comparison Note | AFFINITY_DERIVED | Brief honest alternative framing |

---

# 4. NICHE-SPECIFIC MODULES PUBLICLY DESCRIBED BY PAGEPILOT

| ID | Component | Provenance | Best for |
|---|---|---|---|
| PP-N01 | Ingredient Highlights | PP_VERIFIED | Beauty/skincare; only factual ingredients/materials |
| PP-N02 | Before-and-After Proof | PP_VERIFIED | Beauty/skincare; strict evidence requirement |
| PP-N03 | Routine Steps | PP_VERIFIED | Beauty/skincare / repeat-use products |
| PP-N04 | Size Guide | PP_VERIFIED | Fashion/apparel |
| PP-N05 | Lifestyle Gallery | PP_VERIFIED | Fashion, pets, home, lifestyle products |
| PP-N06 | Spec Comparison | PP_VERIFIED | Tech/gadgets |
| PP-N07 | Demo Video | PP_VERIFIED | Tech/gadgets and demonstrable products |
| PP-N08 | Feature Grid | PP_VERIFIED | Tech/gadgets and scannable benefits |
| PP-N09 | Room / Use-Context Visual | PP_VERIFIED | Home & garden |
| PP-N10 | Value Framing | PP_VERIFIED | Home/garden and considered purchases |

Health/wellness modules inherit extra AFFINITY medical/scientific claim controls.

---

# 5. CART DRAWER / CHECKOUT-INTENT COMPONENTS

| ID | Component | Provenance | Primary job |
|---|---|---|---|
| PP-CART01 | Cart Title | PP_VERIFIED | Orient the drawer |
| PP-CART02 | Total / Subtotal Text | PP_VERIFIED | Show order amount |
| PP-CART03 | Empty Cart State | PP_VERIFIED | Explain empty state |
| PP-CART04 | Checkout Button | PP_VERIFIED | Proceed to checkout |
| PP-CART05 | Product Upsell | PP_VERIFIED | Add relevant item |
| PP-CART06 | Cross-Sell | PP_VERIFIED | Add complementary item |
| PP-CART07 | Countdown / Reservation Timer | PP_VERIFIED | Real reservation/urgency only |
| PP-CART08 | Free-Shipping Progress Bar | PP_VERIFIED | Encourage threshold completion |
| PP-CART09 | Trust Badges | PP_VERIFIED | Reassure at checkout intent |
| AF-CART10 | Quantity Controls | AFFINITY_DERIVED | Edit line items in drawer |
| AF-CART11 | Remove Item | AFFINITY_DERIVED | Basic cart control |
| AF-CART12 | Shipping Threshold Explanation | AFFINITY_DERIVED | Make progress-bar logic explicit |

Affiliate pages that do not own checkout should not instantiate this module merely to imitate ecommerce.

---

# 6. MAGNETIC-STYLE PAGE FORMATS

These are publicly named formats/use cases, not claims about Magnetic's private component IDs.

| ID | Format | Provenance | Core purpose |
|---|---|---|---|
| MAG-F01 | Message-Matched Landing Page | MAG_VERIFIED_FORMAT | Continue ad/campaign promise |
| MAG-F02 | Checklist | MAG_VERIFIED_FORMAT | Actionable opt-in/resource |
| MAG-F03 | Playbook | MAG_VERIFIED_FORMAT | Step-by-step operating resource |
| MAG-F04 | Mini-Guide | MAG_VERIFIED_FORMAT | Concise educational asset |
| MAG-F05 | Resource List | MAG_VERIFIED_FORMAT | Curated useful resources |
| MAG-F06 | Personalized Sales Follow-Up | MAG_VERIFIED_FORMAT | Tailored prospect/account page |
| MAG-F07 | Link-in-Bio Page | MAG_VERIFIED_FORMAT | Route social visitors to matched next steps |
| MAG-F08 | Hosted Campaign Page | MAG_VERIFIED_FORMAT | Fast publish/share page |
| MAG-F09 | HTML Export | MAG_VERIFIED_FORMAT | Reusable webpage output |
| MAG-F10 | PDF Export | MAG_VERIFIED_FORMAT | Downloadable/printable resource |
| MAG-F11 | PNG Export | MAG_VERIFIED_FORMAT | Static visual output |

---

# 7. LEAD-MAGNET / CAMPAIGN COMPONENTS

These are AFFINITY originals that provide the functional grammar required to produce Magnetic-style formats.

| ID | Component | Provenance | Primary job |
|---|---|---|---|
| AF-L01 | Message-Matched Hero | AFFINITY_DERIVED | Confirm continuity from source campaign |
| AF-L02 | Audience Context | AFFINITY_DERIVED | State who resource is for |
| AF-L03 | Pain / Opportunity Intro | AFFINITY_DERIVED | Frame reason to continue |
| AF-L04 | Quick-Win Summary | AFFINITY_DERIVED | Deliver immediate value |
| AF-L05 | Checklist Group | AFFINITY_DERIVED | Organize action items |
| AF-L06 | Checklist Item | AFFINITY_DERIVED | Actionable binary/short task |
| AF-L07 | Playbook Step | AFFINITY_DERIVED | Sequential action block |
| AF-L08 | Mini-Guide Chapter | AFFINITY_DERIVED | Compact educational section |
| AF-L09 | Resource Card | AFFINITY_DERIVED | Resource + why/when to use |
| AF-L10 | Template / Swipe File | AFFINITY_DERIVED | Reusable copy/process asset |
| AF-L11 | Download CTA | AFFINITY_DERIVED | Access downloadable resource |
| AF-L12 | Lead Capture Form | AFFINITY_DERIVED | Collect minimal required information |
| AF-L13 | Prospect-Specific Insight | AFFINITY_DERIVED | Personalized research/observation |
| AF-L14 | Company / Account Context | AFFINITY_DERIVED | Tailor sales follow-up |
| AF-L15 | Credibility / Proof | AFFINITY_DERIVED | Establish trust with real evidence |
| AF-L16 | Low-Friction Meeting CTA | AFFINITY_DERIVED | Book/continue conversation |
| AF-L17 | Link Group | AFFINITY_DERIVED | Organize link-in-bio destinations |
| AF-L18 | Primary Social Offer | AFFINITY_DERIVED | Highlight current best next action |
| AF-L19 | Contact / Newsletter CTA | AFFINITY_DERIVED | Continue relationship |
| AF-L20 | Resource Footer | AFFINITY_DERIVED | Legal/source/next-step closure |

---

# 8. COPY / MESSAGE PRIMITIVES

| ID | Primitive | Provenance | Notes |
|---|---|---|---|
| PP-A01 | Pain-Point Ad Angle | PP_VERIFIED | Public ad-copy page names pain-point angle |
| PP-A02 | Social-Proof Ad Angle | PP_VERIFIED | Requires genuine proof |
| PP-A03 | Offer-Led Ad Angle | PP_VERIFIED | Offer must be current and real |
| PP-A04 | Ad Hook | PP_VERIFIED | Scroll-stopping opening |
| PP-A05 | Ad Primary Text | PP_VERIFIED | Main Meta-style body copy |
| PP-A06 | Ad Headline | PP_VERIFIED | Short high-signal line |
| PP-A07 | Ad Description | PP_VERIFIED | Supporting line where platform uses it |
| PP-A08 | Ad CTA | PP_VERIFIED | Action label |
| AF-A09 | Outcome Angle | AFFINITY_DERIVED | Desired result |
| AF-A10 | Economic Angle | AFFINITY_DERIVED | Savings/ROI when defensible |
| AF-A11 | Convenience Angle | AFFINITY_DERIVED | Time/friction reduction |
| AF-A12 | Technical Angle | AFFINITY_DERIVED | Verified capability/spec advantage |
| AF-A13 | Segment Angle | AFFINITY_DERIVED | Audience/use-case-specific positioning |
| AF-A14 | Comparison Angle | AFFINITY_DERIVED | Local/alternative comparison |

---

# 9. IMAGE / MEDIA COMPONENTS

| ID | Component | Provenance | Primary job |
|---|---|---|---|
| PP-M01 | Studio Product Image | PP_VERIFIED | Clean high-quality product visual |
| PP-M02 | Lifestyle Scene | PP_VERIFIED | Put product in relevant context |
| PP-M03 | In-Hand / In-Use Shot | PP_VERIFIED | Demonstrate scale/use |
| PP-M04 | AI Product Image Variant | PP_VERIFIED | Test creative context |
| PP-M05 | Ad Creative Visual | PP_VERIFIED | Match page/ad angle |
| AF-M06 | Product Detail Macro | AFFINITY_DERIVED | Show controls/material/details |
| AF-M07 | Diagram / Explainer | AFFINITY_DERIVED | Explain mechanism |
| AF-M08 | Comparison Graphic | AFFINITY_DERIVED | Visualize meaningful differences |
| AF-M09 | Step Visual | AFFINITY_DERIVED | Support how-it-works |
| AF-M10 | Data Visualization | AFFINITY_DERIVED | Show verified metrics clearly |
| AF-M11 | Real UGC / Customer Media | AFFINITY_DERIVED | Authentic social proof only |
| AF-M12 | Product Demo Video | AFFINITY_DERIVED | Show operation/use |
| AF-M13 | Lightweight GIF | AFFINITY_DERIVED | Short repeatable process demo |
| AF-M14 | PDF/Guide Illustration | AFFINITY_DERIVED | Support content asset comprehension |

Media fidelity requirements are defined in `skills/AFFINITY_PAGE_ENGINE.md`.

---

# 10. INTERACTIVE / DECISION-SUPPORT COMPONENTS

| ID | Component | Provenance | Primary job |
|---|---|---|---|
| AF-I01 | Savings Calculator | AFFINITY_DERIVED | Personalized economic value |
| AF-I02 | ROI Calculator | AFFINITY_DERIVED | Professional/high-ticket justification |
| AF-I03 | Break-Even Calculator | AFFINITY_DERIVED | Show payback time |
| AF-I04 | Cost-Per-Use Calculator | AFFINITY_DERIVED | Normalize high upfront price |
| AF-I05 | Quiz / Recommender | AFFINITY_DERIVED | Match buyer to product/use case |
| AF-I06 | Configurator | AFFINITY_DERIVED | Choose compatible setup |
| AF-I07 | Segment Selector | AFFINITY_DERIVED | Branch messaging |
| AF-I08 | Comparison Toggle | AFFINITY_DERIVED | Explore alternatives/attributes |
| AF-I09 | FAQ Accordion | PP_VERIFIED | Progressive disclosure |
| AF-I10 | Expandable Details | PP_VERIFIED | Progressive disclosure |

Interactive components require explicit value; no interaction for decoration.

---

# 11. STRUCTURAL / LAYOUT PRIMITIVES

| ID | Component | Provenance | Primary job |
|---|---|---|---|
| AF-STR01 | Container | AFFINITY_DERIVED | Consistent content width |
| AF-STR02 | Section Wrapper | AFFINITY_DERIVED | Spacing/surface control |
| AF-STR03 | Split Layout | AFFINITY_DERIVED | Copy/media balance |
| AF-STR04 | Centered Layout | AFFINITY_DERIVED | Focused message |
| AF-STR05 | Card Grid | AFFINITY_DERIVED | Scannable grouped items |
| AF-STR06 | Bento Grid | AFFINITY_DERIVED | Dense but structured feature presentation |
| AF-STR07 | Horizontal Scroller | AFFINITY_DERIVED | Mobile-friendly repeated content |
| AF-STR08 | Carousel | AFFINITY_DERIVED | Reviews/media when justified |
| AF-STR09 | Masonry | AFFINITY_DERIVED | Review/UGC density |
| AF-STR10 | Sticky Rail | AFFINITY_DERIVED | Desktop summary/action persistence |
| AF-STR11 | Full-Bleed Media | AFFINITY_DERIVED | High-impact demonstration |
| AF-STR12 | Stats Row | AFFINITY_DERIVED | Verified metrics |
| AF-STR13 | Timeline / Steps | AFFINITY_DERIVED | Sequence/process |
| AF-STR14 | Quote Block | AFFINITY_DERIVED | Real attributed quote |
| AF-STR15 | Table | AFFINITY_DERIVED | Structured comparison/specs |
| AF-STR16 | Tabs | AFFINITY_DERIVED | Switch related content compactly |
| AF-STR17 | Accordion Group | AFFINITY_DERIVED | Progressive disclosure |

---

# 12. TRUST / PROOF COMPONENTS

| ID | Component | Provenance | Primary job |
|---|---|---|---|
| AF-T01 | Verified Review Summary | AFFINITY_DERIVED | Consolidate attributable ratings |
| AF-T02 | Testimonial Card | AFFINITY_DERIVED | Real customer quote |
| AF-T03 | Review Wall | AFFINITY_DERIVED | Multiple authentic reviews |
| AF-T04 | Merchant Trust Card | AFFINITY_DERIVED | Seller identity/history/support |
| AF-T05 | Warranty Card | AFFINITY_DERIVED | Warranty clarity |
| AF-T06 | Returns Card | AFFINITY_DERIVED | Returns clarity |
| AF-T07 | Delivery Card | AFFINITY_DERIVED | Shipping clarity |
| AF-T08 | Service / Support Card | AFFINITY_DERIVED | Post-purchase confidence |
| AF-T09 | Certification / Compliance | AFFINITY_DERIVED | Only verified marks/certifications |
| AF-T10 | Source / Evidence Footnote | AFFINITY_DERIVED | Support quantified claims |
| AF-T11 | Limitations Disclosure | AFFINITY_DERIVED | Avoid one-sided persuasion |
| AF-T12 | Freshness Timestamp | AFFINITY_DERIVED | Show volatile price/availability freshness |

---

# 13. GLOBAL SITE COMPONENTS

| ID | Component | Provenance | Primary job |
|---|---|---|---|
| AF-G01 | Header / Minimal Nav | AFFINITY_DERIVED | Brand + essential navigation |
| AF-G02 | Announcement Bar | AFFINITY_DERIVED | Real current announcement only |
| AF-G03 | Breadcrumbs | AFFINITY_DERIVED | Orientation / SEO for deeper sites |
| AF-G04 | Footer | AFFINITY_DERIVED | Legal/contact/navigation closure |
| AF-G05 | Affiliate Disclosure | AFFINITY_DERIVED | Transparent disclosure |
| AF-G06 | Cookie / Consent Layer | AFFINITY_DERIVED | Applicable consent/privacy behavior |
| AF-G07 | Floating CTA | AFFINITY_DERIVED | Persistent action where justified |
| AF-G08 | Back-to-Top | AFFINITY_DERIVED | Long-page utility |
| AF-G09 | Share Controls | AFFINITY_DERIVED | Shareable content assets |

---

# 14. COMPONENT METADATA CONTRACT

Every implemented component should define:

```yaml
id:
name:
role:
provenance:
conversion_goal:
best_for: []
avoid_when: []
required_inputs: []
evidence_requirements: []
copy_limits:
media_requirements:
responsive_behavior:
accessibility_requirements:
analytics_events: []
performance_notes:
fallbacks: []
```

No component is globally “high converting.” Component performance is conditional on traffic, product, offer, audience, awareness and sequence.

---

# 15. DEFAULT COPY LIMITS

Use these as starting constraints, not inflexible rules.

| Component | Default copy constraint |
|---|---|
| Hero eyebrow | 2–6 words |
| Hero headline | 5–12 words |
| Hero support | 18–40 words |
| CTA | 2–5 words |
| Benefit title | 2–6 words |
| Benefit body | 12–30 words |
| Feature item | 8–25 words |
| Trust microcopy | 4–18 words |
| Review quote | Prefer concise excerpt; preserve accuracy |
| FAQ answer | Usually 25–90 words |
| Final CTA support | 15–35 words |
| Resource card | 20–50 words |
| Playbook step | 35–120 words depending format |

If copy exceeds the component's visual capacity, change the component or edit the copy; do not silently shrink typography into unreadability.

---

# 16. COMPONENT SELECTION HEURISTICS

## Cold paid traffic + physical product
Prioritize:
- message-matched hero
- gallery/product visual
- benefit hierarchy
- proof/trust near CTA
- demonstration
- comparison if necessary
- FAQ/objections
- persistent CTA on mobile.

## High-ticket considered purchase
Prioritize:
- clear hero
- mechanism
- spec proof
- total-cost/economic analysis
- comparison
- warranty/delivery/service
- limitations
- FAQ
- repeated CTA.

## Impulse ecommerce
Prioritize:
- fast hero/product gallery
- obvious value
- compact benefits
- real proof
- clear offer
- sticky add-to-cart
- relevant bundle/upsell
- minimal friction.

## Lead magnet
Prioritize:
- message-matched hero
- immediate value preview
- format-specific content
- low-friction capture/download
- next action.

## Personalized sales follow-up
Prioritize:
- prospect/account recognition
- tailored problem/opportunity
- useful insight
- credibility
- low-friction meeting CTA.

---

# 17. PROHIBITED COMPONENT BEHAVIOR

Never instantiate:
- fake countdowns
- fake stock counters
- fake reviews
- fake star ratings
- fake “X people viewing” signals
- unsupported percentage proof
- invented certifications
- fabricated before/after results
- misleading price strikethroughs
- fake cart reservation
- false local scarcity
- dark-pattern forced continuity
- intrusive interaction that blocks core information.

---

# 18. REGISTRY EVOLUTION

A component may be promoted into this registry after:
1. repeated need across pages;
2. clear purpose;
3. responsive/accessibility design;
4. evidence rules defined;
5. at least one successful deployment;
6. no unacceptable performance cost.

Monthly AFFINITY optimization should update component metadata using measured RPV/conversion behavior, not aesthetic preference alone.
