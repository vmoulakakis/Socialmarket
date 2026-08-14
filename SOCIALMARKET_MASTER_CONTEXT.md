# SocialMarket AI + SocialScheduler — Master Technical Context

**Status date:** 2026-08-15  
**Purpose:** Single source of truth for architecture, database, workers, AI evidence pipeline, SocialScheduler handoff, merchant intelligence, pain-gap discovery, vectors, cron jobs, security rules, current production status, known problems, and exact next steps.

---

## 1. Executive goal

The system is being built as a **Greek-market AI Evidence & Pain-Gap Intelligence Engine** with two cooperating applications:

1. **SocialMarket AI**
   - Single source of truth for brands, merchants, categories, products, opportunities, creatives and approved content.
   - Performs market intelligence, Greek demand analysis, competition analysis, merchant/site research, social/public-web evidence collection, pain-gap discovery, AI auditing, semantic clustering and vector search.
   - Owns canonical content identity and publishing intent.

2. **SocialScheduler**
   - Execution-only publishing service.
   - Does **not** own canonical content and does **not** independently create campaigns.
   - Receives immutable approved publishing jobs from SocialMarket.
   - Uses Buffer as the only publication gateway.
   - Handles dedupe, validation, exact schedule execution, retry/reconciliation and status acknowledgement back to SocialMarket.

**Core principle:** there must never be two independent sources of truth for content, merchant intelligence or scheduling.

---

# 2. Repositories

## SocialMarket AI

Repository:

```text
vmoulakakis/Socialmarket
```

Important merged work:

- PR #7 — Merchant Intelligence V4 reusable no-API evidence + skeptic audit
- PR #8 — Evidence V4.1 stronger social discovery, generic audit persistence, semantic search
- PR #9 — automatic audited pain-cluster materialization and embedding refresh

Important merged commits from this work:

```text
8d66a2d0b18f465da3d53638a375266557e7a412
ee29c09cddc3034167c0b95ad695f59f30b6efb8
ceb2965de251469b96b1f394d63386fa03e18850
```

Work started but not yet fully production-validated at the time of this document:

```text
branch: feat/generic-category-pain-worker
```

Purpose of that branch:
- generic evidence gateway usage
- first non-merchant worker
- category/subcategory Greek pain discovery
- generic entity intelligence contract

---

## SocialScheduler

Repository:

```text
vmoulakakis/socialscheduler
```

Architecture already designed and implemented in PR #1:

```text
feat/socialmarket-outbox-executor
```

Role:
- execution-only Buffer microservice
- no independent content intake
- no independent canonical campaigns
- no independent tracking-URL content generation
- no invented schedules

---

# 3. Supabase project

Current clean SocialMarket database project:

```text
Project: socialmarket
Project ref: rpfadpdnnxequgvdcfoq
```

The new database is the clean rebuild intended to avoid the old migration/recovery problems.

The design is **AI-vector-store based**, relational first, with pgvector semantic layers and evidence provenance.

---

# 4. System architecture

```text
                            USER / ADMIN
                                 │
                                 ▼
                         SOCIALMARKET AI
                                 │
          ┌──────────────────────┼───────────────────────┐
          │                      │                       │
          ▼                      ▼                       ▼
   Merchant Intelligence   Market Intelligence      Content Engine
          │                      │                       │
          ▼                      ▼                       ▼
 Website / SEO / SERP      Demand / Competition      Canonical Content
 Reviews / Social          Category Pain Gaps        Approval
          │                      │                       │
          └─────────────┬────────┘                       │
                        ▼                                ▼
                 NORMALIZED EVIDENCE              PUBLISHING OUTBOX
                        │                                │
                        ▼                                ▼
                  SKEPTIC AUDIT AI               SOCIALSCHEDULER
                        │                                │
                 ┌──────┼──────┐                         ▼
                 │      │      │                       BUFFER
              reject  review validated                  │
                              │                         ▼
                              ▼                   FB / IG / TikTok
                       SEMANTIC CLUSTERS
                              │
                              ▼
                         PGVECTOR
                              │
                              ▼
                     SEMANTIC AI SEARCH
```

---

# 5. Architectural invariants

These rules should not be changed casually.

## 5.1 SocialMarket owns the truth

SocialMarket is the canonical store for:

- merchants
- merchant URLs
- merchant categories/subcategories
- market evidence
- social evidence
- AI audit verdicts
- pain gaps
- semantic clusters
- vectors
- brands/sites
- approved content
- publishing jobs

