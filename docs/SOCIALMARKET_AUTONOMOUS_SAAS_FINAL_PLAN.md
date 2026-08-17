# SocialMarket AI — Final Autonomous SaaS Design Plan

**Status:** Canonical TO-BE design baseline  
**Date:** 2026-08-17  
**Primary brain:** SocialMarket AI  
**Execution service:** SocialScheduler  
**Operating mode:** Autopilot-first, minimal owner interaction, zero-paid-LLM default

---

## 1. Product definition

SocialMarket AI is an **autonomous Greek affiliate-commerce intelligence and decision system**.

The owner is **not** expected to configure AI thresholds, ranking weights, RAG settings, freshness windows, model names, research depth, source weights, challenger margins, or workflow details.

The owner interacts with the system only at the strategic-control level:

1. **START / PAUSE / STOP AUTOPILOT**.
2. Set the absolute **minimum expected commission in EUR** that a product must satisfy.
3. Change a small number of **business priorities** when desired.
4. Accept, deprioritize, or **exclude a proposed niche/category** from active demand exploration.
5. Use an emergency stop if publishing/intelligence must halt.

Everything else belongs to the AI Orchestrator.

The system's weekly question is:

> Of all currently eligible Linkwise merchant/product offers that satisfy the owner's profitability floor, which products have the strongest evidence-backed probability of profitable affiliate promotion in Greece now, and has the market changed enough to modify the current Top 100 or promotion outbox?

The desired output is not a weekly report. It is a continuously maintained **promotion portfolio**.

---

## 2. Owner control model — Autopilot Console

The normal SaaS interface should expose a very small control surface.

### 2.1 Mandatory controls

```text
AUTOPILOT               START | PAUSE | STOP
MIN_COMMISSION_EUR      absolute owner-defined number
EMERGENCY_STOP          ON | OFF
```

`MIN_COMMISSION_EUR` is a deterministic hard eligibility gate. The orchestrator may recommend changing it, but it may never silently override the owner's value.

### 2.2 Strategic directives

The orchestrator discovers and proposes niches, audiences and market themes. The owner may intervene only if desired.

Canonical directive states:

```text
AUTO          orchestrator decides normally
PRIORITIZE    give the niche strategic preference when evidence supports it
DEPRIORITIZE  allow discovery but reduce promotion urgency
EXCLUDE       remove the niche from active demand/product promotion consideration
```

These are **semantic directives**, not user-defined numeric weights.

Examples:

```text
Home energy savings     PRIORITIZE
Back-to-school          AUTO
Luxury watches          EXCLUDE
Pet care                AUTO
```

The AI converts the directive into internal policy while preserving evidence quality and profitability constraints.

### 2.3 What the owner does NOT configure

The owner does not normally see or edit:

- demand weights
- pain severity thresholds
- competition weights
- merchant trust thresholds
- source weights
- RAG limits
- embedding thresholds
- model names
- model temperature
- model reasoning mode
- AI batch size
- prompt templates
- research depth
- source freshness TTLs
- evidence sufficiency thresholds
- challenger margin
- ranking score weights
- Top-100 churn thresholds
- creative-selection thresholds
- retry counts
- workflow schedules

These are internal autonomous policy.

---

## 3. Governing architecture principles

1. **Autopilot by default.** Once started, the platform runs without routine owner interaction.
2. **Owner profitability floor is absolute.** AI cannot promote below the configured minimum expected commission.
3. **Owner veto is absolute.** Excluded niches/products/merchants cannot be promoted until the directive changes.
4. **Filters before AI.** Deterministic code removes invalid and commercially ineligible data before semantic reasoning.
5. **Demand before product.** Discover demand/pain first; then search Linkwise for solutions.
6. **Evidence before conclusion.** AI conclusions must reference persisted evidence IDs, timestamps and source quality.
7. **AI chooses its own operational policy.** Model, research depth, retrieval size, source mix and reasoning depth are orchestrator decisions.
8. **Use the cheapest reliable computation first.** SQL/statistics/rules/embeddings before generative AI.
9. **Zero-paid-LLM normal path.** Open-weight/local inference is the default production architecture; paid APIs are not required for normal operation.
10. **Incremental intelligence.** Reprocess only new, changed, stale or strategically affected evidence.
11. **Persistent Top 100.** Rankings are stateful; weekly runs compare incumbents vs challengers.
12. **Fail closed.** If confidence/evidence/model quality is insufficient, preserve the last trusted state.
13. **SocialMarket decides; SocialScheduler executes.** No duplicate marketing brain in SocialScheduler.
14. **Performance closes the loop.** Click/conversion/revenue results calibrate future decisions.
15. **Every autonomous decision is explainable and reversible.**

