# SocialMarket Evidence Framework

Reusable no-API research framework for any entity type: merchant, product, brand, category, competitor, service or pain topic.

## Collectors
- SearXNG: search/SERP/reviews/complaints/social discovery
- Trafilatura: clean site text and metadata extraction
- Scrapy: available for deep crawl jobs
- Playwright: JS-rendered public-page fallback only; no login or access-control bypass
- yt-dlp: YouTube public metadata/comments enrichment when available
- gallery-dl: available as a media/public-source fallback for future collectors

## Contract
Every collector emits normalized evidence with source URL, source kind/platform, collector, confidence, metrics, metadata and content hash.

## Audit
The skeptic audit agent validates identity, source quality/diversity, taxonomy, demand, competition, pain and social evidence. It can return validated / needs_review / rejected. Contradictions lower confidence; they never overwrite authoritative clean-link seeds.

## Semantics
Only audited evidence should feed semantic pain/unmet-need clusters. Large/high-competition merchants can be demand/pain beacons without being solution-whitespace opportunities.
