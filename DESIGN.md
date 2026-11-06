# SocialMarket AI — Consumer Buying Intelligence / DESIGN.md
Version: 2026-11-07. Design authority: UI/UX Pro Max workflow + existing VMDB evidence/affiliate contracts.

## Product and job
- Product: SocialMarket AI consumer marketplace inside the existing Next.js Socialmarket app.
- Audience: Greek online buyers who describe a real problem before they know the exact SKU.
- Primary success action: user enters a purchase need, receives a **source-grounded** shortlist and checks a product at the source merchant via its **unchanged original affiliate URL**.
- Secondary actions: narrow category/price, compare up to 3 offers, save to this page session, ask the Shopping Advisor to explain trade-offs.
- Financial objective: affiliate-approved conversion, never commission-first deceptive ranking. Catalog inclusion is an estimated >=€10 commission gate, not a consumer endorsement.

## Diagnosed legacy issues
1. Critical: old public marketplace was mostly highest-commission sofas and overstated buyer coverage.
2. Critical: stock=UNKNOWN on many Linkwise rows and seller rating/shipping unverified in AliExpress.
3. High: no meaningful conversational decision or visible separation of feed data and AI hypotheses.
4. High: dated selection with inaccessible source validation (previous September data).
5. Medium: UI used editorial brand language but no use-case-first navigation, price comparison, mobile chat or clear action path.

## Design thesis
Editorial Swiss commerce with a warmer Mediterranean green palette, not crypto/enterprise sci-fi.
Dark petroleum hero and soft botanical paper cards contrast the intelligence surface and product imagery; one brand-native geometric spark/constellation references finding a fitting offer rather than "AI magic."

Semantic colors:
- Ink / foreground: #112E31 (body and dark sections)
- Dark canvas: #0E292C / #133B3E (hero)
- Action evergreen: #1A6F62 (affiliate CTA)
- Botanical mint: #BDE7D6 (trust and accent)
- Warm gold: #F4CA7D (uncertainty, focus and status)
- Paper / surface: #F8F7F2, white #FFFFFF

Typography:
- UI: Inter, Segoe UI, system-ui; native Greek diacritics are required.
- Brand headlines: Georgia, Times New Roman, serif; restrained Italianate editorial energy.
- Type scale: fluid headline clamp(42px,5.35vw,85px), sections 37–61px, body 14–18px, labeled metadata 10–13px. Readable Greek accents and source-original English product titles.

Layout:
- Desktop 1440: split hero + 4-column product catalogue with generous margins.
- Small desktop 1024: 3 columns, simple nav.
- Tablet 768: 2 columns, single-column hero.
- Mobile 390/360: 2 cards per row with safe CTA and visible prices, modal chat panel full screen.
- 320: one-column cards, comparable product controls; no clipping.
- Source images displayed using contain and fixed aspect ratio to avoid cropped product context or CLS.
- CSS transitions only; reduced-motion disable.

## UX states and interaction contracts
| Surface | Empty | Loading | Error | Result | Safety |
|---|---|---|---|---|---|
| Product feed | Data-unavailable explanation | Fetch feedback | Retry | Real source images, price, category | Stock unknown remains UNKNOWN |
| Query and category | Useful examples | Preserved filters | No match + reset | Bilingual Greek↔English lexical matching | No invented reviews or popularity |
| Price budget | No budget by default | Immediate field change | Invalid amount native control | Price <= limit | Final merchant checkout can differ |
| Comparison | Hidden | Not applicable | 3-item maximum | Side-by-side source prices and limitations | No fake feature comparison |
| Favorites | Empty until saved | Local only | Not persisted across sessions | Clear selected heart | Never claim saved to account |
| Chat | Intro prompts | Explicit research progress | Retry by resubmit | Grounded product shortlist | Source-only mode shown when model off |
| True AI | Locked until owner cost gate | Two model calls with bounded evidence | Safe hold | Product Fit explanation + Skeptic critic | Model never creates SKUs or validates stock |
| Affiliate CTA | Never disabled if original valid | External handoff | Merchant responsible | Opens exact URL with sponsored noreferrer | Explicit disclosure |

## AI system architecture
1. Public API retrieves whitelisted real offers server-side using existing VMDB service role; secrets never enter browser.
2. Deterministic bilingual query intent, budget and category filter, identity, source URL and product-gate.
3. Source-aware ranker includes relevance and price, not commission amount.
4. MyAgenticTeam Product Fit LLM on up to 4 source-grounded candidates; no raw URLs, no untrusted reviews or merchant instructions.
5. Separate Skeptic LLM checks proposed statements. Validation from model is not evidence validation.
6. Chat return includes \`aiModelExecuted\` and \`mode\`; fallback source-only is honestly marked.
7. Internal broker checks service-role authorization; private global daily budget and per-visitor atomic quota. No automatic publication or purchases.

## Preservation and hard constraints
- The existing ERP-style control tower, audit workflows, SocialScheduler, \`/luxecorner\`, Supabase schema/source-of-truth and Linkwise CD104 tracking are unchanged.
- Additive DB quota table only. No bulk upserts, re-rating merchants, or arbitrary program IDs.
- Neither Awin nor synthetic affiliate links enter SocialMarket product recommendations.
- Unknown stock/shipping/delivery claims cannot be converted to positive facts by the agent.
- Data freshness and named provider are visible when known.
- The ChatGPT Site domain is not modified by a Vercel PR.

## Acceptance checks
- Check user-visible link integrity, no accidental merchant URL rebuild.
- Run Next.js production build, source/agent contract unit tests, Deno check for internal gateway, CI.
- Browser visual QA at 320/360/390/768/1024/1440, contrast, keyboard Tab/focus and reduced-motion must be confirmed before production.
- Validate live remote model only within an explicitly approved owner spend policy and actual end-to-end latency/availability.
- Preview success is not production-release approval.