SocialScheduler must not create alternative canonical records.

## 5.2 Buffer is the only publication gateway

Do not publish directly through multiple Meta/TikTok/Buffer paths.

Desired path:

```text
SocialMarket
   ↓
publishing_outbox
   ↓
SocialScheduler
   ↓
Buffer
   ↓
Facebook / Instagram / TikTok
```

## 5.3 No invented facts

If a public scraper cannot verify a metric:

```text
do not invent likes
do not invent comments
do not invent follower counts
do not invent review counts
```

Store:
- source
- collection method
- timestamp
- confidence
- raw evidence
- audit state

## 5.4 Authoritative clean URLs win

If a clean/validated merchant URL exists, AI research may:

- confirm it
- enrich it
- flag a contradiction

AI research must **not overwrite it with a random search result**.

---

# 6. Merchant source data

A cleaned merchant/deeplink source has been used as identity evidence.

The important source file contained clean HTTP merchant targets and Linkwise deeplink matching.

Observed import state:

```text
existing merchants: 309
clean-link seeds matched: 307
validated/authoritative Linkwise identities: 228
```

Before the fix, old discovery had produced wrong merchant URLs such as:

- directories
- press/news articles
- vendor pages
- unrelated listing pages

The clean Linkwise result is therefore the primary merchant identity source when validated.

---

# 7. Merchant identity model

For each merchant, the system should distinguish:

```text
canonical_name
normalized_name
official_url
official_domain
identity_source
identity_confidence
identity_validated
identity_contradiction
```

Identity precedence:

```text
1. Validated Linkwise / clean source
2. Exact official-domain evidence
3. Merchant site crawl confirmation
4. Multi-source search agreement
5. AI discovery only as candidate
```

Never treat raw SERP discovery as equal to authoritative clean-link identity.

---

# 8. Generic evidence framework

The evidence layer is intentionally **entity-agnostic**.

Supported/future `entity_type` values include:

```text
merchant
product
brand
taxonomy
category
subcategory
competitor
service
pain_topic
```

The same evidence machinery should work without redesigning the database.

---

# 9. Evidence collectors

## 9.1 SearXNG

Purpose:
- search demand
- SERP evidence
- review discovery
- complaint discovery
- alternative queries
- competitor discovery
- social/public-web discovery

Runs as an ephemeral self-hosted container in GitHub Actions.

Typical queries:

```text
"<merchant>" αξιολογήσεις κριτικές
"<merchant>" παράπονα
"<merchant>" alternative
"<category>" αγορά Ελλάδα
"<category>" πρόβλημα
"<category>" δεν βρίσκω
"<category>" πολύ ακριβό
site:reddit.com "<entity>"
site:youtube.com "<entity>"
site:facebook.com "<entity>"
site:instagram.com "<entity>"
site:tiktok.com "<entity>"
```

## 9.2 Trafilatura

Purpose:
- main text extraction
- cleaner RAG input
- remove menus/footer/noise
- links
- tables
- comments where extractable
- merchant page semantic text

Used before AI/category extraction when possible.

## 9.3 Scrapy

Purpose:
- deeper scheduled merchant/site crawl
- sitemap traversal
- categories
- subcategories
- products
- FAQ
- delivery
- returns
- support pages
- guides/blog

Designed more for deeper/weekly research than every lightweight daily pass.

## 9.4 Playwright

Purpose:
- JS-rendered public pages
- fallback when static extraction is weak
- no login bypass
- no CAPTCHA bypass
- no private account access

It is a fallback collector, not the first choice.

## 9.5 yt-dlp

Purpose:
- no-key YouTube enrichment
- video metadata
- public metrics where available
- public comment retrieval where supported

Data is still assigned confidence and audit state.

## 9.6 gallery-dl

Purpose:
- capped enrichment for supported public social/media pages
- fallback only

Do not treat it as an official analytics API.

---

# 10. Social evidence strategy

Target sources:

```text
Instagram
Facebook
TikTok
YouTube
Reddit
forums
web discussions
review sites
```

Social evidence is not just popularity.

The important signals are:

```text
complaints
desires
frustrations
missing features
price objections
delivery problems
returns problems
trust problems
"can't find"
"too expensive"
"alternative"
"wish"
"looking for"
"doesn't"
"missing"
```

Likes are weak signals compared with pain-bearing comments.

---

# 11. Normalized evidence record

