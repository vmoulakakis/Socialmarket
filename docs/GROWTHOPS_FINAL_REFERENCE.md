# GrowthOps Final Operating Reference

Status: CANONICAL
Owner: Growth Orchestrator
Control surface: SocialMarket AI Admin
Operational source of truth: Supabase
Execution adapters: GitHub, Vercel, connected ChatGPT/site-builder adapters
Implementation team model: MyAgenticTeam

## 1. Purpose
Maintain one autonomous, evidence-led GrowthOps system for the user's ACTIVE public sites. The system combines Greek demand and competition intelligence, web analytics, conversion truth, SEO, CRO, creative production, deployment, verification and learning without duplicate autonomous decision loops.

SocialMarket AI and SocialScheduler are infrastructure/control systems and are not optimization targets unless explicitly changed later.

## 2. Canonical architecture
PUBLIC SITES
-> Web analytics by site/page
-> Supabase analytics/state
<- normalized conversion CSV
<- SocialMarket Greek Demand / Competition / Pain intelligence
-> Growth Orchestrator
-> specialist agents
-> AFFINITY + creative production when pages/posts/assets are created or materially revised
-> MyAgenticTeam implementation/review/test pattern
-> GitHub / Vercel / connected ChatGPT-site adapters
-> production verification
-> Supabase experiment/learning records
-> SocialMarket AI Admin status.

## 3. Canonical intelligence inputs
### Web analytics
Use visitors, sessions, pageviews, landing pages, source/referrer/UTM, device/country, CTA clicks, affiliate clicks, funnel/key events, errors and Core Web Vitals when available.

### Conversion CSV
Uploaded conversion/commission/sales CSV is business-truth input after validation and normalization. Track freshness, coverage, last imported period and parse status.

Freshness policy:
- FRESH: full confidence.
- AGING: continue with reduced confidence.
- STALE: avoid aggressive conversion decisions.
- MISSING/INVALID: request a fresh file.

### SocialMarket Greek Demand Brain
Use the existing canonical SocialMarket Demand Intelligence, Greece Market Intelligence, Competition Gap, Demand Beacon, Solution Whitespace, pain-gap, seasonality, forecast and contradiction evidence. GrowthOps consumes these metrics and never creates a competing demand model or overwrites canonical demand/competition/pain/opportunity scores.

## 4. Single decision authority
Only the Growth Orchestrator may prioritize and promote autonomous public-site changes.

Daily control loop:
Collect -> Validate -> Map Market Intent -> Diagnose -> Prioritize -> Delegate -> Execute -> Deploy -> Verify -> Measure -> Learn.

Use site-level locks to prevent conflicting simultaneous changes.

## 5. Specialist responsibilities
- Analytics Agent: telemetry, attribution, anomalies, data quality, CSV ingestion.
- Greek Demand Intelligence Agent: binds site/page intent to canonical SocialMarket intelligence.
- SEO Black Belt Agent: technical SEO, search intent, schema, crawl/indexation, content gaps and internal linking.
- CRO Agent: CTA, funnel, affiliate CTR, UX, trust, copy and experiments.
- Content Agent: evidence-backed buyer-intent, comparison, pain-solver and problem/solution content.
- Research Agent: incremental research only when canonical evidence is uncertain or incomplete.
- Performance Agent: Core Web Vitals, mobile UX, page weight and runtime performance.
- Link & Affiliate Agent: tracking/destination integrity and affiliate-link health.
- Deployment Agent: GitHub/Vercel/builder preview and production promotion.
- QA/Rollback Agent: post-deployment validation and rollback on regression.
- Data Freshness Agent: conversion-file freshness and request state.

## 6. Creation standard: AFFINITY + premium design
Every new or materially revised landing page, mini-site, article/post, comparison page or creative marketing asset must use:
1. canonical demand/pain/competition context,
2. AFFINITY funnel selection and conversion logic,
3. AFFINITY Creative Production art direction,
4. the best-fit modern web framework for the existing project,
5. performance-first implementation,
6. accessibility and honest/verified claims,
7. conversion instrumentation.

Do not force one framework everywhere. Preserve existing architecture when it is appropriate. Use motion/animation only when it improves comprehension, trust or conversion.

## 7. Decision policy
Do not optimize every site every day. Rank opportunities using traffic, SEO gap, conversion gap, Greek demand, competition/whitespace, commercial value, technical risk and evidence confidence.

Examples:
- High Greek demand + high whitespace + weak organic visibility -> SEO/content.
- High demand + meaningful traffic + weak CTA/affiliate CTR -> CRO.
- High demand + high saturation/authority barrier -> differentiated pain-specific long-tail strategy.
- Low/uncertain demand -> collect evidence or wait.
- Good demand but weak merchant economics -> do not force affiliate promotion.

Every material change requires a measurable hypothesis and before/after measurement.

## 8. Deployment and rollback
For GitHub/Vercel sites:
AI change -> reviewable commit/change -> build/preview -> quality gates -> production -> health/analytics verification.

