# SocialMarket Deep Demand Intelligence V3

## Purpose

Upgrade Demand Intelligence from a single evidence-density score into an auditable Greek-market research system without weakening the existing semantic/evidence gates.

The system must answer five different questions separately:

1. **Observed demand:** what evidence do we actually observe?
2. **Latent demand:** what unmet need is implied by multiple weak/partial signals?
3. **Supply pressure:** how much credible solution coverage exists?
4. **Forecast:** how is the evidence-derived demand index likely to move?
5. **Causal confidence:** which relationships survive causal assumptions/refutation?

Never collapse these into one opaque score.

---

## Source-of-truth rule

The existing `api.semantic_category_market_v2`, normalized evidence, validated pain clusters, merchant intelligence and category-market history remain authoritative.

Deep Demand V3 is **additive**. It may interpret and forecast existing signals but it may not rewrite the observed Demand / Competition / Pain metrics to make an opportunity look stronger.

### State labels

Every analytical output must be tagged as one of:

- `OBSERVED` — directly persisted evidence/metric.
- `DERIVED` — deterministic transformation of observed data.
- `INFERRED` — fuzzy/graph/model inference.
- `FORECASTED` — statistical/neural future estimate.
- `CAUSAL_CANDIDATE` — hypothesis requiring identification/refutation.
- `UNAVAILABLE` — insufficient data; no fallback fabrication.

---

## Architecture

```text
Greek public-web + official context + reviews + social + merchant evidence
                                │
                                ▼
                      Normalized Evidence Store
                                │
                    ┌───────────┴───────────┐
                    ▼                       ▼
            Semantic / Vector RAG      Evidence Graph
                    │                       │
                    └───────────┬───────────┘
                                ▼
                      Demand Research Agent
                                │
        ┌───────────────────────┼────────────────────────┐
        ▼                       ▼                        ▼
 Observed Demand Index     Pain / Intent Model      Supply Model
        │                       │                        │
        └──────────────┬────────┴──────────────┬─────────┘
                       ▼                       ▼
              Fuzzy Whitespace Engine   Temporal Engine
                       │                ├─ change points
                       │                ├─ StatsForecast
                       │                └─ NeuralForecast
                       │
                       └──────────────┬───────────────┐
                                      ▼               ▼
                                 Causal Audit      Skeptic Audit
                                      │               │
                                      └───────┬───────┘
                                              ▼
                                  Decision Narrative Engine
                                              │
                                              ▼
                              Kimi-style interactive presentation
```

---

## Retrieval: Hybrid RAG + Graph context

Use the existing pgvector semantic layer for nearest-neighbour pain/evidence retrieval.

Add a lightweight GraphRAG pattern around existing relations rather than indexing the whole corpus with an expensive LLM graph build.

### Graph entities

- taxonomy category/subcategory
- validated pain cluster
- evidence observation
- merchant
- merchant program
- product/offer (when validated)
- source/domain
- seasonal/event context

### Graph relations

- `SUPPORTED_BY`
- `HAS_VALIDATED_PAIN`
- `HAS_SUPPLY`
- `SOLD_BY`
- `SOLVES`
- `CONTRADICTS`
- `ALTERNATIVE_TO`
- `OBSERVED_IN`
- `BELONGS_TO`

Graph degree or centrality is never a demand metric. It is retrieval/context structure only.

---

## Fuzzy inference

Fuzzy logic is used for **whitespace inference**, not to overwrite demand.

Inputs:

- observed Demand Index
- validated Pain Gap
- Supply Index
- Competition Index
- evidence confidence

Example rules:

- high demand + high pain + low supply → very high whitespace
- high demand + high pain + high supply → demand remains high; whitespace becomes moderate
- high demand + high competition → demand remains high; exploitability decreases
- medium demand + high pain + low supply → emerging niche

Output:

- `fuzzy_whitespace_score`
- activated rules
- certainty multiplier
- explicit semantics

---

## Supply model

Demand and supply are independent dimensions.

### Supply features

- trusted merchant count by canonical taxonomy
- active merchant-program count
- product/offer count only when validated product mapping exists
- seller/domain diversity
- merchant trust distribution
- merchant saturation/scale
- price-band breadth when real offer prices exist
- availability/Greek shipping evidence when verified

### Supply outputs

- `supply_coverage_index`
- `trusted_supply_index`
- `supply_fragmentation`
- `solution_diversity`
- `demand_supply_gap`

Do not subtract Supply from Demand. Compute a separate gap/whitespace dimension.

---

## Temporal engine

### Tier 0 — descriptive

< 8 daily observations:

- current observation only
- no trend arrow
- no sparkline implying history
- display `collecting history`