---

## 4. Verified AS-IS foundations to preserve

The current repository already contains useful building blocks and should be consolidated rather than rewritten blindly:

- dedicated `agents`, `workers`, `supabase`, application and workflow layers
- merchant intelligence workers
- Greek demand and category-pain intelligence
- evidence collection and semantic clustering
- pgvector / semantic retrieval
- Linkwise streaming ingestion
- product candidate shortlisting
- product ranking and creative stages
- run observability
- canonical content / outbox concepts
- local-first Ollama runtime
- shared Supabase source of truth
- accepted SocialMarket ↔ SocialScheduler boundary

### Required AS-IS corrections

1. Fixed ranking/opportunity weights must become internal adaptive policy, not owner configuration.
2. `ops.product_intelligence_config` currently contains many low-level settings that should disappear from the normal SaaS UI.
3. The current production ranking path hard-requires DeepSeek; the final architecture must remove that dependency.
4. Any retired/unavailable remote-model route must be removed from production routing.
5. Multiple historical pipeline/workflow versions must be audited and consolidated into canonical production paths.
6. Weekly orchestration must become one explicit stateful intelligence chain.

---

## 5. Three planes: Control, Deterministic Data, AI Brain

The system must maintain a strict separation.

```text
OWNER
  │
  ▼
AUTOPILOT CONTROL PLANE
  │
  ▼
AI ORCHESTRATOR
  │
  ├──────────────► DETERMINISTIC / STATISTICAL DATA PLANE
  │                         │
  │                         ▼
  │                COMPACT EVIDENCE + CANDIDATES
  │                         │
  └─────────────────────────┤
                            ▼
                      AI BRAIN PLANE
                            │
                            ▼
                       AUDIT COUNCIL
                            │
                            ▼
                       DECISION STATE
```

### 5.1 Control plane

Owns:

- start/pause/stop
- owner minimum commission
- strategic niche directives
- emergency stop
- current orchestrator policy version
- run lifecycle
- promotion portfolio state

### 5.2 Deterministic / statistical data plane

Owns:

- Linkwise streaming
- schema validation
- merchant/program resolution
- canonical product identity
- offer deduplication
- price/currency arithmetic
- commission arithmetic
- stock/availability
- valid tracking URL
- owner hard-gate enforcement
- exact niche exclusions
- hashes and change detection
- freshness timestamps
- source metadata
- time-series features
- frequency/velocity statistics
- statistical forecasts
- embeddings/vector retrieval
- persistence
- state transitions

### 5.3 AI brain plane

Owns semantic decisions that code alone cannot reliably make:

- Greek market interpretation
- demand intent interpretation
- pain/problem extraction
- pain clustering interpretation
- solution-requirement extraction
- product↔pain semantic fit
- merchant qualitative interpretation
- competition/whitespace interpretation
- strategic opportunity synthesis
- challenger vs incumbent reasoning
- promotion angle
- creative/copy generation
- independent skepticism/audit

---

## 6. Filters vs AI execution — canonical boundary

| Stage | Deterministic / statistical | AI brain |
|---|---|---|
| Linkwise ingest | stream, parse, validate, hash, dedupe | none |
| Merchant resolution | IDs, domains, exact mappings, deterministic aliases | ambiguous identity only |
| Profitability gate | expected commission EUR, price, currency | none |
| Availability gate | stock, tracking URL, valid offer | none |
| Owner directives | exact EXCLUDE / hard constraints | interpret PRIORITIZE/DEPRIORITIZE context |
| Freshness | hashes, timestamps, TTL enforcement | chooses internal freshness policy |
| Demand measurement | counts, velocity, trends, normalization | interprets meaning and intent |
| Evidence | source metadata, duplicate removal, recency | relevance, contradiction, semantic trust |
| Pain discovery | embeddings, clustering, frequency | interpretation and labeling |
| Product matching | category/spec/vector shortlist | solution-fit reasoning |
| Ranking | hard gates + measured features | contextual synthesis and decision |
| Top-100 change | exact portfolio diff | KEEP/REPLACE/PAUSE rationale |
| Creative | dimensions, URL/media checks | positioning, hook, copy |
| Publishing | exact approved intent | no AI in execution service |

