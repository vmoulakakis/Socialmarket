# SocialMarket AI — VMDB v1.0 release and evidence contract

**Scope:** `sm_intel` private schema in existing VMDB `gqpbskssrvpfjtujwezc`. No other VMDB tenant, legacy table, cron, Edge Function or public API changed.

## Product goal
Scan the entire joined-program Linkwise JSON feed; retain raw records with provenance; **only admit offers for which conservatively calculated, verified minimum affiliate commission is >=EUR10**. Merchant approval, verified tracking, live stock and feed freshness are separate promotion readiness checks. Then use Greek demand vs observed supply, merchant ranking, seasonality/geography, aggregate buying intent, verified factual incentives and graph-based source evidence to rank useful product solutions.

## Source/identity
- The real CD104 Linkwise feed does not expose a reliable `program_id` field. Resolve it from the program route in a *trusted* Linkwise tracking URL `/z/<program>-<route>/CD104/`. Unknowns remain quarantined in raw catalog.
- Identity: `program|product_id|sku` hashed. No price/name in key; delta changes retain identity and update JSON only on hash changes.
- Ingest conservatively: EUR price positive, program resolved, HTTPS Linkwise tracking, source stock remains nullable, expiry remains nullable.
- Keep every raw record including rejected/ambiguous rows. SQL function is private, batch-bounded and idempotent.
- `commission_terms` are time-bounded, publisher-specific, source-attributed and **unverified until reviewed**. Ambiguous flat+percent structures cannot be presumed additive or pick the maximum. The private trigger recalculates each proposed admitted offer and rejects any commission <EUR10 or mismatch with raw source.
- `qualified_offers` != `promotion_ready_offers`. Promotion requires approved merchant, tracked link, true stock, current terms, completed full run within seven days and fresh source values. No user-facing offer without these signals.

## Market intelligence
`research_evidence` retains URLs, observed times, signal kinds, geography, source confidence and contradictory sources. `pain_gap_scores` captures time-scoped Greek demand, supply, intent and seasonality. `merchant_rankings` captures fit/trust/fulfilment/verified incentives without conflating the money with product suitability. `pain_offer_matches` binds actual admitted products to evaluated needs. `graph_nodes/graph_edges/graph_edge_evidence` implement SocialMarket-only two-hop evidence graph; only verified edges eligible for factual reasoning.

Buying intent uses coarse consensual, aggregate patterns, *not* personal inferred vulnerabilities. Incentives must be true, source-verifiable and time-bounded; no fabricated scarcity.

## Deployment
1. The two schema migrations are already applied additively to VMDB; do not manually reapply ad-hoc.
2. Source code and tests are staged in this PR. No automatic full-feed refresh is enabled; legacy minute cron/Edge Function still exists and requires separate controlled cutover.
3. Install pinned Python `ijson`, `requests`, `psycopg[binary]` in a secure worker runtime. Store `SOCIALMARKET_DB_URL` as a server-only secret. Store feed URL as server-only setting; never put tokens in SQL, code, logs or public pages.
4. Run --file fixture dry-run, then bounded remote dry-run, compare counts/checkpoints to source.
5. Mark actual Linkwise commission terms reviewed against *current* publisher conditions before any writes to qualified_offers. Unknowns fail closed.
6. Back up; disable legacy stuck cron only after safe cutover approval, and run a complete worker batch. Until this is done, `promotion_ready_offers` remains empty. Validate stock/tracking, counts, coverage, and cost.
7. No graph edge is verified merely because a merchant or pain exists. Run Greek-market research independently, attach evidence and review before exposing graph-based claims.
8. Track operation time, scanned/qualified/quarantined, feed fingerprint, API cost and failures; restore old jobs only via separate controlled rollback.

