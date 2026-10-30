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
