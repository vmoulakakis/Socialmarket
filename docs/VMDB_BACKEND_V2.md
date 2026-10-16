# VMDB Backend v2 — Problem-First Commerce Intelligence

## North star

VMDB starts from a Greek consumer problem, not from a product feed.

`pain -> evidence -> demand -> supply gap -> opportunity -> merchant fit -> product fit -> presentation -> distribution -> performance -> learning`

## Source of truth

Canonical Supabase project: `gqpbskssrvpfjtujwezc`.

SocialMarket owns intelligence, selection, presentation intent and the publishing outbox. SocialScheduler is execution-only and must not invent merchants, products, claims, tracking URLs or campaigns.

## Data planes

### 1. Raw evidence
Raw observations are immutable/replayable. Large source payloads belong in object storage; PostgreSQL stores source metadata, hashes, extracted facts, timestamps, confidence and lineage. Never destroy raw evidence merely because a scoring model changes.

### 2. Greek demand and pain intelligence
Agents collect multiple independent signals for demand, buyer intent, pain intensity, price/value, seller density, supply quality, scarcity, trend and seasonality. A missing signal lowers confidence; it does not become an invented neutral score.

### 3. Opportunity engine
Opportunity is an evidence-backed relationship between a problem and an underserved Greek-market need. High demand alone is insufficient. Competition is acceptable when current Greek supply is expensive, weak, slow, poorly supported or otherwise fails the problem.

### 4. Merchant 360
Merchant selection combines affiliate performance, expected commission, trust, fulfilment, warranty/returns, value, portfolio quality and problem fit. Product discovery is fail-closed and can run only for eligible merchants. Strategic selection is capped at three merchants per category and three per subcategory.

### 5. Dynamic product discovery / Product 360
Only eligible merchants are scanned. Candidate products are deduplicated, attached to a problem cluster, compared with Greek supply and scored for demand, commercial intent, gap, scarcity, solution fit, landed value, trust, conversion potential, commission and evidence confidence. Rejections remain auditable.

### 6. Social presentation intelligence
Presentation is derived from verified problem/product evidence: audience -> pain -> relatable situation -> failed current solution -> product solution -> proof -> value -> CTA. Claims must retain evidence lineage. Channel-specific hooks and creatives are experiments, not product facts.

### 7. Performance learning
Clicks, delivery, conversions, approved commission and creative outcomes feed prediction calibration. Predicted high conversion followed by sufficient low real performance must reduce confidence/rank rather than be ignored.

## Production policies

Merchant discovery policy `greece_problem_solver_v1`:
- expected commission >= EUR 15
- demand >= 70
- competition <= 45
- supply gap >= 60
- problem solving >= 70
- trust >= 65
- confidence-adjusted score >= 72
- at least 3 evidence sources
- max 3 merchants/category and max 3/subcategory

Product policy `greece_problem_solver_products_v1`:
- merchant must already be eligible
- expected commission >= EUR 15
- demand >= 72
- commercial intent >= 65
- competition <= 45
- supply gap >= 60
- Greek scarcity >= 55
- problem solving >= 72
- price/value >= 60
- trust >= 68
- conversion potential >= 65
- confidence >= 0.68

## Agent roles

The Commerce Intelligence Orchestrator coordinates Demand Scout, Pain Miner, Supply Gap Analyst, Trend Analyst, Merchant Analyst, Portfolio Scout, Product Analyst, Price/Value Analyst, Trust Analyst, Evidence Critic, Ranking Judge, Presentation Strategist and Performance Learner.

Every AI run records model/provider, prompt version, source/evidence lineage, cost/tokens where available, confidence and decision. The Critic must challenge promotion into high-confidence/high-priority states.

## Replay rule

Raw evidence and historical decisions are retained so new agents, prompts or models can replay evidence and re-rank merchants/products without reacquiring the original dataset.
