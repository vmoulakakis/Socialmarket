# SocialMarket AI — Master Architecture & Implementation Source of Truth

**Status date:** 2026-08-15  
**Repository:** `vmoulakakis/Socialmarket`  
**Primary Supabase project:** `socialmarket` / `rpfadpdnnxequgvdcfoq`  
**Document purpose:** single source of truth for architecture, implementation state, data contracts, scoring logic, AI agents, validation gates, production workflows, risks, blockers and execution roadmap.

---

## 1. Executive status

SocialMarket has two distinct intelligence layers:

1. **Merchant Intelligence** — merchant/program research, trust, category/subcategory, demand, competition, pain-gap, social evidence and semantic retrieval.
2. **Product Intelligence** — Linkwise product-feed processing, merchant resolution, commission gating, canonical product creation, product-to-pain RAG, Product Research Agent, Skeptic/Audit Agent and product opportunity ranking.

### Current state

| Area | Status | Meaning |
|---|---|---|
| Merchant foundation | ✅ Implemented | 309 canonical merchant programs imported; merchant research/data model exists |
| Merchant daily research | ✅ Implemented | GitHub/SearXNG worker and daily orchestration exist |
| Merchant social evidence schema | ✅ Implemented | social snapshots, mentions and pain clusters exist |
| Merchant audit architecture | ✅ Implemented / still evolving | audit tables and validation fields exist |
| Product schema | ✅ Implemented | additive product intelligence DB layer created |
| Product Intelligence gateway | ✅ Active | secure GitHub OIDC/Supabase gateway deployed |
| Product deterministic Phase A | ✅ Working | real 3.84 GB feed can be downloaded and streamed |
| Product AI Phase B | ⛔ Blocked | `DEEPSEEK_API_KEY` is not configured in the new Supabase Edge environment |
| Linkwise merchant/program mapping | ⚠️ Unresolved | first real scan returned `merchant_unresolved` for all recovered records |
| Product persistence | ✅ Safely blocked | zero products/offers/audits persisted until mapping + AI audit are valid |
| End-to-end Product Intelligence | ❌ Not production-ready yet | requires feed-contract resolution + DeepSeek configuration + validated run |

**Key principle:** architecture readiness is not the same as data readiness. No product is considered production-ready until the feed contract is resolved and the Product Research + Skeptic Audit path completes successfully.

---

## 2. Non-negotiable design principles

### 2.1 Evidence first

No demand, competition, trust, pain, product opportunity or merchant opportunity score may be invented by an LLM.

Every score must be traceable to one or more of:

- source feed fields,
- merchant/program commercial data,
- public-web evidence,
- search evidence,
- social/review evidence,
- deterministic calculations,
- validated semantic clusters,
- explicit audit outputs.

Missing evidence remains missing. It is **not converted to zero unless the metric definition explicitly requires zero**.

### 2.2 LLMs do not perform deterministic work

LLMs must not be used for:

- database inserts/updates that can be done directly,
- arithmetic commission calculations,
- exact filtering,
- simple deduplication,
- hashing,
- basic normalization,
- direct merchant/program joins.

Use Python/SQL first. Use DeepSeek only where language reasoning materially improves the result.

### 2.3 Merchant and product intelligence are separate but connected

A merchant can be useful as a **Demand/Pain Beacon** while being a poor direct commercial opportunity.

A product can be commercially attractive only when:

- the merchant is resolved,
- commission is correctly calculated,
- the product solves a validated need/pain,
- competition is realistic,
- merchant trust passes minimum gates,
- Product Research and Skeptic Audit both support the recommendation.

### 2.4 No fake fallback

If AI configuration is absent or research confidence is insufficient:

- stop the AI phase,
- keep deterministic diagnostics,
- do not manufacture enrichment,
- do not persist a fake `VALIDATED` result.

### 2.5 Preserve raw provenance

The 3.84 GB product source is processed as a stream. It is **not wholesale-imported into Supabase**.

Persist only:

- canonical products,
- eligible offers,
- research snapshots,
- evidence references,
- audit outputs,
- semantic objects,
- compact run profiles.

---

## 3. Infrastructure truth