### Cost rule

> If a correct result can be obtained through SQL, arithmetic, rules, statistics, hashing or embeddings, generative AI is prohibited for that step.

---

## 7. End-to-end autonomous workflow

```text
OWNER STARTS AUTOPILOT
        │
        ▼
READ OWNER DIRECTIVES
        │
        ▼
ORCHESTRATOR STATE PLANNER
        │
        ├─ previous Top 100
        ├─ previous demand state
        ├─ evidence freshness
        ├─ Linkwise feed changes
        ├─ merchant changes
        ├─ performance feedback
        └─ active niche directives
        │
        ▼
WHAT ACTUALLY CHANGED?
        │
        ▼
TARGETED DATA REFRESH
        │
        ├─ Greek demand sources
        ├─ public social evidence
        ├─ reviews/forums/news/search
        ├─ merchant evidence
        └─ Linkwise product/offers
        │
        ▼
DETERMINISTIC NORMALIZATION
        │
        ▼
DEMAND + PAIN EVIDENCE GRAPH
        │
        ▼
SOLUTION REQUIREMENTS
        │
        ▼
LINKWISE COMMERCIAL UNIVERSE
        │
        ▼
HARD PROFITABILITY / VALIDITY FILTERS
        │
        ▼
VECTOR / STATISTICAL SHORTLIST
        │
        ▼
AI SPECIALIST ANALYSIS
        │
        ▼
INCUMBENTS + CHALLENGERS
        │
        ▼
RANKING DECISION COUNCIL
        │
        ▼
AUDIT COUNCIL
        │
        ▼
TOP 100 vNEXT
        │
        ▼
DIFF vs CURRENT TOP 100
        │
        ├─ no meaningful change ──► HOLD
        │
        └─ justified change
                  │
                  ▼
          PROMOTION PORTFOLIO DELTA
                  │
                  ▼
          CREATIVE / CONTENT AGENTS
                  │
                  ▼
             CREATIVE AUDIT
                  │
                  ▼
            publish.outbox
                  │
                  ▼
            SocialScheduler
                  │
                  ▼
          Buffer / social networks
                  │
                  ▼
          clicks / conversions / revenue
                  │
                  └──────────────► SocialMarket learning
```

---

## 8. Orchestrator design

The Orchestrator is not one giant LLM prompt. It is a **state machine + policy engine + model router + task planner**.

### 8.1 Orchestrator responsibilities

Every cycle it decides autonomously:

- which market areas require refresh
- which evidence is stale
- which sources are worth querying
- which niches need deeper research
- which products deserve semantic analysis
- which model is appropriate for each task
- how much context each model receives
- whether a result needs a second model/auditor
- whether an incumbent remains stronger than challengers
- whether the Top 100 should change
- whether a promotion should be created, paused, replaced or held
- whether content must be regenerated

### 8.2 It may not override

- STOP / PAUSE / emergency stop
- minimum expected commission EUR
- explicit EXCLUDE directives
- security/compliance invariants
- database/publishing safety rules

### 8.3 Orchestrator state machine

```text
STOPPED
  │ START
  ▼
PLANNING
  ▼
REFRESHING_DATA
  ▼
FILTERING
  ▼
REASONING
  ▼
AUDITING
  ▼
PORTFOLIO_DECISION
  ▼
CONTENT_PREPARATION
  ▼
OUTBOX_READY
  ▼
MONITORING
  └────────► next intelligence cycle
```

Any critical failure transitions to:

```text
SAFE_HOLD
```

`SAFE_HOLD` preserves the last trusted portfolio and creates no unverified new publishing intent.

---

## 9. Specialist AI roles

Keep the agent organization small and role-specific. Agents should communicate through structured persisted contracts, not open-ended conversations.

### 9.1 Chief AI Orchestrator

Owns task planning, context scope, routing, policy and final workflow progression.

### 9.2 Greek Demand Intelligence Analyst

Goal: identify real, fresh Greek demand and commercial intent.

Analyzes:

