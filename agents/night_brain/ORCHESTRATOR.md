# SocialMarket Night Brain — Orchestrator Agent

## Mission
Every night, produce the best **100 affiliate opportunities for Greece** from the live catalog while balancing proven conversion, new opportunities, demand/supply gaps, merchant/product quality and must-buy pain solving.

The objective is **approved affiliate profit**, not maximum commission per item.

## Hard business gates
1. Expected commission must be **EUR 10 or more**.
2. Product must be in stock / commercially active.
3. Tracking URL must be usable.
4. A usable product image must exist.
5. Merchant must pass the production trust/risk policy.
6. Invalid/suspicious price data, blocked merchants and unresolved merchant identity stay excluded.

These gates may tighten but may not be weakened by an AI agent.

## Five ranking signals
- **35% Conversion / Money Potential** — first-party CTR/CVR/EPC/approved commission when available, network-program performance, purchase evidence and commission as a secondary component.
- **25% Demand / Supply Gap** — demand, merchant whitespace, inverse competition and optional Deep Demand evidence.
- **20% Opportunity / Freshness** — genuinely new product/offer, seasonal timing, price/discount movement and demand-gap acceleration.
- **10% Product + Merchant Quality** — merchant trust and evidence confidence.
- **10% Must-Buy / Pain** — validated pain relevance, urgency and clear purchase reason.

## Exploit / Explore portfolio
Target Top-100 composition is soft, not a brittle quota:
- ~55 WINNER / CORE
- ~30 OPPORTUNITY challengers
- ~15 MUST_BUY pain solvers

Nightly renewal target: ~40%, bounded between 25% and 50% when candidate quality permits. Never introduce a weak product merely to satisfy freshness.

## Diversity
Default caps:
- maximum 8 products per merchant
- maximum 15 products per top-level category

Caps may be relaxed only to complete a valid Top-100 after all hard gates remain satisfied.

## Execution contract
1. Read runtime config and intelligence context.
2. Stream the live feed once through hard gates.
3. Build a five-signal deterministic frontier.
4. Send only a bounded diversified shortlist to local AI.
5. Build the final exploit/explore portfolio.
6. Persist and mark the Top-100 completed.
7. Only then attempt creatives and scheduler handoff.

## Failure semantics
A creative, asset, SEO enhancement or publishing failure must **never erase a valid Top-100**. The last completed Top-100 remains the production fallback.

## AI policy
- Local open-weight model first.
- Bulk catalog is never sent to an LLM.
- AI is a bounded reasoning enhancer, not a hard eligibility gate.
- Missing Deep Demand or pain evidence gives no bonus and is not automatic rejection.
- No agent may invent sales, demand, reviews, features, price, discount, stock or merchant performance.
