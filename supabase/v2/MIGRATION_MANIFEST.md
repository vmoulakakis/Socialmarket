# SocialMarket V2 — Merchant Intelligence migration manifest

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
| 20260814215330 | `merchant_refresh_resume_active_run_fix` | A retry resumes the active research run rather than creating a duplicate/orphan run. |
| 20260814215438 | `merchant_semantic_search_v1_fix` | Secure semantic merchant search using explicit `extensions.<=>` pgvector operator. |
| 20260814215815 | `merchant_worker_json_envelope_rpc_fix` | Stable JSON-envelope RPCs for evidence/research/vector writes. |
| 20260814220113 | `merchant_pgcrypto_digest_qualification_fix` | Explicit `extensions.digest` in secure functions with empty search path. |
| 20260814220229 | `merchant_research_evidence_quality_gate_v1` | Deep research requires ≥3 evidence items from ≥2 independent domains; DB derives evidence count itself. |

Failed migration attempts are not listed above because Supabase/Postgres rolled them back atomically. In particular, a view-layout replacement and an unqualified pgvector operator were rejected before state changed, then corrected in the successful migrations listed above.

## Invariants

1. `raw.*` is immutable source/audit data. Normalization never overwrites source rows.
2. A Merchant, Affiliate Program, and Product Offer are distinct entities.
3. Commercial affiliate metrics are not consumer-demand metrics.
4. Research is evidence-first and snapshot-based. Refreshes append history rather than overwrite it.
5. A research snapshot is invalid unless the database confirms ≥3 evidence rows from ≥2 independent source domains.
6. AI narrative may interpret collected evidence but may not replace evidence or alter deterministic numeric scores.
7. Vectors are generated only after valid deep research completes; placeholder/hash/fake embeddings are prohibited.
8. `raw`, `catalog`, `intel`, `ai`, and `ops` are not exposed to browser roles.
9. GitHub workers authenticate with GitHub Actions OIDC. The Edge gateway exposes only an RPC allow-list, never a generic table proxy.
10. Worker retries use leasing/`SKIP LOCKED`; infrastructure failures do not silently become merchant-quality failures.
11. Scheduler/publishing tables remain outside this foundation until merchant intelligence is stable.

## Imported source baseline

- Source file: `programs (5)(6).csv`
- Original encoding: `cp1253`
- Original SHA-256: `e45bd93a36eca668f41023494fe5d8bfe5ef87bbf93943804c868a64c8ce5bca`
- Rows: 310 total / 309 accepted / 1 rejected (blank program name)
- Canonical UTF-8 transport SHA-256: `23e3fff8a645b35b5d04560948374d2d37d0f87a0abbab6ffddd3176acc59a48`
- Canonical merchants/programs: 309 / 309
- Imported commercial snapshots: 309
- Commercial scoring model: `commercial_v1`
- Merchant research model: `merchant_research_v2`
- Embedding model contract: `BAAI/bge-m3`, 1024 normalized dimensions, cosine/HNSW.

## Scoring separation

`commercial_v1` is affiliate-program economics only: conversion, EPC, approval, approval speed and commission. It is not treated as consumer demand, trust, SEO strength or final opportunity.

The deep-research layer separately measures evidence-backed trust, SEO/brand visibility, observed competition and Greece-market fit. Final opportunity ranking combines the versioned layers and also exposes a peer-group rank so airlines, logistics, insurance, marketplaces and retailers are not treated as identical businesses.

## Refresh lifecycle

`start_refresh → merchant_deep_research → evidence quality gate → immutable snapshot → enriched semantic_text → BGE-M3 semantic_embedding → refresh_run_status`

Search acquisition is multi-source and evidence-required: ephemeral SearXNG first, DuckDuckGo HTML fallback. An empty SERP causes retry/failure; it never becomes a low merchant score.

The workflow is `.github/workflows/merchant-intelligence-v2.yml`. It supports one merchant UUID or the whole portfolio. On the feature branch it is used for validation; the weekly cron becomes operational from the default branch after the V2 work is deliberately merged.
