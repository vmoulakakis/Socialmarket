# SocialMarket V2 — authoritative migration manifest

This directory is intentionally separate from the legacy `supabase/migrations` chain.
The fresh V2 Supabase project is `socialmarket` (`rpfadpdnnxequgvdcfoq`).
Legacy SocialMarket migrations must not be replayed into this project.

## Authoritative applied order

| UTC migration version | Name | Purpose |
|---|---|---|
| 20260814212811 | `merchant_intelligence_foundation_v1` | Internal schemas, immutable raw import, merchants/programs, commercial snapshots, evidence/research snapshots, pgvector semantic objects, research queue, scoring models. |
| 20260814214220 | `merchant_identity_taxonomy_scoring_v1` | Merchant aliases, taxonomy, category snapshots, metric parsers, versioned commercial percentile scorer. |
| 20260814214508 | `merchant_research_worker_contract_v1` | Narrow claim/evidence/research/embedding/failure RPC contract. |
| 20260814214630 | `merchant_refresh_orchestration_v2` | Refresh run orchestration and research→semantic dependency. |
| 20260814214648 | `merchant_worker_public_rpc_wrappers_v1` | Service-role-only public wrappers for PostgREST. Internal schemas remain unexposed. |
| 20260814214931 | `merchant_embedding_claim_contract_v1` | Safe embedding claim contract returning exact enriched semantic text. |
| 20260814215117 | `merchant_rankings_peer_group_v2_fix` | Global + peer-group ranking and research history views. |
| 20260814215321 | `merchant_worker_ops_schema_usage_fix` | Grants service-role schema usage required to execute narrow `ops` RPCs; no browser grants. |
| 20260814215330 | `merchant_refresh_resume_active_run_fix` | Retry resumes the active research run instead of creating a duplicate/orphan run. |
| 20260814215438 | `merchant_semantic_search_v1_fix` | Secure semantic merchant search using explicit `extensions.<=>` pgvector operator. |
| 20260814215815 | `merchant_worker_json_envelope_rpc_fix` | Stable JSON-envelope RPCs for evidence/research/vector writes. |
| 20260814220113 | `merchant_pgcrypto_digest_qualification_fix` | Explicit `extensions.digest` in secure functions with empty search path. |
| 20260814220229 | `merchant_research_evidence_quality_gate_v1` | Deep research requires ≥3 evidence items from ≥2 independent domains; DB derives evidence count itself. |
| 20260814220826 | `publishing_source_of_truth_v2` | Adds `content` + `publish` schemas, brand/site registry, canonical content items, publishing outbox, exact-schedule requirement, legacy import, executor kill-switch. |
| 20260814220840 | `publishing_worker_rpc_contract_v2` | Service-role-only health/peek/claim/ack/reconcile/import/control RPCs used by the OIDC publishing gateway. |

Failed migration attempts are not listed above because Supabase/Postgres rolled them back atomically before state changed.

## Ownership boundary

### SocialMarket AI owns
- merchants and affiliate programs
- commercial program metrics
- trust / SEO / competition / Greece-market research evidence
- peer-group and global opportunity rankings
- semantic merchant vectors
- brand/site registry
- canonical approved content
- `publish.outbox` publishing intent and final execution state

### SocialScheduler owns
- Buffer authentication and API calls
- Facebook / Instagram / TikTok routing
- exact execution of the date/time already selected by SocialMarket
- queue capacity and media readiness
- duplicate protection
- retries / rate-limit handling
- Buffer reconciliation
- acknowledgement back to SocialMarket

SocialScheduler must not create independent production campaigns or maintain a second production content backlog.

## Invariants

1. `raw.*` is immutable source/audit data. Normalization never overwrites source rows.
2. Merchant, Affiliate Program, Product Offer and Content Item are distinct entities.
3. Commercial affiliate metrics are not consumer-demand metrics.
4. Research is evidence-first and snapshot-based. Refreshes append history instead of overwriting it.
5. A research snapshot is invalid unless the database confirms ≥3 evidence rows from ≥2 independent source domains.
6. AI narrative may interpret evidence but may not replace evidence or alter deterministic scores.
7. Vectors are generated only after valid deep research; placeholder/hash/fake embeddings are prohibited.
8. `raw`, `catalog`, `intel`, `ai`, `ops`, `content`, and `publish` are not browser-exposed data stores.
9. GitHub workers use GitHub Actions OIDC. Edge gateways expose RPC allow-lists, never generic table proxies.
10. Worker retries use leasing/`SKIP LOCKED`; infrastructure failures do not become merchant-quality failures.
11. Every production outbox job requires an explicit `scheduled_for`; the executor never invents or silently moves a date.
12. `socialscheduler` claims are blocked by `ops.executor_controls` until import + dry-run validation pass.
13. Legacy `socialscheduler/config/backlog.json` is migration/rollback input only after cutover, never a parallel production source.

## Imported merchant baseline

- Source file: `programs (5)(6).csv`
- Original encoding: `cp1253`
- Original SHA-256: `e45bd93a36eca668f41023494fe5d8bfe5ef87bbf93943804c868a64c8ce5bca`
- Rows: 310 total / 309 accepted / 1 rejected (blank program name)
- Canonical UTF-8 transport SHA-256: `23e3fff8a645b35b5d04560948374d2d37d0f87a0abbab6ffddd3176acc59a48`
- Canonical merchants/programs: 309 / 309
- Imported commercial snapshots: 309
- Commercial scoring model: `commercial_v1`
- Merchant research model: `merchant_research_v2`
- Embedding model: `BAAI/bge-m3`, 1024 normalized dimensions, cosine/HNSW.

## Merchant scoring separation

`commercial_v1` measures affiliate-program economics only: conversion, EPC, approval, approval speed and commission. It is not trust, consumer demand, SEO strength or final opportunity.

The research layer separately measures evidence-backed trust, SEO/brand visibility, observed competition and Greece-market fit. Final opportunity ranking combines versioned layers and exposes peer-group rank so airlines, logistics, insurance, marketplaces and retailers are not treated as identical businesses.

## Merchant refresh lifecycle

`start_refresh → canary research → evidence quality gate → immutable snapshot → enriched semantic_text → BGE-M3 embedding → full refresh after canary validation`

Search is multi-source and evidence-required: ephemeral SearXNG first, DuckDuckGo HTML fallback. Empty search results cause retry/failure; they never become a low merchant score. The weighted product-intent classifier gives specific product/service signals more weight than incidental words such as “delivery” or “accessories”.

## Publishing cutover lifecycle

`legacy backlog import → outbox audit → SocialScheduler dry-run (peek only) → Buffer reconciliation check → enable executor → main-branch cutover`

Until the final enable step, `publish.claim_jobs_v2('socialscheduler', ...)` is blocked by the database kill-switch. The feature branch workflows therefore cannot accidentally publish during migration validation.
