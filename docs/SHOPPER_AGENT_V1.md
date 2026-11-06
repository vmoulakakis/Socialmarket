# SocialMarket — Buyer Agent V1 (evidence-first vertical slice)

**Change ID:** CHG-SM-BUYER-20261106  
**Status:** READY FOR REVIEW (source implementation on feature branch; not production deployed)  
**Target:** existing Socialmarket GitHub/Vercel application; additive route \`/marketplace/advisor\`.  
**Not target:** the separate \`socialmarket-ai.vmoulakakis.chatgpt.site\` ChatGPT Site. It does not auto-sync with this GitHub repository.

## Intent and verified baseline

The public ChatGPT Site showed six dated editorial picks, not a buyer decision flow. The canonical private SocialMarket application already includes a Merchant/Demand/Skeptic/Night Brain architecture and live VMDB data. New work must **not** create another sovereign demand model or paid model subscription, replace MyAgenticTeam, publish without human-approved outbox workflow or modify existing affiliate URLs.

VMDB \`public.commerce_feed_eligible_offers\` on 2026-11-06 contained 23,613 records, all \`intelligence_status=pending\`. 8,921 with calculated commission >=€10 were La Redoute with \`in_stock=NULL\` (not false). Another 14,349 had \`program_id=unknown\` and zero calculated commission. **0 records passed the simultaneous \`commission>=10 and stock=true\` gate.** \`public.ai_marketplace_selected_v\` returned zero rows; 28 September \`ai_marketplace_selections\` entries were stale. The legacy \`luxecorner_top100_public_v\` returned 100 mostly sofa products by commission and omits stock and skeptic-evidence fields. Its selection is **not** evidence-verified AI.

The current feature must therefore fail closed for customer endorsements and clearly label *research candidates needing verification*.

## Product and design contract

**Audience:** Greek consumers with a concrete purchase need, budget and preferences.  
**Main job:** ask in Greek for a type of item and receive a source-grounded match with a visible verification state and unmodified affiliate destination (on the pre-existing product detail).  
**Visual thesis (UI/UX Pro Max):** restrained editorial commerce, dark petroleum ink #162D35, evergreen #0E665E, warm paper #F6F4EE, subdued mint #DBEFCB, amber #AA6922 for uncertainties; Greek-compatible system font + Georgia editorial headlines, not gratuitous futurism.  
**Signature interaction:** visible verification stages and an amber "requires verification" result surface. This is deliberate product truthfulness, not proof of model execution.  
**A11y contract:** mobile-first width 320/360/390/768/1024/1440, labels, form submit, feedback/errors/empty/retry, focus visible, readable Greek, reduced-motion, minimum practical 44px controls, responsive wrapping.
**Must preserve:** login/admin routes, existing \`/marketplace\` and \`/luxecorner\` functionality, existing database read views, all \`tracking_url\` strings, canonical merchant and demand data, RLS, API/auth boundaries, scheduler controls and costs.

## Real agent orchestration (target end-to-end, separate from implemented slice)

1. **Intent interpreter** — map Greek shopper need to normalized, grounded intent, budget, deal-breakers, buyer context; never hallucinate product specs.
2. **Merchant & Offer Gate (deterministic)** — input canonical Linkwise program/merchant mapping, active validity, stock (true/false/**unknown**), price, original tracking URL, source timestamp, currency; minimum €10 expected commission for monetized offer universe. Unknown merchant or calculation cannot silently pass.
3. **Demand/Pain Evidence Specialist (MyAgenticTeam)** — retrieve **already validated** market pain clusters, Greek demand evidence, seasonality and competitive whitespace; cite evidence IDs. Missing evidence does not become a 0 score or confident marketing narrative.
4. **Hybrid retrieval/ranker** — BM25/lexical + multilingual embeddings + SQL business gates + graph relations (problem→category→merchant→product→offer). Deduplicate SKU variants, compute buyer-relevance, compare total landed costs if known; commercial margin is an *eligibility* check, not the ranking objective.
5. **Product Research & Reasoning Agent** — bounded semantic analysis only on a small, source-grounded candidate list, using facts and evidence IDs; JSON schema: \`fit, support, limitations, missing_fields, evidence_ids, confidence\`. Never generate new product identities, redirect URLs or ungrounded reviews.
6. **Skeptic / Integrity Agent** — independently check identity, evidence freshness, stock, seller, correct product, currency/price, affiliate parameter preservation and contraindications. If not \`VALIDATED\`, withhold "AI recommends" endorsement.
7. **Presentation Specialist (UI/UX Pro Max)** — show 1–3 best tradeoffs: for whom, why, source date, pros/cons, unknowns, price, merchant, original image, CTA routed through verified product details, marked affiliate disclosure. Explicitly show "no verified result" with research alternatives when blockers remain.
8. **Learning Agent** — consent-respecting first-party retrievals, engagements and commission-approved conversions; preserve provenance and track link validation; do not train on guessed CTR/CVR.

MyAgenticTeam is **the existing supervisory control plane**, not a second scheduler. SocialScheduler remains downstream of \`approved publishing intent\`, never triggered by public shopper intent. Existing \`agents/night_brain/ORCHESTRATOR.md\` has more detailed ranking and promotion policy; its active €10 discovery floor is independent of a stricter >€20 Top100 special-promotion policy in the old \`top100-v2\` config.

## Implemented in this feature branch

- \`lib/shopper-agent.mjs\` — source-bound deterministic intent normalization and contextual retrieval, URL allowlist, affiliate link unchanged, price/merchant/stock/expiry/freshness/skeptic-evidence gates, duplicates and ranked results. It never labels unknown-stock products verified.
- \`app/api/marketplace/advisor/route.js\` — bounded, stateless, read-only POST route. Uses existing \`getLuxeTop100()\` as temporary limited-scope discovery source; preserves first-party data model.
- \`app/marketplace/advisor/page.jsx\`, \`components/catalog/BuyerAdvisor.jsx\`, and module CSS — responsive Greek shopper interaction with source/verification and affiliate disclosure.
- \`scripts/validate-shopper-agent.mjs\` — deterministic test fixtures for unknown stock, no evidence, URLs, commission, budget, dedupe and ranking.
- Existing public marketplace receives only an additive deep link to the advisor. No schema migrations, no paid model calls, no production writes, no live recommendations manufactured.

**Truthful runtime wording:** \`mode=bounded_read_only_retrieval\`, \`ai_model_executed=false\`. The first implementation is a meaningful **agentic decision-gate scaffold**, not yet an operational generative shopper agent.

## Next blocked work (not implemented by this PR)

**P0 / data-integrity:** repair feed \`program_id=unknown\` mapping; do not overwrite unknown source availability with true. Run a current merchant availability + Linkwise commission and tracking validation, preserve \`NULL\` until corroboration.

**P0 / canonical audit:** materialize product-evidence + skeptic-audited recommendations into a controlled **public read-only, security-invoker** VMDB view only after internal results and RLS audit; no view based solely on high commission. For stock *unknown*, request live merchant confirmation rather than falsely calling it in stock.

**P1 / true LLM agent activation:** integrate the existing bounded MyAgenticTeam/AI runtime after source evidence, JSON contract, independent critic, privacy/throttle/budget rules and actual model availability have passed. Public API must have rate limiting before any billable inference. Keep \`ENABLE_PAID_REMOTE=0\` unless owner approves a quantified budget. Benchmark explanations on a labeled Greek set.

**P1 / merchandising:** replace source-limited 100 sofas with canonical validated products across meaningful problems/categories; counter affiliate bias with exposure caps, best-value comparison and truthful uncertainty. Add user-attribution and conversion monitoring only with valid consent and network provider reporting.

**P2 / launch:** CI, screenshot QA, accessibility, security review, release approval, Vercel preview/production monitoring. ChatGPT Site itself requires a separate native Sites edit; this repo PR will not change that distinct property.

## Verification and rollback

Proposed local/CI commands: \`node scripts/validate-shopper-agent.mjs\`, \`npm run test:shopper-agent\`, \`npm run build\`. CI is authoritative only when status reports complete. Browser/mobile screenshot inspection remains **UNVERIFIED** unless actually performed. Public LLM execution, real-time stock, live tracking attribution, and sales are **NOT VERIFIED**.

Rollback: do not merge the branch; if merged later, revert commit/PR. The feature is purely additive: the existing marketplace stays intact if its advisor route is removed.

## Risks / security review

The pre-existing \`luxecorner_top100_public_v\` is a convenience feed not strong evidence; source is not widened to the full private \`commerce_feed_eligible_offers\` via anon grants. Existing Linkwise redirect is not rewritten or suffixed; outbound merchant action remains on preexisting product detail route. Do not leak \`service_role\` in public clients. Developer and consumer-facing wording must not claim "AI analyzed reviews," "real-time available," "best in Greece," or "agent recommended" without cited evidence, true model execution and positive review gates.
