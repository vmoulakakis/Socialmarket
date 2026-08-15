---
name: deep-demand-intelligence
description: Build, audit, or explain SocialMarket Greek demand intelligence using evidence-first RAG, fuzzy whitespace, temporal forecasting, supply separation, and causal skepticism.
---

# Deep Demand Intelligence

Use this skill whenever work touches Demand Intelligence, Greek market research, opportunity analysis, demand forecasting, supply/demand correlation, pain gaps or market explanations.

## Non-negotiable semantics

1. Existing production Demand, Competition, Pain, Confidence and Opportunity metrics are observed/derived source facts. Never silently replace them.
2. Demand and Supply are separate dimensions. High supply may reduce whitespace, but it may not reduce the observed Demand Index.
3. Missing data remains missing.
4. Forecasts are forecasts of an evidence-derived index, not search volume, market share or sales.
5. Correlation cannot be described as causation unless causal identification + refutation pass.
6. A neural model may run only after history-readiness and backtest gates pass.
7. Every claim must resolve to source evidence, a deterministic transform, a model output, or an explicit inference label.

## Analytical stack

### Observed layer

Read canonical semantic market rows, normalized evidence, validated pain clusters, merchant supply, product/offer truth and historical snapshots.

### Hybrid RAG layer

Retrieve:
- nearest semantic pain clusters
- supporting evidence rows
- related taxonomy nodes
- merchant solution coverage
- product solutions when validated
- contradictions and rejected evidence

Prefer the existing pgvector store. Add graph traversal only to improve context, not to manufacture signal strength.

### Fuzzy layer

Use fuzzy logic for solution-whitespace inference when hard thresholds would lose nuance.

Inputs may include:
- Demand Index
- Pain Gap
- Supply Coverage
- Competition
- Confidence

Always output activated rules and certainty.

### Temporal layer

- <8 daily observations: descriptive only
- >=8 observations and >=5-day span: statistical forecasting
- >=12 observations: change-point analysis
- >=30 observations and >=21-day span: neural candidate models

Backtest before selecting a model. Statistical baselines must remain available even when neural models exist.

### Causal layer

Use a DoWhy-compatible process only when exogenous data exists and history is sufficient. Require an explicit DAG, estimand, refutation and sensitivity test before using causal language.

## Demand research questions

For each category/subcategory answer:

1. What evidence indicates real Greek consideration or purchase intent?
2. What pain / desired outcome repeats across sources?
3. Is the signal broad or concentrated in one source/domain?
4. How fresh is it?
5. What supply exists and how trusted/diverse is it?
6. Is the market crowded, fragmented or under-served?
7. What changed versus prior observations?
8. What can be forecast with the available history?
9. What alternative explanation could invalidate the thesis?
10. What is the next cheapest test that would reduce uncertainty?

## Output contract

Return a structured narrative:

- `thesis`
- `observed_facts`
- `latent_demand_hypotheses`
- `supply_structure`
- `demand_supply_gap`
- `temporal_regime`
- `forecast`
- `causal_status`
- `contradictions`
- `confidence`
- `next_evidence_to_collect`
- `recommended_action`

Use labels: OBSERVED / DERIVED / INFERRED / FORECASTED / CAUSAL_CANDIDATE / UNAVAILABLE.
