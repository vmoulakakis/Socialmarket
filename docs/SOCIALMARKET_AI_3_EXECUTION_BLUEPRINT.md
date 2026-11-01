# SocialMarket AI 3.0 — Execution Blueprint and Release Evidence

**Owner:** SocialMarket AI Architect · **Scope:** `vmoulakakis/Socialmarket`, private `sm_intel` only inside VMDB `gqpbskssrvpfjtujwezc`  
**Version:** 3.0, authored 2026-11-01. **Status:** Implementation in staged PR #99 + additive private database migrations; production release is NOT approved.

## Mission

Build a verifiable, economics-aware, Greece-first Neural Commerce Intelligence system. Discover genuine customer problems with independently supported demand and gaps in *suitable* Greek supply. Match high-fit products and merchants with true affiliate authorization and conservative calculated commission **≥ EUR10**; learn from independently observed outcomes without deceptive buyer psychology or self-reinforcing model guesses.

**Hard truth:** A 100% intelligent / 100% correct AI system is not possible. Operate with confidence calibration and abstain when data is missing.

## Existing baseline (verified from VMDB on 2026-11-01)
- 3,921 historical raw product rows from **only 3 distinct program IDs**; 773 lack source description. Merchant source directory 334 rows, 317 missing authoritative program ID; 16 enriched merchant profiles ≠ 334 approved.
- 41 GR problem clusters, 386 historical market evidence rows, only 34 linked to a pain cluster; none independently verified.
- 4,360 semantic-search documents with **0 real multilingual E5 vectors**; 5,140 graph edges with **0 independently verified edges**.
- 0 qualified/promotable offers under current verified affiliate gate; 0 commerce conversion events.
- Existing model, scraper and marketing workflow generations in the repository and retired DB references must be treated as noncanonical until migration review.

## Architecture: evidence before inference

`official sources + first-party data`
→ `streamed source audit + versioned catalog / network merchant and commission contracts`
→ `structured GR market signals (demand, supply, competitor, intent, time, geography) and uncertainty`
→ `market and product feature stores`
→ `multilingual E5 + SQL lexical + temporal provenance graph + neural reranker`
→ `two-tower problem/product fit and calibrated business model`
→ `commercial eligibility + independent skeptical review`
→ `attribution + held-out learning loop`.

A paid LLM never approves merchant terms or substitutes for externally observed demand data.

## P0 — Canonical identity and reliability

**Built:** `sm_intel.raw_products`, `merchant_program_directory`, `affiliate_network_programs_v3`, `commission_terms`, `qualified_offers`; delta-only streaming worker with bounded memory, ETag/resume and hard >=EUR10 verification. Awin joins are a SEPARATE network, not Linkwise merchant ID aliases.

**Now verified:** official Awin publisher 3060863: Back Market GR (program 30859) **pending**, not joined. Stored accurately as a network relationship with `active_for_publisher=false`. Zero Awin approved GR programs in read-only query. Do not invent affiliate links.

**Release gate:** source snapshot coverage and provenance, identity uniqueness, current category/publisher contract rate and expiry, truthful stock. Existing Linkwise legacy cron remains untouched until explicit safety review. The user previously instructed NOT to download/import the full Linkwise JSON at this stage.

## P1 — Market Evidence Engine

**Built:** `market_signals_v3` source-family/ID dedup, temporal expiry, region and original source attribution; `market_evidence_coverage_v3`; `market_assessments_v3` with trigger preventing verified assessments without fresh, independent demand and supply proof. 34 historical linked signals backfilled as *candidate only*.

**External source connectors to implement/validate:** Greece search interest (Google Trends is a relative index, NOT absolute volume), own GSC if access authorized, official marketplace/product search, reliable Greek retail comparisons, historical weather/holidays where causal, product availability, first-party opt-in outcomes. No market research score fabricated from a product feed count.

**Gate:** at least 2 independent current source groups, one demand and one observed suitable supply, clear metric definitions and counterevidence before declaring verified market gaps. Missing data yields research task, not a number.

## P2 — Hybrid Neural GraphRAG