- search signals
- major Greek web/public content signals
- social/public discussion
- trend velocity
- seasonality
- commercial intent
- category momentum

Returns structured demand hypotheses with evidence IDs.

### 9.3 Consumer Pain-Gap Analyst

Goal: turn demand into specific unresolved consumer problems.

Extracts:

- complaint
- frustration
- desire
- workaround
- urgency
- failed existing solution
- price sensitivity
- required product attributes

### 9.4 Social Listening Analyst

Goal: detect socially promotable demand and language.

Focuses on public social evidence and extracts:

- recurring pain language
- emerging themes
- audience vocabulary
- creator/content pattern
- product objections
- purchase intent
- social promotability

### 9.5 Affiliate Marketing Strategist

Goal: maximize realistic affiliate revenue, not vanity demand.

Interprets:

- expected commission
- likely conversion
- merchant quality
- offer competitiveness
- funnel stage
- audience/product match
- campaign timing
- social channel fit

### 9.6 Product Solution-Fit Analyst

Goal: determine whether a Linkwise product genuinely solves the validated pain.

Returns:

- fit verdict
- matching product attributes
- missing attributes
- evidence support
- confidence

### 9.7 Merchant Intelligence Analyst

Goal: determine whether the merchant strengthens or weakens the opportunity.

### 9.8 Ranking Decision Agent

Goal: synthesize compact structured evidence into incumbent/challenger decisions.

It does not ingest the raw 3.4–3.8 GB universe.

### 9.9 Creative Strategist

Goal: convert approved promotion decisions into evidence-grounded social content concepts.

### 9.10 Performance Learning Analyst

Goal: compare predicted opportunity with actual outcome and update internal calibration signals.

---

## 10. Independent Audit Council

Primary agents never self-certify high-impact decisions.

### Evidence Skeptic

Attempts to disprove the demand/pain claim using source quality, recency, contradictions and geographic relevance.

### Product-Fit Skeptic

Attempts to prove the selected product does **not** solve the claimed pain.

### Affiliate Economics Skeptic

Challenges whether the opportunity is commercially worth promoting despite apparent demand.

### Ranking Auditor

Challenges why product `#12` should rank above product `#31`, including incumbent/challenger consistency.

### Data Quality Auditor

Checks unresolved merchants, duplicates, missing offers, stale prices, invalid tracking URLs and feed anomalies.

### Architecture/Cost Auditor

Checks unnecessary model calls, duplicate pipelines, redundant context, token waste and workflow inefficiency.

### Audit rule

Auditors receive **compressed evidence and primary-agent output**, not a duplicate full research corpus unless escalation is necessary.

---

## 11. Demand-first intelligence architecture

The canonical reasoning direction is:

```text
Greek market signals
      ↓
Demand theme
      ↓
Purchase intent
      ↓
Pain / unmet need
      ↓
Audience / situation
      ↓
Solution requirements
      ↓
Commercial category
      ↓
Linkwise candidate retrieval
      ↓
Product solution fit
      ↓
Merchant / offer fit
      ↓
Affiliate economics
      ↓
Promotion opportunity
```

Avoid the reverse pattern:

```text
random Linkwise product
      ↓
search for a reason to promote it
```

The reverse pattern creates confirmation bias and unnecessary AI consumption.

---

## 12. Evidence Graph

Supabase should persist an explainable graph-like evidence model connecting:

```text
SOURCE
  ↓
EVIDENCE ITEM
  ↓
DEMAND SIGNAL
  ↓
PAIN CLUSTER
  ↓
SOLUTION REQUIREMENT
  ↓
PRODUCT
  ↓
OFFER
  ↓
MERCHANT
  ↓
RANKING DECISION
  ↓
CONTENT / CAMPAIGN
  ↓
PERFORMANCE
```

Every semantic relationship should retain:

```text
source_id
evidence_id
collected_at
market
language
source_type
source_quality
freshness
confidence
agent_role
model_route
policy_version
audit_verdict
```

This lets the platform answer:

> Why is this product in the Top 100?

and:

> What changed this week that caused it to enter, move or leave?

---

## 13. Linkwise large-feed architecture

The Linkwise universe must be processed as data, never as a giant model context.