### 3.1 Supabase

Production project:

```text
name: socialmarket
project_ref: rpfadpdnnxequgvdcfoq
region: eu-west-1
PostgreSQL: 17.x
```

Old project that must not be used for new work:

```text
socialmarket-ai
project_ref: prrehmcvpyhupvlhtbzg
```

### 3.2 GitHub

Primary repo:

```text
vmoulakakis/Socialmarket
```

Product Intelligence V1 was merged into `main` after passing:

- Product Intelligence CI,
- Merchant Intelligence CI,
- Next.js build.

The Product Intelligence architecture is additive and must not rewrite the merchant engine.

### 3.3 SocialScheduler boundary

`vmoulakakis/socialscheduler` remains the execution-only publishing layer.

Desired boundary:

```text
SocialMarket = intelligence + content source of truth
SocialScheduler = publishing executor
Buffer = final social publisher
```

The Scheduler must eventually point only to the new SocialMarket Supabase project.

---

## 4. Merchant Intelligence foundation

### 4.1 Imported merchant/program universe

Source merchant CSV:

```text
programs (5)(6).csv
```

Verified facts:

- 310 CSV rows,
- 309 valid merchant programs,
- one blank/rejected row retained in raw provenance,
- source encoding: `cp1253`,
- raw source file preserved in the database layer.

### 4.2 Core merchant schemas

Existing logical layers include:

```text
raw.*
catalog.*
intel.*
ai.*
ops.*
content.*
publish.*
api.*
```

Important merchant entities include:

```text
catalog.merchants
catalog.merchant_programs
catalog.merchant_aliases
catalog.taxonomy_nodes

intel.program_commercial_snapshots
intel.merchant_evidence
intel.merchant_research_snapshots
intel.merchant_taxonomy_snapshots
intel.merchant_site_snapshots
intel.category_market_snapshots
intel.merchant_social_snapshots
intel.merchant_social_mentions
intel.merchant_audit_results

ai.semantic_objects
ai.social_pain_clusters

ops.research_jobs
ops.executor_controls
```

### 4.3 Merchant commercial ranking

Commercial-only ranking is a monetization signal, **not consumer demand**.

Never equate:

```text
EPC == demand
commission == demand
affiliate conversion == demand
```

Commercial ranking must remain a separate dimension from Demand Beacon and Solution Whitespace.

### 4.4 Merchant dual-role model

#### Demand/Pain Beacon

High score means the merchant is a valuable evidence source for:

- consumer search activity,
- review volume,
- social conversation,
- repeated complaints,
- repeated desired alternatives,
- engagement,
- category breadth.

Large merchants may score very high here.

#### Solution Whitespace

High score means a realistically exploitable opportunity exists:

- high Greek demand,
- repeated pain,
- meaningful unmet need,
- lower realistic saturation/competition,
- acceptable merchant/product trust,
- strong semantic fit.

Large saturated merchants can be excellent Demand Beacons but weak Solution Whitespace targets.

---

## 5. Merchant research architecture

```text
MERCHANT
  ├─ SITE
  │   ├─ SearXNG discovery
  │   ├─ Scrapy deep crawl
  │   ├─ Trafilatura content extraction
  │   └─ Lighthouse technical SEO
  │
  ├─ SEARCH / MARKET
  │   ├─ SearXNG
  │   ├─ Google suggestions/public search evidence
  │   └─ optional SERP history
  │
  └─ SOCIAL / REVIEWS
      ├─ YouTube public evidence / yt-dlp fallback
      ├─ Reddit/public web
      ├─ Instagram public observation
      ├─ Facebook public observation
      └─ TikTok public observation
              ↓
        EVIDENCE STORE
              ↓
        AUDIT / SKEPTIC LAYER
              ↓
        PAIN GAP ENGINE
              ↓
        VECTOR / RAG LAYER
```

### Social evidence rule

Comments and repeated language are more useful for pain discovery than raw likes.

Examples of useful pain statements:

- too expensive,
- need a smaller version,
- does not ship to Greece,
- want without subscription,
- need an option for children,
- unavailable size,
- need a cheaper alternative,
- need simpler setup,
- product is good but a specific feature is missing.

