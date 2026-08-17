# SocialMarket AI — Autonomous SaaS Final Architecture Plan

**Status:** Proposed canonical TO-BE architecture baseline  
**Date:** 2026-08-17  
**Primary system:** SocialMarket AI  
**Execution system:** SocialScheduler  
**Goal:** Fully autonomous Greek affiliate-commerce intelligence, ranking, content and promotion decision system with minimal owner configuration, minimal paid infrastructure, minimal LLM token use, and evidence-backed weekly Top-100 change control.

---

## 1. Executive decision

SocialMarket AI is the **brain and system of intelligence**. SocialScheduler is the **execution engine**.

The owner sets only a small set of persistent **hard business constraints**. Everything else is decided by the SocialMarket AI Orchestrator from current evidence, historical state and measured performance.

The system must answer one operational question every week:

> Of all eligible Linkwise merchant/product offers available to the Greek market, which products have the strongest evidence-backed probability of profitable affiliate promotion now, and has the evidence changed enough to alter the current Top 100 or promotion outbox?

The system must not regenerate recommendations merely because a weekly cron ran. It must be **stateful**, compare incumbents against challengers, and make only justified changes.

---

## 2. Non-negotiable architecture principles

1. **Owner hard policy is constitutional.** AI may not override it.
2. **Filters before AI.** Deterministic code removes ineligible data before any model call.
3. **AI only where semantic reasoning adds value.** Arithmetic, IDs, joins, price, commission, dedupe, freshness, eligibility and state transitions remain deterministic.
4. **Demand before product.** The system discovers Greek demand, intent and pain first, then searches Linkwise for products that solve the identified problem.
5. **Evidence before conclusion.** Every semantic claim must resolve to evidence IDs and timestamps.
6. **Incremental weekly intelligence.** Recompute only changed/stale parts of the market state.
7. **Top 100 is persistent state, not a disposable report.** Every change has a reason and audit record.
8. **Zero-paid-model default.** Paid remote LLM APIs are not part of the normal production path.
9. **Fail closed.** If reasoning quality or evidence is insufficient, hold the previous trusted state; do not invent a result.
10. **SocialMarket ends at Approved Publishing Intent. SocialScheduler executes exactly that intent.**
11. **The system learns from outcomes.** Promotion and conversion performance must return to SocialMarket for calibration.
12. **No user-facing model tuning.** We do not expose internal score weights, prompt settings, RAG limits or AI thresholds as ordinary SaaS configuration.

---

## 3. Verified AS-IS facts that drive this redesign

The current repository already contains useful foundations and should be evolved rather than rewritten blindly.

### Keep / build on

- Dedicated `agents`, `workers`, `supabase`, app and workflow layers.
- Existing merchant, demand, category pain, semantic, product and ranking workers.
- Existing local-first runtime using Ollama and a small open-weight model.
- Existing pgvector / semantic evidence architecture.
- Existing Linkwise streaming and candidate-shortlisting direction.
- Existing ranking, creative, canonical content and outbox concepts.
- Existing shared Supabase source-of-truth rule.
- Existing accepted SocialMarket ↔ SocialScheduler ownership boundary.
- Existing OIDC-based GitHub worker access to Supabase.
- Existing run observability and audit concepts.

### Must change

1. `agents/ORCHESTRATOR.md` and product runtime logic still contain fixed opportunity weights. These become internal adaptive policy, not owner settings.
2. `ops.product_intelligence_config` currently exposes many internal AI/RAG/scoring parameters. Owner-facing configuration must be reduced drastically.
3. `product_ranking_v363_production.py` currently hard-requires DeepSeek for final ranking/creative stages. This conflicts with the zero-paid-API target.
4. `workers/agentic_intelligence/model_router.py` still targets GitHub Models. **GitHub Models was retired by GitHub on 2026-07-30**, so this route is dead and must be removed.
5. Many versioned pipelines/workflows coexist (`v3`, `v4`, `v43`, `v363`, multiple run_pipeline versions). These must be audited and consolidated after production-equivalence tests.
6. Weekly orchestration must become one explicit stateful intelligence chain instead of many partially overlapping workflows.