**Built:** 384D `search_documents` schema, E5-aware HNSW index and bounded private claim/ack embedding queue, SQL lexical retrieval + RRF, private 1–2 hop evidence graph, and authentic admin-only GraphRAG API. `model_registry_v3` holds candidate model choices with evaluation requirements. Real offline CPU E5 evaluation pipeline added to GitHub CI. Current production E5 vectors still 0 until worker is connected to secure database credentials and executed.

**Candidate model selection:** 
- E5 multilingual-small 384D initial lightweight embedder.
- BGE-M3 as multilingual dense/sparse alternative and Qwen3 Reranker 0.6B as re-ranker benchmark.
- Two-tower PyTorch contrastive product/problem matcher only trained on **≥100 independently verified positive pairs**, ≥10 problem groups, ≥50 products, ≥3 independent evidence sources. Current 0 verified pairs: training is explicitly blocked.
- Heterogeneous GNN is an **evaluation candidate** after sufficient verified graph structure, not a declaration of production readiness.
- Strong paid LLM limited to complex ambiguous evidence and independent review, no automatic tokens.

**Gate:** Greek/Greeklish hard-negative retrieval eval (Recall@20, nDCG@10, false-positive rate), model/version labels, quality-vs-latency benchmark, zero fabricated citations, human review. Newer/larger model only if it beats baseline and fits CPU/GPU envelope.

## P3 — Opportunity and buyer decision intelligence

**Built:** versioned `product_feature_snapshots_v3` from real source fields (3,921 snapshots); `product_problem_hypotheses_v3` with explicit `needs_evidence` and separate verification; conservative lexical baseline and hard-negative fixtures; `market_brain_health_v3`.

**Policy:** Customer-value fit and commercial viability scored separately. Avoid arbitrary single weighted LLM score. Buyer psychology is limited to stated job-to-be-done, perceived risk, compatibility, trust, price-value, friction, local timing; no sensitive personalization, coercion, fake scarcity or hidden inferred vulnerabilities.

**Gate:** no candidate promoted without independently verified suitability, authentic tracking and current program approval. No expected sales predictions before actual attribution.

## P4 — Observed outcome and learning

**Built contracts:** agent outcomes, change proposals, learning observations, model registry and evaluations.
**Absent source:** actual sales/postbacks, returns and approved commissions; current `commerce_performance_events` empty.

**Future operational steps:** store privacy-preserving funnel events, reconcile affiliate sales and refunds, train calibrated learning-to-rank with temporal held-out data and negative examples. Gate changes on improved approval-adjusted revenue per 1,000 qualified visitors *and* no decline in consumer solution utility. Bayesian bandits only after traffic exists.

## P5 — Orchestration and operations

**Existing:** private `socialmarket-architect`, `socialmarket-graphrag` Edge Functions; specialist agent task table and private admin cockpit. Model calls require explicit, evidence-backed escalation; no autonomous publishing.
**New:** persisted source quality and model lineage tables; actual v3 readiness metrics and robust abstention.

One architect dispatches at most 3 bounded tasks per invocation; independent skeptical verifier reviews claims. Source strings are untrusted tool data. Only publish/recommend with reviewed advertiser/publisher terms and affiliate link validity.

## Production release gates

| Gate | Required evidence | Current |
|---|---|---|
| Catalog coverage | Full CD104 and Awin join proof, current identity and safe delta | **Blocked** by user-authorized no-import and terms verification |
| Demand-supply truth | Independent dated GR demand/supply evidence | **Blocked**: 0 verified signals |
| Embeddings | Real stored 384D E5 vectors + 5-query hard-negative benchmark | **CI benchmark staged**, DB 0 vectors |
| Graph facts | Independently provenance-reviewed relationships | **Blocked**: 0 verified edges |
| Neural learning | Holdout data + minimum 100 verified pairs | **Blocked**: 0 verified pairs |
| Commercial activation | publisher approval + current terms + >=EUR10 calculated minimum | **Blocked**: 0 current verified terms |
| User analytics | consented attributable events, sales/returns reports | **Blocked**: 0 events |
| Safe deployment | green CI, security review, protected preview QA | Draft PR only; do not merge into production without independent review |

## What has been ACTUALLY done in this execution (do not overclaim)

