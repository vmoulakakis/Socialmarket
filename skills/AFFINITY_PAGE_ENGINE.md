# AFFINITY Page Engine — PagePilot + Magnetic Pattern Synthesis

Version: 1.0
Status: Canonical page-generation module for AFFINITY
Last researched: 2026-09-07
Primary KPI: Revenue per Unique Visitor (RPV)
Primary dependency: `skills/AFFINITY_SKILL.md`
Execution dependency: `agents/skills/affinity-creative-production/SKILL.md`
Component registry: `agents/skills/affinity-creative-production/COMPONENT_REGISTRY.md`
Page DNA schema: `agents/skills/affinity-creative-production/PAGE_DNA.schema.json`

---

## 0. PURPOSE

This module turns AFFINITY-approved products, offers, campaigns and lead-generation opportunities into high-converting pages without reducing page generation to an unconstrained "make a beautiful landing page" prompt.

It synthesizes publicly observable and documented techniques from PagePilot.ai and Magnetic.ai into an original, reusable AFFINITY page-generation system.

The goal is not to copy proprietary code, exact visual designs, private templates or brand identity. The goal is to reproduce the useful **decision mechanics**:

- structured context gathering
- angle selection
- message matching
- archetype selection
- modular sections/blocks
- component-level copy generation
- brand/design token control
- product-image generation and selection
- responsive assembly
- rapid variants
- direct-response commerce elements
- lead-magnet/content-page generation
- publishing/export
- measurement and learning.

AFFINITY always remains the authority for product validity, evidence, commercial truth, affiliate tracking and Greece/EU market logic.

---

## 1. RESEARCH BOUNDARY AND CONFIDENCE

### PagePilot.ai — publicly verified capabilities used here
Public PagePilot pages and help-center documentation show or state:

- product-page generation from supplier/competitor/product URLs
- optional angle selection before generation
- template/layout selection
- drag-and-drop section ordering
- inline text/image/style editing
- separate desktop/mobile controls
- brand matching
- AI product images
- product-description generation
- ad copy and matching creative generation
- 30+ languages/localization
- on-page SEO
- Shopify publishing/theme compatibility
- customizable cart drawer and upsells
- daily winning-product research
- 8+ professional DTC templates
- 35+ CRO sections/blocks on pricing pages
- 50+ component library referenced by the drag-and-drop builder page.

The public docs explicitly name many product blocks and product sections. Those verified names are represented in the component registry.

### Magnetic.ai — publicly verified capabilities used here
Magnetic publicly describes:

- natural-language page creation
- optional document/context input
- Analyze / Research / Find Image workflow
- audience + painful problem + offer + quick-win input
- generation sequence: analyze prompt → create outline → write copy → get images → apply layout → draft
- message-matched pages by ad angle, audience or funnel stage
- conversion-optimized templates
- lead magnets such as checklists, playbooks, mini-guides and resource lists
- personalized sales follow-up pages
- link-in-bio pages
- editable drafts
- duplicate/remix/variation workflow
- automatically hosted pages
- HTML, PDF and PNG exports
- responsive/mobile-ready pages.

Magnetic does **not** publicly expose a complete internal component manifest. Therefore this module does not claim exact private component names. It uses every public page format and workflow that can be verified, then supplies original AFFINITY components that provide equivalent capabilities.

---

# 2. MASTER PAGE-GENERATION PIPELINE

AFFINITY Page Engine must execute this sequence:

`SOURCE INGEST → CONTEXT NORMALIZATION → ANGLE MATRIX → MESSAGE MATCH → ARCHETYPE → PAGE DNA → COMPONENT PLAN → COPY → MEDIA → DESIGN TOKENS → ASSEMBLY → RESPONSIVE QA → CONVERSION LAYER → LOCALIZATION → VARIANTS → PUBLISH → MEASURE → LEARN`

Detailed flow:

1. **Source ingest**
   - product URL
   - merchant/supplier URL
   - competitor/reference URL
   - user documents/files
   - campaign/ad copy
   - existing brand/site
   - market/evidence packet from AFFINITY/GrowthOps.

2. **Context normalization**
   Produce a structured brief instead of passing raw scraped text directly into generation.

3. **Angle matrix**
   Identify distinct sellable/useful angles.

4. **Message matching**
   Preserve the exact promise, problem framing and intent that generated the click.

5. **Archetype selection**
   Choose the appropriate page family instead of forcing one universal layout.