### Keep unchanged in principle

`docs/decisions/ADR-006-socialmarket-socialscheduler-boundary.md` is directionally correct and remains governing architecture:

- SocialMarket owns intelligence, strategy, content, creatives, approval, intended schedule and `publish.outbox`.
- SocialScheduler claims approved outbox jobs, performs technical publishing, retries/reconciliation and writes execution telemetry back.
- `Scheduler collects; SocialMarket interprets.`

---

## 4. Minimal owner configuration

The normal owner UI should expose only hard business policy.

Recommended baseline:

```text
market                       = GR
min_expected_commission_eur  = owner-defined
excluded_categories          = optional
excluded_merchants           = optional
max_active_promotions        = owner-defined/default
publishing_enabled           = true/false
```

Possible advanced hard controls, hidden under an Advanced section:

```text
allowed_categories
allowed_merchants
forbidden_keywords/compliance exclusions
max_weekly_new_promotions
maximum operational compute budget
```

### The owner must NOT routinely configure

- score weights
- pain thresholds
- demand thresholds
- competition weights
- RAG limits
- embedding thresholds
- LLM batch size
- model temperature
- AI thinking mode
- research depth
- source weighting
- freshness windows
- challenger margin
- confidence calibration

Those belong to **AI policy**, maintained automatically and versioned for audit.

---

## 5. Hard Policy vs AI Policy

### 5.1 Owner Hard Policy

Stored in a small immutable-per-run policy object, versioned and auditable.

Suggested canonical object:

```json
{
  "market": "GR",
  "min_expected_commission_eur": 10,
  "excluded_categories": [],
  "excluded_merchants": [],
  "max_active_promotions": 20,
  "publishing_enabled": true
}
```

A run records exactly which hard-policy version it used.

### 5.2 AI Policy State

AI policy is not directly edited by the owner. It contains dynamic operational decisions such as:

- source priorities by domain/category
- source freshness windows
- evidence sufficiency rules
- research depth
- semantic retrieval limits
- challenger sensitivity
- category-specific ranking emphasis
- whether a category requires deeper research
- whether the current Top 100 is stable enough to hold
- which model/task route is appropriate

AI policy is versioned. Every change requires a reason and may be rolled back.

---

## 6. Filters vs AI Brain — strict execution boundary

This is the central cost and reliability design.

| Stage | Deterministic / statistical plane | AI brain plane |
|---|---|---|
| Linkwise ingest | stream JSON/feed, parse, schema validation, hash, dedupe | none |
| Merchant resolution | exact IDs, domain mappings, deterministic aliases | ambiguous identity only |
| Commercial gate | price, currency, stock, commission €, tracking URL | none |
| Policy gate | owner exclusions/allowlists | none |
| Freshness | timestamps, content hashes, TTL | AI may choose TTL policy, not execute it |
| Demand metrics | counts, velocity, time decay, normalization, forecasts | interpret meaning/context |
| Evidence quality | source metadata, duplicates, recency, language, geo | semantic relevance / contradiction |
| Pain discovery | pre-filter text, embeddings, clustering | name/interpret validated pain cluster |
| Product matching | category/brand/spec filters, vector retrieval | semantic product↔pain solution fit |
| Ranking | hard gates, measured/statistical features | reasoned contextual adjustment and explanation |
| Top-100 change | deterministic diff and safety rules | KEEP/PROMOTE/REPLACE/PAUSE decision rationale |
| Creative | dimensions, URL/image validation | hooks/copy/positioning |
| Publishing | exact approved intent, idempotency | no AI in SocialScheduler execution |

### Rule

If deterministic/statistical logic can answer the question correctly, **do not invoke an LLM**.

---

## 7. Target end-to-end architecture

