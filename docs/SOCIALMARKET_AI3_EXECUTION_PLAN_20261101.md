# SocialMarket AI 3.0 — Approved-direction execution record (2026-11-01)

**Change ID:** SM-AI3-20261101  
**Owner:** AI Architect (decision support only)  
**Repository:** vmoulakakis/Socialmarket, draft PR #99  
**Supabase:** VMDB gqpbskssrvpfjtujwezc, **private sm_intel only**  
**Mode:** BUILD + staged deployment of additive research-only services; do not merge or deploy a new public storefront.  
**Excluded:** historical Linkwise JSON bulk ingestion (explicit prior restriction), live merchant/affiliate approval, publishing, paid ads, purchase, emailing, unrelated VMDB app schemas.

## Intent
Deliver a full-lifecycle, evidence-based Greek Commerce Intelligence Engine that discovers real unserved jobs-to-be-done, identifies fitting products and trusted merchants, estimates economic viability, and learns from attributable conversions. A document search chatbot or a numeric admin dashboard **does not satisfy** this intent.

## Product-level decision contract
1. Identify **market problem** independently of the affiliate feed.
2. Record demand, available local supply, competitors, consumer-stated decision frictions, geography and time **with original independent source records**.
3. Match product to a **solution mechanism**, not only to a shared word.
4. Keep product identity, merchant identity, affiliate program, publisher approval, category exclusions, stock, price, terms valid-from/valid-to and source tracking URL separate.
5. **Hard financial gate:** verifiable conservative estimated approved commission >= EUR10, current publisher/category terms, source-valid tracking and availability. No inference may override this.
6. Rank customer utility separately from business profit. No model may generate affiliate tracking URLs, fabricate purchase intent, imply discount/stock without current proof or label candidate claims as verified.
7. Record evidence, contradictory evidence, decision version, uncertainty and outcome of independent review.
8. Only after actual attribution data exists, train/personalize aggregate conversion models using temporal train/test splits, holdouts and leakage controls.

## Chosen architecture (cost-aware)
- PostgreSQL authoritative data in `sm_intel` (shared VMDB **private**): versioned immutable source observations, commission identity, opportunities, interventions and outcomes.
- **Hybrid retrieval:** `pgvector` + Greek/English FTS + reciprocal rank fusion; temporal evidence graph with strong provenance. No second graph database until profiling proves it necessary.
- **Embedding model:** `intfloat/multilingual-e5-small` (384 dimensions) CPU, versioned; choose larger BGE-M3 only if a human-labeled Greek/Greeklish holdout shows meaningful benefit per cost.
- **Reranking:** BGE-reranker-v2-m3 is evaluation-only until quality and latency measurements.
- **Forecast/ranking:** only after verified training targets; start with calibrated interpretable statistical baselines and gradient boosting, compare GNN to rigorous time-split baseline when positive/negative graph supervision becomes sufficient.
- **Reasoning:** deterministic source contract -> neural retrieval -> narrow LLM only for *complex, independently evidenced* contradictions; run through existing budget-controlled SocialMarket gateway.
- **Buyer psychology:** explicit job-to-be-done, relevant risk and consented aggregate funnel signals. Never hidden sensitive profiling or invented urgency.
- **AI Architect:** up to three bounded agents, specialist reviewer, abstention when evidence absent; all generated changes need independent review and versioned rollback.

## Executed changes in this turn
| Gate | Implementation / validation | Status |
|---|---|---|
| Evidence audit | `sm_intel.opportunity_research_v3` provenance snapshot, observed demand/supply/counterevidence, distinct verified domains, research gaps | **MIGRATED** |
| Product discovery | `sm_intel.opportunity_product_candidates_v3` + `refresh_opportunity_research_v3(100)` | **EXECUTED** (41 problems, candidate-only) |
| Scope quality | Rejected historical TravelAI links; travel/hotel/flight prohibited in future SocialMarket candidate matching | **MIGRATED** |
| Neural execution governance | `sm_intel.neural_model_registry_v3`, retry-limited claim lease, `embedding_health_v3()` | **MIGRATED** |
| Actual neural inference test | Optional CPU E5 Greek + Greeklish + English synthetic smoke in GitHub Actions | **CI initiated; consult final run** |
| Live read API | `socialmarket-intelligence-v3` Edge Function admin-JWT-checked, read-only, no paid calls | **DEPLOYED**, authenticated E2E not yet observed |
| Orchestration integration | `socialmarket-architect` includes evidence audit for pain tasks and research backlog for portfolio | **DEPLOYED v5** |
| CI | Offline retrieval metric tests + Deno typecheck in PR workflow | **CI; consult final run** |