Every evidence record should be queryable independently rather than hidden inside one JSON blob.

Conceptual contract:

```text
entity_type
entity_id
source_kind
source_url
platform
title
body
metrics
collector
collected_at
confidence
content_hash
validation_status
metadata
```

Examples of `source_kind`:

```text
official_site
reviews
complaints
alternatives
demand
social_public_observation
social_comment
social_video
category_competition
```

Live validation after the gateway fix showed:

```text
normalized observations: grew from 240 to 445+, then 475+
social observations: began persisting separately
```

This proved that social evidence was no longer being lost inside snapshot JSON.

---

# 12. Generic evidence database

Generic schemas/tables were created for reusable evidence and AI audit.

Important logical groups:

```text
evidence.*
ai.*
intel.*
ops.*
catalog.*
api.*
content.*
```

The generic model is intended to separate:

- relational canonical data
- raw evidence
- normalized evidence
- audited intelligence
- semantic objects
- embeddings
- operational jobs

---

# 13. Merchant intelligence V4

Important code:

```text
workers/market_intelligence/merchant_intelligence_v3.py
workers/market_intelligence/merchant_intelligence_v4.py
workers/market_intelligence/evidence_collectors.py
workers/market_intelligence/audit_agent.py
```

V4 keeps compatibility with the existing gateway contract but enriches V3 research with:

- clean identity
- more sources
- social evidence
- audit verdict
- pain-language extraction
- stronger semantic payload

---

# 14. Merchant research flow

```text
merchant job
   ↓
read canonical merchant
   ↓
use authoritative official URL if available
   ↓
crawl merchant site
   ↓
extract clean text
   ↓
discover category/subcategory candidates
   ↓
SERP/reviews/complaints
   ↓
social/public-web evidence
   ↓
Greek demand
   ↓
competition
   ↓
pain signals
   ↓
merchant trust/satisfaction
   ↓
AI skeptic audit
   ↓
save snapshot
   ↓
normalize evidence
   ↓
semantic/pain materialization
```

---

# 15. Merchant scoring model

## Demand Beacon Score

Large merchants can be excellent sources of market evidence.

Examples:

```text
Public
Kotsovolos
AliExpress
SHEIN
Sephora
Notino
```

High scale can indicate:
- large demand
- many reviews
- many searches
- many complaints/questions
- rich semantic evidence

A high Demand Beacon Score does **not** mean it is easy to compete with them.

## Solution Whitespace Score

The desired opportunity is approximately:

```text
high Greek demand
+ strong pain
+ lower competition
+ unmet need
+ trusted merchant/product source
+ semantic fit
```

Current conceptual weighting used in the design:

```text
30% Greek Demand
25% Pain Severity
20% Inverse Competition
10% Social Pain Evidence
 7% Merchant Trust
 5% Satisfaction Gap
 3% Semantic Fit
```

Affiliate commission/EPC should be used later as a commercial viability layer, not as the primary pain-gap ranking factor.

---

# 16. Audit AI agent

The Audit Agent is intentionally adversarial.

Its task is:

> Try to prove the research result is wrong.

It should not simply create another score.

Audit dimensions include:

```text
identity
authoritative domain match
entity relevance
source quality
source diversity
taxonomy plausibility
demand evidence
competition evidence
pain evidence
social evidence
contradictions
```

Possible verdicts:

```text
rejected
needs_review
validated
```

Only validated evidence should be eligible for trusted production semantic search.

---

# 17. Entity relevance gate

A major quality problem was discovered during vector search:

An old pain cluster could match because a random article contained a word similar to a merchant name.

This was fixed with entity binding rules.

Important rule:

```text
pain evidence must be relevant to the entity
OR
must belong to a separate category/subcategory pain pipeline
```

Old noisy clusters were marked:

```text
validation_status = stale
embedding_status = stale
```

so they are not used as trusted semantic results.

---

# 18. Merchant pain vs category pain

This distinction is fundamental.

## Merchant audit asks

```text
Is this merchant correctly identified?
Is the merchant trusted?
Does the merchant actually cover these categories?
Are the merchant-specific complaints real?
```

## Category pain discovery asks

```text
What does the Greek market need?
What are users complaining about in this category?
What is too expensive?
What feature is missing?
What is hard to find?
Where is demand high but competitive coverage weak?
```

A pain gap does **not** need to explicitly mention a merchant.

Therefore the correct model is:

