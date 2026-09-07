# SocialMarket Autonomous Commerce OS

## Purpose
One prompt in; one governed execution graph out. SocialMarket is the control plane for all commerce sites, affiliate funnels, intelligence pipelines, growth operations and deployments.

## Source-of-truth hierarchy
1. GitHub is the source of truth for production code.
2. Supabase is the operational memory for runs, steps, evidence, site state and outcomes.
3. Vercel is the primary runtime/deployment target.
4. SocialMarket canonical Demand/Product Intelligence remains the source of truth for market claims.
5. AFFINITY is the canonical site/page intelligence engine.
6. Capability agents are reusable specialists; site-specific agents are prohibited unless a hard integration boundary requires one.

## Prompt contract
Examples:
- `Check all my sites and fix what is broken.`
- `Find a high-opportunity product for Greece and build the funnel.`
- `Improve what is underperforming.`
- `Audit all affiliate links and repair tracking problems.`

The API entry point is `POST /api/orchestrator` with `{ "prompt": "..." }`.

## Runtime sequence
REQUESTED -> UNDERSTOOD -> PLANNED -> EXECUTING -> VERIFYING -> COMPLETE.
Failure path: FAILED -> DIAGNOSE -> REPLAN/RETRY/ROLLBACK.
High-risk path: PLANNED/EXECUTING -> WAITING_APPROVAL -> EXECUTING.

## Capability domains
- intelligence: demand, competition, pain-gap, product ranking
- build: AFFINITY architecture, code change, content
- deploy: preview and production promotion
- operations: health, audit, repair, rollback
- growth: SEO/CRO experiments and measurement
- outreach/finance/destructive operations: approval-gated

## Hard rules
- deterministic gates before LLM calls;
- no invented demand, price, commission, merchant or tracking state;
- production changes require verification and a rollback path;
- public funnels must be indexable unless explicitly configured otherwise;
- orphan production deployments are migration debt, not an acceptable steady state;
- bulk external outreach, paid spend, purchases and destructive actions require explicit approval;
- site performance evidence never overwrites canonical market intelligence;
- insufficient evidence returns WITHHELD rather than fabricated confidence.

## Site registry
`data/site-registry.json` is the bootstrap registry. Runtime state belongs in Supabase `site_registry`. Every production property should eventually have Git linkage, deployment linkage, analytics linkage, affiliate-program linkage and a current health snapshot.

## Self-healing contract
Detect -> Diagnose -> Plan bounded repair -> Test -> Preview -> Verify -> Promote -> Verify production -> Measure -> Persist. If verification fails, rollback/replan instead of silently continuing.

## Current migration debt discovered 2026-09-07
- Beatbot Sora 70: public deployment is reachable but currently has noindex and no verified affiliate tracking URL; source is not Git-linked.
- AffiliateOS: production deploy is reachable but `/api/refresh` has repeated 60-second runtime timeouts; source is not Git-linked.
- myaffiliate: production deployment is broken because Vercel expects a `public` output directory; source is not Git-linked.
- SocialMarket and `/eu-local-day` are reachable and are the first properties under the new control plane.

## Definition of done for the platform
A site is not `managed=true` until code repo, runtime project, production URL, analytics, affiliate tracking, health checks and rollback path are all registered. The target steady state is zero orphan production sites and one orchestration control plane.
