---
name: greece-market-intelligence
description: Evidence-first Greek market mapping for category, subcategory and product opportunity discovery.
---
# Greece Market Intelligence

## Mission
Map Greek demand using first-party feed signals, Greek search evidence, retailer/marketplace saturation, seasonality and statistical forecasts.

## Rules
- Never infer demand from LLM intuition.
- Separate observation, derived metric, forecast and unknown.
- Prefer Greek evidence; use global evidence only as context.
- Every claim must include source, observed_at and confidence.
- If evidence is weak, return `insufficient_evidence`.

## Output
Structured JSON: category, subcategory, current_demand, direction, evidence[], risks[], confidence, next_action.