Do not invent unavailable social metrics.

---

## 6. Semantic / RAG architecture

Do not store only one embedding per merchant.

Target semantic object types:

```text
merchant_profile
category
subcategory
product_need
positive_review_cluster
complaint_cluster
social_comment_cluster
pain_cluster
unmet_need_cluster
alternative_request_cluster
product_solution
seasonal_theme
```

### Cluster repeated pain

Do not embed every raw comment individually if many comments express the same need.

Preferred object:

```text
Pain Cluster
- canonical statement
- raw examples / source references
- frequency
- engagement when available
- source diversity
- severity
- commercial intent
- category/subcategory
- Greek demand
- competition
- confidence
- validation state
- embedding
```

Only audited/validated clusters should drive production product recommendations.

---

## 7. Product Intelligence — source feed

### 7.1 Source

Primary product source:

```text
Google Drive file: linkwise-products.json
size: ~3.84 GB
```

The feed is processed read-only inside ephemeral GitHub runners.

### 7.2 Known product fields from existing streaming code

Previously observed fields include:

```text
product_id
model_name
product_name
description
category
brand_name
tracking_url
thumb_url
image_url
in_stock
availability
valid_from
valid_to
on_sale
currency
price
full_price
discount
city
times_bought
longitude
latitude
address
size
colour
program_name
custom
extra_images
```

**Important:** current real-feed scan proved that the merchant/program identifier contract is not yet correctly mapped in Product Intelligence V1. Existing field assumptions must not be trusted until the JSON feed diagnostic completes and is verified.

### 7.3 First production scan result

The first safe scan recovered:

```text
2,668,657 complete records
```

before encountering a truncated JSON tail.

Result:

```text
merchant_unresolved: all recovered records
products persisted: 0
offers persisted: 0
product research snapshots: 0
product audits: 0
```

This is a successful safety outcome, not a successful product import.

The system correctly refused to persist unresolved products.

### 7.4 Feed integrity policy

If the JSON ends prematurely:

- salvage only complete records already parsed,
- mark run as truncated/incomplete,
- never claim complete Linkwise universe coverage,
- never silently ignore the integrity warning.

---

## 8. Product Intelligence — two-phase architecture

### Phase A — deterministic scan

Phase A can run without DeepSeek.

```text
3.84 GB Linkwise feed
        ↓
stream parser
        ↓
feed normalization
        ↓
merchant/program resolution
        ↓
dominant-merchant policy
        ↓
expected commission calculation
        ↓
commission >= €10 hard gate
        ↓
canonical deduplication
        ↓
RAG candidate profiling
        ↓
compact run profile
```

Phase A must not persist production products when merchant resolution is incomplete.

### Phase B — AI Research + Skeptic Audit

Phase B requires valid DeepSeek configuration.

```text
eligible canonical candidates
        ↓
merchant RAG
        +
validated pain RAG
        +
seasonal/theme RAG
        ↓
Product Research Agent
        ↓
Skeptic / Audit Agent
        ↓
deterministic gates
        ↓
VALIDATED / REJECTED / NEEDS_REVIEW
        ↓
production persistence only if allowed
```

No DeepSeek secret = Phase B skipped.

---

## 9. Commission logic

### 9.1 Core policy

There is **no arbitrary minimum product-price rule**.

Eligibility is driven by expected affiliate revenue:

```text
expected_commission_eur >= 10.00
```

### 9.2 Commission sources

Commission must come from the canonical merchant program, not from an LLM.

Examples of source rules:

```text
percentage commission
flat commission
percentage range
flat range
mixed rule where explicitly supported
```

### 9.3 Conservative range handling

For a commission range such as:

```text
3% - 10%
```

use the conservative minimum unless there is deterministic category/product evidence identifying the exact tier.

### 9.4 Effective price

Use the actual eligible sale/current price when valid.

Example:

```text
price = €140
commission = 9%
expected = €12.60
=> passes €10 gate
```

Example:

```text
price = €500
commission = 1.5%
expected = €7.50
=> fails gate
```

This is why `price >= X` is not a valid substitute for commission calculation.

