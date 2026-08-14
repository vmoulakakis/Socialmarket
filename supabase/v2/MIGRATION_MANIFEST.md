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
| 20260814214931 | `merchant_embedding_claim_contract_v1` | Safe claim contract returning the exact enriched semantic text for real embeddings. |
| 20260814215117 | `merchant_rankings_peer_group_v2_fix` | Global + peer-group ranking and research history views. |

## Invariants

1. `raw.*` is immutable source/audit data. Normalization never overwrites source rows.
2. A Merchant, Affiliate Program, and Product Offer are distinct entities.
3. Commercial affiliate metrics are not consumer-demand metrics.
4. Research is evidence-first and snapshot-based. Refreshes append history rather than overwrite it.
5. AI narrative may interpret collected evidence but may not replace source evidence or alter deterministic scores.
6. Vectors are generated only after deep research completes; no placeholder/hash/fake embeddings are allowed.
7. `raw`, `catalog`, `intel`, `ai`, and `ops` are not exposed to browser roles.
8. GitHub workers authenticate through GitHub Actions OIDC. The Edge gateway only exposes an allow-list of worker RPC actions.
9. Scheduler/publishing tables are intentionally outside this foundation and will be added only after this merchant-intelligence contract is stable.

## Imported source baseline

- Source file: `programs (5)(6).csv`
- Original encoding: `cp1253`
- Original SHA-256: `e45bd93a36eca668f41023494fe5d8bfe5ef87bbf93943804c868a64c8ce5bca`
- Rows: 310 total / 309 accepted / 1 rejected (blank program name)
- Canonical UTF-8 transport SHA-256: `23e3fff8a645b35b5d04560948374d2d37d0f87a0abbab6ffddd3176acc59a48`
- Imported program commercial snapshots: 309
- Commercial scoring model: `commercial_v1`
- Merchant research model: `merchant_research_v2`
- Embedding model contract: `BAAI/bge-m3`, 1024 dimensions, normalized vectors, cosine/HNSW.

## Refresh lifecycle

`start_refresh → merchant_deep_research → evidence + immutable snapshot → enriched semantic_text → semantic_embedding → refresh_run_status`

The weekly workflow is `.github/workflows/merchant-intelligence-v2.yml` and may also be dispatched for one merchant UUID or the whole portfolio.
