# SocialMarket AI — Phase 1 Forensic AS-IS Audit

**Status:** Verified investigation baseline  
**Audit date:** 2026-08-17  
**Main commit audited:** `8be3f05a32ff7b42689ff030d5292b39cf1c8375`  
**Target architecture:** `docs/SOCIALMARKET_AUTONOMOUS_SAAS_FINAL_PLAN.md`  
**Scope:** SocialMarket AI first; SocialScheduler only at the execution boundary  
**Production mutations in this phase:** none

---

## 1. Executive verdict

SocialMarket AI has a strong deterministic ingestion/commercial foundation and a coherent intended SocialMarket → SocialScheduler boundary, but the authoritative autonomous intelligence chain is **not production-complete**.

The dominant failure pattern is not the 5M+ product feed. The front half successfully streams and commercially filters the Linkwise universe. The production break is concentrated in the semantic/AI decision layer and the final publishing handoff.

Current live truth:

- merchant system of record exists and is populated;
- Linkwise production scanning is capable of processing >5M records;
- commercial filtering produces tens of thousands of unique eligible products;
- validated semantic pain state is currently empty;
- the latest Category Pain production run fails at the AI audit gateway;
- there is no persisted production Top-100 product portfolio;
- recent ranking runs fail at AI ranking completeness;
- local open-weight inference code exists but production policy has it disabled;
- direct DeepSeek dependencies remain in Category Pain, ranking and creative gateways;
- old heavy workflows remain active beside the newer weekly chain;
- SocialScheduler is configured to use the canonical SocialMarket outbox, but the current approved outbox has not been claimed and recent outbox calls show transient 503s.

**Architecture conclusion:** preserve the deterministic/data architecture; replace and simplify the AI execution/control plane; consolidate workflow orchestration; prove the outbox cutover end to end.

---

## 2. Canonical intended chain AS-IS

The newer intended chain is:

```text
Merchant Intelligence V4.3
        ↓ successful workflow_run
Semantic Category Pain Intelligence
        ↓ successful workflow_run
Deep Demand Intelligence V3.1
        ↓ successful workflow_run
Product Intelligence + Promotion Ranking
        ↓
Top 100 + Top 20 creative packs
        ↓
content.items
        ↓
publish.outbox
        ↓
SocialScheduler
        ↓
Buffer
```

This direction is correct. The problem is that it is not yet the only production path and several downstream gates are failing.

---

## 3. Verified workflow audit

### 3.1 KEEP — canonical weekly chain concepts

#### Merchant Intelligence V4.3

File: `.github/workflows/merchant-intelligence-v43.yml`

Current intended behavior:

- weekly schedule;
- manual execution supported;
- no normal push-triggered heavy research;
- canonical upstream intelligence refresh.

**Verdict:** KEEP and make this the only heavy merchant production workflow after equivalence validation.

#### Semantic Category Pain Intelligence

File: `.github/workflows/generic-evidence-intelligence.yml`

Current intended behavior:

- runs after successful Merchant V4.3 or manually;
- bounded target set;
- collection and deterministic filtering precede audit;
- persists audited evidence/semantic state.

**Verdict:** KEEP the pipeline concept and collectors, REPLACE the brittle remote AI audit route.

#### Deep Demand Intelligence V3.1

File: `.github/workflows/deep-demand-intelligence-v31.yml`

**Verdict:** KEEP the statistical/model-lab/withhold architecture. Do not force a forecast when history is insufficient.

#### Product Intelligence + Promotion Ranking

File: `.github/workflows/product-intelligence-v1.yml`

Current strengths:

- live Linkwise source is primary;
- deterministic Phase A precedes AI;
- source-universe completeness gates fail closed;
- final contract requires a durable ranked portfolio and complete creative handoff.

**Verdict:** KEEP ingestion, commercial scan, source completeness, shortlist and persistence contracts. REPLACE mandatory DeepSeek ranking/creative execution and redesign final ranking as a persistent incumbent-vs-challenger portfolio.

### 3.2 RETIRE / MERGE — duplicate heavy workflows