```text
MERCHANT INTELLIGENCE
        +
CATEGORY/SUBCATEGORY PAIN INTELLIGENCE
        +
PRODUCT INTELLIGENCE
        ↓
OPPORTUNITY ENGINE
```

---

# 19. Generic category/subcategory pain worker

Work has started for a generic non-merchant worker.

Branch:

```text
feat/generic-category-pain-worker
```

Its purpose is to use taxonomy/category entities as the target of evidence collection.

Expected flow:

```text
category/subcategory
     ↓
Greek demand research
     ↓
SERP competition
     ↓
social/forum/review evidence
     ↓
pain language
     ↓
unmet need clustering
     ↓
audit
     ↓
validated semantic clusters
```

At the status date of this document, this generic worker code had been started but final CI/merge/full production run still needed to be completed.

---

# 20. Semantic clusters

Do not embed every individual comment separately.

Desired model:

```text
hundreds of similar comments
        ↓
one semantic cluster
```

Cluster fields conceptually include:

```text
entity_type
entity_id
cluster_type
canonical_text
category
subcategory
frequency
engagement
source_diversity
evidence_count
demand_score
competition_score
pain_severity
commercial_intent
audit_score
confidence
validation_status
embedding_status
metadata
```

Useful `cluster_type` values:

```text
pain
complaint
unmet_need
alternative_request
desire
product_need
```

---

# 21. Automatic pain-cluster materialization

Implemented logic:

```text
new merchant V4 audit snapshot
        ↓
if rejected → no trusted pain cluster
        ↓
if needs_review → pending/review state
        ↓
if validated → validated cluster
        ↓
deduplicate by entity/type/text hash
```

This prevents rejected research from becoming vector truth.

---

# 22. Embeddings

Deployed Supabase Edge Function:

```text
generic-embedding-worker
```

Status:

```text
ACTIVE
```

Model:

```text
gte-small
```

Vector dimensions:

```text
384
```

Uses Supabase-native AI session rather than an external paid embeddings API.

---

# 23. Generic embedding queue

```text
validated cluster
      ↓
embedding_status = pending
      ↓
generic embedding job
      ↓
gte-small
      ↓
embedding_gte vector(384)
      ↓
embedding_status = ready
```

A cron job runs approximately every 5 minutes to:
1. find/enqueue newly validated semantic clusters
2. call the generic embedding worker

---

# 24. Semantic search

Deployed Edge Function:

```text
semantic-pain-search
```

Status:

```text
ACTIVE
```

Purpose:
- natural language pain queries
- vector search against validated semantic clusters
- filterable by entity type / cluster type

Example query:

```text
θέλω κάτι πιο οικονομικό γιατί η υπάρχουσα λύση είναι ακριβή
```

Desired future result:

```text
validated pain clusters
→ relevant categories
→ low-competition gaps
→ candidate merchants
→ candidate products
```

The search uses cosine similarity and a pgvector index.

---

# 25. HNSW vector index

Semantic search is intended to use an HNSW pgvector index for fast cosine similarity.

Important security detail discovered during implementation:

Because hardened functions use:

```text
search_path = ''
```

the pgvector operator had to be schema-qualified.

This was fixed rather than weakening the function security model.

---

# 26. Supabase Edge Functions

Important currently deployed functions include:

```text
merchant-intelligence-gateway
merchant-research-gateway
merchant-intelligence-worker
generic-embedding-worker
semantic-pain-search
evidence-gateway
publishing-outbox
```

---

# 27. merchant-research-gateway

Important responsibilities:

```text
OIDC authentication from GitHub Actions
claim jobs
save merchant intelligence
save snapshots
save semantic text
normalize evidence
protect authoritative merchant URL
complete job
fail/requeue job
```

A critical fix was made:

Before:
- V4 evidence was stored mainly inside a JSON snapshot
- social evidence was not queryable as independent rows
- research could overwrite merchant URL

After:
- evidence is persisted as normalized rows
- social records persist separately
- authoritative clean URL has precedence

---

# 28. evidence-gateway

Generic OIDC gateway created for non-merchant evidence workers.

Purpose:

```text
category worker
product worker
brand worker
competitor worker
service worker
future collectors
```

It avoids creating a new database-specific gateway for every intelligence entity.

---

# 29. GitHub Actions — Merchant Intelligence

Main workflow:

```text
.github/workflows/merchant-intelligence-v3.yml
```

Despite the historical filename, it now executes the V4 evidence/audit stack.

