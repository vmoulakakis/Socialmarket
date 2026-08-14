# SocialMarket AI — Greek Hidden Opportunity Engine

SocialMarket is the **single source of truth for brands, market intelligence, approved content and publishing intent**. It discovers opportunities; it does not own Buffer execution.

## Core flow

1. ingest and normalize market/product data
2. category + subcategory discovery
3. collect demand evidence
4. measure competition gap
5. run statistical forecasting
6. evaluate purchase friction
7. calculate HIGO opportunity score
8. evidence / contradiction audit
9. select the best brand/site fit
10. create and approve content + creative
11. write one canonical content item and per-platform executions to `publishing_outbox`
12. SocialScheduler claims approved outbox jobs and owns Buffer scheduling/publishing
13. execution status is acknowledged back into SocialMarket

## Ownership boundary

### SocialMarket owns
- Brands & Sites registry
- products, merchants, niches and market evidence
- forecasting and HIGO scoring
- campaign/content strategy
- creative approval
- canonical `content_items`
- `publishing_outbox`
- published/failed status as returned by the executor

### SocialScheduler owns
- Buffer authentication
- Facebook / Instagram / TikTok channel routing
- rolling queue capacity
- exact scheduling
- media readiness checks
- deduplication
- publish/retry safety
- Buffer status reconciliation

**SocialScheduler must not invent independent campaigns or maintain a second production content backlog.**

## Business gates
- Price >= EUR 150 before AI scoring for high-ticket product discovery
- Active/in-stock offer
- Valid tracking URL and usable product image
- High demand + low attention/commercial saturation
- Purchase-friction gate, relaxed only by verified strong discount
- Opportunity score and confidence are separate

## Stack
- Next.js / Vercel admin
- Supabase Postgres + pgvector + Auth + Storage
- Supabase `publishing-outbox` Edge Function as the executor handoff API
- GitHub Actions OIDC authentication from `vmoulakakis/socialscheduler` (no shared secret in either repo)
- DeepSeek primary, OpenRouter free failover
- GitHub Actions market-intelligence workers
- StatsForecast numeric forecasting
- Skill-driven agent roles under `agents/skills/`

No secret belongs in GitHub.