---

## 10. Merchant resolution contract

This is the current P0 data blocker.

Required logic:

```text
feed merchant/program identifier
        ↓
normalization
        ↓
exact canonical program match
        ↓
known alias match
        ↓
domain / clean-site corroboration
        ↓
confidence
        ↓
resolved merchant_id + merchant_program_id
```

### Resolution rules

1. Prefer exact normalized program identifiers.
2. Use `catalog.merchant_aliases` for known deterministic aliases.
3. Use clean/official domain only as corroborating evidence.
4. Never overwrite an authoritative clean URL with weaker search discovery.
5. Do not use fuzzy matching blindly across millions of products.
6. Any ambiguous merchant mapping must become `NEEDS_REVIEW`, not guessed.
7. Cache resolved program mapping locally during a feed run; do not repeatedly query the DB for each record.

### Current diagnostic

A JSON feed-contract diagnostic is now part of the repo to inspect a bounded sample of the real source and identify:

- actual field names,
- field types,
- merchant/program-like identifiers,
- top identifier distributions,
- compact sample values.

It must remain read-only.

---

## 11. Dominant merchant policy

Examples include large platforms/retailers such as major marketplaces and very high-saturation retailers.

Policy:

```text
Dominant merchant
    ├─ allowed as Demand/Pain Beacon
    ├─ allowed as competition evidence
    ├─ allowed as review/social pain evidence
    └─ may be excluded from direct promotion/whitespace ranking
```

Do not discard their evidence. Separate **evidence value** from **promotion value**.

---

## 12. Canonical product model

The feed can contain duplicates/variants/repeated offers. Product Intelligence must create a stable canonical layer.

### Canonical product identity candidates

Use strongest available evidence in this order:

1. stable external product ID when scoped correctly,
2. merchant + stable product ID,
3. brand + normalized model/SKU,
4. brand + normalized product name + meaningful attributes,
5. deterministic canonical key fallback.

### Never merge solely because names look similar

Variants such as:

- size,
- colour,
- storage capacity,
- model generation,
- bundle,
- package quantity

may be commercially distinct.

### Product vs offer

```text
canonical product = what the item is
merchant offer    = how/where it is currently sold
```

Offer contains price, availability, tracking link, merchant/program and calculated commission.

---

## 13. Product RAG inputs

Each candidate product should be evaluated against three evidence families.

### A. Merchant RAG

- trust,
- risk,
- Greek fit,
- merchant category/subcategory,
- validated reputation,
- competition/saturation,
- merchant whitespace.

### B. Pain RAG

- repeated pain clusters,
- unmet needs,
- alternative requests,
- constraints,
- desired outcomes,
- commercial intent,
- source diversity.

### C. Theme / seasonal RAG

Examples:

```text
Back to School 2026
parents
students
teachers
home office
travel
Christmas
gifting
summer
fitness
home organisation
```

Themes are contextual relevance signals; they are not substitutes for demand evidence.

---

## 14. Product Research Agent

### Role

Determine whether a deterministic candidate is a credible solution to validated demand/pain.

### Inputs

The agent receives compact evidence only:

- product facts,
- merchant facts,
- commission result,
- relevant validated pain IDs,
- relevant theme IDs,
- market/competition evidence,
- evidence confidence.

### Agent constraints

The Product Research Agent must:

- use only supplied RAG/evidence IDs,
- not invent reviews,
- not invent demand volume,
- not invent competition,
- not change deterministic commission,
- not fabricate merchant identity,
- explicitly report insufficient evidence.

### Output

Structured output should contain:

```text
solution_fit
pain_ids_used
merchant_evidence_ids_used
theme_ids_used
strengths
weaknesses
risk_flags
reasoning_summary
recommended_state
confidence
```

---

## 15. Skeptic / Audit Agent

The Skeptic Agent is separate from Product Research.

Its job is to try to disprove the recommendation.

### Audit questions

