# SocialMarket AI Orchestrator

## Existing merchant / market intelligence — preserved
1. ingest_and_normalize merchant/program evidence
2. category_discovery
3. subcategory_discovery
4. collect_demand_evidence
5. measure_competition_gap
6. run_statistical_forecast
7. evaluate_purchase_friction
8. calculate merchant Demand Beacon + Solution Whitespace
9. evidence_audit
10. materialize validated pain evidence / vectors

The merchant pipeline is the intelligence backbone and is not rewritten by Product Intelligence.

## Product Intelligence V1 — additive consumer of merchant truth
1. stream the raw product feed; never wholesale-import it
2. resolve feed program → canonical merchant/program
3. compute effective price and deterministic expected commission
4. hard gate `expected_commission_eur >= 10`
5. exclude `demand_beacon_only` / dominant merchant offers from promotion
6. canonicalize product identity and deduplicate offers
7. retrieve validated pain/unmet-need RAG plus current seasonal/theme RAG
8. Product Research Agent: grounded title/category/description + pain/theme candidate matching
9. Product Skeptic Agent: attempt to disprove the research result
10. compute deterministic merchant-aware Product Opportunity Score
11. persist only commission-eligible product/offers and their audited intelligence
12. materialize validated product-solution semantic objects for embedding/RAG
13. only validated/high-ranking products can enter content/creative generation
14. approved content ends at `publish.outbox`; SocialScheduler owns execution after that boundary

## Hard gates
Hard gates always execute before expensive model calls. Forecast numbers, price, discount and commission arithmetic come from deterministic tooling, never from the LLM. The orchestrator must stop on insufficient evidence rather than manufacture confidence.

## Product Opportunity V1 weights
- 25% Pain-Gap Fit
- 20% Merchant Solution Whitespace / Opportunity
- 15% Greek Demand
- 12% Expected Commission (diminishing-return normalization, after the EUR10 hard gate)
- 10% Inverse Competition
- 8% Seasonal/Thematic Demand
- 5% Merchant Trust
- 3% Discount Attractiveness
- 2% Product Evidence Confidence

## Model routing
DeepSeek V4 Pro is the Product Research + Skeptic/Audit reasoning provider with thinking enabled. RAG constrains the model to supplied evidence IDs; the LLM cannot invent commission, demand, merchant identity, pain IDs or theme IDs. Secrets are injected at runtime and never committed.