1. Added and applied additive versioned `sm_intel_neural_market_foundation_v3` migration and `sm_intel_affiliate_network_truth_v3` migration.
2. Generated 3,921 real versioned product-feature snapshots.
3. Backfilled 34 historical problem-linked evidence rows as **candidate** research signals, never as verified demand.
4. Implemented and tested safety guard: verified opportunity requires >=2 independent, current demand/supply sources. Synthetic fixtures rolled back.
5. Registered five cost-aware model candidates as **candidate**, none falsely marked ready.
6. Added local zero-token Greek lexical baseline and hard-negative regression, real Hugging Face E5 CPU benchmark and trainable PyTorch two-tower with a hard zero-label training block.
7. Queried official connected Awin programme membership and persisted Back Market GR program **pending**, no active joined programme.
8. Did NOT fetch the full CD104 JSON, insert new bulk products, spend paid AI model tokens, create public recommendation pages, or release unreviewed code to production.

## Source-of-truth design rule

Do not conflate `source_imported`, `identified`, `verified_evidence`, `estimated_demand`, `merchant_joined`, `commission_eligible`, `product_fit`, `promotion_ready`, `revenue_observed`. Each requires separate dated proof and auditability.

## 2026-11-01 23:15 Athens — Neural activation & reliability gates

**Validated live changes:**

1. DB function `sm_intel.opportunity_brief_v3` now excludes `relevance_review='rejected'`. Verified 2 affected Greek problems expose 0 candidates and report 4 rejected records excluded each. All 8 historically rejected product matches are hidden; no candidate is falsely represented as commercially eligible.
2. `sm_intel.market_evidence_coverage_v3` now counts a verified source only when its provenance is independently identifiable, observation is <=90 days old, not future-dated, and source expiry is still valid. Real check: 41 problems, 37 total signals, 0 verified demand, 0 verified supply, 0 review-ready. This intentionally reports honest incompleteness.
3. Added `.github/workflows/socialmarket-e5-protected-backfill.yml` for a **manual-only, CPU, E5, max 16/32/64/128 document batch** with concurrency lock, protected `socialmarket-intelligence` GitHub environment, exact main SHA, dedicated `SOCIALMARKET_DB_URL` secret, URL project-ref preflight and post-write model checks. There is no push or cron trigger.
4. No production E5 vectors have been written. GitHub workflow dispatch requires its reviewed commit present on main, a manually approved environment and explicit `SM_INTEL_E5_APPROVED=true` environment variable. This PR is still draft; do not bypass the gates.
5. Existing SocialMarket AI Architect automation was **run-now requested** once to continue original independent GR market research; do not infer completion or evidence import before the automation actually reports an outcome.
6. Supabase 384-d vector storage and HNSW schema already exist and match the E5 model contract. The private `socialmarket-graphrag` function remains lexical-only until (a) production documents have real E5 embeddings, and (b) a secured E5 query encoding endpoint is deployed and configured. Never claim vector retrieval active merely because CI synthetic benchmark passed.

**Release checklist for model activation**:
- [x] Error/relevance false-positive guard blocks all 8 rejected pairs at the opportunity brief API.
- [x] Market evidence freshness and source-independence check enforced in live coverage.
- [x] 4,360 pending vectors / 0 ready verified before worker release.
- [x] CPU E5 model executed successfully on synthetic Greek cases in GitHub Actions; its recorded model evaluation is still **pending** on realistic merchant catalog test labels.
- [ ] Independent PR code/security review and protected environment approval.
- [ ] Confirm GitHub protected environment `socialmarket-intelligence` has active required reviewers, `SM_INTEL_E5_APPROVED=true` and `SOCIALMARKET_DB_URL` secret, with strictly scoped database account (not cross-project superuser).
- [ ] Merge audited revision and manually dispatch one bounded **16-doc** run. Check actual `embedding_status=ready`, model provenance, error/lease counts and Greek retrieval evidence before scaling.
- [ ] Repeat only if live correctness and resource metrics meet thresholds; do not perform full backfill automatically.
- [ ] Deploy a secure CPU E5 query encoder (same embedding model and pooling) on authorized server such as existing private Oracle node, and configure server-only TLS URL and random access token. Never expose the decoder or DB credentials to browser clients.
- [ ] Separately complete human-labeled GR retrieval benchmark and merchant commission verification before any end-user recommendations.