6. **Page DNA generation**
   Create a machine-readable page specification before writing code or styling.

7. **Component planning**
   Select only components that serve the buyer decision path.

8. **Component-level copy generation**
   Write to each component's purpose and length constraints.

9. **Media planning/generation**
   Decide where real product media, diagrams, generated lifestyle visuals, comparisons or demos are needed.

10. **Design-token generation**
    Produce consistent typography, spacing, radius, color, layout and motion rules.

11. **Assembly**
    Build using reusable components rather than free-form section-by-section HTML invention.

12. **Responsive adaptation**
    Tune mobile/tablet/desktop hierarchy, order, spacing and sticky behavior.

13. **Conversion layer**
    Add trust, commerce or lead-capture functionality only when justified.

14. **Localization**
    Rewrite for local buyer context; do not mechanically translate persuasive copy.

15. **Variant generation**
    Create controlled angle/audience/offer variants.

16. **Publish/export**
    Deploy or export based on project requirements.

17. **Measure and learn**
    Feed RPV/conversion behavior back into future angle, archetype and component selection.

---

# 3. CONTEXT BRIEF

Before generation create:

```yaml
context_brief:
  market:
  locale:
  traffic_source:
  campaign:
  audience:
  awareness_stage:
  purchase_mode:
  core_pain:
  core_desire:
  offer:
  quick_win:
  main_mechanism:
  primary_objection:
  secondary_objections: []
  verified_claims: []
  supported_claims: []
  prohibited_claims: []
  product_facts: []
  logistics_facts: []
  warranty_returns_facts: []
  economic_facts: []
  competitor_context: []
  target_action:
  affiliate_or_checkout_destination:
  brand_voice:
  visual_context:
```

No page should be generated from raw source text without this normalization step.

---

# 4. SOURCE-URL INGESTION — PAGEPILOT-STYLE, AFFINITY-CONTROLLED

When a product/supplier/competitor URL is supplied:

1. Extract facts:
   - title/model
   - specs
   - price
   - variants
   - product imagery
   - included items
   - claims
   - FAQs
   - reviews/social proof only if real and attributable
   - delivery/warranty/returns
   - visible positioning cues.

2. Separate **facts** from **copy**.

3. Do not reproduce competitor or supplier wording verbatim except unavoidable factual labels.

4. Rebuild messaging around the chosen AFFINITY angle and buyer problem.

5. Preserve source-media provenance.

6. Never copy a competitor's proprietary HTML/CSS/component implementation.

7. Extract useful layout ideas only as abstract patterns:
   - proof near CTA
   - image-led explanation
   - comparison before final CTA
   - review density
   - offer structure
   - information sequence.

8. Reconcile extracted claims with AFFINITY's evidence ledger. Unsupported supplier claims remain prohibited.

---

# 5. ANGLE ENGINE

Create an angle matrix before page construction.

Potential angle classes:

- pain-point
- desired outcome
- economic savings
- time savings
- labor reduction
- convenience
- premium quality
- speed
- safety/risk reduction when supportable
- local scarcity/availability when verified
- price-value gap
- technical superiority when verified
- ease of use
- gift/lifestyle
- professional ROI
- social-proof-led when proof is real
- offer-led
- viral/trend context
- seasonal use case
- segment-specific use case.

Score each angle:

```yaml
angle:
  relevance_to_traffic: 0-10
  pain_or_desire_strength: 0-10
  evidence_strength: 0-10
  differentiation: 0-10
  visual_demonstrability: 0-10
  economic_strength: 0-10
  trust_risk: 0-10
```

Prefer the highest evidence-backed angle, not the most dramatic copy.

---

# 6. MESSAGE-MATCH ENGINE — MAGNETIC-STYLE

Every campaign page must continue the promise that generated the click.

For each traffic source capture:

```yaml
message_match:
  source_hook:
  source_problem:
  source_promise:
  source_visual_theme:
  source_offer:
  landing_headline:
  landing_supporting_message:
  proof_required:
  CTA_continuity:
```

Rules:

- Do not use a generic homepage hero after a highly specific ad.
- Reuse the **meaning** of the source hook, not necessarily the exact words.
- Hero must answer the visitor's implied question: "Am I in the right place?"
- If ad angle changes materially, create a page variant rather than weakening the page with multiple competing hero messages.
- Traffic-stage mismatch is a structural defect, not a copy detail.

---

# 7. PAGE ARCHETYPES

The engine chooses an archetype before components.

## Commerce / product archetypes