An older Merchant Intelligence workflow remains active with daily/push execution even though V4.3 is now the intended weekly source.

This creates:

- duplicate heavy research;
- unnecessary compute/token usage;
- multiple possible upstream states;
- harder incident diagnosis;
- higher risk that downstream intelligence starts from a noncanonical refresh.

**Required action after parity test:** disable/retire the legacy production trigger and retain only historical code or explicit diagnostics where useful.

The repository also contains multiple generations of `run_pipeline_v*`, merchant versions, category-pain versions, product-ranking versions and patch/diagnostic workflows.

**Policy:** no new V10/V11 parallel architecture. Every legacy path must receive one classification: `KEEP_CANONICAL`, `MERGE`, `DIAGNOSTIC_ONLY`, or `RETIRE`.

---

## 4. Linkwise / commercial data plane — strongest part of the system

The authoritative failed ranking run completed its commercial front half successfully.

Latest inspected Phase A profile:

```text
records_seen                         5,452,909
resolved_records                     ~4.33M
commission_eligible_records          721,252
commission_eligible_offers           243,756
unique_commission_eligible_products   43,709
```

The pipeline also records deterministic exclusions such as:

- commission below floor;
- merchant unresolved;
- merchant trust below gate;
- blocked/demand-beacon merchant policy;
- out of stock;
- missing image;
- price-integrity quarantine.

### Conclusion

**Do not rewrite feed ingestion.**

The correct TO-BE shape is:

```text
Linkwise multi-GB feed
   ↓ stream
schema / record validation
   ↓
merchant resolution
   ↓
price + stock + tracking validation
   ↓
absolute owner commission floor
   ↓
canonicalization / dedupe
   ↓
cheap statistical scoring
   ↓
local embeddings / semantic retrieval
   ↓
small diverse candidate set
   ↓
AI reasoning
```

This is already directionally present and should be hardened, not replaced.

---

## 5. Commercial concentration risk

The Phase A profile shows a major candidate concentration:

- Yoox represents roughly 85% of the commission-eligible candidate offers in the inspected profile.

The current code treats feed concentration as a diversity signal rather than claiming it is Greek market share. That distinction is correct.

**TO-BE rule:** feed share must never masquerade as market demand. Diversity constraints should prevent one large catalog from monopolizing the AI shortlist, while actual demand/competition evidence determines opportunity.

A second item requires audit: hundreds of thousands of records are excluded under `dominant_or_blocked_merchant`. This exclusion must be explainable from explicit merchant policy/validated market evidence, not merely feed size.

---

## 6. Semantic pain layer — P0 blocker

Live database audit currently shows:

```text
validated evidence.semantic_clusters = 0
```

The latest Product Phase A profile therefore reports:

```text
validated_pain_clusters_available_for_phase_b = 0
```

The latest inspected Semantic Category Pain production run processed its target set but failed all targeted audit operations with `audit_batch` HTTP 500 errors.

Supabase edge-function telemetry independently shows repeated `evidence-gateway` HTTP 500 responses in the same production period.

### Root architectural issue

`supabase/functions/evidence-gateway/index.ts` directly owns DeepSeek inference.

That means a remote model/provider/gateway failure can prevent validated semantic pain materialization entirely.

### TO-BE

Preserve:

- collectors;
- normalized evidence;
- deterministic source/relevance gates;
- embedding and clustering;
- skeptic semantics;
- evidence IDs and provenance.

Replace:

- direct paid-provider coupling inside the evidence gateway.

New interface:

```text
evidence package
   ↓
AI Task Router
   ├─ deterministic answer possible → no LLM
   ├─ small local model sufficient → local bounded JSON
   ├─ stronger local model needed → local reasoning tier
   └─ no model meets quality gate → SAFE_HOLD / NEEDS_EVIDENCE
```

No paid provider is required for normal operation.

---

## 7. Deep Demand / forecasting

The live `demand_model_lab_runs` population currently contains hundreds of runs and the audited status is `withheld` rather than fabricated success.

This is a positive safety property: the model lab is refusing to claim forecast quality before enough history exists.

### Verdict

**KEEP** the withhold behavior.

