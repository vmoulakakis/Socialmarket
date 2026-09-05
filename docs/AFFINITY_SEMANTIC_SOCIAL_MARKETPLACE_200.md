# AFFINITY Semantic Social Marketplace 200

Status: canonical production architecture
Market: Greece
Portfolio size: 200 active opportunities

## 1. Product thesis

This is not a Top-100 feed and not a generic affiliate storefront. It is a semantic pain-to-solution marketplace.

A visitor starts from a job, pain, constraint or desired outcome. The system maps that intent to a curated product opportunity whose commercial facts, merchant/seller quality and Greek-market position have been audited.

Semantic hierarchy:

`niche -> subniche -> job_to_be_done -> pain -> market_gap -> solution -> product`

Internal ranking is evidence-first. Public presentation is buyer-first.

## 2. Two independent 100-product portfolios

### Linkwise Discovery 100

- Scan the full Linkwise joined-program product universe as a stream.
- Do deterministic work before AI: merchant resolution, commission arithmetic, stock, tracking, image, safety, price integrity, canonicalization and deduplication.
- Expected commission must be strictly greater than EUR 30.
- Merchant must pass all merchant gates.
- Maximum 3 selected products per merchant.
- Select 10 semantic opportunity clusters and up to 10 materially different products per cluster.
- AI is used only on bounded evidence-rich candidates after deterministic filtering.

Merchant production gate:

- `trust_score >= 65`
- `research_confidence >= 0.55`
- `global_rank <= 100`
- `risk_flag = false`
- merchant/program resolution must be deterministic

The current merchant score scales make these thresholds deliberately selective. They are stored in configuration and may only be changed explicitly; underfill is preferred to hidden quality relaxation.

### AliExpress Exclusive 100

- Use the authenticated AliExpress affiliate API.
- Search from semantic opportunity/JTBD queries, not generic trending lists alone.
- Expected commission must be strictly greater than EUR 30.
- Delivery target is Greece.
- Maximum 3 products per seller.
- Product and seller quality evidence is mandatory.
- Greek availability must classify as `ABSENT` or `VERY_RARE`.
- `UNKNOWN`, `AVAILABLE` and `FUNCTIONAL_EQUIVALENT_EXISTS` are rejected from the exclusive portfolio.
- Search exact model, aliases/OEM/rebrands and functional equivalents.

Minimum Greek surfaces:

- Skroutz
- BestPrice
- Public
- Kotsovolos
- Plaisio
- relevant specialist Greek retailers
- broader Greek web search

Absence from one marketplace is never enough to prove scarcity.

## 3. Agent hierarchy

### Opportunity Cartographer

Builds evidence-backed semantic opportunity clusters from validated pain clusters, category demand, Greek market context, seasonality and observed social/affiliate feedback.

It does not select products.

### Source Miners

Linkwise Miner and AliExpress Miner search their own source universes using the selected semantic clusters.

### Product Research Agent

For each bounded candidate, builds the positive commercial case using only supplied evidence.

Outputs:

- semantic fit
- Greek demand fit
- pain fit
- whitespace
- audience
- use case
- organic potential
- paid media potential
- product-quality evidence score
- source-quality evidence
- conversion architecture suggestion

### Skeptic / Quality Agent

Independently tries to reject the product.

It checks:

- unsupported product claims
- weak identity
- weak merchant/seller evidence
- hidden Greek equivalent
- bad shipping/returns/warranty signals
- commission inconsistency
- misleading novelty
- category mismatch
- weak pain fit
- safety/regulatory risk
- duplicate/variant pollution
- evidence contradictions

Only `validated` products may be selected.

### Portfolio Optimizer

Hard constraints are applied before optimization.

Linkwise:

- target 100
- 10 semantic clusters
- up to 10 products per cluster
- max 3 products per merchant

AliExpress:

- target 100
- max 3 products per seller
- semantic/category diversity
- no Greek availability outside the exclusive gate