Important behavior:

```text
GitHub Actions
  ↓
install Python collectors
  ↓
start ephemeral SearXNG
  ↓
run audited deep research
  ↓
OIDC → Supabase gateway
```

GitHub OIDC is preferred over copying database/service-role secrets into GitHub.

---

# 30. CI

Merchant V4 CI validates:

```text
Python compile
audit smoke tests
entity relevance tests
pain binding tests
workflow dependency checks
```

It explicitly tested that irrelevant generic articles are not accepted as merchant pains.

The Next.js application build has also passed in the relevant merged PRs.

---

# 31. Cron / background jobs

Important Supabase cron jobs observed or designed:

```text
socialmarket-daily-merchant-refresh
```

Schedule:

```text
15 0 * * *
```

Purpose:
- enqueue daily merchant deep-research jobs

```text
socialmarket-requeue-expired
```

Schedule:

```text
*/5 * * * *
```

Purpose:
- recover expired research leases

```text
generic embedding refresh
```

Approximate schedule:

```text
*/5 * * * *
```

Purpose:
- enqueue validated semantic clusters
- vectorize pending clusters

```text
socialmarket-daily-taxonomy-pain-refresh
```

Designed schedule:

```text
00:45 UTC daily
```

Purpose:
- category/subcategory pain intelligence refresh

The generic category worker still needs final production validation.

---

# 32. Research jobs

Operational queue is used for background intelligence.

Typical concepts:

```text
entity_type
entity_id
job_type
status
priority
reason
requested_at
not_before
lease_owner
lease_expires_at
attempt_count
payload
dedupe_key
```

Statuses:

```text
queued
running
completed
failed
```

Leasing is required to avoid duplicate concurrent work.

---

# 33. Generic collection jobs

A generic queue was also introduced:

```text
ops.collection_jobs
```

Intended fields:

```text
entity_type
entity_id
collection_type
collector_policy
status
priority
payload
```

This is the correct abstraction for future non-merchant collectors.

---

# 34. Merchant refresh behavior

A controlled second full merchant refresh was queued after:
- clean Linkwise identity import
- stricter relevance rules
- better social evidence persistence
- V4.1 merge

Observed queue state during the run included:

```text
completed: 36
queued: 249
running: 24
```

This was an intermediate state, not a final completion figure.

The important interpretation:
- the full 309 merchant population was requeued
- the run was actively processing with the corrected stack

---

# 35. Research quality observation from the corrected run

Examples of merchant results with strong entity relevance:

```text
Remixshop
Xenodoxeio
Prince Oliver
Surfshark
Abadianakis
AMMA
```

Some had:

```text
entity relevance = 100
```

but merchant-specific pain phrase count remained `0`.

This is why pain discovery must be category-centric in addition to merchant-centric.

---

# 36. Taxonomy strategy

Do not trust navigation text blindly as subcategory.

Examples of bad candidates:

```text
Home
Contact
Βοήθεια
EXTRA ΕΚΠΤΩΣΗ 30%
ΚΟΥΠΟΝΙ HOT30
```

The Audit Agent now checks taxonomy plausibility.

Long-term preferred taxonomy derivation should combine:

```text
site sitemap
breadcrumbs
structured data
category URLs
repeated category anchors
product corpus
merchant program metadata
semantic classification
cross-merchant taxonomy agreement
```

---

# 37. SEO intelligence

Current merchant intelligence includes:
- site reachability
- HTTPS
- title
- description
- canonical
- viewport
- structured data
- H1
- robots
- sitemap
- organic evidence
- search footprint

Planned/desired enhancement:
- deeper Lighthouse-style technical SEO
- rank history
- domain competition
- structured-data validation

SEO should be a supporting signal, not the sole opportunity score.

---

# 38. Competition analysis

Competition must not equal "number of Google results".

Better competition dimensions:

```text
number of strong domains
SERP concentration
large retailer dominance
price-comparison dominance
category breadth
content authority
review authority
ad saturation where observable
social share of voice
merchant availability
```

The Opportunity Engine should use **inverse competition** only after verifying real demand.

---

# 39. Satisfaction and trust

Merchant trust should use multiple forms of evidence:

```text
identity confidence
site quality
review sentiment
complaint severity
delivery complaints
refund complaints
fraud/scam evidence
source diversity
long-term public footprint
```

A merchant can have:
- high demand
- high pain
- poor trust

That should **not** automatically become a recommended solution.

---