TO-BE ranking should use:

- observed current demand evidence;
- measured trend velocity;
- social/public-market signals;
- seasonality;
- statistical confidence;
- model forecast only where forecast validation is sufficient.

A missing trustworthy forecast must not imply zero demand and must not be replaced by LLM guesswork.

---

## 8. Product ranking — P0 blocker

Live Supabase currently shows:

```text
intel.product_ranking_runs = 3
intel.product_rankings     = 0
```

Inspected run outcomes:

- latest run: failed at `ai_ranking`; required at least 100 fully ranked products, got 0;
- previous run: same 0/100 completeness failure;
- earlier run: reached later stage but final contract had only 64 ranked products and failed.

The failed current run proves the deterministic front half was healthy:

- checkout: success;
- ranking/creative gateway preflight: success;
- feed contract: success;
- live feed download: success;
- Phase A commercial universe scan: success;
- source-universe completeness: success;
- final AI ranking step: failure.

### Code-path finding

`workers/product_intelligence/product_ranking_v363_production.py` requires the ranking and creative gateways to report DeepSeek configured.

`workers/product_intelligence/product_ranking_v32.py` then sends shortlist batches through remote rank + audit calls and recursively splits failed batches down to individual items.

The durable run metadata preserves the final 0/100 completeness error but does not currently provide a sufficiently useful durable per-provider/per-item failure reason for forensic diagnosis.

### Verdict

**KEEP:**

- full-universe deterministic competition;
- high-recall shortlist;
- merchant/category diversity controls;
- source-record hashes;
- RAG context;
- strict minimum final portfolio contract;
- fail-closed persistence.

**REPLACE:**

- mandatory DeepSeek gateway;
- full fresh AI rerank assumption;
- provider-specific logic embedded in decision gateways.

**ADD:**

- model-agnostic AI Task Router;
- local benchmarked model pool;
- content/evidence hash cache;
- incumbent/challenger state;
- ranking-delta decisions;
- durable per-call telemetry: route/model/prompt-hash/input-hash/latency/status/schema failure/retry/final decision;
- SAFE_HOLD if quality threshold is not reached.

---

## 9. Current model-routing truth

The repository contains useful local-first code:

- Ollama runtime;
- small Qwen default;
- bounded JSON mode;
- reasoning disabled for cheap classification tasks;
- deterministic/vector-first intent.

However, the live `ops.ai_model_policy` does **not** currently use that architecture in production:

```text
local_open_weight_enabled = false   for all inspected task types
github_models_enabled     = true    for all inspected task types
deepseek_enabled          = true    for merchant/product research and product audit
```

### Verdict

The local runtime is a **KEEP/BUILD-ON code asset**, not yet a production capability.

TO-BE model routing must be task-based:

```text
Tier 0  SQL / rules / statistics / embeddings
Tier 1  very small local classifier/extractor
Tier 2  stronger local semantic/reasoning model
Tier 3  local skeptic / second-model audit
FAIL    SAFE_HOLD
```

The orchestrator chooses the tier and model. The owner never chooses a model.

---

## 10. Owner control plane

The current `ops.product_intelligence_config` contains many low-level settings such as thresholds, RAG limits, AI batch sizes, thinking mode and score weights.

That is incompatible with the final SaaS product philosophy.

### TO-BE public Autopilot controls

```text
AUTOPILOT            START | PAUSE | STOP
MIN_COMMISSION_EUR   absolute owner value
EMERGENCY_STOP       ON | OFF
```

Optional strategic directives:

```text
AUTO
PRIORITIZE
DEPRIORITIZE
EXCLUDE
```

Applied to orchestrator-proposed niches/categories/themes.

### Internal only

All model, threshold, weighting, RAG, freshness, batch, research-depth, challenger and source-weight decisions move to versioned AI policy and are not ordinary owner configuration.

---

## 11. Top-100 target state

The system currently has no persisted production Top-100 portfolio.

TO-BE introduces persistent portfolio state:

```text
product
previous_rank
current_rank
portfolio_state
promotion_state
evidence_snapshot_hash
commercial_snapshot_hash
last_material_change_at
last_researched_at
last_audited_at
decision_reason
audit_verdict
```