- Direct Product Landing
- Pain → Gap → Solution
- Benefit-Led DTC Product Page
- Demonstration-Led Product Page
- Comparison-Led Product Page
- High-Ticket Trust Page
- Savings / ROI Product Page
- Quiz / Recommender Product Page
- Use-Case Branching Product Page
- Editorial Review
- Buying Guide + Product Recommendation
- Product Microsite
- Product Mini-Site
- Offer / Bundle Page

## PagePilot-inspired niche archetype rules

### Beauty & skincare
Favor, only when factual and appropriate:
- ingredient/material highlights
- routine/how-to-use steps
- real before/after proof only if valid
- benefit hierarchy
- reviews/trust
- FAQ.

### Health & wellness
Use extra claim scrutiny. Favor:
- benefit framing without unsupported medical claims
- trust/warranty/returns
- usage explanation
- FAQ
- evidence/limitations.

### Fashion & apparel
Favor:
- lifestyle gallery
- size/fit guide
- variants
- styling/use contexts
- bundles where commercially real.

### Tech & gadgets
Favor:
- spec comparison
- demo video
- feature grid
- compatibility
- what's included
- FAQ.

### Pets
Favor:
- problem/emotional context without manipulation
- lifestyle/use images
- real reviews
- bundle/consumable logic where relevant.

### Home & garden
Favor:
- use-case context
- room/environment visuals
- value/economic framing
- dimensions/installation
- comparison.

## Magnetic-inspired lead-generation/content archetypes

- Message-Matched Landing Page
- Checklist
- Playbook
- Mini-Guide
- Resource List
- Downloadable Template Page
- Personalized Sales Follow-Up Page
- Link-in-Bio Page
- Campaign Resource Page
- Prospect-Specific Insight Page

---

# 8. PAGE DNA

Every page must be specified before implementation.

Example:

```json
{
  "page_id": "product-x-meta-pain-angle-v1",
  "objective": "affiliate_click",
  "market": "GR",
  "locale": "el-GR",
  "traffic_source": "meta",
  "audience": "homeowners",
  "awareness": "problem-aware",
  "angle": "electricity-cost-waste",
  "archetype": "pain-gap-solution",
  "primary_cta": "Δες την τρέχουσα προσφορά",
  "design": {
    "personality": "premium-clean-technical",
    "density": "medium",
    "motion": "restrained",
    "radius": "large"
  },
  "sections": [
    {"type": "hero", "component_id": "AF-HERO-PRODUCT-SPLIT-01"},
    {"type": "problem", "component_id": "AF-PAIN-CARDS-01"},
    {"type": "mechanism", "component_id": "AF-MECHANISM-STEPS-01"},
    {"type": "proof", "component_id": "AF-SPEC-PROOF-01"},
    {"type": "comparison", "component_id": "AF-COMPARE-TABLE-01"},
    {"type": "trust", "component_id": "AF-TRUST-STACK-01"},
    {"type": "faq", "component_id": "AF-FAQ-ACCORDION-01"},
    {"type": "cta", "component_id": "AF-CTA-FINAL-01"}
  ]
}
```

The canonical machine-readable schema is stored in `PAGE_DNA.schema.json`.

---

# 9. COMPONENT INTELLIGENCE

Components are chosen by suitability, not visual preference.

Every reusable component should expose metadata:

```yaml
component:
  id:
  role:
  conversion_goal:
  best_for: []
  avoid_when: []
  requires: []
  evidence_requirements: []
  copy_limits:
  media_requirements:
  mobile_behavior:
  analytics_events: []
  fallbacks: []
```

Example:

```yaml
component:
  id: AF-HERO-PRODUCT-SPLIT-01
  role: hero
  conversion_goal: affiliate_click
  best_for: [physical_product, problem_aware, cold_traffic]
  avoid_when: [complex_multi-product_comparison]
  requires: [product_visual, primary_value_prop]
  evidence_requirements: [headline_claims_supported]
  copy_limits:
    eyebrow_words: 2-6
    headline_words: 5-12
    body_words: 18-36
    CTA_words: 2-5
  mobile_behavior: image_after_copy
```

Do not let the model invent new page structure freely until existing registry components have been considered.

---

# 10. COMPONENT-LEVEL COPY GENERATION

Write copy after section/component selection.

## Hero
- Eyebrow: 2–6 words
- Headline: generally 5–12 words
- Supporting copy: generally 18–40 words
- CTA: 2–5 words
- Optional microtrust line: 4–14 words.

