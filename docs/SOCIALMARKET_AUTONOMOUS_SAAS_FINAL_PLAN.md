# SocialMarket AI — Final Autonomous SaaS Design Plan

**Status:** Canonical TO-BE design baseline  
**Date:** 2026-08-17  
**Primary brain:** SocialMarket AI  
**Execution service:** SocialScheduler  
**Operating mode:** Autopilot-first, minimal owner interaction, zero-paid-LLM default

> **Implementation evidence:** The verified AS-IS investigation and migration verdict are maintained in `docs/SOCIALMARKET_PHASE1_FORENSIC_AUDIT.md`. The forensic audit is the required implementation companion to this design and must be updated when production facts change.

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

---

## 4. Control-plane hierarchy

```text
OWNER
  │
  ├─ START / PAUSE / STOP
  ├─ absolute MIN_COMMISSION_EUR
  ├─ optional strategic directives
  ├─ optional niche veto
  └─ emergency stop
  │
  ▼
AUTOPILOT CONTROL PLANE
  │
  ├─ State/Freshness Planner
  ├─ AI Policy Brain
  ├─ Model Router
  ├─ Workflow Orchestrator
  ├─ Portfolio Manager
  └─ Audit Controller
```

The owner provides intent and hard business limits. The control plane converts them into execution policy.

The control plane must never expose internal weights as if they were business configuration.

---

## 5. Hard filters vs strategic directives vs AI reasoning

### 5.1 Hard filters

Hard filters are deterministic, explainable and non-negotiable during a run.

Examples:

```text
product parse valid?
merchant resolved?
tracking URL valid?
price valid?
in stock?
minimum commission reached?
owner niche EXCLUDE?
compliance exclusion?
```

If a product fails a hard filter, it never reaches expensive AI.

### 5.2 Strategic directives

Directives influence exploration and promotion priority but do not manufacture evidence.

Example:

```text
Home Energy = PRIORITIZE
```

The orchestrator may:

- allocate more collection/research attention;
- lower the threshold for *researching* a challenger;
- increase source diversity checks;
- revisit stale evidence sooner;

It may **not**:

- invent demand;
- lower the owner's commission floor;
- fabricate product fit;
- skip skeptic audit;
- force a product into Top 100 without evidence.

### 5.3 AI reasoning

AI handles questions that require semantic/contextual interpretation:

- what consumer problem is expressed?
- how severe/urgent is it?
- is there real purchase intent?
- what solution attributes matter?
- does a specific product actually solve it?
- is the social angle authentic or forced?
- does new evidence justify replacing an incumbent?

---

## 6. End-to-end target workflow

```text
AUTOPILOT STARTED
       │
       ▼
READ OWNER CONTROL STATE
       │
       ▼
STATE / FRESHNESS PLANNER
       │
       ├─ previous Top 100
       ├─ previous evidence hashes
       ├─ current directives
       ├─ source freshness
       ├─ merchant/feed changes
       └─ previous performance
       │
       ▼
WHAT CHANGED?
       │
       ▼
DEMAND INTELLIGENCE
       │
       ├─ search/public web
       ├─ high-traffic Greek sources
       ├─ social/public signals
       ├─ communities/reviews
       ├─ commercial/search intent
       ├─ trend velocity
       └─ seasonality
       │
       ▼
PAIN / NEED INTELLIGENCE
       │
       ├─ complaint
       ├─ desire
       ├─ workaround
       ├─ dissatisfaction
       ├─ urgency
       ├─ buying intent
       └─ unmet solution requirement
       │
       ▼
EVIDENCE NORMALIZATION
       │
       ├─ dedupe
       ├─ source quality
       ├─ recency
       ├─ Greek relevance
       ├─ public provenance
       └─ embeddings / clusters
       │
       ▼
SOLUTION REQUIREMENTS
       │
       ▼
LINKWISE COMMERCIAL UNIVERSE
       │
       ├─ streaming
       ├─ merchant resolution
       ├─ stock
       ├─ price
       ├─ tracking
       ├─ commission
       ├─ owner hard gates
       └─ canonical products/offers
       │
       ▼
CHEAP CANDIDATE SHORTLIST
       │
       ├─ deterministic/statistical rank
       ├─ embeddings
       ├─ demand/product semantic retrieval
       ├─ merchant/category diversity
       └─ prior performance
       │
       ▼
AI PRODUCT DECISION PLANE
       │
       ├─ Product Fit Analyst
       ├─ Affiliate Strategist
       ├─ Social Promotability Analyst
       └─ Ranking Strategist
       │
       ▼
INDEPENDENT AUDIT COUNCIL
       │
       ├─ Evidence Skeptic
       ├─ Product-Fit Skeptic
       ├─ Affiliate Economics Skeptic
       └─ Ranking Auditor
       │
       ▼
INCUMBENTS vs CHALLENGERS
       │
       ▼
TOP 100 vNEXT
       │
       ├─ no material change → HOLD
       │
       └─ material change
             │
             ▼
       PROMOTION DELTA
             │
             ▼
       CREATIVE / CONTENT
             │
             ▼
       CREATIVE AUDIT
             │
             ▼
       content.items
             │
             ▼
       publish.outbox
             │
             ▼
       SOCIALSCHEDULER
             │
             ▼
       BUFFER / SOCIAL
             │
             ▼
       PERFORMANCE
             │
             └─────────────► SOCIALMARKET LEARNING
```