```text
LINKWISE FEEDS (~multi-GB)
        │
        ▼
STREAM PARSER
        │
        ▼
SCHEMA + DATA QUALITY
        │
        ▼
MERCHANT RESOLUTION
        │
        ▼
CANONICAL PRODUCT / OFFER IDENTITY
        │
        ▼
PRICE / CURRENCY / COMMISSION
        │
        ▼
OWNER MIN COMMISSION HARD GATE
        │
        ▼
STOCK / TRACKING / VALIDITY GATES
        │
        ▼
DEDUPLICATION + BEST OFFER
        │
        ▼
CHEAP COMMERCIAL CANDIDATE UNIVERSE
        │
        ▼
CATEGORY + KEYWORD + VECTOR RETRIEVAL
        │
        ▼
SMALL SEMANTIC SHORTLIST
        │
        ▼
AI PRODUCT-FIT ANALYSIS
```

Generative AI should see hundreds of well-selected candidates at most over an entire cycle, not millions of raw records.

---

## 14. Profitability architecture

### 14.1 Owner floor

The owner sets:

```text
MIN_COMMISSION_EUR = X
```

Products below `X` are ineligible regardless of AI enthusiasm.

### 14.2 AI commercial intelligence

Above the hard floor, the orchestrator evaluates expected profitability using measured and inferred signals such as:

- expected commission EUR
- price competitiveness
- merchant performance
- historical CTR
- affiliate click-through
- conversion rate
- EPC/revenue where available
- stock reliability
- purchase friction
- demand intensity
- pain urgency
- competitive saturation
- social promotability

The owner does not configure these weights.

### 14.3 Learning objective

As performance history grows, ranking should move from static heuristics toward calibrated expected value:

```text
Expected Promotion Value
≈
P(click | audience, creative, channel)
× P(conversion | click, product, merchant)
× expected commission EUR
× confidence / risk adjustment
```

This remains subordinate to the owner's minimum-commission gate.

---

## 15. Model routing — autonomous and zero-paid default

The owner never chooses a model.

The Orchestrator's Model Router maintains an internal **model capability registry** and chooses the best available zero-paid/open-weight route for each task.

### 15.1 Routing order

```text
1. deterministic/statistical method
2. embedding/vector method
3. smallest competent local open-weight model
4. stronger local open-weight model when required
5. second independent local model for high-impact audit if useful
6. fail closed / hold trusted state if quality is insufficient
```

No paid remote LLM is necessary for the normal production path.

### 15.2 Model selection criteria

For each agent task, the router benchmarks/records:

- structured JSON reliability
- Greek language quality
- reasoning accuracy
- evidence-grounding accuracy
- hallucination rate
- latency
- RAM/CPU footprint
- context efficiency
- token count
- task-specific benchmark score

The router chooses by **task fitness**, not by one global favorite model.

### 15.3 Example task classes

```text
classification / labels      → very small model
Greek semantic extraction    → small Greek-capable model
pain/product fit              → medium local reasoning model
ranking challenger decision  → strongest validated local model
skeptic audit                 → independent validated model/route
copy generation               → creative-capable local model
```

### 15.4 No permanent model lock-in

The model registry must support replacing a model without changing business logic. New open-weight models can be benchmarked automatically and promoted only when they outperform the current route on SocialMarket's own evaluation set.

---

## 16. Token and compute minimization

Token minimization is a core architecture requirement.

### 16.1 Never resend unchanged evidence

Persist:

- content hash
- semantic hash
- prior agent result
- model/version
- evidence IDs
- policy version
- expiration/freshness state

If none of the material inputs changed, reuse the validated result.

### 16.2 Delta research

Weekly runs should answer:

```text
What changed?
```

not:

```text
Rebuild everything.
```

### 16.3 Context compression

Before AI:

```text
raw pages/comments/reviews
        ↓
clean text
        ↓
deduplicate
        ↓
extract relevant spans
        ↓
cluster
        ↓
statistical summaries
        ↓
vector retrieval
        ↓
compact evidence packet
        ↓
LLM
```

### 16.4 Structured single-turn contracts

Default:

- one agent turn
- strict JSON
- bounded fields
- evidence IDs instead of repeated quotations
- no chain-of-agent conversations
- no repeated generic system prompt context

### 16.5 Audit by exception

Deep/independent audits are mandatory for promotion-impacting decisions, but routine unchanged state should not trigger full duplicate reasoning.

---

## 17. Stateful Top-100 portfolio