The optimizer cannot relax commission, merchant/seller quality, Skeptic, tracking, safety or Greek-market gates to fill a quota.

## 4. Product quality assurance

The system cannot physically guarantee product quality. It guarantees a documented quality-evidence process.

`product_quality_score` represents the strength of evidence supporting a commercially responsible recommendation, not a laboratory certification.

The score incorporates as available:

- merchant/seller trust
- identity/specification completeness
- review/order evidence from authoritative source fields
- return/warranty evidence
- logistics practicality
- price integrity
- product documentation
- source consistency
- safety/compliance red flags
- contradiction audit

Minimum selected score: 75/100.

## 5. AFFINITY score

Hard gates always override score.

Suggested components:

- Greek demand: 16
- pain intensity: 12
- Greek whitespace: 14
- differentiation: 8
- commission economics: 10
- merchant/seller trust: 10
- price/value: 8
- logistics: 6
- warranty/returns: 5
- organic potential: 5
- paid potential: 3
- demonstrability/viral: 3

Minimum selected AFFINITY score: 76/100.

## 6. Evidence and semantics

Every selected item stores:

- semantic cluster key
- niche/subniche
- job to be done
- pain statement
- gap statement
- solution statement
- evidence summary
- semantic tags
- research scores
- Skeptic verdict
- merchant/seller quality fields
- Greek availability classification

Verified facts and model inference must remain distinguishable in the evidence ledger.

## 7. Public marketplace experience

Public UX is not a conventional category catalogue.

Hero concept:

> Do not search for a product. Start with what you need to fix.

Primary interaction:

1. Search a pain/outcome in natural language.
2. Semantic filters surface relevant pain clusters.
3. Product cards explain `Pain -> Gap -> Solution`.
4. Trust/evidence signals are displayed without exposing internal affiliate economics.
5. CTA uses the verified affiliate deep link.

The public marketplace never exposes internal commission values, model prompts or operator-only diagnostics.

## 8. Admin control plane

Private admin must expose:

- Linkwise selected / 100
- AliExpress selected / 100
- semantic clusters
- max products per merchant/seller observed
- merchant rank/trust/confidence
- exact expected commission
- product quality score
- AFFINITY score
- Greek availability
- Research + Skeptic reasoning summaries
- evidence ledger
- tracking URL
- SocialScheduler lifecycle
- provider-confirmed published state
- rejection/hold gate counts

All policy failures are visible. No silent fallback.

## 9. SocialScheduler boundary

`SocialMarket -> SocialScheduler -> Buffer/provider`

Lifecycle:

`SELECTED -> CONTENT_READY -> SOCIALSCHEDULER -> CLAIMED -> PROVIDER_SCHEDULED -> PROVIDER_CONFIRMED_PUBLISHED -> LEARNING_HISTORY`

Provider-confirmed publication is the truth signal.

Published source hashes are excluded from future active selection runs.

## 10. Social content

Each selected product generates a structured creative object:

- buyer
- pain
- JTBD
- primary hook
- alternative hooks
- proof points
- objections
- Greek market angle
- caption
- hashtags
- CTA
- image/media
- verified affiliate URL
- recommended social formats

AFFINITY landing pages are selective. Build one only when education, comparison, calculation, configuration or trust-building is likely to materially improve conversion.

## 11. Feedback learning

Observed publishing and affiliate outcomes become priors for future runs:

- niche prior
- subniche prior
- merchant/seller prior
- product-type prior
- hook prior
- platform prior

Engagement is not automatically treated as purchase demand.

## 12. Failure philosophy

The system must fail visibly and conservatively.

Examples:

- 84 valid Linkwise products => show 84/100, do not weaken merchant gates.
- 61 AliExpress products with verified >EUR30 commission and Greek scarcity => show 61/100, do not add lower-commission products.
- Greek research unavailable => `UNKNOWN` and reject from AliExpress Exclusive.
- malformed AI JSON => retry/bisect/quarantine candidate; do not erase the entire portfolio.

Quality is a hard contract, not a target-filling preference.