- Is the merchant mapping correct?
- Is commission truly >= €10?
- Is the product actually the same item represented by the canonical record?
- Does the product really solve the referenced pain?
- Is the pain validated and fresh?
- Is the competition score supported?
- Is this merely a popular product rather than whitespace?
- Is the merchant too saturated for promotion?
- Are sources sufficiently diverse?
- Are there contradictions?
- Is any score based on missing data?
- Is the affiliate/tracking offer currently valid?

### Audit outcomes

```text
VALIDATED
REJECTED
NEEDS_REVIEW
```

Only `VALIDATED` candidates may enter production recommendation retrieval.

---

## 16. Product Opportunity score

Current intended weighting:

```text
25% Pain-Gap Fit
20% Merchant Solution Whitespace
15% Greek Demand
12% Expected Commission
10% Inverse Competition
 8% Seasonal / Thematic Demand
 5% Merchant Trust
 3% Discount
 2% Evidence Confidence
```

### Hard gates precede weighted scoring

A high weighted score cannot override:

- unresolved merchant,
- commission below €10,
- invalid/unsafe merchant,
- invalid tracking URL,
- rejected audit,
- insufficient identity confidence,
- severe contradiction.

---

## 17. Product persistence rule

Supabase must not become a copy of the giant source feed.

Persist only what is needed for intelligence and retrieval.

Expected product-layer concepts:

```text
catalog.products
catalog.product_offers
intel.product_research_snapshots
intel.product_audit_results
ai.semantic_objects (product_solution / related semantic objects)
```

Exact physical definitions are controlled by the migration files in the repository.

### Persistence sequence

```text
resolve merchant
→ calculate commission
→ pass hard gates
→ canonicalize
→ research
→ audit
→ persist/update canonical product + eligible offer
→ create semantic object
→ embed
→ expose only validated records to production API/view
```

---

## 18. Embeddings

Current merchant production path has used Supabase-native `gte-small` / 384 dimensions for some objects.

Historical architecture also considered multilingual BGE-M3 / 1024 dimensions.

Do not treat them as equivalent.

Every semantic record must track:

```text
embedding_model
embedding_dimensions
embedding_version
content_hash
embedded_at
status
```

Recommended short-term policy: keep the currently operational free/native embedding path consistent unless a deliberate migration to BGE-M3 is executed and versioned.

---

## 19. Edge functions / gateways

Relevant active functions include merchant research/evidence/semantic infrastructure plus Product Intelligence.

Product gateway:

```text
slug: product-intelligence-gateway
purpose: GitHub OIDC protected product research/persistence boundary
```

Current health check confirmed:

```text
gateway: healthy
deepseek_configured: false
target model configured by gateway: deepseek-v4-pro
```

Do not run AI Product Phase B until the secret is present and a model health request succeeds.

---

## 20. GitHub Actions

### Product Intelligence V1

Production workflow supports:

```text
workflow_dispatch
scheduled execution
path-scoped controlled triggers
```

Run sequence:

```text
checkout
→ Product Gateway health
→ setup Python
→ download source feed read-only
→ Phase A deterministic scan
→ Phase B only if DeepSeek configured
→ upload compact profile/artifacts
→ delete raw feed + local staging
```

### Safety

Raw feed must be deleted from the ephemeral runner after processing, including failure paths.

Artifacts must contain only compact diagnostics/profiles, not the 3.84 GB source.

---

## 21. Security / RLS

RLS must be designed deliberately.

Never blindly enable RLS without policies if it breaks workers.

Preferred boundary:

```text
internal/raw/intel tables
    ↓ private worker/service access
controlled api.* / public read views
    ↓ application consumers
```

GitHub workers should use OIDC/gateway paths instead of storing Supabase service-role/database credentials in repository secrets where avoidable.

Before public production, run a complete security audit for:

- RLS status,
- exposed schemas,
- SECURITY DEFINER functions,
- anon grants,
- authenticated grants,
- Edge function JWT configuration,
- secrets,
- stale old-project URLs.

---

## 22. Clean merchant links

The clean-links workbook exists and contains merchant destination URLs.

Important distinction:

```text
actual_http_site / destination URL != final Linkwise affiliate tracking URL
```

Do not invent final affiliate deeplinks.

A clean destination URL can be used for merchant identity corroboration, but final tracking URLs require verified Linkwise program/action data.