## Acceptance evidence
- Existing snapshot isolated: 3921 raw legacy offers, 16 unverified historic commission terms, 41 pain + 16 merchant nodes (as of implementation).
- No eligible offers auto-promoted from historical snapshot.
- Zero cross-project rows, zero consumer PII in graph and zero client schema grants.
- Hard gate and trigger tested with verified fixture; commission boundary below/exactly/above EUR10.
- End-to-end 3.84GB full scan is **NOT VERIFIED** without actual worker execution and source coverage comparison.

## AI Architect Orchestrator — implemented 2026-10-30

**Database facts (verified on VMDB, dated snapshot):**
- `public.linkwise_program_commissions`: **334 distinct source program names**, **17 nonempty program IDs**, **317 missing IDs**; source import was 2026-09-17.
- `public.merchant_profiles`: **16 enriched merchant profiles**; this is NOT the total Linkwise program population. Neither program approvals nor tracking verified flags are established from the 16 profiles.
- `sm_intel.merchant_program_directory`: **334 source program rows** preserved; no program was dropped based on absent ID. **334 terms_valid_to unknown**, approvals not assumed.
- `sm_intel.graph_nodes`: **4,694** including 334 program nodes.
- `sm_intel.graph_edges`: **5,140** source-labeled candidate edges; 0 independently verified. Product→program links: 2,379 based solely on exact CD104 source program IDs (not current approval).
- `sm_intel.search_documents`: **4,360** searchable docs, 0 real E5 vectors at this snapshot. SQL/FTS/RRF works, but no genuine multilingual vector retrieval until external E5 worker produces embeddings.
- `sm_intel.agent_tasks`: **4,713 queued** (3,921 product analyst + 334 identity + 334 commission verification + 41 Greek demand research + 41 skeptical QA + 41 graph librarian + 1 architect).
- `public.commerce_performance_events`: zero observed conversion events. Outcome-based learning has no verified training feedback yet.

**Deployed production endpoints**: `socialmarket-graphrag` and `socialmarket-architect` (active Supabase Edge Functions), both manually validate authenticated admin JWT. Existing `socialmarket-ai` is the model gateway with budget reservations; the orchestrator's agent outputs are explicitly candidate-only. These functions are LIVE code endpoints, but external full-feed ingestion, query-vector service and successful paid model requests are not yet verified end-to-end.

**Recurring ChatGPT AI Architect automation**: daily scoped audit/research task created; this is separate from app runtime and does not grant blanket production modification rights. Check actual runs before claiming outputs have landed in DB.

**Risk gates**:
- Program `active_since` is not `valid_to`, and a CSV ID is not publisher approval.
- Backfill merchant mappings only with verified official source and preserve URL provenance.
- Model cannot auto-approve merchants, change affiliate payout rate, invent stock, fabricate demand or alter advertising.
- Follow actual DeepSeek budgets and max 3 specialist tasks per invocation.
- Greek market `high_demand_low_supply` requires independently sourced demand metrics and observed local supply; keyword hypotheses are not measurements.
- Record all user learning as verified opt-in outcomes, not inferred personal vulnerabilities.
- No continuous background paid model runner exists solely because an Edge Function is active; use the daily automation as a monitored autonomous research pathway, and independently configure credentialed server worker if needed.

## Streaming / delta-only feed release contract — 2026-10-31

**Authoritative source:** user-supplied full `https://affiliate.linkwi.se/feeds/1.2/CD104/programs-all/.../feed.json`, verified by source metadata only. Encrypted Supabase Vault secret `socialmarket_linkwise_cd104_full_feed_url_v1` is present and has the expected URL path, columns prefix, category inclusion prefix and CD104 suffix. Never output the decrypted URL or send it in logs.

**Explicit request: do NOT ingest the live feed now.** No live HTTP GET or product upload has been run. The feature is deployed in private VMDB as a migration and staged in GitHub (draft PR), but the production manual workflow has not been invoked.

**Canonical forthcoming importer:**
`workers/product_intelligence/linkwise_delta_only_v2.py` + `sm_intel.ingest_new_only_batch(uuid,bigint,jsonb,text)`.

