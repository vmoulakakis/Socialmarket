# AI Backend V1 — Direct AliExpress + Agentic Demand

Backend only. No application or frontend implementation is part of this branch.

## Contract

The only deterministic promotion gate is:

```
expected_commission_eur >= 10
```

There are deliberately **no deterministic filters** for EU warehouse, seller rating,
review count, delivery time, scarcity, price gap, trust, demand, or conversion.
Those dimensions are evidence for AI agents and the final AI judge.

## Data flow

```
Demand / problem agents
  -> ai_source_queries
  -> direct SocialMarket AliExpress gateway
  -> ai_product_candidates + ai_product_offers
  -> ai_promotion_candidates_v (commission >= EUR 10 only)
  -> AI advocate / risk / commercial / judge evaluations
  -> existing commerce evidence + forecast + learning infrastructure
```

## Secrets

Set only in the SocialMarket / VMDB Supabase runtime:

- ALIEXPRESS_APP_KEY
- ALIEXPRESS_APP_SECRET
- ALIEXPRESS_TRACKING_ID
- optional ALIEXPRESS_APP_SIGNATURE
- optional ALIEXPRESS_API_URL
- optional ALIEXPRESS_SIGN_METHOD

No AliExpress secret belongs in GitHub.

## Why EU warehouse is not a gate

EU fulfillment remains strong positive evidence. A non-EU offer can still win when the
AI judges the complete landed-cost, seller, delivery, scarcity, demand and conversion
trade-off to be better. This is intentional.