If clean URL and web discovery disagree:

- do not overwrite the clean URL automatically,
- record a contradiction,
- send to audit/review.

---

## 23. Current blockers — P0

### P0.1 Resolve actual Linkwise feed merchant/program contract

Current Product Intelligence assumes a merchant/program field that did not resolve against the 309 merchants in the real run.

Required next result:

```text
actual feed field/value
→ exact/alias mapping table
→ merchant_id
→ merchant_program_id
```

Acceptance criterion:

- high resolution rate,
- explainable mapping,
- no broad fuzzy guesses,
- dominant merchant mappings explicitly recognized,
- unresolved remainder quantified.

### P0.2 Configure DeepSeek in new Supabase

Required:

```text
DEEPSEEK_API_KEY
```

in the new SocialMarket Supabase Edge environment.

Acceptance criterion:

- gateway health shows configured,
- one test Product Research request succeeds,
- one Skeptic Audit succeeds,
- structured schema validates,
- no fallback hallucination.

### P0.3 Re-run Product Intelligence end to end

After P0.1 + P0.2:

1. run deterministic scan,
2. verify merchant-resolution distribution,
3. verify commission distribution,
4. inspect dominant merchant exclusions,
5. run Product Research Agent,
6. run Skeptic Audit,
7. persist only audited records,
8. query DB counts,
9. manually inspect a statistically useful sample,
10. only then mark Product Intelligence production-ready.

---

## 24. P1 improvements

### Merchant taxonomy quality

Fix subcategory extraction so navigation labels do not become taxonomy.

Prefer:

- schema.org breadcrumbs,
- sitemap/category paths,
- product-grid headings,
- repeated stable URL segments,
- Trafilatura-cleaned content.

Return NULL when evidence is weak.

### Social evidence collectors

Free/no-API first:

- SearXNG,
- Trafilatura,
- Scrapy,
- yt-dlp,
- Playwright,
- guarded public-web collectors.

Public social scraping must use lower confidence than official structured sources.

### Audit expansion

Add deterministic gates for:

- source diversity,
- evidence freshness,
- impossible zero competition,
- domain contradictions,
- taxonomy nonsense,
- weak social-account match,
- insufficient pain evidence.

---

## 25. P2 integration

After Product Intelligence is validated:

```text
Validated Product Opportunity
        ↓
Content Agent
        ↓
content.items / campaign object
        ↓
publish.outbox
        ↓
SocialScheduler
        ↓
Buffer
```

Publishing must never bypass audit status.

---

## 26. Recommended repo structure

```text
Socialmarket/
├─ agents/
│  ├─ ORCHESTRATOR.md
│  ├─ merchant_*.md
│  ├─ product_research_agent.md
│  └─ product_skeptic_agent.md
│
├─ workers/
│  ├─ market_intelligence/
│  ├─ evidence/
│  └─ product_intelligence/
│     ├─ stream_feed.py / shared parser
│     ├─ product_agents.py
│     ├─ product_intelligence_v1.py
│     ├─ product_phase_a_scan.py
│     └─ feed-contract diagnostics
│
├─ supabase/
│  ├─ functions/
│  │  ├─ merchant-research-gateway/
│  │  ├─ evidence-gateway/
│  │  ├─ semantic-pain-search/
│  │  └─ product-intelligence-gateway/
│  └─ migrations/
│
├─ .github/workflows/
│  ├─ merchant intelligence CI/production
│  ├─ product intelligence CI/production
│  └─ feed-contract diagnostics
│
└─ docs/
   └─ SOCIALMARKET_MASTER_ARCHITECTURE.md
```

---

## 27. Production acceptance checklist

SocialMarket Product Intelligence is **production-ready only when every item below is true**.

### Feed

- [ ] real JSON contract documented
- [ ] truncated-tail behavior tested
- [ ] recovered coverage measured
- [ ] merchant/program field verified

### Merchant resolution

- [ ] resolution rate measured
- [ ] exact + alias matching validated
- [ ] ambiguous mappings isolated
- [ ] dominant merchants correctly flagged

### Commission

