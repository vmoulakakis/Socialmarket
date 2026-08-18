# Night Brain Skills + Tools

## Core skills

### 1. Catalog Streaming + Immutable Gates
Tool: `night_brain_gate_tools.stage_feed`

Purpose: stage the multi-million-record Linkwise catalog at the immutable EUR 10 economic floor without sending bulk data to a generative model.

Hard checks:
- EUR currency
- not explicitly out of stock
- merchant identity resolved deterministically
- tracking URL decoded and destination domain matched to merchant official domain
- explicit evidenced merchant block only
- price/data-integrity quarantine

Missing main image is **not** a bulk reject.

### 2. Business Gate Agent
Tools: local provider-neutral AI Task Router + runtime config.

Runs once per nightly portfolio, not once per product.

Purpose: decide whether current unit economics justify a promotion commission floor above EUR 10.

Inputs include aggregated first-party CTR/CVR/EPC/approved commission, known media/content cost and observed program baselines.

Boundaries:
- never below EUR 10
- default EUR 10
- runtime-config maximum floor
- cannot raise merely to favor high commission
- deterministic candidate-pool safety can relax an over-tight decision back to EUR 10

### 3. Commercial Scoring
Tools: deterministic Python + runtime config.

Signals:
- conversion / money potential
- demand / supply gap
- opportunity / freshness
- product + merchant quality
- must-buy / pain

### 4. Demand / Supply Intelligence
Tools: Supabase decision context, merchant intelligence, optional Deep Demand.

Deep Demand is additive context, never a mandatory gate.

Merchant dominance/feed concentration are diversification evidence, not hard exclusions.

### 5. First-Party Learning
Tools: `ops.affiliate_performance_daily` via ranking decision context.

Use observed CTR, CVR, EPC and approved commission with sample-size confidence. Observed data outranks modeled evidence.

### 6. Bounded Landing-Page Enrichment
Tool: `night_brain_gate_tools.recover_shortlist_images`.

Only shortlisted candidates missing a usable feed image are enriched.

Recovery order:
1. feed `extra_images`
2. validated merchant destination page
3. `og:image` / `twitter:image` / equivalent meta image

No multi-million-page crawl is allowed. A usable image is required before final AI/portfolio entry.

### 7. Local AI Opportunity Reasoning
Tool: provider-neutral AI Task Router backed by local Ollama / Qwen.

Only a bounded diversified candidate frontier is exposed. No paid provider is required for normal production.

### 8. Portfolio Optimization
Tool: deterministic exploit/explore selector.

Controls: Winners/Core, Opportunities, Must-Buy, merchant caps, category caps, renewal bounds and quality-ranked fallback.

### 9. SEO
Tool: deterministic factual SEO.

SEO never invents product facts and cannot block a completed ranking.

### 10. Creative Generation
Tools: local AI creative agent, independent creative audit, deterministic renderer, Supabase Storage, creative gateway.

Creative work runs only after Top-100 persistence and completion.

### 11. Publishing / Outbox
Tools: `content.items`, `publish.outbox`, `publish.delivery_history`, SocialScheduler refill/rebalance functions and provider workers.

The scheduler is responsible for exposure/fatigue and timing; ranking is responsible for commercial opportunity.

### 12. Observability
Tools: `intel.product_ranking_runs`, run metadata, GitHub Actions artifacts and Supabase operational tables.

Every run records candidate counts, effective promotion commission floor, image recovery statistics, strategy segments, renewal percentage, model/cache usage and downstream degradation.

## Merchant block semantics
A merchant may be hard-blocked only with explicit auditable evidence. Controlled reasons include owner/manual block, compliance/legal, fraud/abuse, inactive merchant/program or repeated validated tracking-integrity failure.

Low trust, dominance or high competition affect quality/diversity but are not themselves block reasons.

## Non-negotiable tool boundaries
- GitHub runner: heavy feed streaming + local Ollama compute + bounded landing-page recovery.
- Supabase: source of truth, runtime policy, durable ranking, first-party learning, merchant block evidence, content/outbox state.
- LLM: bounded business/reasoning tasks only; never bulk catalog ingestion.
- Paid inference: optional escalation only if explicitly enabled later; not required by Night Brain.
