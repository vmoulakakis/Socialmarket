# SocialMarket AI — Greek Market Decision Intelligence

[![CI](https://github.com/vmoulakakis/Socialmarket/actions/workflows/ci.yml/badge.svg)](https://github.com/vmoulakakis/Socialmarket/actions/workflows/ci.yml)

> Agentic market-intelligence system that converts noisy public evidence into audited Greek-market opportunities and canonical publishing intent.

**Portfolio:** https://dealora-ai.com/portfolio  
**Admin:** private by design

## What it solves

Affiliate and product systems usually start with inventory and commission. SocialMarket starts earlier: **is there a real problem, real demand, trustworthy evidence and a defensible opportunity?**

```text
Merchant / category / product universe
                ↓
Public-web + first-party evidence
                ↓
Identity + provenance normalization
                ↓
Demand / competition / pain signals
                ↓
Skeptical AI audit
                ↓
Semantic clusters + opportunity ranking
                ↓
Canonical approved content / publishing intent
                ↓
SocialScheduler execution plane
```

## Architectural thesis

SocialMarket is the **brain and source of truth**. It owns merchant/category/product intelligence, evidence, AI audit, pain-gap discovery, semantic search, opportunity ranking, content generation, approval and canonical publishing intent.

It stops at:

```text
Approved Publishing Intent → publish.outbox
```

[`vmoulakakis/socialscheduler`](https://github.com/vmoulakakis/socialscheduler) is the separate execution plane. It claims approved outbox jobs, sends them through Buffer, reconciles provider state and writes execution status back. It does not create a second content or merchant truth.

See [`docs/decisions/ADR-006-socialmarket-socialscheduler-boundary.md`](docs/decisions/ADR-006-socialmarket-socialscheduler-boundary.md).

## Core gates

A product/opportunity should not reach the trusted decision path unless it can survive the relevant gates:

- active / eligible offer
- valid tracking URL
- usable product image
- authoritative merchant identity
- Greek demand evidence
- meaningful pain / unmet need
- low or defensible competition
- merchant trust / risk checks
- skeptical evidence audit
- separate **opportunity score** and **confidence**
- only validated evidence enters trusted semantic search

## Stack

- **App:** Next.js 15 / React 19 / Vercel
- **Data:** Supabase Postgres + pgvector + Auth + Storage
- **Evidence:** SearXNG, Trafilatura, Playwright and yt-dlp fallbacks
- **Workers:** Python + GitHub Actions
- **Edge:** Supabase Deno Functions
- **AI:** model-router architecture for semantic interpretation, review and bounded escalation
- **Agents:** skill-driven roles under `agents/` and `skills/`

## Source-of-truth model

```text
Relational canonical data
        +
Normalized evidence with provenance
        +
Adversarial audit state
        +
Semantic clusters / vectors
        =
Decision-ready intelligence
```

The system deliberately avoids treating model prose as ground truth. Authoritative URLs, deterministic eligibility and source evidence outrank model inference.

## Build boundaries

The repository contains two TypeScript runtimes with different module systems:

- Next.js application code is checked by the root TypeScript configuration.
- `supabase/functions/**` is Deno code and is validated independently with `deno check` in CI.

This separation prevents the Next build from incorrectly compiling Deno `npm:` / `jsr:` imports while retaining explicit Edge Function validation.

## Security rules

- no real credential belongs in GitHub
- service-role and provider secrets remain server-side
- SocialMarket does not contain Buffer execution credentials
- public evidence collectors do not bypass login/CAPTCHA/private-account controls
- unknown metrics remain unknown rather than being invented

## Related flagship systems

| System | Role |
| --- | --- |
| [Dealora](https://dealora-ai.com) | consumer buying-decision engine |
| [AI Greece Travel](https://github.com/vmoulakakis/travel_ai) | destination-first vertical decision intelligence |
| [SocialScheduler](https://github.com/vmoulakakis/socialscheduler) | safety-first autonomous execution plane |

## Development

```bash
npm install
npm run test:design-v2
npm run test:demand-v3
npm run build
```

See [`SOCIALMARKET_MASTER_CONTEXT.md`](SOCIALMARKET_MASTER_CONTEXT.md) and [`docs/`](docs/) for deeper architecture and operational decisions.
