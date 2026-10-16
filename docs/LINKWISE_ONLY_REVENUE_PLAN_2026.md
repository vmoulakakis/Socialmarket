# SocialMarket: Linkwise-only revenue and safety contract (proposal)

Status: **DRAFT FOR REVIEW — NOT DEPLOYED**. Scope: Linkwise affiliate only; no other commerce source/API; do not change unrelated projects. Source-of-truth: canonical VMDB plus verified Linkwise merchant/program records.

## Commercial objective
Reach EUR 5,000/month of **approved** affiliate commissions (before operating expenses and taxes), progressively. Monitor visitors -> attributable outbound clicks -> transactions -> approved/declined commission -> paid; optimize approved EUR per 100 *qualified* clicks, not raw commission or simulated EPC.

## Source freshness (user-approved cadence)
- Discover **new product IDs weekly**; don't repeat AI analysis or rewrite unchanged 2M+ records.
- Retire offers by `valid_to` as they expire; verify availability of currently promoted offers separately and cheaply.
- Never infer "out of stock" from NULL stock; unknown blocks confident publication pending verification, but is not a deletion signal.
- If source offers only complete snapshots, stream once weekly, dedupe on stable composite product identity, compare canonical content hashes, and persist only new/changed IDs; avoid materializing entire product data in DB.
- Don't delete absent entries after partial/failed feed scans. Use completed source watermark and a configurable consecutive-absence rule.
- Full scans/AI reanalysis require explicit approval.

## Merchant and program eligibility
Hard checks: approved joined Linkwise program + valid affiliate tracking, merchant/site identity verified, geography/service supported, offer not expired, publication/legal eligibility. Unknown evidence => `needs_review`, not fabricated approval or permanent rejection.
Match `linkwise_program_id` from authoritative program list or Linkwise tracking route to canonical merchant domain; name/alias only as evidence-backed fallback. Log confidence, rule and rejection reason. Verify link route against program before publication.
Commercial ranking: actual approved EPC (EUR/click), Greek problem demand/purchase intent, checkout trust, fulfillment/returns, creative opportunity and evidence confidence. Never conflate EPC100 with EPC/click; label model estimates vs actual.

## Organic growth
Start with 3–5 manually audited, approved merchants; 4–5 Greek problem-first themes per week; repurpose to short video, carousel, useful group answers and original SEO landing pages. Use connected scheduling tools only on **Linkwise-dedicated** accounts; do not hijack or alter existing queues for other projects. Manual group contributions must obey platform/group rules and disclose affiliate relationships. Video should be platform-appropriate (do not submit static images as TikTok video).
Use first-party UTMs and campaign IDs; Linkwise subIDs only after verifying allowable field contract. Distinguish page visits, outbound clicks, approved sales, paid commissions; QR routes to mobile-friendly landing page with its own campaign ID.

## Revenue checkpoints
Phase 0: 0 broken tracking URLs; verified program->merchant match; production metrics trustworthy.
Phase 1: initial attributable sales and approved EPC by channel/merchant.
Phase 2: evidence-backed 1,000–2,500 qualified affiliate clicks/month with viable economics.
Phase 3: scale only profitable organic campaigns; only consider paid ads if program/platform permits and approved margin supports it.
Target scenario: EUR 0.40 approved EPC requires 12,500 attributable affiliate clicks/month for EUR 5,000 in approved commissions. Not a forecast.

## Verified blocking conditions as of 2026-10-16 (read-only review)
- VMDB pg_cron `linkwise-auto-ingest-v17` runs every minute and invokes deployed Edge Function v17, while the user explicitly wants **weekly** discovery.
- A v17 `commerce_feed_runs` row remains `running` since 2026-09-17 with checkpoint `skip=34000`; the function's `previous_chunk_running` guard prevents progress. Recent persisted HTTP responses report skipped runs, not ingestion.
- VMDB canonical offers 3,921, last seen 2026-09-17; 1,542 have unknown program identity and zero estimated commission.
- Merchant 360: 0 of 66 ranking records pass current hard gates. Canonical performance-event table empty; historical Linkwise exports have clicks and one Cardinal order, not evidence of sustained merchant conversion.
- Deployed v17 uses `price>120`, not verified payout economics; the deployed source differs from the GitHub function. It embeds an auth token: rotate/secure before production work. Never disclose the token in reports.
- Some workflows point to retired Supabase endpoints; do not re-enable blindly.

## Proposed change sequence (future gated PRs, not this PR)
1. Back up and document currently deployed Edge Function, cron job and checkpoints, preserving running-state evidence.
2. Design weekly scheduler with expiry-only lightweight checks; idempotent stale-lock recovery using lease/heartbeat, *not* manual status resets that could race an active run.
3. Make product identity reliable; test Linkwise route parsing with synthetic fixtures. Use stable product-id identity independent of price, and a separate canonical content fingerprint.
4. Link program commissions/approved eligibility; replace estimated payout short-circuits; maintain rejection/explanation counters.
5. Implement campaign attribution and accepted commissions before scale.
6. Canary with small audited product subset, dry-run diff, rollback strategy and user approval before production cutover.

**Non-goals:** changing production SQL, cron, secrets, deploys or social queues; importing 2M+ products on every run; any non-Linkwise affiliate source.
