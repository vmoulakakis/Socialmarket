---
name: back-to-school-gap
description: Discover high-demand, low-competition, high-quality Greek Back-to-School products that are difficult to buy offline and have defensible real discounts.
---
# Greek Back-to-School Hidden Gap

## Mission
Find Back-to-School 2026 products for Greece that solve a validated buyer pain better than the mass-retail baseline. Prefer online-first or niche merchants and products that are difficult to find in Greek physical stores.

## Hard promotion gates
- final selling price strictly greater than EUR 50
- current active/in-stock status verified from a live source
- usable product image and valid affiliate/deeplink route
- sufficient promotion runway; stale feed `valid_to` is not accepted as live availability evidence
- high-quality evidence must survive final audit
- no travel/tourism/luggage products unless a future campaign explicitly changes scope

### Discovery versus promotion validity
A stale or missing feed `valid_to` must not automatically eliminate a discovery candidate. The July 2026 Linkwise snapshot proved that this can remove almost the entire useful universe. Discovery may retain candidates with uncertain/short feed validity, but **promotion requires a fresh live stock/availability check** and adequate campaign runway.

## Major-retailer policy
Treat Jumbo, Public, Plaisio, Kotsovolos, e-shop.gr, Skroutz, BestPrice, IKEA and JYSK primarily as market/supply benchmarks, not preferred source merchants.
- Target portfolio: >=90% of selected products from outside major chains.
- Maximum major-retailer exceptions: 10% of final products.
- A major-retailer exception requires an exceptional SKU-level reason: unusually strong verified deal, online-only/rare SKU, high pain fit, and low physical availability.

## Demand gate
`high_demand` requires at least two independent, defensible demand signals. Preferred evidence:
1. Greek pain/category demand demonstrated by product engagement, verified reviews, ownership/Q&A activity, search/ranking evidence or repeated market activity.
2. Exact-product or close product-family review/ranking evidence from independent or authenticated retailer sources.
3. Linkwise `times_bought`, stock movement or offer-change evidence **when populated and credible**.

The July 2026 Linkwise snapshot contains almost no usable BTS `times_bought` evidence; therefore missing/zero `times_bought` is **not evidence of low demand** and is not a mandatory gate. Merchant EPC or affiliate conversion rate is NOT consumer product demand and may only be used as a commercial/merchant signal.

## Competition and offline-scarcity gate
Low competition is evaluated at the pain/feature-combination and exact SKU level, not only at broad category level.
Measure:
- major-chain presence
- number of meaningful Greek sellers
- exact/near-exact SKU duplication
- marketplace seller breadth
- retailer/category saturation
- physical store pickup/branch/showroom evidence
- dominant brands and promoted-offer duplication

Default automated winner limits:
- no exact major-retailer presence
- no verified physical-store pickup for the exact SKU
- <=4 meaningful Greek sellers
- offline-scarcity score >=70/100

A rare product with weak demand is not an opportunity. A popular commodity with wide Greek availability is not a hidden gap.

## Pain-first process
1. Build Greek mass-retail baseline.
2. Extract and validate buyer pains from independent evidence.
3. Convert each pain into measurable product requirements.
4. Embed pain descriptions, Greek-retail products and affiliate candidate products.
5. Retrieve products with high pain similarity and low mass-retail coverage.
6. Verify claimed product features deterministically/source-first.
7. Audit demand, competition, quality, merchant trust, delivery, warranty and discount.
8. Run contradiction/evidence audit before promotion.

## Deep-learning gap analysis
Use BGE-M3 embeddings for multilingual semantic retrieval. Use density clustering (HDBSCAN when practical) to surface repeated pains/product-solution clusters that keyword rules miss. Semantic similarity is discovery only; it never substitutes for feature or market evidence.

Conceptual novelty signal:
`solution_novelty = pain_similarity - mass_retail_similarity`

## True-deal policy
Never assume the Linkwise/raw `discount` field is a percentage. Some merchant feeds provide an **absolute EUR discount amount**. Whenever `price` and `full_price` are available, compute:

`verified_discount_pct = (full_price - price) / full_price * 100`

Then compare current price against, when available:
- merchant reference/full price
- recent/30-day low
- exact-SKU prices in Greece
- comparable peer-group median
- cross-market prices as a sanity check, not as the sole Greek deal benchmark
- shipping-inclusive landed cost

A nominal crossed-out discount is downgraded or rejected when the current price is not materially better than the realistic Greek market price. Regional EU promotions may differ; do not claim "best price" without Greek-market evidence.

## Quality gate
Quality is a gate, not a commission-weighted preference. Evidence may include verified specifications, materials/build, warranty, independent or authenticated product reviews, defect/return signals, brand/manufacturer credibility and merchant reliability. Merchant ratings must not be confused with product ratings. Generic return-policy text is not defect evidence. Unknown/private-label products require stronger evidence.

## BTS Hidden Product Score
Use only after hard gates and evidence checks:
- 25% product quality
- 20% validated pain fit
- 20% offline scarcity
- 15% true deal strength
- 10% Greek demand
- 7% merchant trust
- 3% affiliate economics

Apply hard penalties/kills for major-chain ubiquity, high seller saturation, commodity duplication, fake discounts, slow/expensive delivery, weak warranty, high return friction, poor evidence or strong counter-evidence.

## Portfolio constraints
Default final campaign target: 20 products.
- price > EUR 50 for every product
- max 3 products per merchant
- max 4 products per pain cluster
- max 2 major-retailer exceptions
- >=90% from niche/online-first/non-major merchants

## Output
For every final product return structured evidence for:
product, merchant, tracking_url, price, verified_discount, target_segment, validated_pain, pain_evidence, Greek_demand_evidence, exact_product_demand_evidence, major-retailer coverage, Greek seller breadth, physical_availability_evidence, offline_scarcity, product_fit, quality, merchant_trust, competition, BTS_hidden_product_score, confidence, objections, and creative_angle.
