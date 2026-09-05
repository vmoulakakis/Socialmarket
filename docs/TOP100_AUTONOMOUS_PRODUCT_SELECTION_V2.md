# SocialMarket AI — Autonomous Top-100 Product Selection V2

## Objective
Maintain a rolling Top-100 sellable-opportunity set for Greece where diversity is controlled, commercial quality is evidence-based, and published opportunities are automatically retired from the active candidate list.

## Portfolio composition rule
- Maximum **5 distinct product families / categories** in the active Top-100.
- Each selected category should contain roughly 20 opportunities unless evidence strongly favors a different allocation.
- Do not fill the list with superficial SKU variants. Products inside a category must solve meaningfully different sub-problems, price bands, buyer profiles, or use cases.
- Category allocation is re-optimized daily from observed demand, scarcity, margin/commission potential and historical publishing/conversion outcomes.

## Eligibility gates
A candidate is eligible only when the evidence layer can support all material checks:
1. **Greece scarcity** — unavailable in major Greek retailers/marketplaces or demonstrably rare/hard to source locally.
2. **Commission floor** — expected commission **> €20** per confirmed sale after the current affiliate economics are applied.
3. **Greek-market sellability** — clear pain-gap, buyer persona, acceptable landed cost, shipping feasibility and realistic conversion path in Greece.
4. **Commercial intent** — evidence of search, social, marketplace, competitor, category, trend or adjacent-buyer demand.
5. **No invented seller/warranty claims** — seller geography, certifications, warranty, returns and stock are treated as unverified unless evidence proves them.

## Daily AI ranking model
Every daily run re-scores all eligible candidates using a composite opportunity score. Agents should synthesize rather than simply average metrics.

Recommended dimensions:
- demand now
- 7/30/90-day demand momentum
- forecast demand
- scarcity in Greece
- expected commission value
- conversion ease
- organic-content potential
- paid-ads viability
- pain severity / urgency
- competitive intensity
- landed-cost attractiveness
- seller/logistics risk
- evidence freshness
- historical SocialScheduler engagement / conversion feedback

The model must explicitly penalize:
- duplicated or near-identical products
- stale evidence
- products already published
- poor media readiness
- weak Greek-market fit
- regulatory or logistics friction
- categories that exceed the concentration cap

## Learning loop
Daily selection must become better from execution feedback:
1. SocialMarket creates an `approved publishing intent` with immutable product identity and `source_hash`.
2. SocialScheduler claims and publishes the approved item.
3. SocialScheduler writes execution/provider state back to the outbox.
4. Once provider reconciliation proves the item was published, SocialMarket sets the candidate state to `published` and records the platform/post IDs.
5. `published` candidates are excluded from the active Top-100 and the daily optimizer backfills them with the next-best eligible candidates.
6. Engagement, click, conversion and failure signals update category/product priors for future ranking.

## Required product lifecycle flags
Use these canonical states (or map existing database values to them):
- `candidate`
- `eligible`
- `selected_top100`
- `approved_for_social`
- `claimed_by_scheduler`
- `published`
- `retired`
- `blocked`

Required execution fields:
- `published_at`
- `published_platforms[]`
- `scheduler_execution_ids[]`
- `provider_post_ids[]`
- `source_hash`
- `selection_run_id`
- `selection_score`
- `selection_reasons[]`

## Viral / high-conviction exception
If the daily agents identify a product with unusually strong viral or commercial potential that is not materially available on major Greek sites:
- mark it `landing_candidate=true`;
- require fresh evidence and affiliate-link validation;
- generate an AFFINITY pain-gap / decision-tool landing page;
- deploy it as a **separate public production deployment** (a new Vercel project is optional; a separate deployment/domain boundary is sufficient);
- keep private SocialMarket admin routes and data out of the public deployment;
- publish the landing URL through the normal SocialMarket → SocialScheduler outbox path.

## Daily operating sequence
1. ingest fresh product/evidence signals
2. resolve Greek availability/scarcity
3. calculate affiliate commission economics
4. forecast demand and conversion probability
5. score candidates
6. optimize category allocation (≤5 categories)
7. remove provider-confirmed published items
8. backfill Top-100
9. generate/refresh approved social intents
10. generate AFFINITY landing candidate when threshold is met
11. send only approved intents to SocialScheduler
12. reconcile publish state and metrics back into learning features

## Definition of GREEN
The selection engine is GREEN only when:
- Top-100 contains ≤5 categories,
- every active candidate passes the commission and scarcity gates,
- no provider-confirmed published candidate remains in the active Top-100,
- all selected records have a current evidence timestamp and source hash,
- SocialScheduler reconciliation is readable,
- any auto-created public landing deployment is isolated from the private admin surface.
