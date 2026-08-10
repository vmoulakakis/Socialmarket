---
name: high-ticket-product-selection
description: Apply deterministic eligibility gates and market kill-switches before expensive AI analysis.
---
# High-Ticket Product Selection

## Feed hard gates
A product is eligible for the market-intelligence universe only when all are true:
- price >= EUR 150
- `valid_to` exists and is strictly more than 20 calendar days from the current date in `Europe/Athens`
- active / not explicitly out of stock
- valid tracking URL
- usable source image
- not travel, tourism, luggage, baggage or travel-accessory related

The validity rule is rolling and must be evaluated again on every market run, not only at import time.

## Validity runway
Products that survive the >20-day gate receive a runway score:
- 21–30 days: 40
- 31–60 days: 65
- 61–90 days: 85
- 91+ days: 100

Runway contributes to HIGO but never overrides a hard gate.

## Competition kill-switch
High market saturation is an exclusion, not merely a negative ranking weight.
- Seller Competition >= configured kill threshold => DROP every product in that market scope.
- Ad Pressure Proxy >= configured threshold with sufficient evidence confidence => DROP.
- Never label the proxy as directly observed paid-ad volume. Store provenance and confidence.
- Price, discount, demand and forecast cannot override a competition kill.

Seller pressure combines merchant breadth, product density, brand breadth and, when available, external commercial-domain evidence.

## Purchase friction
After the feed and market gates, evaluate whether the product can be bought confidently online. High fit/touch/sensory categories require an exceptional verified discount to remain eligible.

## Ranking principle
Only survivors receive demand, forecast, attention-gap, evidence-quality, offer-reliability, validity-runway and creative-potential scoring.

## Decision thresholds
- <60 drop
- 60–74 monitor
- 75–84 watchlist
- 85–91 create creative
- >=92 priority

Confidence is separate from HIGO. High score with weak confidence must not auto-promote.