The Top 100 is a versioned portfolio, not a regenerated weekly list.

Each current product has:

```text
current_rank
previous_rank
entry_date
last_material_change
current_decision
promotion_status
confidence
reason_codes
evidence_snapshot_id
policy_version
```

Every cycle compares incumbents with challengers.

Decision states:

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

A challenger does not replace an incumbent because its raw score is marginally higher. Replacement requires **material evidence advantage** after audit and stability checks.

This prevents unnecessary portfolio churn and repeated creative generation.

---

## 18. Weekly autonomous cycle

The owner does not need to initiate each weekly run after Autopilot is started.

```text
WEEKLY CYCLE
   │
   ▼
1. Verify Autopilot state
2. Load minimum commission + directives
3. Load previous trusted portfolio
4. Detect changed/stale inputs
5. Refresh only required demand/evidence
6. Refresh Linkwise commercial universe
7. Apply hard gates
8. Update demand/pain graph
9. Generate candidate challengers
10. Run selective AI analysis
11. Compare incumbents vs challengers
12. Run independent audit
13. Persist Top-100 vNext
14. Calculate portfolio delta
15. Create content only for required promotion changes
16. Audit content/assets
17. Write approved publishing intents to outbox
18. Monitor SocialScheduler execution
19. Ingest performance feedback
20. Update calibration/state
```

If no material market change is found:

```text
Top 100 = HOLD
No unnecessary AI expansion
No unnecessary creative regeneration
No unnecessary outbox churn
```

---

## 19. Promotion portfolio and outbox

A rank change does not automatically mean a new post.

The Orchestrator owns a separate **promotion portfolio decision** considering:

- existing campaign saturation
- recent content cadence
- product momentum
- creative freshness
- channel fit
- conversion history
- promotion conflicts
- seasonality
- current owner directives

Outbox intent should retain decision provenance:

```text
product_id
portfolio_version
previous_rank
current_rank
decision_type
decision_reason
commission_eur
demand_delta
pain_delta
merchant_delta
commercial_delta
confidence
evidence_snapshot_id
audit_verdict
content_id
creative_ids
intended_schedule
outbox_status
```

---

## 20. SocialMarket ↔ SocialScheduler boundary

The accepted architecture boundary remains:

### SocialMarket AI owns

- demand intelligence
- pain intelligence
- merchant intelligence
- product intelligence
- affiliate economics
- Top-100 ranking
- promotion portfolio
- content strategy
- creative generation
- approval
- intended publication schedule
- affiliate/tracking URL
- canonical content
- `publish.outbox`
- interpretation of post-publication performance

### SocialScheduler owns

- claiming approved outbox jobs
- provider/Buffer connection
- technical preflight
- exact execution of approved time/content/asset/URL
- retries for technical failures
- provider rate limits
- reconciliation
- publication IDs/permalinks
- raw execution telemetry

### Forbidden behavior

SocialScheduler may not independently change:

- product
- merchant
- affiliate URL
- caption
- creative
- schedule strategy
- ranking
- campaign strategy

Business changes return to SocialMarket AI.

---

## 21. Performance-learning loop

The mature system must learn from actual outcomes.

```text
SocialMarket prediction
        ↓
Top-100 / promotion decision
        ↓
content + creative
        ↓
SocialScheduler
        ↓
social network
        ↓
impression / engagement / click
        ↓
affiliate click / conversion / revenue
        ↓
SocialMarket performance store
        ↓
calibration
        ↓
future ranking / creative / channel decisions
```

The goal is to learn category/channel/merchant relationships such as:

- which pain signals predict conversion
- which merchants outperform apparent demand
- which social signals are noisy
- which creative angles drive affiliate clicks
- which ranks actually deserve promotion
- how quickly different categories decay

These are internal learned policies, not user settings.

---

## 22. Supabase target responsibility

Supabase remains the canonical state layer.

Recommended logical domains:

```text
control.*      autopilot state, owner directives, policy versions
market.*       demand, niches, trends, forecasts
merchant.*     identities, programs, merchant intelligence
product.*      canonical products, offers, commercial eligibility
evidence.*     raw/normalized evidence, claims, audits
semantic.*     embeddings, clusters, retrieval objects
ranking.*      portfolio versions, candidates, decisions
content.*      content items, creatives, approvals
publish.*      outbox, acknowledgements, publishing state
performance.*  social/affiliate telemetry and calibration
ops.*          runs, model telemetry, errors, costs, audit logs
```

