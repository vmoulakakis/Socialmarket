# Autonomous Social Marketing Engine

## Purpose
Run affiliate social marketing with minimal operator involvement. SocialMarket selects products, validates affiliate destinations, generates campaign assets and copy, maintains rolling 30-day coverage, schedules via Postiz/Buffer, and reports incidents/analytics.

## Product sources
1. Supabase `products` + `opportunity_scores` (primary).
2. Authenticated admin CSV import (staging/intake). CSV products must still pass market intelligence before autonomous selection.

## Hard gates
- price >= EUR 100
- active/preferred/market-eligible product
- affiliate tracking URL present
- usable product image present
- confidence >= configured minimum
- HIGO >= configured minimum
- no competition kill

## Expected-conversion ranking
The deterministic priority combines HIGO, demand, forecast momentum, offer strength, merchant trust and inverse competition/ad pressure. AI is used for semantic strategy/copy; selection never depends on a single opaque LLM judgment.

## Creative pipeline
- follow and validate affiliate landing page
- structured evidence extraction
- marketing angles
- Facebook/Instagram/TikTok/LinkedIn copy variants
- original platform-sized promotional creative using the real product image
- QR encodes exact tracking URL on Facebook/Instagram/LinkedIn
- TikTok has no QR by default and uses `/links/tiktok` + per-product tracked `/go/[slug]`

## Publishing
`PublisherRouter` uses:
- Facebook/Instagram/LinkedIn: Postiz first, Buffer fallback
- TikTok: Buffer first, Postiz fallback

If Postiz is not configured, Buffer remains operational. Buffer scheduling is executed by the authenticated Supabase `buffer-sync` Edge Function so the Buffer secret never needs to live in the GitHub worker.

## Autonomy controls
- rolling 30-day coverage keeper
- hard-QA auto approval only
- fail-closed incidents when evidence/media/price/quality is invalid
- idempotent publish jobs
- maximum five publishing attempts
- exponential retry delay
- six-hour campaign regeneration cooldown
- provider health snapshots

## Admin surfaces
- `/product-to-post`: autonomous campaign control + CSV intake + calendar
- `/monitor`: provider health + queue + incidents + clicks + engine runs

## Public surfaces
- `/links/tiktok`: stable TikTok link-in-bio product page
- `/go/[slug]`: click-tracked redirect to immutable affiliate URL snapshot

## Production enablement order
1. PostgreSQL healthy and writable.
2. Apply Product-to-Post migrations.
3. Run security/performance advisors.
4. Verify Buffer channels and Postiz configuration if used.
5. Generate one canary campaign.
6. Verify media URL, QR/link destination and scheduled post.
7. Merge PR #4 to enable the scheduled autonomous workflow.
