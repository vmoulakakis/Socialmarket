# ADR-006 — SocialMarket / SocialScheduler Ownership Boundary

Status: **Accepted**

## Decision

Both applications use the same Supabase project:

`rpfadpdnnxequgvdcfoq`

There is one canonical data model. Neither repository may create a duplicate merchant, product, content, campaign or publishing database.

## SocialMarket AI owns

- merchant intelligence
- category/subcategory intelligence
- product intelligence
- evidence and audit
- pain-gap discovery
- semantic vectors and opportunity ranking
- brand/site registry
- content strategy
- platform-specific content generation
- creatives
- approval
- exact intended schedule
- affiliate/tracking URL
- canonical `content.items`
- canonical `publish.outbox`
- interpretation of post-publication performance

SocialMarket ends at **Approved Publishing Intent**.

## SocialScheduler owns

- claiming approved jobs from `publish.outbox`
- Buffer/provider account connectivity
- exact execution of `scheduled_for`
- technical preflight
- rate limits
- retries for transient technical failures
- reconciliation with Buffer/platform state
- external post IDs/permalinks
- publication status ACK back into the shared outbox
- raw execution telemetry

SocialScheduler begins at **Execute Approved Publishing Intent**.

## Forbidden duplication

SocialMarket must not contain:

- Buffer execution logic
- Meta/TikTok account connection UI for publishing
- provider credentials
- independent scheduler queues
- execution retries
- provider reconciliation logic

SocialScheduler must not contain:

- merchant/product intelligence
- pain-gap ranking
- campaign strategy generation
- canonical content generation
- affiliate-link rewriting
- creative replacement decisions
- independent schedule generation
- duplicate content/product tables

## Operational adaptation rule

SocialScheduler may retry the same approved publishing intent after a transient technical failure. It may not invent a new marketing time, caption, product, URL or creative. Business-level changes return to SocialMarket.

## Analytics rule

`Scheduler collects; SocialMarket interprets.`

Raw execution/performance data can be collected by SocialScheduler and written to the shared database. Learning, ranking and future campaign decisions belong to SocialMarket.

## Database rule

The shared database is the integration boundary. Cross-repository synchronization by copying records is prohibited.

Views/RPCs may expose controlled projections, but physical source-of-truth records remain singular.