Verify as applicable:
- build success,
- HTTP 200 critical routes,
- no new runtime errors,
- canonical/robots/sitemap,
- schema/metadata,
- affiliate-link validity,
- no material Core Web Vitals regression,
- no unsupported claims.

Keep one canonical active production deployment per site and retain rollback references. Do not delete useful deployment history merely for dashboard cleanliness.

For ChatGPT-created/other builder sites use the adapter abstraction read -> edit -> deploy -> verify. If no write adapter exists, record pending action rather than claiming execution.

## 9. Autonomy levels
AUTO: analytics repair, schema/metadata, technical SEO, crawlability, internal/broken links, safe performance/image fixes.

AUTO + MEASURE: CTA wording/placement, section ordering, trust signals, affiliate prominence, non-destructive conversion copy/layout.

EXPERIMENT: larger CRO/content/layout variants with baseline, measurement window and rollback.

USER APPROVAL: domains, pricing, payment/checkout, legal/compliance claims, credentials, destructive production/data deletion, irreversible major redesigns.

## 10. Scheduling ownership and duplicate-prevention policy
The system must not create a second recurring automation when an existing canonical stage already owns the responsibility.

### ChatGPT task ownership
- `Daily GrowthOps`: the single daily AI decision/orchestration loop for public-site SEO, CRO, Greek demand context, content/creative generation, MyAgenticTeam execution and deployment verification.
- Older standalone `Daily Public SEO` and standalone `Conversion Optimization` are disabled and must remain disabled while Daily GrowthOps owns those responsibilities.
- Unrelated personal/condition-watch tasks are outside GrowthOps and are not duplicates.

### Supabase pg_cron ownership
Supabase cron is for deterministic preparation/workers/state maintenance, not a second AI GrowthOps decision engine.

Current deduplication policy:
- standalone duplicate SocialScheduler auto-heal is disabled where the AI autopilot worker already performs the same auto-heal.
- standalone duplicate SocialScheduler feedback sync is disabled where the AI autopilot worker already performs the same feedback sync.
- conversion cron is data/metrics preparation only and must not become a second autonomous CRO decision engine.
- weekly SocialScheduler optimization must have only one automatic canonical execution path; the duplicate GitHub weekly optimizer schedule is manual-only.
- provider publishing workflows (Buffer/PostZen/BrightBean), v10 poster-gated refill, demand intelligence, merchant intelligence, product intelligence, embeddings and Top-100 stages remain distinct when they perform different pipeline functions.

Before adding or enabling any future cron/task/workflow, compare its responsibility and called functions against existing ChatGPT tasks, Supabase cron and GitHub Actions. If materially duplicated, consolidate instead of enabling both.

## 11. MyAgenticTeam
MyAgenticTeam is the implementation/review/test operating model, not a second planner or scheduler. Use the smallest capable team for each delegated task and return execution evidence to Supabase. It must not create independent priorities, schedules, market models or conflicting site edits.

## 12. SocialMarket AI Admin
Do not create another admin dashboard. SocialMarket AI Admin is the single control/status surface for Portfolio, Analytics, Greek Demand, Competition/Whitespace, SEO, CRO, Experiments, Deployments, Data Freshness, Agents and Actions.

## 13. Learning loop
For every experiment/change persist hypothesis, target site/page, market context, baseline, implementation/deployment reference, measurement window, before/after metric, lift, confidence and outcome.

Outcome states:
- KEEP
- ITERATE
- ROLLBACK

Store reusable winning/losing patterns in Supabase without writing site-performance lift back into canonical market-demand truth.

## 14. Notification policy — FINAL
The user does not want intermediate emails from the GrowthOps run.

For each scheduled Daily GrowthOps execution:
- Send ZERO emails while the run is in progress.
- Do not send a separate CSV-staleness email during the run.
- After the run reaches its terminal state, send EXACTLY ONE completion email.
- The single completion email includes: run status (GREEN/AMBER/RED), sites analyzed, material changes actually completed, deployments and verification, measurable results where available, errors/blockers, approvals required, and conversion CSV freshness.
- If a new conversion CSV is required, include the upload request inside this same final email.
- If the run cannot complete normally, the terminal failure/blocked state still counts as completion for notification purposes: send one final email explaining the blocker and do not send additional duplicate emails for that run.
- Never claim execution, deployment, conversion lift or success without evidence.

## 15. Non-negotiable rules
- Supabase is operational source of truth.
- SocialMarket canonical intelligence is market-truth source.
- SocialMarket AI Admin is the only admin/status UI.
- One Growth Orchestrator owns public-site autonomous decisions.
- No duplicate daily SEO/CRO/demand decision loops.
- No duplicate demand model.
- Evidence before action; measurement after material changes.
- Preserve working production and rollback capability.
- One final email per Daily GrowthOps run; no intermediate GrowthOps emails.
