# SocialMarket AI — Token-Efficient Hybrid GraphRAG & Streaming Delta v1

Status 2026-10-30: implemented private VMDB contract and admin Edge orchestration;
full Linkwise feed **NOT downloaded or ingested**. No 24/7 independent paid LLM
worker has been started.

## Exactly what is the feed?

The owner supplied a CD104 Linkwise `programs-all` JSON URL containing:
`product_id,model_name,product_name,description,category,brand_name,tracking_url,
thumb_url,image_url,in_stock,availability,valid_from,valid_to,on_sale,currency,
price,full_price,discount,city,times_bought,longitude,latitude,address,size,
colour,custom,extra_images,variations` and other category parameters.

**DO NOT commit, print, publicly expose or download this URL without an approved run.**
Configured as a *private Supabase Vault secret*:
`socialmarket_linkwise_cd104_full_feed_url_v1`. Secret value is not in repository.

Current 3,921 `sm_intel.raw_products` legacy records have canonical key
`program_id|source_product_id` (not SHA256). Delta parser reproduces this
identity; mutable prices/titles/links are excluded.

## Delta-only source-to-DB flow

```text
CD104 full source (HTTPS) --streamed ijson array + gzip + no redirects-->
bounded 150-item / 4MB batches --stable program|product_id-->
sm_intel.ingest_new_only_batch() --(INSERT ON CONFLICT DO NOTHING)-->
new raw_products only --conditional verified >=EUR10 commission-->
qualified_offers candidates
         +-->new search docs / new graph nodes / agent research tasks
```

- The feed must be scanned to discover unseen IDs; only incoming **new products**
  are written. Existing rows retain original raw JSON, price, availability and
  tracking links. This is deliberately `new_only`, **not** a price/stock update.
- ETag-based conditional GET may skip the scan when the origin says unchanged.
  No ETag => full stream scan is necessary; do not pretend this is a remote delta API.
- Maximum 150 records and 4MB per DB batch, no whole-feed loading. If oversized,
  fail safely rather than crash/OOM. Persist per-batch progress, tolerate restarts
  by rescanning + ON CONFLICT DO NOTHING.
- Program identity: known program route in Linkwise tracking, never guessed by
  product name. `unknown` legacy ID conflicts are recorded in
  `delta_identity_conflicts`, not silently duplicated.
- Existing products are never updated. Therefore current prices and stock for
  existing rows **will become stale**; the promotion readiness view blocks
  candidates without a recent complete run, verified stock, tracking and terms.
  Consider a separately approved stock/price-change refresh only if required.
- Invalid source ID cannot be deduplicated and is counted as unidentifiable.
  A malformed source record is never promoted.
- `valid_from` and `valid_to` are interpreted as product-offer validity.
  Merchant program expiry is a **different**, independently verified term.
- Raw catalog includes new commercial ineligible products (not promotional).
  `qualified_offers` has hard calculated and verified >=EUR10 gate.

### Manual release workflow

`.github/workflows/socialmarket-vmdb-full-refresh-manual.yml`:
`fixture_only` default (offline; no feed request), `preview_1000`,
`preview_10000`, `full_dry_run`, `delta_new_only_commit`.
Only main branch, with explicit manual dispatch; no scheduled auto import.
Requires `SOCIALMARKET_DB_URL` server-only GitHub secret to read the Vault URL.
No feed ingestion run was performed in this change.

## HF model decision (CPU first, no per-token model charges)

| Tier | Selected model/tool | Why | When | Production status |
|---|---|---|---|---|
| T0 | PostgreSQL exact ID/commission/currency/time SQL | lossless, fast, no inference | every item | DB live |
| T1 | PostgreSQL `simple` FTS + pg_trgm + RRF | Greek lexical, SKU, spelling; zero tokens | every search | DB live |
| T2 | `intfloat/multilingual-e5-small`, 384D | Greek + English semantic relation; CPU self-host | semantic retrieval, batch embeddings | embedding queue live; worker code ready, 0 actual vectors |
| T3 | Postgres evidence graph, max 2 hops | explain merchant/pain/product provenance | after retrieval | graph live, currently candidate edges |
| T4 | Existing SocialMarket AI model gateway (budgeted) | resolve genuinely difficult contradictory evidence | only when ≥2 independently verified research sources OR high-level architect synthesis, not basic product scans | Edge endpoint deployed; no successful real LLM orchestration invocation yet |

Alternative evaluated, not mixed into live 384D index:
- `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` has Greek
  support; comparative holdout evaluation needed before any replacement.
- `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` is a multilingual reranker but
  Greek is not explicitly in the model card's listed languages; **not default**.
- `BAAI/bge-m3` is richer but heavier; no justification at this data quality
  and evidence/coverage stage. Do not spend CPU/GPU capacity before measured recall.

No model can fabricate merchant program IDs, approvals, valid-to, real Greek
demand volumes, live competitor availability, or source tracking URLs.

### AI Architect routing

`socialmarket-architect` v3 defaults to inexpensive deterministic operations;
it calls the budgeted existing model gateway only for special research/skeptic
tasks with at least two verified external sources, or strategic architect
synthesis. Caller may set `use_ai:false` to force zero provider LLM calls.
Maximum 3 specialist tasks per run, rate/quota limits inherited from existing
SocialMarket model gateway. Never turn candidate AI prose into a verified row.

## Follow-on release gates

1. Obtain a real network/source response **only after separately starting manual
   preview** (owner explicitly said do not ingest now).
2. Inspect source JSON shape and HTTP content encoding/ETag safely before commit.
3. Compare first 10k records with old 3,921 ID keys and resolve merchant mapping
   conflicts and program IDs; no assumption that 16 profiles cover 334 programs.
4. Benchmark stream duration, DB growth and cost, then optional full dry-run.
5. Confirm authoritative Linkwise commission terms for publisher CD104;
   never invent `valid_to` from `active_since`.
6. Self-host E5 and fill embedding queue; run held-out Greek/Greeklish recall,
   citation integrity and graph provenance eval.
7. Validate true conversion events before any adaptive learning loop changes weights.
