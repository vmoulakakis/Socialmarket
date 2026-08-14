# SocialMarket AI — Greek Hidden Opportunity Engine

Agentic market-intelligence and content-decision system for Greece.

## Ownership boundary

SocialMarket AI is the **brain and source of truth**. It owns merchant/category/product intelligence, evidence, AI audit, pain-gap discovery, semantic search, opportunity ranking, content generation, approval and canonical publishing intent.

SocialMarket stops at:

```text
Approved Publishing Intent → publish.outbox
```

The separate `vmoulakakis/socialscheduler` repository is the **execution plane**. It reads the same Supabase database, claims approved outbox jobs, sends them through Buffer, reconciles provider state and writes execution status back. It must not duplicate products, merchants, content or campaign intelligence.

See `docs/decisions/ADR-006-socialmarket-socialscheduler-boundary.md`.

## Shared database

Production Supabase project:

```text
rpfadpdnnxequgvdcfoq
```

Silent fallback to older Supabase projects is forbidden.

## Core business gates

- Active/eligible offer
- Valid tracking URL and usable product image
- High Greek demand + meaningful pain
- Low or defensible competition
- Merchant trust/risk gate
- Opportunity score and confidence remain separate
- Only audited evidence is eligible for validated semantic search

## Stack

- Next.js / Vercel admin
- Supabase Postgres + pgvector + Auth + Storage
- SearXNG + Trafilatura + Playwright/yt-dlp fallbacks
- GitHub Actions market-intelligence workers
- Supabase-native semantic embeddings
- Skill-driven agent roles under `agents/skills/`

## Publishing rule

This repository must not contain Buffer execution credentials, provider account-connection UI, independent publishing queues, publishing retries or provider reconciliation logic. Those belong to SocialScheduler.

No secret belongs in GitHub.
