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
The canonical order is deterministic/local, then GitHub Models included quota,
then DeepSeek V4, and finally OpenAI as the last resort. DeepSeek V4 Flash runs
without thinking for routine bounded work, Flash/high for ambiguous audits, and
V4 Pro/max only for hard skeptic, contradiction, forecast or recovery cases.
Direct DeepSeek/OpenAI routes remain fail-closed until cost is explicitly
approved and a database budget reservation succeeds. OpenAI fallback uses the
cost-sensitive GPT-5.6 Luna for ordinary recovery and GPT-5.6 Sol only for the
highest-complexity unresolved cases. RAG constrains every model to supplied
evidence IDs; no model may invent commission, demand, merchant identity, pain
IDs or theme IDs. Secrets are injected at runtime and never committed.

## MyAgenticTeam control plane
MyAgenticTeam mirrors the production pipeline as a bounded four-role graph; it
does not replace deterministic workers or Supabase truth:

1. Demand Beacon Analyst — accepts source IDs and taxonomy only; large Greek
   commerce sites are `demand_beacon`, never `competitor`.
2. Pain Gap Validator — accepts extracted first-person evidence IDs; catalogue
   presence and SERP snippets cannot prove pain.
3. Forecast Skeptic — accepts daily demand-index observations; returns
   WITHHELD or conservative/base/upside index scenarios with assumptions.
4. Affiliate Decision Orchestrator — accepts validated gap/forecast/product IDs
   and applies commission, merchant, evidence, duplication and publish gates.

Handoffs contain IDs, bounded summaries and confidence—not full pages or chat
history. The control-plane credit limit is zero and no schedule is active until
the owner explicitly approves billable execution. Production automation remains
the tested GitHub/Supabase local-first path.

## Token and cost contract
- deterministic filters, hashes, arithmetic and forecasts run before any LLM;
- local Qwen is first and capped at 360 output tokens per bounded call;
- no more than 8 free semantic calls per scoped run (default workflow: 8);
- deduplicated evidence packets contain only the minimum fields required;
- paid remote inference is fail-closed (`ENABLE_PAID_REMOTE=0`);
- every model call records route, model, token counts when available and cost;
- insufficient evidence returns WITHHELD and never triggers a larger model loop.
