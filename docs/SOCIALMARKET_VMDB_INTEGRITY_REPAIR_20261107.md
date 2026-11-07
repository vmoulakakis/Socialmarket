# SocialMarket AI — Integrity repair record (2026-11-07)

Source of truth: existing Supabase VMDB (gqpbskssrvpfjtujwezc). Nothing in this repair grants merchant approval or publishes to social channels.

## A. Linkwise identity backfill — DONE IN LIVE DATABASE
Recovered all 14,349 missing source program IDs from original CD104 tracking routes. Pairings:
- 399 / spartoo.gr / 12,807
- 438 / paraxenies.gr / 728
- 100 / z-mall.gr / 425
- 435 / mustshoes.gr / 341
- 427 / dealway.gr / 37
- 10599 / donedeals.gr / 11

Source mapping changed 14,349 unknown program IDs -> 0 unknown; all 14,349 original tracking URL hashes remained unchanged; no source key duplicates. The private sm_intel.linkwise_route_identity_evidence table stores source-observed network ID, destination, original URL hash and previous ID. New sm_intel.normalize_cd104_raw_offer trigger normalizes only unknown source program IDs upon future ingest, without changing links or merchant approvals.

Database migration IDs:
- linkwise_source_route_identity_backfill_20261107
- linkwise_ingress_normalization_guard_v1

## B. Merchant membership — BLOCKED BY NETWORK PROOF
16 active merchant profiles, 0 verified programs or verified tracking links. Historical 334 merchant program directory entries are not signed current Linkwise publisher terms. The six recovered source route IDs cannot prove approval or commission. Require current official CD104 joined-program details, exact approved program ID, identity, dates and official commission rule. All source approval flags intentionally remain false.

## C. Stock — CORRECT UNKNOWN, NO FAKE CONFIRMATION
9,264 source offers have unknown stock: 8,921 La Redoute and 343 Xenodoxeio. The stock field is not inferred from fuzzy description/delivery text. Updated future-import code in stream_feed.py, linkwise_product_bootstrap.py and linkwise_top100_commission.py on the feature PR, using actual program IDs, conservative minimum commission rule and strict source boolean stock.

IMPORTANT ACTIVE EDGE DRIFT: the live linkwise-feed-ingest v19 function implements a different auto-scheduler with a programs-all feed than the checked-in repository file. Do not overwrite it with checked-in version without scheduler compatibility and token rotation verification. The DB trigger handles current raw Linkwise program identity.

## D. Semantic GraphRAG — REAL WORKER PREPARED, OPERATIONAL POPULATION NOT ASSUMED
4,360 sm_intel.search_documents records previously had 0 E5 vectors. The existing sm_intel.claim_embeddings and sm_intel.ack_embedding require exact doc hash and claimed worker. The new workers/sm_intel/e5_worker.py uses true intfloat/multilingual-e5-small normalized 384D passage embeddings and locally computed model, never synthetic vectors or substituted gte-small.
- Live-deployed OIDC-protected socialmarket-e5-worker Edge function, no public data-write access.
- Bounded GitHub Actions .github/workflows/socialmarket-e5-backfill.yml, one-off 8-doc pilot when workflow is recognized, then manual workflow_dispatch only.
- Confirm actual ready count and model benchmark before claiming GraphRAG is operational. Query encoder must use the same E5 model.

## E. Qualified offers and canonical selections — INTENTIONALLY ZERO
sm_intel.qualified_offers=0, promotion_ready_offers=0, public.ai_marketplace_selected_v=0. The 28 previous active selections date from September and are not official currently verified. No flags or scores were falsified to create a marketing claim. Only independent, fresh verified membership/terms, inventory, evidence and skeptic gate may qualify.

## F. Social outbox — DONE IN LIVE DATABASE
37 old scheduled records matched exactly and uniquely against real external social provider posts via original full tracking link, caption, provider, platform, and scheduled time within 5 minutes.
- TikTok: 15 confirmed SocialChamp POSTED, actual network IDs and permalinks.
- LinkedIn: 12 confirmed SocialChamp POSTED, actual network IDs and permalinks.
- Instagram: 10 confirmed Buffer sent with actual provider sentAt; Buffer id saved only as metadata, not masquerading as Instagram media ID.
37 updated to published in public.social_publishing_outbox. No duplicate publications or rewritten affiliate links. SocialChamp exact post timestamps were not fabricated.

## G. Live integrity views
Migration socialmarket_truth_gates_and_affiliate_reconciliation_views_20261107:
- sm_intel.socialmarket_integrity_gate_v1: 7 source-truth operational states.
- sm_intel.linkwise_network_identity_review_v1: six network route IDs and evidence gaps.
- sm_intel.social_outbox_reconciliation_v1: external status proof.
Private security-invoker read-only views; no anon/client privileges.

## Verification & next steps
Verify live:
  select gate_key, observations, failing, current_state from sm_intel.socialmarket_integrity_gate_v1 order by gate_key;

Next source of truth required: authoritative current joined Linkwise program/terms and fresh merchant stock. Next runtime gate: confirm actual 384D vectors and Greek E5 retrieval quality. Never turn verified offers on based on missing approvals.

Code: draft GitHub PR 103 on feat/agentic-shopper-evidence-gate-20261106. Live DB changes applied independently of draft branch; application code and standalone E5 workflow are not a merged production rollout.