---

## 7. AI model strategy — task fitness, not one permanent model

There is no user-selected model.

The Orchestrator maintains a benchmarked model registry and chooses the lowest-cost local/open-weight model that meets the task quality gate.

```text
Tier 0  deterministic / SQL / statistics / embeddings
Tier 1  small local model: classify / extract / normalize
Tier 2  stronger local model: semantic reasoning / product-pain fit
Tier 3  independent local audit model: skeptic / challenge
FAIL    SAFE_HOLD
```

Key rules:

- do not call an LLM where rules/statistics suffice;
- use strict structured output;
- use bounded context;
- no chain-of-agents conversational loops;
- cache by model + task + prompt version + input hash;
- unchanged evidence reuses prior trusted result;
- stronger model is invoked only when a cheaper validated model is insufficient;
- if no available model passes quality requirements, hold the trusted portfolio state.

Paid remote APIs may exist as an explicitly disabled future option, but the product must not require them for normal operation.

---

## 8. Agent role system

Agents are **roles with scoped contracts**, not persistent personalities chatting to one another.

### Chief Orchestrator

Owns planning, task dispatch, state transitions and final portfolio proposal.

### Greek Demand Analyst

Interprets current Greek demand, intent, momentum, seasonality and market context.

### Social Signal Analyst

Extracts useful public social/community signals and separates engagement from commercial intent.

### Pain-Gap Analyst

Transforms evidence into validated consumer problems and unmet solution requirements.

### Merchant Intelligence Analyst

Maintains merchant identity, trust, authority, commercial suitability and offer reliability.

### Product-Solution Analyst

Maps problem requirements to real Linkwise product attributes/evidence.

### Affiliate Strategist

Evaluates conversion plausibility, economics, offer quality and promotion potential.

### Ranking Strategist

Compares candidates and incumbents using structured evidence and calibrated features.

### Evidence Skeptic

Attempts to disprove market/pain conclusions.

### Product-Fit Skeptic

Attempts to disprove that the product solves the claimed pain.

### Affiliate Economics Skeptic

Attempts to disprove commercial viability.

### Ranking Auditor

Challenges material Top-100/promotion changes.

### Creative Strategist + Creative Skeptic

Only run for products selected for new or materially changed promotion.

---

## 9. Token and compute minimization

Normal weekly operation must be incremental.

```text
hash inputs
  ↓
compare to last trusted state
  ↓
unchanged? → reuse
changed/stale? → deterministic refresh
  ↓
statistics / embeddings
  ↓
compact evidence packet
  ↓
smallest validated local model
  ↓
material portfolio change possible?
    no → stop
    yes → deeper reasoning + skeptic
```

This means:

- the multi-GB Linkwise feed is streamed, never placed in model context;
- only filtered candidates get semantic work;
- only serious challengers get deep reasoning;
- only portfolio-changing decisions get expensive audit;
- only promoted changes trigger creative generation.

---

## 10. Persistent Top-100 portfolio

The Top 100 is state, not a generated report.

Each entry needs:

```text
product_id
preferred_offer_id
current_rank
previous_rank
portfolio_state
promotion_state
rank_confidence
evidence_snapshot_hash
commercial_snapshot_hash
performance_snapshot
last_material_change_at
last_researched_at
last_audited_at
decision_reason
audit_verdict
```

Canonical state decisions:

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

The system should prefer portfolio stability unless new evidence is materially better.

---

## 11. Promotion decision layer

Top-100 membership and active promotion are related but not identical.

The Orchestrator decides:

- whether a product belongs in the portfolio;
- whether it should actively receive promotion now;
- whether existing creative is still valid;
- whether a new angle is justified;
- whether a campaign should pause due to demand, stock, merchant, commission or performance deterioration.

This avoids regenerating/scheduling content for every Top-100 item every week.

---

## 12. SocialMarket / SocialScheduler boundary

The accepted boundary remains:

```text
SOCIALMARKET
WHAT + WHY + WHO + MESSAGE + EXACT APPROVED INTENT
        │
        ▼
publish.outbox
        │
        ▼
SOCIALSCHEDULER
claim + technical preflight + exact execution + retry + reconciliation
        │
        ▼
BUFFER / NETWORKS
```

SocialScheduler must never choose a product, niche, marketing angle or new schedule independently.

Performance/raw execution telemetry returns to the shared database; SocialMarket interprets it.

---

## 13. Learning loop

The system eventually calibrates predictions against outcomes:

```text
demand/pain/product prediction
        ↓
Top 100
        ↓
promotion
        ↓
impressions
        ↓
clicks
        ↓
affiliate clicks
        ↓
conversion
        ↓
commission revenue
        ↓
EPC / conversion rate
        ↓
calibration by category / source / merchant / creative / channel
```

The AI may adapt internal policy from observed results while never silently changing the owner's hard profitability floor or exclusions.

---

## 14. Failure behavior

Autonomy must be safe.

```text
bad/missing feed                  → preserve prior trusted state
unresolved merchant               → reject candidate
commission below owner floor      → reject candidate
weak demand evidence              → no promotion escalation
local model unavailable           → retry bounded/local alternative
all validated local models fail   → SAFE_HOLD
semantic audit fails              → do not materialize new claim
ranking audit fails               → keep incumbent
creative audit fails              → no outbox
outbox execution fails            → SocialScheduler technical retry only
emergency stop                    → no new publishing intent
```

Autopilot means automated decisions, not automated risk-taking.

---

## 15. Implementation sequence

The implementation order is governed by the forensic audit rather than by adding more parallel versions.

```text
PHASE 1  forensic AS-IS audit                 ← documented
PHASE 2  canonical Autopilot control plane
PHASE 3  provider-neutral local AI Task Router
PHASE 4  restore semantic pain production
PHASE 5  zero-paid product ranking + audit
PHASE 6  persistent Top-100 portfolio
PHASE 7  incumbent/challenger delta engine
PHASE 8  promotion decision + delta creative
PHASE 9  SocialScheduler cutover proof
PHASE 10 performance feedback / calibration
PHASE 11 workflow/code retirement + governance hardening
```

No legacy production path should be deleted until the replacement passes equivalence/acceptance tests.

---

## 16. Production definition of done

SocialMarket AI is production-ready only when one authoritative Autopilot run can prove:

```text
START
 ↓
current Greek demand evidence
 ↓
validated pain / need intelligence
 ↓
Linkwise full-universe commercial scan
 ↓
shortlist
 ↓
local/open-weight AI reasoning
 ↓
independent audit
 ↓
persisted Top 100
 ↓
portfolio delta
 ↓
approved promotion delta
 ↓
creative + audit
 ↓
content.items
 ↓
publish.outbox
 ↓
SocialScheduler claim
 ↓
Buffer schedule
 ↓
ACK / reconciliation
 ↓
performance telemetry back to SocialMarket
```

with:

- no paid model required;
- no owner interaction during the run;
- unchanged intelligence reused;
- hard commission floor enforced;
- exclusions enforced;
- failures fail closed;
- every material decision explainable from evidence.

---

## 17. Final product principle

**The owner sets direction. SocialMarket AI thinks. SocialScheduler executes. Performance teaches the next decision.**
