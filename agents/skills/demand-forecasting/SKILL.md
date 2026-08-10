---
name: demand-forecasting
description: Interpret statistical forecasts without inventing future demand.
---
# Demand Forecasting

## Mission
Use numeric outputs from StatsForecast models; LLM reasoning may interpret but never manufacture the forecast.

## Required horizons
- 7–14 day nowcast
- 28 day short term
- 56 day campaign horizon
- 84 day seasonal view

## Rules
- Show prediction interval and confidence.
- Downgrade confidence on sparse or regime-changing series.
- Compare product signal with parent category/subcategory trend.
- Prefer direction and interval over fake point precision.

## Output
JSON: horizon_days, direction, growth_low, growth_mid, growth_high, model, confidence, warnings[].
