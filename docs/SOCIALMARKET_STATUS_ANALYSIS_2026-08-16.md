# SocialMarket AI — Production Status Analysis

**Report date:** 2026-08-16  
**Repository:** `vmoulakakis/Socialmarket`  
**Production Supabase:** `socialmarket` / `rpfadpdnnxequgvdcfoq`  
**Report scope:** Merchant Intelligence → Category Pain → Deep Demand → Product Intelligence / Promotion Ranking → Creative → Content → SocialScheduler / Buffer.

---

## 1. Executive assessment

SocialMarket has moved from an architecture-complete but product-output-blocked state to a production repair / verification state.

The two most important production repair sets are now merged to `main`:

1. **Product Ranking V3.6.2 production repair** (`314c766ca944592e764ce780a9196e1d6e44ccca`)
   - direct Linkwise transport false-failure fixed;
   - expected commission policy aligned to **>= EUR 10**;
   - adaptive ranking explicitly allows eligible products without validated pain to rank, while giving them no pain/evidence bonus;
   - expired Creative Gateway GitHub OIDC tokens refresh automatically;
   - AI/SEO/creative singleton failures are observable instead of silently swallowed;
   - full SEO is required for the final saved ranking set;
   - all Top-20 creative packs must pass the independent Creative Skeptic with `READY`;
   - 20 complete durable creative packs / 60 PNG assets are required before final completion;
   - canonical content persistence must be explicitly approved before handoff.

2. **Category Pain V4.7 audit-stability repair** (`0018f1d465ab92b730565a01c1af83bb26da7031`)
   - changed DeepSeek audit request size from four taxonomy targets per call to one target per call;
   - increased workflow timeout for the safer lower-concurrency path;
   - **no validation, source-diversity, severity, commercial-intent or market-evidence threshold was relaxed**.

### Overall status

| Domain | Status | Assessment |
|---|---|---|
| Merchant foundation | GREEN | 309 canonical merchants/programs and 309 semantic objects present |
| Merchant Intelligence | GREEN | latest scheduled V4.3 workflow completed successfully |
| Category Pain collection | AMBER | repair merged; new production V4.7 run is validating removal of previous HTTP-500 audit failures |
| Validated pain availability | RED | currently 0 validated semantic pain clusters; 4 pending out of 43 total |
| Deep Demand V3.1 | GREEN / WITHHELD | workflow succeeds and correctly withholds unsupported forecasting/causal claims due insufficient history |
| Linkwise feed contract | GREEN | live contract validation passes |
| Direct Linkwise transport | GREEN | authoritative V3.6.2 production run has now passed direct live feed download successfully |
| Deterministic Product Phase A | AMBER | authoritative run is currently executing Phase A |
| Adaptive Product Ranking V3.6.2 | AMBER | code/CI fixed; live final ranking still requires authoritative completion |
| SEO enrichment | AMBER | strict complete-set contract implemented; live verification pending final ranking step |
| Top-20 Creative generation | AMBER | stale-OIDC defect repaired and tested; live 20/20 READY verification pending |
| Durable creative assets | AMBER | 60-asset contract implemented; live persistence verification pending |
| Product DB persistence | RED until final run | no product rankings/products/offers persisted yet; fail-closed behavior is intact |
| Canonical product content | RED until final run | no product-related canonical content persisted yet |
| SocialScheduler / Buffer | GREEN | latest checked scheduled executor run succeeded; current outbox remains safe |
| Frontend source build | GREEN | GitHub CI Next.js build passes |
| Vercel deployment | AMBER | external Vercel build-rate-limit status remains outside the repaired intelligence pipeline |

---

## 2. Production truth vs architecture truth

The system deliberately distinguishes **code readiness**, **data readiness** and **production proof**.

A feature is not marked production-ready only because code exists or CI passes. For Product Intelligence the required proof is an observable chain:

```text
real Linkwise feed
→ feed contract
→ merchant/program resolution
→ price/stock/tracking integrity
→ expected commission >= EUR 10
→ deterministic/adaptive shortlist
→ demand / merchant / pain / theme context where available
→ AI ranking
→ independent ranking audit
→ SEO enrichment
→ Top-20 creative generation
→ Creative Skeptic READY 20/20
→ 60 durable assets
→ persisted ranking/content
→ explicit publish scheduling
→ SocialScheduler
→ Buffer
```

The authoritative Product Ranking V3.6.2 production run is currently progressing through this chain. Direct Linkwise download has already passed after the repair; Phase A is the current live stage at report creation time.

---

## 3. Merchant Intelligence

### Live state

- canonical merchants: **309**
- canonical merchant programs: **309**
- `ai.semantic_objects`: **309**
- evidence audits:
  - `VALIDATED`: **5**
  - `NEEDS_REVIEW`: **1,247**
  - `REJECTED`: **490**

The latest checked scheduled **Merchant Intelligence V4.3 Semantic** workflow completed successfully.

### Assessment

**GREEN.** Merchant infrastructure is operational and continues to provide merchant trust, commercial, taxonomy and evidence context. Merchant popularity/commercial metrics remain separate from real consumer demand.

---

## 4. Category Pain Intelligence

### Pre-repair failure

The scheduled Category Pain production run processed **33 taxonomy targets** and all **33 failed at `audit_batch`** with `evidence-gateway` HTTP 500 responses.

This is the direct operational explanation for the lack of newly validated pain clusters despite evidence collection activity.

### Repair

Category Pain V4.7 changes only request orchestration:

```text
old: up to 4 large taxonomy/evidence bundles → one DeepSeek audit request
new: 1 taxonomy/evidence bundle → one DeepSeek audit request
```

Existing hard validation remains unchanged:

- same consumer-text requirement;
- same source/domain independence rules;
- same market metric requirements;
- same confidence threshold;
- same audit-score threshold;
- same pain-severity threshold;
- same commercial-intent threshold;
- no synthetic pain and no fallback validation.

### Live state

At report creation:

- `evidence.semantic_clusters`: **43** total
- validated: **0**
- pending: **4**
- V4 collection jobs:
  - completed: **56**
  - queued: **32**
  - running: **1**

A new production V4.7 workflow is currently executing after the merge.

### Assessment

**AMBER for pipeline health; RED for validated-pain availability.** The operational failure has been repaired in code/CI, but production proof requires the current run to complete without the former 33/33 audit failure. Even a successful run may legitimately produce zero validated clusters if evidence does not meet strict standards.

---

## 5. Deep Demand Intelligence V3.1

### Live workflow

Latest checked scheduled Deep Demand V3.1 workflow: **SUCCESS**.

Database state:

- `intel.demand_analysis_runs`: **3 completed**
- `intel.demand_model_lab_runs`: **282 WITHHELD**

### Why `WITHHELD` is correct

The current model-lab history is too shallow for defensible time-series or causal forecasting. A representative latest result reports:

- daily observations: **1**
- history span: **0 days**
- requires **90 raw points** and **30-day span** before production forecast eligibility;
- statistical challengers: withheld;
- neural challenger: withheld;
- change-point detection: withheld;
- rolling-origin validation: withheld;
- causal readiness: withheld;
- production forecast: `null`.

This is not a malfunction. It proves the model governance is working: complex forecasting cannot manufacture certainty from insufficient history.

### Assessment

**GREEN / intentionally WITHHELD.** Deep Demand is operational, but calibrated production forecasts will become eligible only after sufficient observed history accumulates. Until then, ranking may use valid observed/derived evidence but must not represent withheld forecasts as observed demand.

---

## 6. Product Intelligence and Promotion Ranking

### Previous verified Phase A universe

The latest complete usable pre-repair deterministic scan established the scale of the decision universe:

- recovered complete records: **2,668,657**
- commission-eligible records: **115,551**
- eligible offers: **111,595**
- unique commission-eligible products: **27,283**

This proves the previous zero recommendation result was not evidence of “no products”; it was a funnel/gating/production-completion problem.

### Product Ranking V3.6.2 repairs