```text
OWNER HARD POLICY
      │
      ▼
SOCIALMARKET ORCHESTRATOR
      │
      ├─────────────── STATE / FRESHNESS PLANNER
      │                         │
      │                         ▼
      │                  What changed this week?
      │
      ▼
DETERMINISTIC DATA PLANE
      │
      ├─ Linkwise streaming ingest
      ├─ merchant resolution
      ├─ commercial eligibility
      ├─ dedupe/canonicalization
      ├─ evidence normalization
      ├─ time-series/statistical features
      └─ local embeddings / retrieval
      │
      ▼
SMALL CANDIDATE / EVIDENCE SETS
      │
      ▼
AI INTELLIGENCE PLANE
      │
      ├─ Greek Demand Analyst
      ├─ Social/Pain Analyst
      ├─ Affiliate Strategist
      ├─ Merchant Analyst
      ├─ Product-Solution Analyst
      ├─ Ranking Decision Scientist
      └─ Audit Council
      │
      ▼
PERSISTED MARKET STATE + EVIDENCE GRAPH
      │
      ▼
INCUMBENT TOP 100 vs CHALLENGERS
      │
      ▼
KEEP / PROMOTE / UPRANK / DOWNRANK / REPLACE / PAUSE / REMOVE
      │
      ▼
AUDITED TOP 100 vNEXT
      │
      ├─ no material promotion change → HOLD
      │
      └─ material change
              │
              ▼
       CREATIVE / CONTENT AGENTS
              │
              ▼
       APPROVED PUBLISHING INTENT
              │
              ▼
         publish.outbox
              │
              ▼
         SocialScheduler
              │
              ▼
        Buffer / networks
              │
              ▼
      performance telemetry
              │
              └──────────────► SocialMarket learning
```

---

## 8. Agent roles and contextual scope

Agents are **specialists**, not autonomous databases. They receive compact structured context and return strict schemas.

### 8.1 Chief AI Orchestrator

Owns:

- weekly plan
- task graph
- freshness decisions
- research budget
- state transitions
- agent routing
- final proposal for Top-100 changes

Does not:

- calculate commissions
- invent facts
- bypass hard policy
- publish directly

### 8.2 Greek Demand Intelligence Analyst

Goal: determine what Greek consumers are actively seeking, discussing, comparing or preparing to buy.

Inputs:

- normalized public market/search/social/content evidence
- trend features
- prior demand state

Outputs:

- demand entities
- purchase-intent signals
- velocity / acceleration interpretation
- seasonality context
- source/evidence IDs
- confidence

### 8.3 Social Listening & Pain-Gap Analyst

Goal: convert public consumer evidence into validated problems, frustrations, unmet needs, desired outcomes and workaround behavior.

Outputs are pain clusters, not product recommendations.

### 8.4 Affiliate Marketing Strategist

Goal: determine whether an observed opportunity is realistically promotable as an affiliate offer.

Considers:

- purchase intent
- funnel stage
- price friction
- trust requirement
- merchant attractiveness
- social promotability
- expected affiliate economics
- likely conversion barriers

### 8.5 Merchant Intelligence Analyst

Goal: evaluate merchant relevance, trust, category authority, price/offer quality and conversion context.

### 8.6 Product-Solution Analyst

Goal: answer one narrow question:

> Does this product actually solve this validated pain / demand requirement?

It receives only shortlisted eligible products plus compact evidence/RAG context.

### 8.7 Ranking Decision Scientist

Goal: combine measured features and audited semantic judgments into an explainable Top-100 decision.

It does not receive millions of products. It receives a deterministic shortlist plus incumbent state.

### 8.8 Creative Strategist

Runs only for products that genuinely require new/updated campaign content.

### 8.9 Audit Council

Independent roles:

- Evidence Skeptic
- Product-Fit Skeptic
- Affiliate Economics Skeptic
- Ranking Auditor
- Data Quality Auditor
- Architecture/Cost Auditor

The audit layer attempts to disprove important decisions. It does not merely rephrase the primary agent output.

---

## 9. Greek demand source architecture

Do not hardcode a permanent list of “top sites.” Maintain a **source registry** that is periodically re-evaluated.

Each source gets metadata:

```text
source_id
source_type
market=GR
audience/reach proxy
commercial intent class
freshness
collection method
public-access status
terms/compliance status
noise score
historical reliability
category coverage
last successful collection
```

Signal classes:

- Search intent
- Social/public discussion
- Reviews/comments
- Commercial/e-commerce intent
- Price/offer intent
- News/cultural momentum
- Forums/community pain
- Competition/saturation
- Seasonality

The orchestrator may change source emphasis by category and week, but source provenance is always preserved.

---

## 10. Linkwise 3–4 GB product universe strategy

Never send the feed to AI.

### Phase A — deterministic streaming

```text
feed
 → stream parse
 → schema validate
 → resolve merchant/program
 → compute price/currency/commission
 → apply owner hard policy
 → validate tracking/availability
 → canonicalize identity
 → dedupe offers
 → hash product state
 → compare with previous feed snapshot
```

Persist only necessary canonical state and change fingerprints. Do not persist a useless duplicate of every raw byte when the feed can be re-fetched.

### Phase B — cheap candidate generation

Use:

- category mappings
- product title/spec lexical matching
- merchant context
- local embeddings
- pgvector
- BM25/keyword retrieval where useful
- current demand/pain entities

This reduces millions of offers to a manageable candidate universe.

### Phase C — AI only on shortlist

AI evaluates only products with a plausible validated reason to compete for ranking.

---

## 11. Zero-paid-API model strategy

### 11.1 GitHub Models

Do **not** build on GitHub Models. GitHub retired GitHub Models on **2026-07-30**.

Official reference: `https://docs.github.com/en/github-models`

### 11.2 GitHub Actions compute

The Socialmarket repository is currently public. Standard GitHub-hosted runners for public repositories are currently free. `ubuntu-latest` public runners currently provide **4 CPU, 16 GB RAM and 14 GB SSD**.

Official references:

- `https://docs.github.com/en/actions/reference/runners/github-hosted-runners`
- `https://docs.github.com/en/billing/concepts/product-billing/github-actions`

This makes small quantized local models practical for bounded weekly semantic tasks, subject to benchmark validation.

### 11.3 Runtime

Preferred production hierarchy:

```text
0. deterministic/statistical result
1. local embeddings
2. local small open-weight LLM
3. stronger local open-weight LLM only for ambiguous/high-value cases if runner capacity permits
4. fail closed / defer — not paid remote API
```

### 11.4 Inference engines

Primary options:

- `llama.cpp` for lean CPU GGUF inference in GitHub Actions
- Ollama for development/self-hosted runtime and compatibility with existing code

`llama.cpp` supports quantized local inference and an OpenAI-compatible server.

Reference: `https://github.com/ggml-org/llama.cpp`

### 11.5 Embeddings

Keep embeddings local and cheap. Existing `gte-small`/pgvector direction is valid. Benchmark against current small multilingual sentence-transformer alternatives only if quality improves Greek semantic retrieval materially.

### 11.6 Model selection policy

Do not permanently hardcode a model name as “the brain.” Add a benchmark harness that evaluates candidate small open-weight models against a SocialMarket Greek evaluation set.

Score each candidate on:

- Greek understanding
- structured JSON compliance
- pain extraction precision/recall
- product↔pain fit
- contradiction detection
- ranking consistency
- hallucination rate
- CPU latency
- memory
- tokens generated

The current local `qwen3.5:0.8b` route becomes one benchmark candidate, not an architectural dependency.

---

## 12. Token / context minimization protocol

The objective is not simply “use a cheaper model.” The objective is to **avoid asking a model unnecessary questions**.

### Level 0 — no AI

Applied to every Linkwise record and every evidence item where possible.

- parsing
- hashing
- dedupe
- arithmetic
- eligibility
- statistics
- freshness
- lexical matching

### Level 1 — embeddings only

Used for semantic candidate retrieval and clustering.

No generative tokens.

### Level 2 — micro reasoning

Small local model receives compact structured objects, not raw pages.

Typical payload:

```json
{
  "pain": {"id":"...","summary":"...","signals":[...]},
  "product": {"id":"...","title":"...","features":[...]},
  "merchant": {"id":"...","trust":72},
  "measured": {"demand":81,"commission_eur":14.2}
}
```

### Level 3 — high-value reasoning

Only for:

- potential Top-100 entrants
- material rank changes
- disputed/high-value products
- final promotion decisions
- skeptic audit

### Required optimizations

1. Content hash cache: same evidence + same prompt version + same model = reuse result.
2. Evidence dedupe before embedding or LLM use.
3. Incremental collection based on freshness/change state.
4. Compact normalized evidence fields; no full HTML in prompts.
5. Retrieval top-k bounded by task.
6. Strict JSON outputs only.
7. Single-turn specialist agents; no open-ended agent conversations.
8. No chain-of-thought persistence.
9. Maximum input/output token budget per task type.
10. Batch only semantically compatible items.
11. Reuse prior weekly validated state unless invalidated.
12. Audit deltas, not the entire unchanged universe.
13. Generate creatives only when a promotion decision changes or current creative expires/fails.

---

## 13. Evidence graph

The canonical intelligence layer should model relationships explicitly:

```text
SOURCE
  ↓
SIGNAL
  ↓
DEMAND ENTITY
  ↓
PAIN / DESIRED OUTCOME
  ↓
SOLUTION REQUIREMENT
  ↓
PRODUCT
  ↓
OFFER / MERCHANT
  ↓
PROMOTION DECISION
  ↓
CONTENT / CAMPAIGN
  ↓
PERFORMANCE
```

Every semantic edge carries:

```text
evidence_ids
source_ids
observed_at
fresh_until
confidence
agent_version
model_version
prompt_version
audit_status
```

This enables explainability and selective recomputation.

---

## 14. Stateful Top-100 design

Top 100 is a versioned portfolio.

Each weekly run compares:

```text
incumbent Top 100
vs
eligible changed products
vs
new challengers
```

Possible decisions:

```text
KEEP
PROMOTE
UPRANK
DOWNRANK
REPLACE
PAUSE
REMOVE
HOLD
```

A rank score alone must not create churn.

Each change stores:

```text
previous_rank
current_rank
decision
decision_reason
demand_delta
pain_delta
merchant_delta
economics_delta
competition_delta
confidence_delta
evidence_changed
audit_verdict
```

### Weekly portfolio rule

If evidence changes are immaterial, keep the existing trusted ranking and generate **no unnecessary outbox work**.

---

## 15. Ranking architecture

### Hard gates first

Examples:

- owner minimum commission
- resolved merchant
- valid affiliate/tracking URL
- valid price/currency
- available product/offer when availability is known
- not excluded by policy
- canonical product identity
- feed freshness
- merchant not blocked

### Measured/statistical feature layer

Examples:

- demand level
- demand velocity
- trend acceleration
- seasonality
- competition density
- merchant historical performance
- offer price competitiveness
- expected commission €
- promotion historical CTR/EPC/conversion where available
- evidence freshness/diversity

### AI semantic feature layer

Examples:

- pain severity interpretation
- purchase-intent interpretation
- solution requirement extraction
- product↔pain fit
- social promotability
- differentiation
- contradiction/risk

### Final decision

Use deterministic features + calibrated AI semantic judgments + incumbent/challenger context.

Do not expose a permanent set of user-editable weights. Any internal weighting/calibration is versioned AI policy and must be evaluated against historical outcomes.

---

## 16. SocialMarket ↔ SocialScheduler production contract

The existing ADR remains the basis.

```text
SocialMarket
  WHAT / WHY / WHO / MESSAGE / INTENDED TIME
      ↓
Approved Publishing Intent
      ↓
publish.outbox
      ↓
SocialScheduler
  WHEN-EXACTLY / PROVIDER EXECUTION / RETRY / RECONCILIATION
      ↓
Buffer / network
```

SocialScheduler may not invent:

- product
- merchant
- affiliate URL
- caption
- creative
- schedule
- campaign strategy

Business-level changes return to SocialMarket.

---

## 17. Feedback / learning loop

