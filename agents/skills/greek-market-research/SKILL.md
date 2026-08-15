---
name: greek-market-research
description: Run evidence-first Greek market research for categories, subcategories, pains, alternatives, prices, merchant supply and official context without fabricating unavailable metrics.
---

# Greek Market Research

## Objective

Discover what Greek consumers are trying to achieve, what blocks them, what alternatives they seek, and how much credible solution coverage exists.

## Query families

Use canonical taxonomy aliases and natural Greek language. Expand across:

- αγορά / θέλω / ψάχνω / καλύτερο / αξίζει
- πρόβλημα / παράπονα / μειονεκτήματα
- πολύ ακριβό / φθηνότερο / οικονομικότερο
- δεν βρίσκω / δεν υπάρχει / εξαντλημένο
- εναλλακτική / χωρίς συνδρομή / χωρίς προμήθεια
- για παιδιά / ηλικιωμένους / ταξίδι / μικρό χώρο / κατοικίδια
- επιστροφή / παράδοση / εγγύηση / υποστήριξη
- comparison / reviews / forums / Reddit / YouTube / public social web

Do not treat query-result count as search volume.

## Source tiers

1. Official Greek/EU statistics and public institutions — contextual/exogenous evidence.
2. First-party merchant/product pages — supply/availability/product facts.
3. Independent reviews, forums and discussion sources — pain/experience evidence.
4. Search-engine discovery pages — discovery only; inspect the underlying source.
5. Public social observations — lower confidence unless structured/verified.

## Evidence record

Persist source URL, title/body, collector, timestamp, geography, confidence, source class, query, entity/taxonomy binding and content hash.

## Quality gates

- category/entity relevance must pass
- at least two independent source types for strong claims
- source diversity is not raw row count
- duplicate syndication does not count as diversity
- stale evidence lowers confidence
- promotional/navigation noise is rejected
- official context may contextualize demand but cannot inflate a demand proxy unless it directly measures the relevant phenomenon

## Research synthesis

Separate:

- explicit demand
- consideration intent
- pain / dissatisfaction
- desired outcome
- constraint
- switching trigger
- alternative request
- supply coverage
- price/availability facts
- season/event context
- contradiction

## Greek-market report

For each taxonomy node produce:

- evidence-backed market thesis
- strongest observed signals
- pain/JTBD clusters
- source diversity/freshness
- merchant/supply structure
- missing evidence
- alternative explanations
- cheapest next research action
