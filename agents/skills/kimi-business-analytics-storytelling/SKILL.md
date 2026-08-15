---
name: kimi-business-analytics-storytelling
description: Turn SocialMarket evidence into presentation-grade interactive business analytics scenes with strong hierarchy, visual explanation and explicit uncertainty.
---

# Kimi-style Business Analytics Storytelling

This skill borrows the presentation principle, not Kimi branding or proprietary implementation: content structure should determine the visual form.

## Scene grammar

Every scene must answer one business question:

1. **Question** — what decision are we trying to make?
2. **Headline** — one defensible finding, not a generic title.
3. **Primary visual** — the chart/diagram best suited to that question.
4. **Drivers** — 2–4 explanatory factors.
5. **Evidence** — provenance, source diversity, freshness and uncertainty.
6. **Implication** — what changes operationally?
7. **Action** — investigate, test, promote, wait, collect more data, or reject.

## Visual selection

- time movement → line/range chart
- demand vs supply → quadrant/bubble plot
- category composition → treemap only when area has honest semantics
- pain intensity across categories → heatmap
- evidence relationships → graph/Sankey only with real entity-level linkage
- funnel → funnel/waterfall only with actual stage lineage
- uncertainty → bands/error bars/confidence chips
- comparison → sorted bars/table, not decorative radar charts

## Semantic color grammar

- cyan = observed evidence
- violet = AI/inference
- emerald = validated/profitable
- amber = modeled/uncertain
- red = contradiction/risk
- gray = missing/unavailable

Never use color to imply precision that the data does not have.

## Demand presentation sequence

1. Executive market thesis
2. Demand anatomy
3. Demand × Supply regimes
4. Jobs-to-be-Done / Pain map
5. Market structure and trusted solution coverage
6. Temporal regime + change points
7. Forecast ensemble/readiness
8. Evidence graph and contradictions
9. Causal/counterfactual lab when eligible
10. Decision board

## Interaction

Prefer:
- category/subcategory drilldown
- timeframe filter
- compare mode
- evidence drawer
- confidence/provenance hover
- model toggle only when multiple models are valid
- AI explain using the exact current filtered context

Avoid:
- card wallpaper
- KPI repetition
- fake sparklines
- automatic animation that hides comparison
- huge explanatory footnotes in the main visual field

## QA

Before accepting a scene, ask:
- Can the user understand the main finding in five seconds?
- Does the visual answer a real business question?
- Can every number be traced?
- Are OBSERVED / INFERRED / FORECASTED visually distinct?
- Is missing data honestly visible?
- Does the next action follow from the evidence?