# 40. Pain-gap design

The desired object is not merely a keyword.

Example:

```text
Pain:
Users want robotic cleaning but current options feel too expensive.

Intent:
affordable automated cleaning

Desired outcome:
robotic cleaning below a lower price threshold

Constraint:
price

Category:
Home > Cleaning > Robot Vacuums

Demand:
HIGH

Competition:
MEDIUM

Pain severity:
HIGH

Commercial intent:
HIGH
```

This semantic object is far more useful than storing only:

```text
robot vacuum cheap
```

---

# 41. Opportunity discovery flow

Target future production flow:

```text
user problem
    ↓
semantic query
    ↓
validated pain clusters
    ↓
category/subcategory matches
    ↓
Greek demand
    ↓
competition
    ↓
merchant trust
    ↓
candidate products/solutions
    ↓
commercial viability
    ↓
ranked opportunity
```

---

# 42. SocialScheduler — final responsibility boundary

SocialScheduler must be treated as:

```text
execution plane
```

not:

```text
content brain
```

Its responsibilities:
- receive SocialMarket outbox jobs
- check explicit schedule
- dedupe
- Buffer preflight
- create scheduled Buffer execution
- reconcile Buffer status
- ACK back to SocialMarket
- no independent content creation

---

# 43. SocialScheduler important files

Implemented architecture included:

```text
src/socialmarket_outbox.py
src/main.py
src/scheduler_v2.py
scripts/migrate_socialmarket_backlog.py
tests/test_socialmarket_outbox.py
tests/test_scheduler_v2.py
.github/workflows/social-scheduler.yml
.github/workflows/migrate-socialmarket-backlog.yml
```

---

# 44. SocialScheduler safety invariants

```text
No shareNow
No shareNext
Only customScheduled
Explicit schedule required
Expired target is rejected
Scheduler does not invent new dates
Existing Buffer error is not blindly retried
Instagram/TikTok media required
Imported backlog reconciles against Buffer
```

---

# 45. Publishing outbox

SocialMarket owns publishing intent.

Core logical tables:

```text
brand_sites
content_items
publishing_outbox
```

Important RPC concepts:

```text
queue_content_item
claim_publishing_jobs
ack_publishing_job
list_publishing_reconcile_jobs
```

Important dedupe rule:

```text
unique(content_item_id, platform)
```

Claiming uses a lease/skip-locked pattern.

---

# 46. Publishing kill switch

A production kill switch was designed:

```text
socialscheduler_control
```

Default:

```text
enabled = false
```

until migration/import/dry-run/reconciliation is complete.

This prevents accidental half-cutovers.

---

# 47. SocialMarket brand/site registry

Known portfolio examples used in the project:

```text
CoffeeGo AI
CabinPilot Travel
CabinPilot Smart Savings
Λύσεις που Αξίζουν / Biz Box Solver
Travel AI / GreekVibes
Red Raven Eyewear
```

SocialMarket should be the canonical place to connect these properties with:
- brand
- site
- content
- market opportunity
- publishing

---

# 48. Security model

## Database

Internal tables should not be broadly accessible from frontend clients.

Preferred approach:

```text
internal schemas
  ↓
RLS / admin guards
  ↓
controlled RPCs / api views
  ↓
frontend
```

Avoid exposing:
- raw evidence
- operational queues
- internal research jobs
- administrative settings
- private content operations

directly to anonymous/authenticated users.

## GitHub → Supabase

Preferred method:

```text
GitHub Actions OIDC
```

instead of:
- database password
- service-role key
- shared long-lived secret

Gateway verifies repository/workflow/ref.

---

# 49. Edge Function JWT note

Some gateways have:

```text
verify_jwt = false
```

because they perform **custom strict GitHub OIDC verification inside the function**.

Do not interpret this automatically as unauthenticated.

Other user-facing/internal Supabase functions use normal JWT verification.

---

# 50. RLS

Generic evidence tables were intended to be created with RLS enabled.

Important principle:

```text
RLS policy design must match worker/frontend access
```

Do not enable arbitrary deny-all policies without checking required background workers.

Do not leave internal tables open simply to make development easier.

---

# 51. What NOT to do

Do not:

```text
❌ create a second merchant database in SocialScheduler
❌ let AI overwrite validated merchant URLs
❌ treat random SERP result as official domain
❌ embed every raw comment separately
❌ trust social likes as proof of pain
❌ rank popularity as opportunity
❌ publish unaudited research as validated truth
❌ auto-reschedule expired approved posts
❌ create direct multiple social publishing paths
❌ use fake/mock fallbacks in production intelligence
❌ store all evidence only as opaque JSON
```

