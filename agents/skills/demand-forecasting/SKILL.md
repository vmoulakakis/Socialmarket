---
name: demand-forecasting
description: Forecast canonical category/product opportunity while preserving observed, modeled and hypothetical data boundaries.
---
# Demand Forecasting

## Mission
Interpret numeric/statistical signals for canonical SocialMarket categories, subcategories and validated products. LLM reasoning may explain drivers and scenarios but must never manufacture historical demand or future conversions.

## Semantic prerequisites
- Forecast only canonical `product_taxonomy` categories/subcategories.
- Never forecast navigation labels, brands, cities, languages, campaign names or service-policy labels as market categories.
- Seasonal themes such as Back To School may be forecast as `demand_theme`, separately from taxonomy.
- Product forecasts require canonical taxonomy plus validated product/pain evidence.

## Data states
Every metric must be labeled conceptually as one of:
- `observed`: directly collected/ingested.
- `derived`: deterministic calculation from observed facts.
- `modeled`: statistical forecast with method/interval.
- `scenario`: explicit user/agent assumption such as clicks/day or CPC.
- `missing`: not collected; never replace with zero unless zero was actually observed.

## Required horizons
- 7–14 day nowcast
- 28–30 day short term
- 56 day campaign horizon
- 84–90 day seasonal view

## Affiliate conversion forecasting
When program CVR/EPC/approval exists, use it only as an observed merchant-program baseline. Product conversion forecasts must report assumptions and confidence. First-party SocialMarket CVR/EPC overrides network baselines only when enough first-party observations exist.

## Rules
- Show prediction/scenario interval and confidence.
- Downgrade confidence on sparse, stale, contaminated or regime-changing evidence.
- Compare product signal with canonical parent category/subcategory and active demand themes.
- Prefer direction, interval and decision thresholds over fake point precision.
- Never invent search volume, CTR, CPC, AOV, revenue or conversion counts.

## Output
JSON: entity_type, canonical_category, canonical_subcategory, horizon_days, data_state, direction, low, base, high, model_or_scenario_basis, confidence, observed_inputs[], assumptions[], missing_inputs[], warnings[].