## Benefit block
- Heading: 3–8 words
- Benefit title: 2–6 words
- Benefit body: 12–30 words.

## Feature/spec block
- Feature name: concise factual label
- Explanation: translate the feature into buyer relevance
- Never turn a technical specification into an unsupported outcome.

## FAQ
- Questions should reflect actual buyer objections/search intent
- Answers should be specific, direct and evidence-safe.

## Comparison
- Use symmetric dimensions
- Include disadvantages and local alternatives where relevant.

## CTA section
- Restate outcome, not generic hype
- Reinforce real risk reduction
- CTA should describe the next action honestly.

## Product description — PagePilot-derived structure
When a structured product description is useful:
1. opening hook
2. benefit list
3. spec table
4. proof/trust line.

---

# 11. BRAND DNA AND DESIGN TOKENS

The engine must never style sections independently without a shared system.

Generate:

```yaml
brand_dna:
  voice:
  sophistication:
  emotional_tone:
  visual_personality:
  color_semantics:
  typography_character:
  image_style:
  icon_style:
  motion_style:
```

Design token layer:

```yaml
design_tokens:
  container_max:
  page_gutter_mobile:
  page_gutter_desktop:
  section_spacing:
  card_spacing:
  display_font:
  body_font:
  hero_size:
  h2_size:
  h3_size:
  body_size:
  body_line_height:
  heading_color:
  body_color:
  brand_color:
  accent_color:
  button_background:
  button_text:
  surface_1:
  surface_2:
  border_color:
  corner_radius:
  shadow_rule:
  motion_rule:
  focus_rule:
```

PagePilot-style controls that must be represented in our own token system:
- heading font size
- body font size
- heading color
- body color
- brand color
- CTA/button background
- CTA/button text
- corner rounding
- secondary CTA action
- mobile-specific spacing/order/visibility.

AFFINITY adds:
- container/grid
- section rhythm
- line length
- elevation/shadow
- image crop rules
- motion budget
- accessibility/focus behavior.

---

# 12. VISUAL AND IMAGE ENGINE

Treat media selection/generation as its own stage, not an afterthought.

For each section specify:

```yaml
visual_intent:
  purpose:
  asset_type:
  subject:
  context:
  aspect_ratio:
  fidelity_requirement:
  source_priority:
  text_overlay_allowed:
  mobile_crop:
```

Asset classes:

- verified product hero
- product detail
- use-case/lifestyle
- in-hand/use demonstration
- clean studio image
- background-isolated product
- diagram
- comparison visual
- step/how-it-works visual
- real customer/UGC only when authentic
- generated lifestyle context clearly non-documentary
- short demo video
- GIF where useful
- infographic/data visualization.

PagePilot-style image principles we keep:
- start from clear product references
- prefer full product visibility
- clean source background where possible
- avoid watermarks/text/logos in generation inputs where possible
- use niche/audience-specific prompting instead of generic scenery
- generate multiple visual contexts for testing.

AFFINITY fidelity rule:
AI-generated imagery must not alter critical product shape, controls, included accessories, scale, safety configuration or claimed result. If exact fidelity is required, use verified manufacturer/merchant imagery or reference-image generation workflows.

---

# 13. DIRECT-RESPONSE COMMERCE LAYER — PAGEPILOT-INSPIRED

For ecommerce/checkout pages, consider:

- hero
- product gallery
- rating/review count
- product title/subtitle
- pricing
- variants
- quantity selector
- add-to-cart
- benefits
- trust badges
- guarantee/warranty
- expandable shipping/returns/details
- sticky add-to-cart
- reviews/testimonials
- review grid
- feature highlights
- image-with-text
- image-with-benefits
- competition/comparison table
- quantified proof only when evidence exists
- demo video
- FAQ
- bundles/upsells
- recommended products
- final CTA.

Do not add every component. Select the minimum set that resolves the buyer's decision barriers.

---

# 14. CART DRAWER / HIGH-INTENT MOMENT

When the site owns checkout/cart:

Possible elements:
- line items
- quantity controls
- clear subtotal/total
- checkout CTA
- relevant one-click upsell
- cross-sell
- free-shipping progress bar when threshold is real
- trust/payment badges
- shipping reassurance
- countdown/reservation timer only when genuinely implemented and truthful.

Rules:
- Do not fabricate cart reservation.
- Do not use fake stock or fake countdowns.
- Upsells must be relevant and not obstruct checkout.
- Mobile cart interaction must remain fast and accessible.