1. Stream full JSON using `ijson`, bounded 100-row batch and max 128 KiB per record (oversized records safely omitted and counted, not stored as truncated facts). Only one parsed product is held at once in addition to the batch, no 3.84 GB in-memory array.
2. Source `program_id` from genuine `go.linkwi.se/z/{program}-.../CD104/` tracking URL, stable key `program_id|product_id`. Do not trust the converted uploaded spreadsheet deeplinks.
3. Check `valid_from` and `valid_to` timestamps, positive EUR sale price, real source tracking link and verified current commission terms.
4. **Hard gate:** conservatively computed commission >= EUR10. Other rows are counted as unqualified and are *not inserted by v2*. Source data remains accessible in the upstream feed.
5. Insert **only new product identities**, using `ON CONFLICT DO NOTHING` and exact historical `program_id + source_product_id` lookups; never update existing JSON, price, stock, tracking, merchant, identity or seen timestamps.
6. Batch commit is atomic and audit-ledger-backed. Explicit offset must match `feed_runs.scanned`; replay of the same batch hash is idempotent, but mismatched replay is blocked. High-level run completion requires the final scanned count to match the final checkpoint.
7. Honor a strong ETag for snapshot-safe resume. On disconnect without strong ETag, begin a new full scan and skip existing products; never infer byte offsets in JSON. Conditional If-None-Match allows a 304 skip when a prior full run is unchanged.
8. Expose the manual workflow only on main, with choices fixture_only, preview_1000, preview_10000, full_dry_run and separately selected delta_new_only_commit. No cron or background feed import is enabled by this change.
9. A current production price/stock update is a **separate future** lightweight feed/offer-state reconciliation, because the present user-authorized delta policy is strictly insert-only. Consequently, old offers must remain fail-closed rather than pretending they are fresh.

**Uploaded merchant files inspected but NOT imported**:
- `programs_with_websites(1).csv`: 340 names, semicolon-separated, websites are unverified candidates (30 'High', 44 'High-Medium', 266 'Medium').
- `programs_with_sites_and_deeplinks_converted(1).csv`: 315 names, 314 deeplinks all use `/z/12858-0/CD104/`, despite different merchant identities; do not use as valid tracking URLs. Example: 24home.gr belongs to source program `11532` while the file route is `12858`.
- `programs_with_sites_and_deeplinks(1).xlsx`: same 315-program listing. These three attachments have NOT been committed or imported into VMDB.

**Hugging Face model policy** (repo metadata inspected, no model inference benchmark performed):
- **Tier 0 / always free of model tokens:** exact SQL identity, calculation, deduplication, fee/validity checks, source freshness and graph joins.
- **Tier 1 / offline CPU embeddings:** [intfloat/multilingual-e5-small](https://huggingface.co/intfloat/multilingual-e5-small), 384 dimensions, multilingual Greek/English, MIT; existing private vector schema expects this exact model/dimension.
- **Tier 2 / optional CPU local extraction:** [Qwen/Qwen3-0.6B](https://huggingface.co/Qwen/Qwen3-0.6B), 0.75B parameters, Apache 2.0, only candidate structured categorization after benchmark on Greek and Greeklish holdout; no presumed accuracy.
- **Tier 3 / paid only complex unresolved claims:** existing bounded `socialmarket-ai` DeepSeek endpoint after 2+ independent verified cited sources, contradictions/uncertainty and explicit `use_ai:true`. Missing evidence causes zero token spend, not speculative research.
- Benchmarks are needed before choosing a larger LLM, and server CPU/RAM cost is not the same as paid API token cost.

**Verification evidence:** SQL transaction test on three fixtures: legacy row unchanged; new row with exactly EUR10 admissible under synthetic verified terms; 9.99 EUR row rejected. Batch replay correct with rollback. Deno typechecks and Python fixture tests in GitHub Actions; **no actual full-feed throughput benchmark or billing validation**.
