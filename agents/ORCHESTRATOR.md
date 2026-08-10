# SocialMarket AI Orchestrator

State flow:
1. ingest_and_normalize
2. category_discovery
3. subcategory_discovery
4. collect_demand_evidence
5. measure_competition_gap
6. run_statistical_forecast
7. evaluate_purchase_friction
8. calculate_higo
9. evidence_audit
10. queue_creative_if_approved

Hard gates always execute before expensive model calls. Forecast numbers come from statistical tooling, never from the LLM. The orchestrator must stop on insufficient evidence rather than manufacture confidence.

Model routing: DeepSeek primary; OpenRouter `openrouter/free` only on provider failure. Secrets are injected at runtime and never committed.