```text
predicted opportunity
      ↓
Top 100
      ↓
promotion decision
      ↓
content
      ↓
SocialScheduler
      ↓
social network
      ↓
engagement/clicks
      ↓
affiliate click/conversion/revenue
      ↓
SocialMarket performance store
      ↓
calibration / policy learning
```

The ranking system should eventually optimize real outcomes, not only proxy scores.

Important learned relationships may be category-specific. Example: social velocity may be highly predictive for beauty but weak for a high-friction appliance category. The model should learn that from observed results instead of exposing a manual slider.

---

## 18. Supabase target responsibilities

Supabase remains canonical persistent state.

Logical responsibility groups:

### Control

- owner hard policy
- AI policy versions
- run state
- kill switches

### Catalog

- merchants
- programs
- canonical products
- offers
- feed change hashes

### Intelligence

- sources
- evidence
- signals
- demand entities
- pain clusters
- semantic objects/embeddings
- product-solution links

### Ranking

- ranking runs
- ranked products
- incumbent/challenger deltas
- decision reasons

### Audit

- agent outputs
- skeptic verdicts
- model/prompt versions
- evidence references

### Content / publishing

- canonical content items
- creatives/assets
- `publish.outbox`

### Performance

- scheduler execution telemetry
- social metrics
- affiliate performance
- calibration snapshots

Existing tables should be reused where they already satisfy these responsibilities. Do not create duplicate parallel schemas merely to match this document.

---

## 19. Vercel / SaaS UI target

Vercel serves the control/inspection experience, not the intelligence compute engine.

The primary UI becomes intentionally simple:

### Control Tower

- system health
- current weekly run stage
- last successful intelligence refresh
- Top-100 changes
- promotion changes
- critical audit warnings

### Top 100

- rank
- product/merchant
- expected commission
- evidence-backed reason
- current decision
- previous rank/delta
- confidence

### Why this product?

One drill-down page:

- demand
- pain
- solution fit
- merchant/offer
- economics
- evidence
- audit verdict
- promotion history/performance

### Settings

Only hard owner constraints.

### Emergency control

- publishing kill switch
- optionally pause autonomous intelligence runs

No routine AI engineering controls are shown to the SaaS owner.

---

## 20. Workflow consolidation target

Current versioned GitHub Actions must be inventoried and classified:

```text
KEEP
MERGE
REPLACE
RETIRE
```

Target production chain:

```text
weekly-socialmarket-orchestrator
    1. policy snapshot
    2. source/feed freshness plan
    3. merchant delta refresh
    4. Greek demand delta refresh
    5. pain/evidence delta refresh
    6. Linkwise product delta/eligibility
    7. candidate generation
    8. AI semantic analysis
    9. incumbent/challenger ranking
   10. independent audit
   11. Top-100 commit
   12. changed-promotion content/creative work
   13. outbox commit
   14. observability/final report
```

CI/test workflows remain separate. Heavy production intelligence should not cascade from ordinary code pushes.

---

## 21. Independent developer / architecture audit

Every major implementation PR is scored against:

- correctness
- data integrity
- deterministic-vs-AI separation
- evidence grounding
- token/context efficiency
- compute efficiency
- security
- observability
- idempotency
- failure behavior
- maintainability
- commercial relevance

Review outcome:

```text
KEEP
IMPROVE
REPLACE
DELETE
```

No component survives only because it already exists.

---

## 22. Implementation phases

### P0 — Architecture freeze and forensic baseline

- preserve current production state
- inventory every workflow/model call/table/gateway
- benchmark current product ranking path
- document failures and duplicated versioned paths
- verify SocialScheduler outbox contract end to end

### P1 — Remove invalid/paid inference dependencies

- remove GitHub Models inference route
- disable paid DeepSeek/OpenAI as production dependencies
- replace ranking/creative health checks that require DeepSeek
- introduce one canonical local-model provider interface
- benchmark small open-weight models on GitHub runner hardware
- preserve fail-closed behavior

### P2 — Simplify policy model