**Safety:** no new Linkwise full-feed download, no public promotion, no paid API model calls, no artificial product/demand scoring from pending labels.

## 2026-11-01 — CD104 full-feed product admission, strict > EUR10 + valid_to from today

User authorized full import (supersedes earlier no-full-scan instruction). This authorization **does not** authorize inventing publisher commissions or treating an unapproved advertiser as joined.

### Canonical qualification

- Input: the user's long CD104 `programs-all` feed URL, already stored only in encrypted VMDB Vault `socialmarket_linkwise_cd104_full_feed_url_v1`. Do not display or commit decrypted URL.
- Scan all feed records via bounded `ijson`; `program_id|product_id` is the stable product identity. Stream insert-only delta for new records; reconcile existing raw items separately.
- **STRICT** calculated minimum commission `> 10.00 EUR` (exact `10.00` is rejected). Price is not commission; use reviewed current publisher CD104 programme-specific terms, conservative rate type and verified effective validity.
- **MANDATORY** product `valid_to` (not null) strictly later than processing timestamp (and on/after local Europe/Athens today). Missing, malformed, expired, not yet valid, non-EUR, invalid tracking identity or unresolved terms remain excluded from admitted catalog.
- Existing raw rows are not overwritten. Additional `sm_intel.reconcile_existing_eligible_offers_v4(5000)` admits old valid products only once a verified contract becomes effective; new imported rows through `sm_intel.ingest_new_only_batch`.
- `sm_intel.delta_feed_batches` now audits missing expiry, expired, missing terms, and commission not above EUR10 per bounded committed batch; `sm_intel.product_expiry_commission_audit_v4` and `linkwise_program_readiness_v4` expose read-only operator diagnostics.
- Formal publisher approval, current stock and tracking readiness remain independent promotion gates. Product admission alone does not permit public promotion.
- The manual GitHub workflow `.github/workflows/socialmarket-vmdb-full-refresh-manual.yml` now runs existing reconciliation before full source commit; requires main branch, runtime DB credential and explicit workflow_dispatch. This PR remains DRAFT / unmerged, so a full live import **has not been run**.

### Observed live baseline — 2026-11-01 around 23:36 Europe/Athens

- 3,921 historical raw products across 3 program IDs: `23` (2,036; no `valid_to`), `unknown` (1,542; 1,507 no `valid_to`, 35 expired), `205` (343; 339 future valid, 4 expired).
- Total: 3,543 missing `valid_to`, 39 expired, 339 future-dated but lacking verified commission terms.
- `sm_intel.commission_terms`: 16 historical CD104 records (14 percent-min, 2 flat-min), **0 verified** and no current independent terms expiry. A Linkwise CD104 feed provides product prices, not full current commission contracts for all programs. Source evidence is required from the official publisher network before eligibility can be computed.
- `sm_intel.qualified_offers` remains 0. `sm_intel.feed_runs` and `delta_feed_batches` remain 0 for new streaming worker. Reconciliation ran safely and admitted 0 from the current real data. Never misstate this as a successful all-products import.
- Real PostgreSQL transaction rollback acceptance: synthetic verified percent-min term and exact expiry boundary; one offer with EUR10.001 commission admitted, exact EUR10 rejected, null and expired dates rejected, unknown terms blocked; batch replay idempotent. Separate synthetic old-row reconciliation checks one correct admission and no overwrites. All fixture rows rolled back.

### Remaining activation blockers

1. Current source-authentic, publisher-specific Linkwise commission terms and account/program approval, including effective dates and category/exception rules; do not promote imported CSV into verified terms by assumption.
2. Approved main-branch GitHub Actions environment with a scoped `SOCIALMARKET_DB_URL` credential for a long-running (potential multi-GB) full-feed scan. Supabase Edge Functions have short wall-clock/memory limits and are not a safe replacement for full 3.84GB streaming.
3. Latest exact-commit CI and independent review, then explicitly dispatch the main-branch one-shot `delta_new_only_commit` and inspect count/failures. Do not add a silent daily cron or bypass user/account secrets.
