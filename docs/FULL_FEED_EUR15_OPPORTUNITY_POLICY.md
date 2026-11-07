# SocialMarket AI — Full-universe, EUR15-only research contract

Effective owner rule: **calculated affiliate commission >= EUR 15 per proposed purchase** is the **only business eligibility cutoff** at the initial full-feed screening boundary. All other data, including stock, merchant identity confidence, dates, image, SKU, lower demand scores, competition, merchant trust and conversions, remain context for later ranking, uncertainty disclosure or publishing governance. Safety restrictions and external network terms are not commercial profitability thresholds.

## What is actually live
The canonical VMDB currently contains 23,613 Linkwise offers, of which 8,382 carry **historical estimated** EUR15+ commission in existing source rows (all from program 23 / La Redoute). This is NOT a complete 3.5 million source scan. A prior small Linkwise discovery examined 1,000 products and 0 cleared its commission verification rule; it is NOT evidence about the entire pool. The 18 stored prior AI discovery candidates are from an AliExpress 1,500-offer pilot and have no verified demand or competition.

## New implementation in the existing PR
- `workers/product_intelligence/all_feed_opportunity_discovery.py` — memory-bounded ijson full JSON feed pass; accepts EVERY category/merchant and stock state for research. Reads historical network commission rates by CD104 advertiser ID, not by merchant name. Missing rate = unpriced rather than fabricated zero. Sole economic exclusion: commission estimate under EUR15.
- Weights for research-priority ranking (not additional selection gates): problem-fit 35%, observed demand 25%, inverse competition 20%, conversion/traction potential 20%. Unavailable observations stay NULL and lower confidence. The original tracking URL is copied byte-for-byte.
- `supabase/functions/socialmarket-fullfeed-discovery/index.ts` — deployed OIDC-only Edge gateway to the existing VMDB; reads source network rates and inserts *only* `research_candidate` rows in `public.ai_discovery_candidates_v2` at calculated EUR15+. No network approval or social posting actions exist.
- `.github/workflows/full-feed-discovery.yml` — manual job that reads an explicitly configured full source feed URL (secret `LINKWISE_FULL_FEED_URL`) or the existing known historic large Drive feed snapshot, invokes the scanner, and persists a maximum 100–1000 investigational candidates in batches of 20. No automatic scheduled ingestion or remote LLM spend.
- `test_all_feed_opportunity_discovery.py` regression tests: below-15 excluded, missing-rate unknown, null and false stock retained as evidence, conversion != proof of affiliate sales, missing demand/competition != verified zero. CI enabled.

## Business methodology (the current limitations matter)
A genuine high-demand, low-competition conclusion REQUIRES independently measured and dated demand, seller counts/search SERP saturation, reviews and regional supply. In November 2026 existing VMDB `market_demand_observations` has 0 rows; 36 `ai_demand_signals` are labelled `hypothesis`; product conversion events are 0. Consequently new results are **research opportunities** and must never be advertised as proven low competition, measured conversions or officially payable commission. The score is an investigation prioritizer, not an independently validated prediction.

## Funnel
3.5m input (once the operator provides an authentic full feed) -> source-ID commission calculation -> EUR15-only eligible pool -> ranked evidence-aware candidate frontier -> MyAgenticTeam research and independent commercial skeptic -> source-price/freshness/merchant/stock/terms disclosure -> approved promotions if verified. This does NOT turn merchant approvals, dated stock or network terms into a **discovery hard filter**; they are safeguards for claiming purchase availability or payable commissions downstream.

## Owner metrics
- scanned / EUR15+ / commission unknown / under floor / shortlist coverage
- % candidates with direct verified demand observation
- % candidates with verifiable competition/seller saturation data
- product CTR, click-to-sale CVR, approved sales, actual EPC, reversal rate when received from network
- % original links unchanged and no duplicate promotion.
No sales claims or revenue forecasts unless conversion events exist.

## Required next operational steps
1. Configure a true full-catalog Linkwise CD104 feed URL in GitHub Actions secret `LINKWISE_FULL_FEED_URL`. It must not be restricted to a dozen categories. Or use the historical 3.84GB Drive snapshot only as historical input.
2. Manually trigger the full-feed workflow on the repository's default branch after PR review/merge; GitHub Actions only dispatches registered workflows. Read the counts before treating output as all 3.5m.
3. Enrich shortlisted items with independently dated Greek market demand and competition observations. Use strict source provenance; do not treat earlier AI hypotheses as measured demand.
4. Plug the evidence-enriched frontier into the existing seven-role AI architect/skeptic + buyer advisor; preserve the original URLs and never auto-publish unverified products.
5. Verify the full Edge gateway/store and end-to-end UI; no browser E2E or full-feed run has occurred during this design update.

GitHub review: https://github.com/vmoulakakis/Socialmarket/pull/103
