# Night Brain Skills + Tools

## Core skills

### 1. Catalog Streaming
Tool: `product_intelligence_v1.stage_feed`

Purpose: stream the multi-million-record Linkwise feed once, enforce hard commercial integrity rules and stage only eligible candidates. Bulk feed data never reaches a generative model.

### 2. Commercial Scoring
Tools: deterministic Python + runtime config.

Signals:
- conversion / money potential
- demand / supply gap
- opportunity / freshness
- product + merchant quality
- must-buy / pain

### 3. Demand / Supply Intelligence
Tools: Supabase decision context, merchant intelligence, optional Deep Demand.

Deep Demand is additive context, never a mandatory gate.

### 4. First-Party Learning
Tools: `ops.affiliate_performance_daily` via ranking decision context.

Use observed CTR, CVR, EPC and approved commission with sample-size confidence. Observed data outranks modeled evidence.

### 5. Local AI Opportunity Reasoning
Tool: provider-neutral AI Task Router backed by local Ollama / Qwen.

Only a bounded diversified candidate frontier is exposed. No paid provider is required for normal production.

### 6. Portfolio Optimization
Tool: deterministic exploit/explore selector.

Controls: Winners/Core, Opportunities, Must-Buy, merchant caps, category caps, renewal bounds and quality-ranked fallback.

### 7. SEO
Tool: deterministic factual SEO.

SEO never invents product facts and cannot block a completed ranking.

### 8. Creative Generation
Tools: local AI creative agent, independent creative audit, deterministic renderer, Supabase Storage, creative gateway.

Creative work runs only after Top-100 persistence and completion.

### 9. Publishing / Outbox
Tools: `content.items`, `publish.outbox`, `publish.delivery_history`, SocialScheduler refill/rebalance functions and provider workers.

The scheduler is responsible for exposure/fatigue and timing; ranking is responsible for commercial opportunity.

### 10. Observability
Tools: `intel.product_ranking_runs`, run metadata, GitHub Actions artifacts and Supabase operational tables.

Every run records counts, strategy segments, renewal percentage, model/cache usage and downstream degradation.

## Non-negotiable tool boundaries
- GitHub runner: heavy feed streaming + local Ollama compute.
- Supabase: source of truth, runtime policy, durable ranking, first-party learning, content/outbox state.
- LLM: bounded reasoning only; never bulk catalog ingestion.
- Paid inference: optional escalation only if explicitly enabled later; not required by Night Brain v1.
