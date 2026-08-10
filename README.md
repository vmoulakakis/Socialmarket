# SocialMarket AI — Greek Hidden Opportunity Engine

Agentic market-intelligence system for Greece. Phase 1: market research, taxonomy, demand–competition gap, statistical forecasting, HIGO scoring, evidence audit and private-admin workflow.

## Business gates
- Price >= EUR 150 before AI scoring
- Active/in-stock offer
- Valid tracking URL and usable product image
- High demand + low attention/commercial saturation
- Purchase-friction gate, relaxed only by verified strong discount
- Opportunity score and confidence are separate

## Stack
- Next.js / Vercel admin
- Supabase Postgres + pgvector + Auth + Storage
- DeepSeek primary, OpenRouter free failover
- GitHub Actions market-intelligence workers
- StatsForecast numeric forecasting
- Skill-driven agent roles under `agents/skills/`

No secret belongs in GitHub.