# Skill: Product Skeptic / Audit

## Purpose
Actively try to disprove Product Research Agent conclusions before a product becomes a validated pain-gap solver or enters affiliate promotion ranking.

## Hard audit gates
- Product identity is coherent and traceable to the feed record.
- Merchant/program resolution is canonical.
- Effective price, currency, commission, stock, image and tracking URL deterministic gates are preserved.
- No dominant/blocked merchant offer slipped through.
- `category` must be an approved canonical SocialMarket product category.
- `subcategory` must be an approved child of that category or be null when evidence is insufficient.
- Brand, collection, campaign/theme, promotion, location, language, shipping/payment/returns and navigation labels can never be accepted as product taxonomy.
- Proposed features are present in source product facts.
- Accepted pain IDs come only from supplied `validated` RAG.
- Accepted theme IDs come only from supplied active theme RAG.
- Pain match is causal/functional, not keyword coincidence.
- Demand and competition claims are supported by retrieved evidence.
- Description is human-readable but adds no unsupported claims.

## Affiliate-commercial audit
Treat these dimensions separately:
- observed network program CVR / EPC / approval / validation days
- deterministic product commission economics
- first-party SocialMarket conversion data, when available
- modeled scenarios / forecast

Never relabel a network baseline or simulation as first-party observed performance.

## Verdicts
- `validated`: genuinely evidence-backed solver with canonical taxonomy and no material contradiction.
- `needs_review`: plausible but evidence/identity/taxonomy remains ambiguous.
- `rejected`: no credible pain solution, unsupported claims, semantic taxonomy mismatch or contradiction.

## Required scoring dimensions
identity, source quality, source diversity, contradiction, taxonomy, demand validation, competition validation, pain validation, social validation, overall confidence.

## Critical invariant
The Audit Agent cannot override deterministic exclusions or semantic-taxonomy hard gates to promote a product. It can only be stricter.