**Observed snapshot:** 41 problem clusters, 21 with partial signals and 20 still requiring research; 0 independently verified market gaps, 0 qualified affiliate offers, 4,360 searchable docs, 0 real E5 embeddings. Eight lexical product candidates were found but were unrelated travel products; all eight were retained as *rejected* for audit rather than promoted. **The present corpus is not yet sufficient for real purchase recommendations.**

## Remaining gates — execute in this order
**P0: Reconcile source contracts and data freshness** (active and blocked)
- Old Linkwise cron/Edge job is separate and not reliably refreshing the database; change only with reviewed cutover, preserved history and monitored fallback.
- Import complete **publisher-specific** program metadata through the official source. 334 source program records are not 334 verified approvals. Missing program IDs/validity block commission.
- Record new vs unchanged vs expired products without overwriting existing historical records.

**P1: Real multilingual semantic deployment** (not yet production verified)
- Run CPU E5 worker in secured runtime with server-only DB credentials, backfill existing search docs in leased batches, checkpoint and observability.
- Prepare **human-labeled** Greek/Greeklish catalog query relevance set with hard negative examples; benchmark Recall@20, nDCG@10, latency, cost, candidate source freshness and false-positive rates.
- Enable reranker only if it beats lexical+E5 baseline on held-out data.

**P2: Greek demand/supply evidence** (not complete)
- Source independent market demand/supply by region and day with timestamped URLs, counterevidence, market availability and observation precision.
- Build validated customer problems/solutions and alternatives. Source-count alone is never evidence of high demand/low supply.

**P3: Merchant/product decision engine** (not complete)
- Versioned program eligibility and commission, trust, fulfillment, price/stock, solution efficacy and offer expiry.
- Independent review and truly approved offers, or recommendation abstention.

**P4: Outcome learning** (not complete)
- Collect consented aggregate CTR, verified conversion postbacks, approved commissions, refunds and source/version attribution.
- Model training only after statistically adequate data; guard against survivorship, time leakage, data sparsity and merchant gaming. No policy self-approval.

**P5: Personal Intelligence workspace** (later)
- Explain **why** an opportunity was accepted/rejected, its evidence and counterevidence, suitable solution, merchant risk, real performance, forecasts and AI model uncertainty. Operations dashboard remains subordinate.

## Acceptance and rollback
- No cross-project tables modified; new schemas nonpublic with RLS and service-role-only grants.
- No unsupported demand volume, zero fake commercial approvals, no anonymous access to data.
- Unit/CI tests for retrieval metrics, JSON schema, JWT check, fail-closed promotion and model fallbacks.
- New migrations are additive and auditable; generated v3 candidates can be marked rejected or rebuilt without modifying underlying raw products or evidence.
- No public merge/production UI update without independent CI and verified authenticated browser QA.
- Status reporting MUST distinguish `MIGRATED`, `CODED`, `DEPLOYED`, `TESTED`, `PRODUCTION INFERENCE VERIFIED`.

## Neural proof / production validation addendum (2026-11-01)
- **Executed real CPU E5 smoke:** GitHub Actions [run 41347702932](https://github.com/vmoulakakis/Socialmarket/actions/runs/41347702932), completed success. Model output: **4/5 positive-vs-negative labeled synthetic pairs correct** (`pair_recall_at_1=0.8`, `average_positive_margin=0.0481`). The Greeklish query `pos na metrao ygrasia xwrafiou` failed (margin -0.02478); this is a concrete multilingual weakness, NOT a general accuracy estimate. No Supabase vectors were written and no paid language-model inference was called.
- **Regression discovered by CI:** first v3 Edge API typecheck failed on interpolating `unknown` UUID, subsequently fixed in commit `bb393fcc` and Edge Function deployed as v2. Await latest PR CI to confirm all gates.
- **Opportunity evidence:** actual `refresh_opportunity_research_v3(100)` assessed all 41 problems. 21 partial evidence, 20 research needed, 0 independently review-ready. Eight travel-related lexical matches were **rejected** (not deleted, not published) to respect non-travel SocialMarket scope.
- **Production neural backlog:** `embedding_health_v3()` reports 4,360 documents pending and **0 ready**. The lease-based worker is coded but needs a secure CPU runner and database credentials; a smoke test against synthetic examples is NOT a production indexing run.
- **P0 SQL acceptance:** `opportunity_brief_v3` returns only research candidate facts, zero commercial promotion, and the new private tables deny anon access. No source data, programs, commission terms, prices, or legacy ingestion jobs were altered.