No second canonical intelligence database should be created in GitHub Actions, Vercel or SocialScheduler.

---

## 23. GitHub Actions target responsibility

GitHub Actions is an execution environment, not the source of truth.

Target production orchestration should converge toward a small number of workflows:

```text
CI
AUTOPILOT WEEKLY INTELLIGENCE
TARGETED REFRESH / RECOVERY
MODEL BENCHMARK / EVALUATION
MAINTENANCE / DATA QUALITY
```

Historical version-specific workflows should be retired after equivalence validation.

A code push must not automatically trigger expensive market-wide intelligence unless explicitly required.

---

## 24. Vercel target responsibility

Vercel serves the SaaS application/control experience.

The UI should emphasize:

### Home / Autopilot

```text
Autopilot: RUNNING
Min commission: €X
Last successful intelligence cycle
Current Top 100 version
Promotions active
Changes this week
Critical alerts
START / PAUSE / STOP
```

### Strategic Priorities

AI-proposed niches with simple controls:

```text
AUTO | PRIORITIZE | DEPRIORITIZE | EXCLUDE
```

### Top 100

Explainable portfolio with:

- rank
- change
- product
- merchant
- expected commission
- key demand/pain thesis
- confidence
- promotion status
- why it changed

### Audit / Explainability

Owner can inspect why the system acted but does not need to configure the underlying AI.

---

## 25. Security and autonomy invariants

1. No model may directly write arbitrary SQL.
2. AI returns structured decisions; deterministic services validate and persist them.
3. Every promotion-impacting AI result must pass schema validation.
4. Owner hard constraints are checked again at persistence and outbox time.
5. An excluded niche cannot re-enter through semantic similarity.
6. A product below minimum commission cannot enter ranking or outbox.
7. Missing/stale critical commercial facts cause HOLD/PAUSE, not assumption.
8. Outbox is idempotent.
9. SocialScheduler cannot invent business decisions.
10. Every state transition is audit logged.

---

## 26. Canonical engineering roles for the redesign

The implementation should be reviewed through these expert roles:

```text
Chief AI Software Architect
Affiliate Marketing Strategist
Greek Demand / Marketing Data Scientist
AI/ML Engineer
Data Engineer
Search/RAG Engineer
Ranking / Decision Scientist
Supabase/Postgres Engineer
Full-Stack SaaS Engineer
MLOps/GitHub Actions Engineer
SocialScheduler Integration Engineer
Security / Reliability Engineer
Independent Architecture & AI Audit Council
```

These are design responsibilities; they do not imply a separate LLM call for every role on every production run.

---

## 27. AS-IS forensic audit before refactor

Before implementation changes, inventory and classify every current component as:

```text
KEEP
MERGE
REFACTOR
REPLACE
DELETE
```

Audit scope:

- every GitHub Actions workflow and trigger
- every agent skill
- every worker version
- every current model call
- every Supabase Edge Function
- every migration/table/RPC relevant to intelligence
- Linkwise ingestion and feed contracts
- evidence collectors
- embeddings/RAG
- product ranking
- creative pipeline
- outbox
- SocialScheduler integration
- Vercel configuration/control UI
- performance feedback

No new parallel `vNext` stack should be created before this consolidation map exists.

---

## 28. Implementation roadmap

### Phase 0 — Canonical architecture

- merge this design baseline
- freeze new parallel architecture variants
- define acceptance tests

### Phase 1 — Forensic AS-IS map

- model-call graph
- workflow-trigger graph
- Supabase data lineage
- agent inventory
- KEEP/MERGE/REFACTOR/REPLACE/DELETE matrix

### Phase 2 — Autopilot control plane

- create simple global Autopilot state
- implement START/PAUSE/STOP/emergency stop
- make minimum commission the owner absolute profitability floor
- implement niche strategic directives
- remove low-level AI tuning from normal owner UI

### Phase 3 — Zero-paid model plane

- benchmark local/open-weight models against SocialMarket evaluation cases
- remove mandatory paid-model dependencies
- create task-specific model registry
- implement autonomous router
- implement fail-closed quality thresholds internally

### Phase 4 — Incremental intelligence planner

