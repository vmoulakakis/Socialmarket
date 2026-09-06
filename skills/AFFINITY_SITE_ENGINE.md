# AFFINITY Site Engine — Multi-Page Website / Store Architecture

Version: 1.0
Status: Canonical extension of AFFINITY Page Engine
Last researched: 2026-09-07

Dependencies:
- `skills/AFFINITY_SKILL.md`
- `skills/AFFINITY_PAGE_ENGINE.md`
- `config/affinity-page-engine.json`
- `agents/skills/affinity-creative-production/SITE_DNA.schema.json`
- `agents/skills/affinity-creative-production/PAGE_DNA.schema.json`
- `agents/skills/affinity-creative-production/COMPONENT_REGISTRY.md`
- `agents/skills/affinity-creative-production/BUILD_HANDOFF.schema.json`
- `agents/skills/affinity-creative-production/QA_GATES.md`

---

## 0. Purpose
The Page Engine governs individual conversion/content pages. The Site Engine governs how multiple Page DNA objects become one coherent website/store with shared brand, navigation, information architecture, conversion paths, SEO, analytics and cross-route QA.

This closes the gap between “generate a landing page” and “build a real site.”

---

# 1. Public pattern synthesis

PagePilot publicly describes whole-store generation including a branded homepage, product pages, collection pages, navigation, theme/layout, product catalog, cart drawer and upsells. AFFINITY abstracts this into a platform-independent Site DNA instead of coupling the system to Shopify.

Magnetic is primarily page/campaign-asset oriented; its reusable/remixable asset model informs campaign microsites and page families inside a Site DNA.

Never copy vendor code, private templates or exact protected designs.

---

# 2. Site types

Supported default site archetypes:

## Single-product brand
Typical routes:
- `/`
- `/product`
- `/how-it-works`
- `/compare`
- `/faq`
- `/support` or trust page
- legal routes.

## Multi-product DTC
Typical routes:
- `/`
- `/collections/...`
- `/products/...`
- `/about`
- `/faq`
- `/contact`
- `/cart` when owned checkout
- search
- legal.

## Affiliate content-commerce
Typical routes:
- `/`
- `/problems/...`
- `/guides/...`
- `/compare/...`
- `/reviews/...`
- `/products/...` or recommendation pages
- disclosure/about/contact/legal.

## Campaign microsite
Typical routes:
- message-matched landing
- proof/resource page
- FAQ
- lead/download/offer route if separate.

Keep navigation intentionally minimal.

## Lead-generation site
Typical routes:
- home
- service/solution
- audience/use-case pages
- resources
- proof/case-study where real
- contact/book
- legal.

## SaaS marketing site
Typical routes:
- home
- product/features
- use cases
- integrations when real
- pricing when applicable
- resources
- FAQ
- contact/demo/signup.

## Editorial-commerce hub
Typical routes:
- topic/category hubs
- buying guides
- comparisons
- reviews
- problem/solution articles
- recommendation pages.

---

# 3. Mandatory Site Engine flow

`SITE CONTEXT → BRAND/STORE DNA → SITE TYPE → USER JOURNEYS → INFORMATION ARCHITECTURE → NAVIGATION → ROUTE INVENTORY → PAGE DNA PER ROUTE → GLOBAL COMPONENTS → CONVERSION PATHS → INTERNAL LINKING → SEO/LOCALIZATION → BUILD HANDOFFS → CROSS-ROUTE QA → DEPLOY → MEASURE`

Do not start by generating pages independently and stitching them together afterward.

---

# 4. Site context

Create:

```yaml
site_context:
  site_id:
  market:
  locales: []
  business_model:
  primary_objective:
  secondary_objectives: []
  product_catalog_model:
  audience_segments: []
  traffic_sources: []
  owned_checkout:
  affiliate_handoff:
  content_strategy:
  brand_store_dna_ref:
  existing_site_to_preserve:
```

---

# 5. User journeys before sitemap

Define actual paths, not a list of pages.

Examples:

```yaml
journey:
  id: paid_problem_aware
  entry: /lp/problem-angle
  audience: homeowner
  goal: affiliate_click
  path:
    - message_matched_landing
    - proof
    - comparison
    - merchant_handoff
```

```yaml
journey:
  id: organic_comparison
  entry: /compare/product-vs-alternative
  goal: qualified_affiliate_click
  path:
    - comparison
    - detailed_review
    - trust
    - merchant_handoff
```

The sitemap serves journeys; journeys do not exist to justify a large sitemap.

---

# 6. Information architecture

Model:
- entities/products
- categories/collections
- problems/pains
- audiences/use cases
- guides/articles
- comparisons
- resources
- trust/support/legal.

Avoid creating thin pages for every possible keyword combination. Programmatic routes require meaningful unique intent/content/data.

---

# 7. Navigation model

Choose one:
- campaign-minimal
- minimal
- standard
- mega-menu.

Navigation must reflect information architecture and highest-value journeys.

Rules:
- campaign pages should not leak attention through unnecessary navigation
- ecommerce sites need discoverability without overwhelming shoppers
- content-commerce hubs need topic hierarchy and useful internal linking
- mobile navigation requires independent QA
- footer carries secondary/legal/trust navigation.