### Tier 1 — statistical

>= 8 daily observations and >= 5-day span:

- StatsForecast AutoETS / Theta
- prediction intervals where available
- robust linear fallback only if the library runtime fails
- change-point detection after >= 12 daily observations

### Tier 2 — neural

>= 30 daily observations and >= 21-day span:

- NeuralForecast NHITS first
- later evaluate NBEATSx / TFT / PatchTST with backtests
- exogenous variables only when their provenance is real
- never enable a transformer merely because it is available

### Model selection

Backtest multiple models. Promote a neural model only when it beats the statistical baseline on rolling-origin validation and remains stable under data perturbation.

---

## Causal layer

Correlation is not allowed to become causal language automatically.

Use a DoWhy-compatible process only when sufficient history/exogenous series exist:

1. declare a causal DAG
2. identify estimand
3. estimate effect
4. placebo/refutation tests
5. sensitivity analysis
6. reject causal language if refutation fails

Candidate exogenous variables may include only properly sourced series, e.g. verified price change, merchant availability, season/event timing, official economic context or real advertising observations. Search-result count is not a causal variable by default.

---

## Greek market research agents

### 1. Greek Demand Researcher

Discovers Greek-language demand, intent and consideration evidence. Expands queries with canonical aliases and Greek natural-language expressions.

### 2. Pain & Jobs-to-be-Done Analyst

Clusters desired outcomes, constraints, objections, frustrations, switching triggers and alternative requests.

### 3. Supply Intelligence Analyst

Measures solution coverage without contaminating Demand.

### 4. Temporal Forecast Scientist

Runs model readiness, change-point analysis, statistical backtests and neural forecasts.

### 5. Causal Skeptic

Attempts to disprove causal explanations and separates correlation from intervention evidence.

### 6. Evidence Auditor

Verifies provenance, freshness, entity/category binding, source diversity and contradictions.

### 7. Business Intelligence Storyteller

Transforms the evidence into an executive analytical narrative without inventing missing values.

### 8. UI / Visualization Critic

Ensures visual hierarchy, accessibility, chart-question fit and no deceptive visual encoding.

---

## Presentation engine — Kimi-inspired, not slide imitation

Each analytical scene follows:

```text
QUESTION
  ↓
HEADLINE FINDING
  ↓
PRIMARY VISUAL
  ↓
WHAT DRIVES IT
  ↓
EVIDENCE / UNCERTAINTY
  ↓
SO WHAT?
  ↓
ACTION / NEXT TEST
```

### Demand workspace scenes

1. **Executive Thesis** — strongest defensible Greek-market finding.
2. **Demand Anatomy** — decompose evidence, pain, commercial intent and confidence.
3. **Demand × Supply Regime Map** — no demand contamination by supply.
4. **Pain / Jobs-to-be-Done Map** — semantic clusters and constraints.
5. **Market Structure** — competition, trusted supply, fragmentation, concentration.
6. **Temporal Regime** — history, change points, model readiness and forecasts.
7. **Evidence Graph** — explain which sources/pains/merchants support the thesis.
8. **Causal / Counterfactual Lab** — only if readiness gates pass.
9. **Decision Board** — investigate / test / promote / wait / reject with explicit confidence.

---

## External OSS patterns adopted

- Nixtla `StatsForecast`: statistical benchmark/forecast tier.
- Nixtla `NeuralForecast`: neural time-series tier with NHITS/NBEATSx/TFT candidates.
- `ruptures`: structural/change-point detection.
- PyWhy `DoWhy`: causal identification/refutation discipline.
- Microsoft `GraphRAG`: graph-structured retrieval methodology, adapted lightweight to SocialMarket's existing relational/vector graph.
- `scikit-fuzzy`: fuzzy inference patterns; production can use explicit deterministic memberships for reproducibility.
- Vercel frontend-design + web-design-guidelines: build + audit pattern.
- BI skill patterns: KPI semantics, executive narrative, chart-question fit and drill-down.

No upstream repository is allowed to override SocialMarket evidence semantics or data governance.

---

## Autonomous operating loop

```text
collect evidence
→ normalize
→ relevance gate
→ skeptic audit
→ semantic cluster
→ embed
→ update observed category market
→ update supply model
→ temporal readiness check
→ statistical forecast if eligible
→ neural candidate/backtest if eligible
→ causal readiness/refutation if eligible
→ narrative synthesis
→ visualization QA
→ publish analytical snapshot
```

A human may intervene by overriding scope, excluding evidence, requesting a rerun, or marking a hypothesis for review. The autonomous path remains fail-closed when data quality is insufficient.
