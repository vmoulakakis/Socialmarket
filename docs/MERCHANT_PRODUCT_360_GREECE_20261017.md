# Merchant + Product 360 | Greece 2026 | Evidence-first audit

Date: 2026-10-17. Scope: SocialMarket VMDB. This is a read-only baseline, not completed AI scoring or an approved Linkwise merchant list. Reproducible all-row SQL: reports/sql/merchant_product_360_readonly_20261017.sql.

## Observed data
- Registered commission records: **334**. Complete recorded Linkwise IDs: **17**. Missing IDs: **317**. Merchants with imported offers matched by program ID: **2**.
- Merchant profiles: **16** active, **0** with recorded program_approved=true, **0** tracking_verified=true. These blanks/false values do NOT prove network rejections. Only authenticated Linkwise publisher records may establish approvals.
- Imported offers: **3,921** (La Redoute 2,036, Xenodoxeio 343, unresolved program 1,542). Latest last_seen_at: September 17, 2026.
- In stock true: **0**. Stock null: 2,379; unresolved-program offers marked false: 1,542. A false imported flag is not definitive evidence of out-of-stock.
- Image URLs: 3,921. HTTPS: 3,193; HTTP: 728. Check actual response, exact variant, copyright/usage and image format. Don't turn HTTP into HTTPS without verification.
- Linkwise URL format: 3,921. It is NOT a validated conversion attribution or domain approval.
- Modeled per-sale expected_commission_eur >= EUR20: 1,701 (all currently La Redoute). The number is a mathematical estimate, not an official NET payout or observed approved commission.
- Vector DB extension pgvector installed. commerce_semantic_documents: 484 (0 embedded). product_embeddings: 0. The product semantic RAG is not populated.
- Feed history: 19 completed, 3 failed, 8 stuck running; no new products imported since September 17.

## Competitors and the missing product proposition
Skroutz already offers an AI shopping assistant with natural-language recommendations, comparisons and alternatives; its 2025 report states +21% orders, +21% Home/Garden, +19% Technology and more than 5m AI-assistant messages. BestPrice advertises 4,000+ shops, roughly 12m offers, price graphs and comparisons. Shopflix aggregates millions of products, direct marketplace purchasing and delivery logistics. Mere "AI shopping chat" or a smaller offer list is NOT defensible differentiation.

Business proposition: "You tell us what will go wrong if you buy the wrong product; our agent checks fit, costs and alternatives, and finds a suitable validated merchant offer or advises not to buy." Distinctive practical problems: sofa will not fit stairway; laptop listed GPU does not match actual model; cabin luggage does not meet the booked fare limits; merchant return rules costly; home office compatibility and measurements; child-room safety and budget constraints. Reddit examples are qualitative signals to validate, not measured prevalence.

Sources:
- https://corporate.skroutz.gr/press-el/skroutz-etisia-anaskopisi-2025/
- https://corporate.skroutz.gr/en/news/voithos-ai/
- https://www.bestprice.gr/giati-bestprice
- https://shopflix.gr/merchant-registration
- https://www.greekecommerce.gr/news/deltia-tipou/erevna-ilektronikou-emporiou-greca-2026-2/
- https://www.reddit.com/r/greece/comments/1wo54bz/
- https://www.reddit.com/r/greece/comments/1op2bh7/
- https://www.linkwi.se/gr-el/texnologia/ergaleia/

## All 334 merchant records — 360 contract
1. Canonical legal merchant identity, website, category and Linkwise program ID.
2. Actual Dealora/SocialMarket publisher-channel approval and allowed traffic types, sourced from official Linkwise account/API.
3. Versioned official commission terms, category exclusions, eligible NET commission base, caps and reversal rules.
4. Program-specific genuine Linkwise tracking/deep links, consent-aware attribution.
5. Feed source freshness, coverage, correct product variants and price/stock evidence.
6. Consumer value: delivery, assembly, returns, warranty, support and claims corroboration.
7. Verified demand: Greek pain-gap sources, commercial intent and measurable search volume only when available.
8. Measured approved EPC100, attributed orders, cancellations, statistical sample size, not assumed CVR.
9. SEO difficulty, practical differentiation and distribution economics.
10. Risk, confidence, explicit missing evidence, last update, human review and next action.