Canonical weekly decisions:

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

### Change rule

A weekly cron is permission to reassess, not a reason to change the portfolio.

Only material evidence/commercial/performance change should cause promotion churn.

---

## 12. SocialScheduler handoff audit

The ownership boundary is correct and should remain:

```text
SocialMarket
  decides WHAT / WHY / WHO / MESSAGE / exact approved intent
        ↓
publish.outbox
        ↓
SocialScheduler
  executes WHEN/WHERE exactly as approved
        ↓
Buffer
```

The SocialScheduler production workflow defaults to `socialmarket_outbox` and uses GitHub OIDC to call the shared Supabase publishing endpoint.

`src/socialmarket_outbox.py` correctly includes:

- OIDC token acquisition;
- transient retry for 502/503/504;
- claim/lease semantics;
- ACK back to SocialMarket;
- metrics batch return path.

### Current live problem

Live outbox snapshot:

```text
approved rows = 14
cancelled rows = 65
approved rows ever claimed = 0
approved rows with external post id = 0
```

The approved rows are currently Facebook-only, and the earliest approved schedule in the inspected set is already in the past.

Recent Supabase edge logs also show repeated `publishing-outbox` 503 responses, although some calls succeed.

### Verdict

**KEEP** the contract/client architecture.

**P0/P1 cutover work:**

- identify the exact 503 action/failure condition;
- prove claim succeeds against a controlled approved test job;
- prove Buffer schedule creation;
- prove ACK updates outbox state;
- prove idempotent retry;
- prove late-job behavior;
- prove Instagram/TikTok media preflight;
- prove performance telemetry returns to SocialMarket.

No SocialScheduler marketing intelligence should be added.

---

## 13. KEEP / MERGE / REPLACE / RETIRE matrix

| Component | Verdict | Reason |
|---|---|---|
| Shared Supabase canonical data model | KEEP | Correct system-of-record boundary |
| ADR-006 SocialMarket/SocialScheduler ownership | KEEP | Correct separation of decision vs execution |
| Merchant Intelligence V4.3 | KEEP | Canonical weekly merchant foundation |
| Legacy heavy merchant workflow triggers | RETIRE | Duplicate research and conflicting orchestration |
| Linkwise live-feed streaming | KEEP | Successfully handles multi-million-record universe |
| Deterministic commercial gates | KEEP | Cheap, explainable, scalable |
| Merchant resolution | KEEP + IMPROVE | Strong exact-domain resolution; unresolved volume still material |
| Price-integrity quarantine | KEEP | Prevents bad commission arithmetic |
| pgvector / embeddings | KEEP | Correct semantic retrieval plane |
| Evidence collectors | KEEP | Valuable public-evidence acquisition layer |
| Evidence Gateway direct DeepSeek audit | REPLACE | Current production bottleneck / paid-provider coupling |
| Demand model with withholding | KEEP | Correct uncertainty behavior |
| Fixed user-visible ranking weights | REPLACE | Orchestrator should own adaptive internal policy |
| Product shortlist / diversity | KEEP + IMPROVE | Essential token-control layer |
| Mandatory DeepSeek rank/audit/SEO | REPLACE | Zero-paid target + current 0/100 failure |
| Mandatory DeepSeek creative generation/audit | REPLACE | Same coupling; generate only on promotion delta |
| Local Ollama runtime code | KEEP + ENABLE | Useful zero-paid foundation but disabled in live policy |
| Current model policy | REPLACE | Production policy does not match target architecture |
| Multiple versioned production pipelines | MERGE / RETIRE | Excess execution paths and maintenance cost |
| Top-100 one-shot report semantics | REPLACE | Must become persistent portfolio |
| Canonical `content.items` / `publish.outbox` | KEEP | Correct handoff state model |
| SocialScheduler outbox client | KEEP + HARDEN | Correct contract; cutover not yet proven |
| Buffer execution in SocialScheduler | KEEP | Correct execution boundary |
| Main branch without protection | HARDEN | Governance risk after runtime convergence |