#### A. Direct feed transport

Fixed a real Python logging defect that raised after a valid multi-shard Linkwise merge. The new authoritative production run has already passed the direct feed download step successfully.

#### B. Commission policy

Production workflow and runtime configuration now explicitly use:

```text
minimum expected commission = EUR 10
minimum merchant trust = 50
```

Runtime config is now:

- version: **7**
- profile: **Adaptive Ranking V3**
- selection policy: **adaptive_ranking_v3**
- minimum expected commission: **EUR 10**

#### C. Pain is not an entrance gate

Adaptive discovery behavior:

```text
validated pain present   → evidence-backed score/confidence bonus
validated pain missing   → zero pain bonus / lower evidence confidence
validated pain missing   ≠ automatic product rejection
```

Strict `VALIDATED` semantics remain independent. Missing pain cannot be invented or converted into favorable evidence.

#### D. Missing competition remains conservative

```text
competition missing → inverse-competition bonus = 0
```

Missing data never becomes “low competition”.

#### E. AI / Creative OIDC

Creative calls can occur after a long deterministic/ranking/SEO stage. The previously cached GitHub OIDC token could expire before creative generation. V3.6.2 now refreshes a token after HTTP 401 and retries once. Regression coverage validates this behavior.

#### F. Stronger final contract

A production-complete ranking now requires:

- at least **100 ranked products**;
- complete SEO enrichment for the target saved ranking set;
- **20 Top-ranked creative packs**;
- independent Creative Skeptic verdict `READY` for **20/20**;
- **3 durable PNG assets per creative product**;
- **60 assets total**;
- successful persisted ranking set;
- approved canonical content persistence.

No partial ranking/creative state should be promoted as final.

### Current live state

At report creation, the authoritative Product Ranking V3.6.2 run has:

- gateway preflight: **SUCCESS**
- live feed contract: **SUCCESS**
- direct Linkwise download: **SUCCESS**
- deterministic Phase A: **RUNNING**
- final ranking: pending Phase A/completeness gate

Current database remains fail-closed:

- `catalog.products`: **0**
- `catalog.product_offers`: **0**
- `intel.product_ranking_runs`: **0**
- `intel.product_rankings`: **0**

### Assessment

**AMBER.** The key code defects are fixed and direct feed transport is now production-proven. Full Product Intelligence is not declared GREEN until the authoritative run persists the required final ranking/creative/content contract.

---

## 7. SEO, Creative and Content

### Required final product payload

For a saved ranked product the system now supports/targets:

- canonical product facts and attributes;
- rank score/band;
- expected commission;
- merchant/demand/competition/whitespace/trust context;
- evidence and confidence context;
- AI promotion reasoning;
- SEO title;
- meta description;
- short and long description;
- keywords;
- search intent;
- slug;
- feature bullets;
- exact immutable tracking URL;
- real product image;
- Top-20 creative pack where applicable;
- independent creative audit;
- durable PNG asset URLs.

### Live content state

At report creation:

- `content.items`: **23 total existing items**
- product-related canonical content from the new ranking pipeline: **0**

This is expected while the authoritative final ranking remains incomplete.

### Publishing safety

The creative persistence path does **not invent publication schedules**. Final content can be approved/persisted without automatically entering `publish.outbox` unless an explicit schedule is supplied.

This preserves the invariant:

```text
intelligence/content approval != permission to invent a posting time
```

---

## 8. SocialScheduler / Buffer

### Live state

`publish.outbox` currently contains **68** records:

- scheduled: **3**
- cancelled: **65**

The 3 scheduled records have external post IDs and no recorded errors in the latest live check.

The latest checked `vmoulakakis/socialscheduler` scheduled workflow completed successfully.

### Boundary

```text
SocialMarket
  = product intelligence
  + ranking
  + canonical content
  + publish.outbox truth

SocialScheduler
  = execution-only worker

Buffer
  = final social publishing service
```

### Assessment

**GREEN.** Publishing execution is operational. New Product Intelligence content has not yet been handed off because final product ranking is still fail-closed, which is the correct safety behavior.

