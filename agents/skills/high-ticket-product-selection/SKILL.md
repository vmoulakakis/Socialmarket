---
name: high-ticket-product-selection
description: Legacy-named skill retained for compatibility; apply profitability-first deterministic eligibility and semantic market gates before expensive AI analysis.
---
# Product Commercial Selection

> The historical “high-ticket” filename is retained only for compatibility. **There is no global EUR150 minimum price rule.**

## Deterministic feed hard gates
A product can enter AI research only when all required production rules pass:
- merchant resolves canonically
- merchant is not blocked/dominant-market excluded
- merchant trust meets the configured threshold
- product is not explicitly out of stock
- usable tracking URL exists
- usable product image exists
- effective price is valid and currency can be evaluated safely
- price-integrity checks do not flag suspicious units/scales
- conservative expected affiliate commission meets the configured minimum (production default EUR10)
- dynamic feed/candidate saturation controls pass

Do not invent a minimum product price. A €60 product with strong expected commission and conversion economics may be superior to a €500 product.

## Semantic eligibility
Before validation/promotion:
- category must be canonical SocialMarket product taxonomy
- subcategory must be a valid child or null
- at least the configured number of validated pain/unmet-need clusters must be matched
- Product Research and independent Skeptic Audit must agree strongly enough to pass configured pain-fit, evidence and overall-audit thresholds

Navigation, brands, locations, campaign themes and service links never become product taxonomy.

## Commercial viability
Evaluate separately:
- expected commission per approved conversion
- network merchant-program CVR / EPC / approval / validation days when observed
- modeled commission per 100 clicks and break-even CPC
- first-party SocialMarket EPC/CVR/ROI when enough data exists
- product pain fit, demand, competition and evidence confidence

Network program metrics are baselines, not first-party product results.

## Competition / saturation policy
Competition is evidence-bound. Use seller/merchant breadth, commercial-domain evidence, product duplication and solution coverage. Do not label a proxy as observed ad volume. A configurable hard competition kill-switch may be used only when the evidence confidence required by configuration is met.

## Ranking principle
Only deterministic survivors receive Product Research → Pain/Theme RAG → Skeptic Audit → affiliate opportunity ranking. Ranking is configuration-driven and must expose component scores.

## Decision output
JSON: eligible, deterministic_gates{}, canonical_category, canonical_subcategory, pain_matches[], observed_network_kpis{}, modeled_economics{}, first_party_kpis|null, opportunity_components{}, final_score, evidence_confidence, verdict, reasons[].
