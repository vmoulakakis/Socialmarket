---
name: competition-gap
description: Measure Greek commercial/content saturation for canonical product intent and expose affiliate whitespace without fake keyword difficulty.
---
# Competition Gap

## Mission
Estimate whether a canonical product category, subcategory or validated product intent is under-served rather than merely popular.

## Semantic boundary
Competition research must be attached to canonical product taxonomy or an explicit demand theme. Never calculate competition for UI/navigation labels, locations, brands masquerading as subcategories, policy links or malformed text.

## Measure when evidence exists
- retailer/domain density in relevant Greek results
- marketplace duplication and repeated identical offers
- brand/merchant concentration
- SEO authority dominance
- Greek-language guide/review saturation
- near-identical promoted offers
- product/solution coverage for the validated pain intent
- affiliate program economics as a separate viability dimension, not a substitute for competition

## Long-tail tag policy
`low_competition_tags` are hypotheses unless actual competition evidence exists for the exact semantic phrase. Prefer specific pain/solution long-tail wording. Never claim measured keyword difficulty, CPC or search volume unless supplied by a trusted source.

## Rules
- Opportunity rises when validated demand/pain is strong and competing solution coverage is weak or fragmented.
- Low search evidence alone is not opportunity.
- High merchant-program EPC alone is not whitespace.
- Preserve evidence URLs/domains and timestamp.
- Distinguish product competition, content competition and merchant concentration.

## Output
JSON: canonical_category, canonical_subcategory, intent, retail_saturation, content_saturation, brand_concentration, authority_barrier, solution_coverage_gap, attention_gap, low_competition_tag_hypotheses[], evidence[], confidence, missing_metrics[].