---

## 9. Frontend / deployment

GitHub CI builds the Next.js frontend successfully. The most recent external GitHub Vercel status observed before this report showed a Vercel **build-rate-limit** failure.

This is treated separately from the intelligence engine:

- application source build: **GREEN**
- intelligence/data pipeline: independent
- Vercel account/deployment quota: **AMBER external blocker**

No claim is made that the Vercel production deployment is repaired by the ranking/pain changes above.

---

## 10. Safety and governance controls preserved

The repairs deliberately preserve the following non-negotiable controls:

1. No LLM-generated commission values.
2. No LLM-generated product identity or merchant identity.
3. No missing competition → favorable competition assumption.
4. No synthetic demand volume.
5. No synthetic validated pain.
6. Product can rank without pain, but missing pain lowers evidence strength and cannot create a `VALIDATED` claim.
7. Skeptic/audit layers remain independent from generation/ranking.
8. Deep Demand forecasting remains withheld when temporal history is inadequate.
9. Raw multi-gigabyte Linkwise feed is streamed/staged ephemerally rather than wholesale imported into Supabase.
10. Tracking URLs remain immutable source facts.
11. Product content is not scheduled without an explicit publication schedule.
12. Partial failed ranking/creative runs do not become a production recommendation list.

---

## 11. Current blockers and residual risk

### P0 — authoritative Product V3.6.2 completion

Acceptance requires live proof of:

```text
>=100 persisted rankings
complete SEO contract
20/20 Creative Skeptic READY
60 durable PNG assets
approved canonical product content
```

Direct Linkwise transport is already proven fixed in the current run.

### P0 — Category Pain V4.7 production proof

Acceptance requires the current run to complete without the prior HTTP-500 audit-batch collapse. Validated cluster count may remain zero if source evidence is genuinely insufficient.

### P1 — demand history accumulation

Deep Demand cannot produce calibrated production forecasting until temporal gates are met. This must be solved by collecting real history, not by relaxing the model gate.

### P1 — frontend deployment quota

Vercel build-rate-limit remains an external deployment issue. GitHub source build itself is healthy.

---

## 12. Production acceptance dashboard

The system should be considered fully production-ready only when the following are simultaneously true:

| Check | Target |
|---|---:|
| Canonical merchants/programs | 309 healthy |
| Merchant Intelligence scheduled run | success |
| Category Pain workflow | clean completion |
| Product feed contract | success |
| Direct Linkwise transport | success |
| Product complete records scanned | >2,000,000 |
| Eligible canonical candidates | >10,000 |
| Minimum expected commission | EUR 10 |
| Persisted final rankings | >=100 |
| Saved rankings with SEO | 100% target set |
| Top creative products | 20 |
| Creative Skeptic READY | 20/20 |
| Durable assets | 60 |
| Canonical product content | approved/persisted |
| SocialScheduler health | success |
| Invented schedules | 0 |
| Invented evidence | 0 |

---

## 13. Final assessment

SocialMarket is no longer blocked by the original merchant-resolution/no-product architectural dead end. It has a real large commercial product universe and an adaptive ranking architecture capable of ranking candidates without requiring perfect pain evidence at the entrance.

The production posture at this report timestamp is:

```text
Merchant Intelligence       GREEN
Category Pain engine        AMBER (production verification running)
Validated pain data         RED (0 validated today)
Deep Demand engine          GREEN / forecasts correctly WITHHELD
Direct Linkwise transport   GREEN / production proven
Product Phase A             AMBER / running
Final Top-100 ranking       AMBER / verification pending
SEO                          AMBER / verification pending
Top-20 audited creatives    AMBER / verification pending
60 durable assets           AMBER / verification pending
SocialScheduler / Buffer    GREEN
Frontend source build       GREEN
Vercel deployment quota     AMBER external
```

The correct next milestone is not another architectural redesign. It is successful live completion of the two repaired production paths and verification of their persisted outputs. Until that proof exists, SocialMarket should remain fail-closed for new product promotion content.