- hashes
- TTL/freshness state
- evidence reuse
- changed-source planner
- selective research depth
- cost/token telemetry

### Phase 5 — Demand/Pain Intelligence VNext canonicalization

- consolidate Greek demand sources
- consolidate social/public evidence collectors
- canonical demand signal
- canonical pain cluster
- solution-requirement extraction
- skeptic validation

### Phase 6 — Linkwise commercial engine

- canonical streaming ingestion
- merchant resolution
- product/offer canonicalization
- owner commission hard gate
- deterministic commercial shortlist
- semantic retrieval against solution requirements

### Phase 7 — Stateful Top-100 engine

- incumbent/challenger model
- persistent portfolio versions
- material-change rules
- ranking decision agent
- independent ranking audit
- portfolio delta

### Phase 8 — Promotion decision engine

- separate rank from promotion decision
- campaign saturation/cadence logic
- creative freshness
- channel selection
- promotion delta states

### Phase 9 — Creative + outbox

- generate only for justified portfolio changes
- independent creative audit
- canonical content persistence
- exact publishing intent

### Phase 10 — SocialScheduler hard integration

- outbox-only consumption
- technical execution only
- ACK/reconciliation
- performance telemetry return

### Phase 11 — Learning/calibration

- affiliate performance ingestion
- social performance ingestion
- prediction-vs-outcome analysis
- internal policy calibration
- category/merchant/channel learning

### Phase 12 — Production proof

One authoritative green run must prove:

```text
Autopilot STARTED
→ owner directives loaded
→ Greek demand refreshed selectively
→ pain gaps validated
→ Linkwise universe streamed
→ commission hard gate applied
→ candidates retrieved
→ local AI reasoning completed
→ audit council passed
→ Top 100 persisted
→ portfolio delta persisted
→ content generated only where needed
→ outbox written
→ SocialScheduler executed exact intent
→ telemetry returned
→ no paid LLM API required
```

---

## 29. Acceptance criteria

The redesign is complete only when all are true:

### Autonomy

- owner can START and then leave the system unattended
- weekly cycles execute without configuration prompts
- orchestrator chooses models, source scope, thresholds and research depth
- no ordinary run requires manual approval/configuration unless the system enters SAFE_HOLD

### Owner simplicity

Normal control requires only:

- Start/Pause/Stop
- minimum commission EUR
- optional niche priority/exclusion directives
- emergency stop

### Intelligence quality

- every Top-100 product is linked to current evidence
- every promoted product has a validated demand/pain/product thesis
- every material ranking change has an explanation
- independent audit can reject weak primary-agent conclusions

### Efficiency

- raw Linkwise feed is never passed to an LLM
- unchanged evidence is not repeatedly re-reasoned
- deterministic filters execute before generative reasoning
- token/model telemetry is persisted
- zero-paid inference is the default end-to-end route

### Reliability

- failures preserve last trusted portfolio
- no product below minimum commission enters Top 100/outbox
- excluded niches cannot enter promotion
- SocialScheduler cannot change business intent

### Learning

- publication and affiliate performance return to SocialMarket
- ranking can compare predicted vs actual results
- model/policy calibration can evolve without exposing tuning controls to the owner

---

## 30. Final system definition

```text
OWNER
  │
  │  START / PAUSE / STOP
  │  MIN COMMISSION €
  │  OPTIONAL STRATEGIC PRIORITIES / NICHE VETO
  │
  ▼
SOCIALMARKET AI AUTOPILOT
  │
  ├─ decides what to research
  ├─ chooses the best validated model per task
  ├─ decides evidence freshness
  ├─ discovers Greek demand
  ├─ discovers pain gaps
  ├─ maps solution requirements
  ├─ searches eligible Linkwise products
  ├─ evaluates merchants/offers
  ├─ maintains Top 100
  ├─ decides promotion portfolio changes
  ├─ generates/audits content
  └─ writes approved publishing intent
  │
  ▼
SOCIALSCHEDULER
  │
  └─ executes exactly
  │
  ▼
SOCIAL NETWORKS / AFFILIATE RESULTS
  │
  ▼
PERFORMANCE FEEDBACK
  │
  └──────────────► SOCIALMARKET AI LEARNING
```

**SocialMarket AI is the brain. The owner supplies the business objective and veto power, not the intelligence configuration.**