Affiliate pages that send users to a merchant generally should not simulate a fake cart.

---

# 15. LEAD MAGNET / CONTENT PAGE ENGINE — MAGNETIC-INSPIRED

For non-commerce lead assets, choose a format first.

## Checklist
Typical structure:
- message-matched hero
- what this solves
- checklist groups
- concise action items
- optional quick-win callout
- CTA/download/next action.

## Playbook
- outcome
- who it is for
- prerequisite/context
- sequential steps
- examples/templates
- mistakes/risks
- next action.

## Mini-guide
- promise
- executive summary
- 3–7 concise chapters/sections
- diagrams/examples
- action summary
- CTA.

## Resource list
- purpose
- category filters/groups
- resource cards
- reason to use each resource
- next step.

## Personalized sales follow-up
- prospect/account-specific hero
- relevant observed context
- problem/opportunity
- tailored insight
- useful resource/recommendation
- proof/credibility
- low-friction CTA.

## Link-in-bio
- concise identity/context
- primary current offer/resource
- grouped topic links
- social proof if real
- newsletter/contact CTA.

---

# 16. RAPID VARIANT / REMIX ENGINE

Do not regenerate the whole page randomly for every experiment.

Use controlled inheritance:

```yaml
variant:
  parent_page_id:
  locked:
    - design_tokens
    - component_structure
    - product_facts
    - compliance_copy
  change:
    - audience
    - angle
    - hero
    - selected_proof
    - CTA_copy
```

Recommended variant families:
- audience variant
- problem variant
- outcome variant
- economic framing variant
- source/ad message-match variant
- proof-order variant
- hero visual variant
- short vs long explanation variant.

The Magnetic principle retained here is **reuse + remix**, not repeated full redesign.

---

# 17. AD-TO-PAGE CREATIVE CONTINUITY

When PagePilot-style ad generation is requested, create the ad and page as one system.

Ad package:
- hook
- primary text
- headline
- description
- CTA
- visual concept
- target audience
- angle ID.

The destination page must share:
- same angle ID
- same primary problem/promise
- compatible visual story
- same offer
- consistent CTA expectation.

Generate multiple ads per angle rather than mixing unrelated angles into one page.

---

# 18. LOCALIZATION

Localization is rewriting for the market, not literal translation.

For Greece:
- native Greek phrasing
- EUR
- Greece-specific delivery/warranty context
- local comparator context where relevant
- local idioms only when natural
- no US-centric shipping, pricing or social proof assumptions.

Preserve:
- brand voice
- persuasion structure
- component hierarchy
- factual meaning
- evidence status.

Reflow copy where Greek text expands relative to English.

---

# 19. RESPONSIVE CONTROL

Each component must define mobile behavior.

For every breakpoint consider:
- order
- stacking
- image crop
- padding
- text size
- CTA width
- sticky behavior
- table overflow/alternative layout
- tap targets
- accordion interaction
- carousel swipe behavior
- hidden/deferred noncritical media.

The default is mobile-first. Desktop is not the master layout that gets mechanically shrunk.

---

# 20. SEO / DISCOVERY LAYER

Where search traffic matters:
- buyer-intent title/meta
- semantic headings
- canonical URL
- Open Graph metadata
- optimized alt text
- structured data only when valid
- FAQ schema only when real FAQ content exists and eligibility is appropriate
- internal links for mini-sites
- product/spec content that avoids supplier duplicate text
- localized keyword intent.

Do not distort conversion copy merely to insert keywords.

---

# 21. PUBLISHING AND EXPORT MODES

The engine can target:

- existing Next.js/React application
- static HTML/CSS/JS
- Astro/content-first site
- Shopify theme/template/section architecture
- no-code/builder-native implementation when the project already uses one
- shareable hosted campaign page
- printable PDF
- PNG/visual export where required.

Publishing mode is selected from the destination workflow, not from preference for a framework.

---

# 22. EXPERIMENTATION ORDER

Prioritize:

1. product/offer
2. audience/use case
3. angle/message match
4. hero proposition
5. economic framing
6. proof order/type
7. CTA placement/copy
8. component sequence
9. image treatment
10. visual styling.

Do not start with random button-color tests when the offer or message match is uncertain.

Keep tests interpretable. Avoid changing many unrelated variables in one experiment.

---

# 23. PAGE QUALITY SCORE

Before launch score 0–100:

- Message match — 12
- Evidence/claim integrity — 12
- Product/offer clarity — 10
- Hero comprehension — 10
- Decision-path completeness — 10
- Trust/risk reduction — 10
- Visual hierarchy — 8
- Mobile UX — 8
- Performance — 6
- CTA clarity — 6
- SEO/metadata correctness where relevant — 4
- Analytics readiness — 4

Minimum default launch score: 85, with no hard failure in claims, tracking, destination or mobile usability.

---

# 24. GENERATION QA

PASS only when:
- source facts are reconciled with evidence
- angle is explicit
- traffic/message match is explicit where applicable
- archetype is named
- Page DNA exists
- every section maps to a registry component or justified custom component
- no unsupported claim appears
- no fake review/testimonial/scarcity/urgency appears
- product media is accurate enough for the use
- mobile layout passes
- typography and spacing are systematic
- CTA destination is correct
- affiliate tracking is verified when applicable
- analytics events are planned/working
- page performance is acceptable
- page can be edited/reused without rewriting the whole codebase.

---

# 25. COMPONENT CREATION RULE

A new component may be added to the registry only when:

1. existing components cannot express the needed job cleanly;
2. the new component solves a repeatable decision/communication need;
3. it has defined mobile behavior;
4. it has evidence/claim requirements;
5. it has copy/media constraints;
6. it can be reused across at least one meaningful class of pages;
7. it does not exist merely for decorative novelty.

After successful tests, promote strong custom components into the reusable registry.

---

# 26. CLOSED-LOOP COMPONENT LEARNING

Track component-level performance where feasible:

```yaml
component_performance:
  component_id:
  archetype:
  audience:
  traffic_source:
  impressions:
  view_rate:
  interaction_rate:
  downstream_CTA_rate:
  RPV:
  experiment_ids: []
```

Do not declare a component universally "high converting" from one page. Learn conditional fit:

`component × audience × archetype × traffic × offer`

---

# 27. MONTHLY PAGE-ENGINE OPTIMIZATION

During monthly AFFINITY optimization:

- review winning/losing page variants
- update component metadata
- retire consistently weak/deceptive/noisy patterns
- add new verified vendor/public techniques worth learning from
- refresh responsive/performance practices
- update archetype rules
- update copy constraints from measured outcomes
- preserve historical experiment evidence
- keep vendor-derived patterns abstract and original.

---

# 28. REQUIRED EXECUTION OUTPUT

When this engine is used, return/store:

```yaml
page_engine_output:
  context_brief:
  selected_angle:
  message_match:
  archetype:
  page_dna:
  component_ids: []
  copy_plan:
  media_plan:
  design_tokens:
  localization:
  experiment_hypothesis:
  variant_plan:
  analytics_events: []
  QA_score:
  deployment_or_export:
```

---

# 29. PUBLIC RESEARCH SOURCES USED FOR THIS MODULE

Primary PagePilot public sources checked on 2026-09-07:
- https://pagepilot.ai/
- https://pagepilot.ai/pricing
- https://pagepilot.ai/shopify-sections-and-blocks
- https://pagepilot.ai/drag-and-drop-page-builder
- https://pagepilot.ai/shopify-product-page-templates
- https://pagepilot.ai/product-description-generator
- https://pagepilot.ai/ai-product-image-generator
- https://pagepilot.ai/ai-ad-copy-generator
- https://pagepilot.ai/editable-cart-drawer
- https://pagepilot.ai/multi-language-ai-store
- https://pagepilot.ai/daily-winning-products
- https://docs.pagepilot.ai/en/articles/9682830-6-1-generate-your-product-page-with-pagepilot-ai
- https://docs.pagepilot.ai/en/articles/10358200-5-2-product-blocks
- https://docs.pagepilot.ai/en/articles/10358291-5-3-product-sections
- https://docs.pagepilot.ai/en/articles/10358281-5-4-general-layout-settings
- https://docs.pagepilot.ai/en/articles/10358288-5-5-cart-drawer-settings

Primary Magnetic public source checked on 2026-09-07:
- https://getmagnetic.ai/

These references are research provenance, not dependencies required at runtime.

---

# 30. FINAL RULE

The combined lesson from PagePilot and Magnetic is:

**Do not ask AI to design a page from scratch. Give it verified context, a conversion objective, a selected angle, a page archetype, a component grammar, copy limits, media intent and design tokens — then generate controlled variants and learn from real outcomes.**

That principle is mandatory for AFFINITY creative production.
