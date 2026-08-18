# SocialMarket Night Brain — Orchestrator Agent

## Mission
Every night, produce the best **100 affiliate opportunities for Greece** from the live catalog while balancing proven conversion, new opportunities, demand/supply gaps, merchant/product quality and must-buy pain solving.

The objective is **approved affiliate profit**, not maximum commission per item.

## Gate model
Night Brain separates **immutable validity gates** from **adaptive business selectivity**.

### Immutable candidate-universe gates
1. Expected commission must be **EUR 10 or more**. EUR 10 is the owner floor and can never be lowered by AI or runtime config.
2. Currency must be EUR.
3. Product must not be explicitly out of stock.
4. Tracking URL must be structurally valid and decode to an HTTP(S) merchant destination whose domain matches the catalogued merchant official domain.
5. Merchant identity must resolve deterministically.
6. Suspicious/invalid price data is quarantined as a data-integrity issue. Positive-price validation is an implementation invariant, not a commercial ranking strategy.
7. A merchant hard block is allowed only when `promotion_mode=blocked` has an auditable block reason code and explanation.

### Adaptive commission gate
A local **Business Gate Agent** may choose a higher nightly promotion commission floor based on observed unit economics such as first-party EPC/CVR/approved commission and known acquisition/content cost.

Rules:
- `effective_promotion_floor = max(EUR 10, agent decision)`
- default is EUR 10
- the agent must not raise the floor merely to prefer high-commission products
- runtime config bounds the maximum agent floor
- if a raised floor leaves an unsafe/thin diversified candidate pool, the system safely relaxes back to EUR 10

The EUR 10 universe is retained until the bounded promotion gate is applied, so opportunistic EUR 10–EUR 14 products are not permanently lost from discovery.

## Image policy
Missing main image is **not a bulk-feed reject**.

For the bounded shortlist only:
1. use a valid feed `extra_images` URL when available;
2. otherwise fetch the already validated merchant destination page;
3. recover `og:image`, `twitter:image` or equivalent product image metadata;
4. require a usable HTTP(S) image before the candidate can enter the final AI/portfolio path.

This avoids crawling millions of landing pages while still rescuing good affiliate opportunities with incomplete feed imagery.

## Merchant blocking policy
Dominance, feed concentration, high competition or a mediocre trust score **do not by themselves block a merchant**.

They influence quality scoring, diversification and exposure caps.

A hard `blocked` merchant requires explicit evidence and one of the controlled reasons such as:
- owner/manual block
- compliance/legal issue
- fraud/abuse evidence
- affiliate program inactive
- merchant inactive
- repeated validated tracking-integrity failure

Dominant merchants remain eligible and are controlled through portfolio caps and competition signals.

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

Caps may be relaxed only to complete a valid Top-100 after all immutable gates remain satisfied.

## Execution contract
1. Read runtime config and intelligence context.
2. Stage the live feed through immutable validity gates at the EUR 10 universe floor.
3. Run the Business Gate Agent once to choose the bounded nightly promotion floor.
4. Build the five-signal deterministic frontier with diversity.
5. Recover missing imagery only on the bounded shortlist.
6. Send only the resulting bounded diversified shortlist to local AI opportunity reasoning.
7. Build the final exploit/explore portfolio.
8. Persist and mark the Top-100 completed.
9. Only then attempt creatives and scheduler handoff.

## Failure semantics
A creative, asset, SEO enhancement or publishing failure must **never erase a valid Top-100**. The last completed Top-100 remains the production fallback.

If the Business Gate Agent fails, the EUR 10 floor is used. If image recovery fails for one candidate, only that candidate is removed; the ranking engine continues with the remaining bounded frontier.

## AI policy
- Local open-weight model first.
- Bulk catalog is never sent to an LLM.
- Product-ranking AI is a bounded reasoning enhancer, not a hard eligibility gate.
- The Business Gate Agent can tighten commission selectivity but can never weaken the EUR 10 floor.
- Missing Deep Demand or pain evidence gives no bonus and is not automatic rejection.
- No agent may invent sales, demand, reviews, features, price, discount, stock or merchant performance.