- [ ] percentage rules tested
- [ ] flat rules tested
- [ ] range rules tested conservatively
- [ ] sale price handling tested
- [ ] `>= €10` hard gate verified
- [ ] no legacy minimum-price gate remains

### Product canonicalization

- [ ] duplicate handling tested
- [ ] variants not incorrectly merged
- [ ] stable canonical keys defined

### RAG

- [ ] merchant context attached
- [ ] validated pain clusters attached
- [ ] seasonal themes attached
- [ ] evidence IDs preserved

### AI

- [ ] DeepSeek secret configured
- [ ] Product Research structured output tested
- [ ] Skeptic Audit tested
- [ ] invalid JSON/timeout retry policy tested
- [ ] no fake fallback exists

### Database

- [ ] products/offers persisted only after gates
- [ ] audit state recorded
- [ ] semantic objects created only as intended
- [ ] API views expose validated records only

### Security

- [ ] RLS/grants audited
- [ ] no old Supabase URL remains in new production paths
- [ ] no service-role secret committed
- [ ] OIDC gateways verified

### Observability

- [ ] run profile contains counts by stage
- [ ] rejection reasons counted
- [ ] unresolved merchants counted
- [ ] commission bands counted
- [ ] audit outcomes counted
- [ ] failures/errors recorded without losing provenance

---

## 28. Definition of done

The project is not done because code exists.

It is done when a real production run can prove the following chain:

```text
real Linkwise record
→ correct canonical merchant/program
→ deterministic expected commission >= €10
→ correct canonical product
→ relevant validated pain/theme context
→ Product Research recommendation
→ independent Skeptic validation
→ production DB persistence
→ semantic retrieval
→ content eligibility
→ publish outbox
→ SocialScheduler execution
```

Every arrow must be observable and auditable.

---

## 29. Immediate execution order

### Step 1
Finish JSON feed-contract diagnostic and identify the true merchant/program identifier.

### Step 2
Patch resolver and run bounded validation against the 309 canonical merchant programs.

### Step 3
Re-run Phase A and obtain real counts:

```text
records recovered
resolved merchant offers
unresolved offers
commission >= €10
commission < €10
dominant exclusions
unique canonical products
merchant distribution
category distribution
```

### Step 4
Configure DeepSeek secret and validate gateway model call.

### Step 5
Run Phase B on a bounded representative candidate set first.

### Step 6
Audit results manually + automatically.

### Step 7
Only after bounded validation, run full production persistence.

### Step 8
Expose validated product opportunities to the application/content pipeline.

---

## 30. Decision log

### Accepted decisions

- Keep Merchant Intelligence unchanged and add Product Intelligence as a separate layer.
- Process giant product feed by streaming, not wholesale DB import.
- Use `expected commission >= €10` rather than product-price threshold.
- Keep dominant merchants as evidence beacons but potentially exclude from direct promotion.
- Separate deterministic Phase A from AI Phase B.
- Use Product Research Agent plus independent Skeptic/Audit Agent.
- Persist only after deterministic gates and audit.
- Prefer free/deterministic tooling before paid model calls.
- Do not invent missing market/social metrics.
- Treat pain-gap opportunity as different from merchant popularity.

### Explicitly rejected patterns

- `price > 50` / `price > 100` / `price > 150` as product eligibility.
- LLM-generated commission values.
- LLM-generated demand numbers without evidence.
- importing all 3.84 GB source rows into Supabase.
- blind fuzzy merchant matching.
- automatically trusting zero competition.
- treating likes alone as pain evidence.
- allowing AI output to bypass Skeptic Audit.
- calling a candidate `VALIDATED` because an LLM produced fluent text.

---

## 31. Final operational rule

**SocialMarket recommends evidence-backed solutions to validated user pain, not merely popular merchants or high-commission products.**

Commercial viability is necessary, but it is only one dimension.

The production system must optimize the intersection of:

```text
VALIDATED PAIN
×
REAL GREEK DEMAND
×
SOLUTION WHITESPACE
×
TRUSTED MERCHANT / VALID OFFER
×
EXPECTED COMMISSION
×
AUDIT CONFIDENCE
```

That intersection is the core SocialMarket intelligence product.