---

# 52. What should become daily

Desired autonomous daily cycle:

```text
00:15 merchant refresh enqueue
       ↓
merchant research
       ↓
merchant audit
       ↓
normalized evidence

00:45 taxonomy/category pain enqueue
       ↓
category pain research
       ↓
social/forum/review evidence
       ↓
audit
       ↓
semantic clusters

every ~5 min
       ↓
requeue expired work
       ↓
enqueue embeddings
       ↓
vectorize validated clusters
```

---

# 53. AI model philosophy

Use deterministic/data tooling first.

LLM usage should be focused on tasks where semantic reasoning adds value:

```text
taxonomy classification
semantic clustering
contradiction resolution
pain interpretation
commercial-intent classification
audit explanation
opportunity synthesis
```

Do not spend LLM calls on:
- database inserts
- joins
- simple filtering
- scheduling
- deterministic calculations

---

# 54. Free-first philosophy

Preferred free/open components:

```text
PostgreSQL
Supabase
pgvector
Supabase gte-small embeddings
SearXNG
Trafilatura
Scrapy
Playwright
yt-dlp
gallery-dl
GitHub Actions
```

Paid/external APIs should be optional upgrades for:
- higher volume
- reliability
- official social analytics
- richer SERP metrics

The architecture must continue to function without requiring them.

---

# 55. Current known limitations

## 55.1 Social platforms

Without official APIs:
- Instagram/Facebook/TikTok extraction is less reliable
- layouts and anti-bot behavior can change
- public metrics may be unavailable

Therefore:
- confidence must be lower
- source provenance must be stored
- absence of data is not evidence of absence

## 55.2 Social coverage

At one live check, persisted social observations had started appearing but were still limited, initially concentrated in Facebook results.

This should be treated as an early validation of persistence, not proof of broad platform coverage.

## 55.3 Category pain worker

The generic category/subcategory pain worker is the next critical production step.

At document creation:
- generic DB abstractions exist
- evidence gateway exists
- worker code had been started
- final CI/merge/full run was not yet confirmed

## 55.4 Taxonomy quality

Some historic merchant subcategories came from navigation/promotional text.

The new audit catches obvious cases, but a stronger taxonomy pipeline is still recommended.

---

# 56. Immediate next steps — exact order

## P0 — complete generic category pain worker

1. Finish `generic_entity_intelligence.py`.
2. Ensure it reads `ops.collection_jobs`.
3. Use `evidence-gateway`.
4. Run SearXNG category demand queries.
5. Run category-level social/forum queries.
6. Extract pain/unmet-need candidates.
7. Apply category relevance gate.
8. Store normalized evidence.
9. Produce semantic clusters.
10. Audit clusters.
11. Merge only after CI green.
12. Run a controlled Greek category sample.
13. Validate output manually.

## P0 — complete current 309 merchant refresh

After the active run completes:

Check:
```text
completed / failed / rejected / needs_review / validated
```

Then inspect:
- authoritative URL preservation
- category quality
- subcategory quality
- evidence counts
- social coverage
- audit reasons
- trust score
- demand score
- competition score

Do not accept a high completion count alone as quality proof.

## P0 — audit semantic search again

After new validated clusters exist:

Test Greek queries such as:

```text
θέλω κάτι πιο οικονομικό γιατί οι υπάρχουσες λύσεις είναι ακριβές
δεν βρίσκω μικρή συσκευή που να χωράει στο ταξίδι
θέλω προϊόν για τρίχες κατοικιδίων αλλά τα robot vacuum δεν τα καταφέρνουν
θέλω εναλλακτική χωρίς συνδρομή
```

Verify:
- returned cluster is actually relevant
- evidence URLs support it
- category is correct
- merchant is not incorrectly inferred from generic pain

## P1 — product intelligence

Add `product` entity support:

```text
product identity
merchant
category
price
availability
reviews
pain solved
pain created
semantic fit
competition
```

Then match:

```text
validated pain cluster
   ↓
candidate products
```

## P1 — opportunity engine

Create final ranking with separate components:

```text
demand
pain
competition
trust
social proof
semantic fit
availability
commercial viability
```

Always keep score components visible for auditability.

## P1 — merchant/category dashboard

Admin UI should show:

```text
merchant
official URL
identity source
category/subcategory
trust
demand beacon
competition
pain evidence
social evidence
audit verdict
last researched
next refresh
```

Also:

```text
category
demand
competition
pain clusters
validated unmet needs
candidate merchants
```

---

# 57. Recommended production views

Useful controlled API/admin views:

```text
api.merchant_intelligence
api.validated_merchant_opportunities
api.validated_pain_clusters
api.category_opportunities
api.merchant_evidence_summary
api.social_evidence_summary
```

Do not expose the raw internal queue tables to clients.

---

# 58. Recommended audit trace

Every high-level opportunity should be explainable.

Example:

```text
Opportunity ID
Category
Pain
Demand Score
Competition Score
Pain Severity
Trust Score
Social Evidence Score
Audit Score
Sources
Merchants
Products
Why selected
Why competitors are weak
Last refreshed
```

This makes the system useful for real consulting/business decisions rather than opaque AI scoring.

---

# 59. Definition of VALIDATED

A result should not be labelled VALIDATED only because a numeric threshold is exceeded.

Suggested requirements:

```text
identity passes
entity/category relevance passes
minimum evidence count passes
minimum source diversity passes
no major contradiction
demand evidence exists
competition evidence exists where required
pain evidence is entity/category bound
audit score above threshold
```

For high-stakes recommendations, prefer at least two independent source types.

---

# 60. Final target state

The target system is:

```text
Greek Market Intelligence
        +
Merchant Intelligence
        +
Category/Subcategory Pain Discovery
        +
Social/Public-Web Evidence
        +
Skeptic AI Audit
        +
Semantic Vector Store
        +
Opportunity Ranking
        +
Canonical Content Engine
        +
Controlled Publishing Outbox
        +
SocialScheduler/Buffer Execution
```

The goal is not merely to find popular products.

The goal is:

> **Find validated unmet needs in the Greek market, understand why users feel the pain, estimate real demand and competition, identify trustworthy merchants/products that can solve the pain, and convert the best evidence-backed opportunities into controlled content and publishing workflows.**

---

# 61. Recovery / continuation instructions for future AI sessions

When continuing this project, do not redesign from memory.

First inspect:

```text
vmoulakakis/Socialmarket
main
```

Then inspect:
- latest GitHub Actions for Merchant Intelligence V4
- branch/PR status of generic category pain worker
- Supabase project `rpfadpdnnxequgvdcfoq`
- `ops.research_jobs`
- `ops.collection_jobs`
- merchant refresh state
- evidence counts
- social evidence counts
- semantic cluster validation states
- embedding states
- deployed Edge Functions
- cron jobs

Before changing schema:
1. inspect current table/function definition
2. create additive migration
3. version migration in Git
4. test CI
5. apply once
6. verify post-migration state
7. avoid DB/repo migration drift

Before calling a pipeline "working":
- run it
- inspect persisted data
- test semantics
- confirm source provenance
- confirm audit behavior
- confirm that rejected data does not leak into validated search

---

# 62. Quick status checklist

```text
[✓] clean SocialMarket Supabase project
[✓] relational + vector architecture
[✓] merchant canonical model
[✓] clean Linkwise identity seeds
[✓] merchant V4 research worker
[✓] SearXNG
[✓] Trafilatura
[✓] Playwright fallback
[✓] yt-dlp enrichment
[✓] gallery-dl enrichment support
[✓] normalized evidence persistence
[✓] social evidence persistence
[✓] skeptic Audit Agent
[✓] entity relevance gate
[✓] stale/noisy pain quarantine
[✓] generic semantic clusters
[✓] generic embedding worker
[✓] 384-d gte-small embeddings
[✓] semantic pain search
[✓] HNSW vector search
[✓] automatic pain materialization
[✓] cron-based embedding refresh
[✓] evidence-gateway
[✓] SocialMarket content source-of-truth architecture
[✓] SocialScheduler execution-only architecture
[✓] Buffer-only publishing path design
[~] second 309-merchant revalidation run
[~] generic category/subcategory pain worker
[ ] validated category pain production sample
[ ] product intelligence layer
[ ] final opportunity engine
[ ] full admin intelligence dashboard
[ ] full SocialScheduler production cutover verification
```

---

## End of master context

This file should be updated whenever there is a material change in:
- schema
- worker architecture
- Edge Functions
- scoring
- validation rules
- cron
- content/publishing ownership
- production cutover status