Each merchant gets independent fields: readiness_score (observed data coverage), market_opportunity_insight (AI + source citations), publisher_approval_state (official source), activation_state (deterministic hard gate). An AI agent can RECOMMEND approval or identify missing evidence; it can never forge Linkwise authorization.

Observed DATA READINESS example (not conversion ranking): La Redoute 75/100, Xenodoxeio 65/100, 15 other ID-known programs 45/100, remaining 317 programs at most 10/100. All remain HOLD pending missing proof. Source fields in attached SQL; a higher completeness index is not "top merchant performance".

## All 3,921 offers — 360 contract
Every source ID gets canonical product + variant ID, merchant program identity, title, category, brand, verified model/spec facts, matching authentic image and rights, true price, shipping/returns, stock freshness, Linkwise deeplink, explicit official commission eligibility, compatibility constraints, pain matches, missing facts, safety/legal flags, evidence date, content fingerprint and confidence.
Provide a row-level blocked_reasons array and an all-row score in attached query. Do not permanently reject 1,542 unresolved imports; fix merchant identity and source stock flags first.
After source recovery, index product text and validated facts via hybrid BM25/pg_trgm + pgvector + multilingual reranking. LLM output must cite exact evidence and may not invent data.

## Demand niches to validate in Greece
1. Furniture fit for tight rooms, stairwells, delivery costs and sofa decisions — imported La Redoute supply exists but remains stale.
2. Premium luggage/cabin restrictions and warranty — Samsonite recorded program ID; current product feed absent.
3. High-value home office compatibility and total-cost checks — merchant/feed expansion required.
4. Children's rooms, storage, stability and safety — Cilek is a research candidate; Linkwise program ID not established.
5. Tech spec mismatch/compatibility, home network and power backup — distinctive objective data required.
6. Premium digital subscriptions and total-cost privacy decisions — NordVPN/Surfshark nominally high rates, missing IDs, official approvals and verifiable terms.
These are hypotheses, NOT confirmed Keyword Planner demand, conversions or relative profitability. Run Google Search Console + Greek SERP + forums + verified merchant coverage before choosing spending niches.

## AI 360 orchestration (MyAgenticTeam)
Agent A: Greece demand/SEO researcher delivers problem evidence, search intent and SERP competitors.
Agent B: Merchant verifier reads authentic Linkwise enrollment, payout evidence, fresh feeds, legal status and exact SKU variants.
Agent C: Product fit + QA skeptic checks contraindications, real photo, total costs and no-purchase alternative.
Orchestrator combines structured records and cited insights, never overrides hard commercial gates.
Only NEW/CHANGED feed records are re-embedded; short-cycle price/stock updates do not force semantic recompute. Benchmark 100+ Greek/Greeklish test questions with Recall@5, nDCG@5, latency, false-claim rate, wrong-merchant rejection and no-offer correctness. Comparing BGE-M3 and multilingual E5 is a planned experiment, NOT completed setup.

## Conversion and release gates
Dealora publisher property verified, exact program joined/approved, channel permitted, current price and available stock, genuine redirect, category terms verified and conservative net commission per eligible nonreversed sale >= EUR20. Publication suppressed if any critical fact unknown. This business rule MUST NOT silently mutate the separate SocialMarket EUR10 default.
Clicks -> actual attributed orders -> approved/declined/reversed -> paid Linkwise commissions; never equate modeled earnings with approved EPC.
Only after approval and real browser QA should traffic be driven to customer-focused editorial pages with true images, evidence, alternatives and transparent affiliate links. No autoposting to personal socials or production database write from this research audit.

## Delivery sequence
0. Preserve production state and fix stalled feed lease/TTL and partial snapshot safety.
1. Secure authenticated read-only Linkwise program/website applications + payouts evidence; import status truth without fabricating approval.
2. Normalize all registry IDs/merchant aliases and product variants; image validation, real stock and fresh prices.
3. Populate vector embeddings and run Greek buyer-fit tests; add versioned Merchant360/Product360 evidence snapshots.
4. Release one vertical slice of multi-category AI agent + approved offer cards; mobile/desktop proof and outbound tracking.
5. Publish original pain-to-solution SEO pages and permissioned videos; rank on observed approved EPC with confidence intervals.
6. Expand to 334 registries and all source feeds incrementally; audit/correct before promoting all records.
