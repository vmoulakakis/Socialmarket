---
name: demand-evidence
description: Collect and normalize auditable demand signals for Greece.
---
# Demand Evidence

## Mission
Build current-demand evidence from feed behavior, search/trend data, retail signals and observed market activity.

## Signal priority
1. First-party feed signals such as times_bought, stock, price and offer changes.
2. Stable Greek search/trend signals.
3. Retailer/marketplace presence and changes.
4. Editorial/social signals only as weak supporting evidence.

## Guardrails
- Search-result count is not demand.
- Social buzz is not sales.
- Every signal needs source, observed_at, normalized_score and confidence.
- Conflicting evidence must remain visible.

## Output
JSON: signal_type, source, raw_value, normalized_score, direction, evidence, confidence.