---

# 8. Route inventory

Every route must specify:

```yaml
route:
  path:
  page_type:
  purpose:
  audience:
  traffic_intent:
  page_dna_ref:
  layout_dna_ref:
  indexing:
  canonical:
  parent_route:
  primary_conversion:
  supporting_links: []
```

No orphan pages.

---

# 9. Page families

Reuse Page/Layout DNA across related route families while allowing content/angle differences.

Examples:
- product-page family
- comparison family
- buying-guide family
- category/collection family
- problem-solution family
- campaign landing family
- article family.

A page family should share structural grammar and brand rules without producing near-identical duplicate copy.

---

# 10. Global component layer

Site-scoped components may include:
- header/navigation
- announcement bar when truthful
- site search
- collection/category navigation
- cart/cart drawer for owned checkout
- affiliate disclosure
- newsletter/contact CTA
- footer
- cookie/consent layer where applicable
- global trust/support links.

Global components use Component Registry IDs and shared design tokens.

---

# 11. Store / owned-commerce mode

When the property owns checkout, Site DNA can include:
- product catalog
- collections/categories
- search/filtering
- product detail pages
- variant selection
- cart/cart drawer
- checkout handoff
- real free-shipping threshold
- relevant upsell/cross-sell
- account/order functions when platform provides them.

AFFINITY does not reimplement mature platform checkout functionality merely to look custom. Preserve reliable native commerce infrastructure.

---

# 12. Affiliate mode

When the site does not own checkout:
- no fake internal cart
- clear merchant handoff
- validated tracking URLs
- disclosure
- merchant/delivery/warranty facts close to CTA
- page/site analytics continue until outbound click; merchant conversion/revenue joins later when data is available.

---

# 13. Homepage logic

Homepage is a router and trust surface, not automatically the best paid-traffic destination.

A homepage may contain:
- clear brand/category proposition
- primary use cases/categories
- featured/high-priority offers or products
- proof/trust
- problem/solution entry points
- resources/content
- final CTA.

Paid ads with a specific promise usually go to a message-matched landing page rather than generic homepage.

---

# 14. Collection/category logic

Collection/category pages should support choice:
- clear category intent
- useful sorting/filtering where catalog warrants it
- concise category guidance
- product/solution cards
- comparison cues
- buyer guide links
- SEO text only when useful, not filler.

---

# 15. Internal-linking engine

Links should support:
- user journey continuation
- topical relationships
- comparison discovery
- trust/support resolution
- SEO crawl hierarchy.

Prioritize contextual links over large arbitrary link clouds.

Maintain:
- no orphan important routes
- shallow access to high-value pages
- parent/child relationships
- relevant product↔guide↔comparison connections.

---

# 16. Site-level SEO

Require:
- canonical policy
- sitemap
- robots policy
- internal-linking model
- metadata/page intent per route
- structured data only where valid
- locale/hreflang strategy where implemented
- duplicate-variant control
- redirects for moved/retired routes.

Do not index experimental near-duplicate landing variants without an intentional strategy.

---

# 17. Localization

Each locale uses the same Site DNA intent but can adapt:
- navigation labels
- route slugs when appropriate
- local currency/context
- delivery/warranty information
- comparisons
- culturally natural copy.

Do not create locales merely because translation is possible. Roll out markets based on business/demand rationale.

---

# 18. Site-level analytics

Track:
- entry route
- journey ID
- page transitions
- search/category/product interactions
- affiliate outbound or ecommerce events
- lead events
- cross-route funnel completion
- RPV/revenue by entry page, journey and traffic source.

The Page Engine remains responsible for page/component events; Site Engine connects those into journeys.

---

# 19. Cross-route QA

In addition to Page Engine QA, verify:
- navigation works on mobile/desktop
- no important orphan routes
- no broken internal links
- consistent Brand/Store DNA
- global CTA and disclosure behavior
- cart/search if enabled
- canonical/sitemap/robots consistency
- route-level analytics
- redirects
- footer/legal/trust access
- conversion path end-to-end.

---

# 20. Site experiment policy

Prefer page/route experiments over redesigning the whole site simultaneously.

Site-level experiments may test:
- navigation architecture
- collection organization
- journey routing
- homepage category framing
- internal-linking strategy.

Require explicit hypothesis and guardrails. Do not change navigation + brand + product mix + page layouts simultaneously and call the result an interpretable test.

---

# 21. Build handoff

A Site Engine build passes to builders:
- Site DNA
- Brand/Store DNA
- route inventory
- Page DNA reference per route
- Layout DNA/page family rules
- global components
- design tokens
- asset manifest
- navigation/internal-link map
- commerce/affiliate action model
- analytics contract
- QA acceptance
- deployment/rollback policy.

Builders implement; they do not invent site strategy during coding.

---

# 22. Success definition

A good site is not “many good pages.” It is a coherent system in which:

**brand + information architecture + journeys + message-matched pages + reusable layouts/components + trustworthy conversion paths + performance/accessibility + measurement**

work together.

The Site Engine exists so AFFINITY can build both exceptional landing pages and exceptional full sites without losing governance at the multi-page level.