- create/minimize owner hard-policy surface
- move internal thresholds/weights to AI policy state
- keep configuration versioning/audit
- simplify Vercel Settings UI

### P3 — Canonical incremental data plane

- Linkwise feed hashing/delta handling
- merchant/product/offer canonicalization
- evidence dedupe/freshness
- zero-LLM feature computation
- source registry

### P4 — Demand and pain intelligence vNext

- dynamic Greek source selection
- incremental evidence collection
- local embedding / clustering
- compact AI interpretation
- evidence skeptic

### P5 — Product candidate and ranking vNext

- deterministic eligible universe
- demand/pain driven candidate retrieval
- product-solution AI only on shortlist
- stateful incumbent/challenger ranking
- ranking audit

### P6 — Promotion delta engine

- distinguish rank change from promotion change
- generate content only when required
- reuse valid creatives where possible
- canonical outbox handoff

### P7 — Closed-loop performance learning

- ingest scheduler/social/affiliate outcomes
- build calibration datasets
- category-specific outcome analysis
- adapt AI policy without altering owner hard policy

### P8 — Production convergence

One authoritative green chain must prove:

```text
policy
→ demand
→ pain
→ Linkwise eligibility
→ candidate shortlist
→ local AI analysis
→ audited Top 100
→ promotion delta
→ content/creative
→ outbox
→ SocialScheduler execution contract
→ telemetry return
```

---

## 23. Acceptance criteria

The TO-BE system is production-ready only when all are true:

1. Normal weekly path makes **zero paid LLM API calls**.
2. No code path depends on retired GitHub Models.
3. Owner can operate the system with a small hard-policy configuration only.
4. Linkwise full feed is processed without sending raw universe data to an LLM.
5. At least 95% of unchanged weekly state avoids repeat generative reasoning where hashes/evidence remain valid; exact target will be benchmarked.
6. Every Top-100 change has persisted evidence and decision reason.
7. Every promotion outbox entry maps to an audited promotion decision.
8. No weak/failed AI response silently becomes a promotion.
9. SocialScheduler cannot alter business intent.
10. Re-running the same weekly state is idempotent.
11. Model/prompt/policy versions are recorded.
12. AI and data-quality audits can block a change.
13. Performance telemetry returns to SocialMarket.
14. One complete E2E production run is green and reproducible.

---

## 24. First implementation backlog

Execute in this order:

1. **Forensic model-call map:** locate every OpenAI/DeepSeek/GitHub Models/Ollama call.
2. **Workflow graph:** map every production workflow, trigger and dependency; identify duplicates.
3. **Supabase contract audit:** map owner config, AI policy, evidence, ranking, content, outbox and performance tables/RPCs.
4. **Local inference benchmark harness:** test candidate open-weight models using Greek SocialMarket evaluation fixtures on `ubuntu-latest`.
5. **Remove GitHub Models route:** it is retired and must not remain a production fallback.
6. **Remove mandatory DeepSeek ranking dependency:** local/fail-closed path must own production.
7. **Owner policy migration:** reduce user-facing configuration to hard constraints.
8. **Incremental intelligence planner:** add state/freshness/delta planning before heavy research.
9. **Top-100 portfolio delta model:** persist incumbents/challengers and decisions.
10. **Promotion delta engine:** only changed promotion decisions generate new content/outbox work.
11. **Audit council implementation:** independent evidence/product/ranking checks.
12. **E2E proof run:** no paid inference, complete Top 100, audited outbox handoff.

---

## 25. Governing product definition

**SocialMarket AI is an autonomous Greek affiliate market decision engine.**

The owner defines the non-negotiable commercial rules. The system continuously determines:

- what demand exists
- what changed
- what problem people are trying to solve
- what Linkwise product best solves it
- which merchant/offer is commercially viable
- how strong the evidence is
- whether an incumbent Top-100 product should keep its position
- whether a challenger deserves promotion
- whether new content is required
- whether the decision survives independent audit

SocialScheduler then executes the approved publishing intent exactly as supplied.

That separation is the canonical architecture for the next implementation phase.