---

## 14. P0 blockers before Autopilot can be called production-ready

### P0-1 — Semantic pain production

Acceptance:

- Category Pain production run completes without remote paid dependency;
- validated pain clusters > 0 with evidence provenance;
- source diversity and skeptic audit are durable;
- repeated unchanged evidence does not consume new generative inference.

### P0-2 — Zero-paid ranking route

Acceptance:

- at least 100 final eligible products ranked using local/open-weight routing;
- deterministic gates preserved;
- local model output schema validity measured;
- skeptic audit independent from primary ranker where practical;
- no paid API required;
- failure produces SAFE_HOLD, not an invented ranking.

### P0-3 — Persistent Top 100

Acceptance:

- Top 100 persisted as authoritative portfolio state;
- next run compares incumbents vs challengers;
- unchanged products reuse prior trusted reasoning where evidence hashes are unchanged;
- every change has reason + evidence + audit.

### P0-4 — Canonical orchestration

Acceptance:

- one production Autopilot chain;
- legacy heavy workflows disabled/diagnostic-only;
- START/PAUSE/STOP controls the chain;
- emergency stop prevents new promotion intent;
- failed upstream intelligence blocks downstream mutation.

### P0-5 — Publishing cutover proof

Acceptance:

- approved test intent claimed by SocialScheduler;
- scheduled once in Buffer;
- ACK persisted;
- duplicate execution prevented;
- late/invalid/media failures behave safely.

---

## 15. P1 intelligence upgrades after P0 stability

1. Current Greek source-priority registry with empirical source-quality scoring.
2. Incremental social/public-signal collection driven by change detection.
3. Niche proposal engine with owner semantic directives.
4. Product-pain solution requirement graph rather than raw similarity alone.
5. Merchant/offer conversion priors from real affiliate performance.
6. Category-specific calibration of demand/pain/social/economics interactions.
7. Promotion-delta creative generation only for new/materially changed winners.
8. Closed-loop learning from impressions → clicks → EPC → conversions → revenue.
9. Portfolio diversity constraints learned from realized performance rather than arbitrary static caps.
10. Automated model benchmark suite and router policy promotion/rollback.

---

## 16. Token / compute minimization contract

The future orchestrator must enforce:

```text
1. hash source/evidence/product state
2. compare with last trusted state
3. skip unchanged work
4. run deterministic filters
5. run statistics
6. run embeddings/retrieval
7. create compact evidence packets
8. call smallest validated local model
9. escalate locally only if task complexity requires it
10. audit only decisions capable of changing portfolio/publishing state
11. cache model result by task + model + input hash + policy version
```

No LLM should see the 3–5 GB feed directly.

---

## 17. Phase 2 engineering order

Do not begin by rewriting everything.

```text
A. freeze canonical workflow inventory
B. build model-call registry + telemetry contract
C. benchmark local open-weight models by task
D. introduce provider-neutral AI Task Router
E. route Category Pain through local model tiers
F. restore validated semantic pain production
G. route Product Ranking/Audit through local tiers
H. persist first authoritative Top 100
I. add incumbent/challenger delta engine
J. simplify owner UI to Autopilot controls
K. consolidate/retire legacy workflows
L. prove SocialScheduler outbox cutover
M. close performance feedback loop
N. protect main + required checks
```

Each step requires a production-equivalence or acceptance test before deleting the previous path.

---

## 18. Final Phase 1 decision

The system should **not be rebuilt from scratch**.

The correct transformation is:

```text
CURRENT
strong data plane
+ fragmented workflows
+ direct provider-coupled AI
+ no durable Top100
+ unproven publishing cutover

          ↓

TO-BE
strong data plane preserved
+ one Autopilot control plane
+ model-agnostic local AI router
+ incremental evidence intelligence
+ persistent Top100 portfolio
+ independent audit gates
+ exact SocialScheduler execution
+ outcome-learning loop
```

**Phase 1 recommendation:** proceed to implementation through the provider-neutral local AI router and canonical orchestration layer first. Do not spend engineering effort polishing the current DeepSeek-specific gateway chain.