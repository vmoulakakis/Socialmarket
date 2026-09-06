# AFFINITY Creative Production Skill

## Mission
Create and continuously improve high-converting public pages, posts, articles, comparison experiences and creative marketing assets by combining the canonical `skills/AFFINITY_SKILL.md` funnel/conversion framework with a modern, performance-first web-design system.

This skill is execution guidance for GrowthOps. It does not select products, invent demand, replace SocialMarket canonical market intelligence or create an independent schedule.

## Required upstream context
Before creation, consume the Growth Orchestrator task packet containing as available:
- canonical category/subcategory/product/pain IDs
- Greek demand and direction
- competition/whitespace state
- validated pain/desire/use-case evidence
- target audience/use-case segment
- affiliate/merchant/tracking evidence
- total-solution-cost/economic comparison evidence
- existing site/page analytics and conversion baseline
- SEO/search intent
- experiment hypothesis and target KPI.

If evidence required by AFFINITY hard gates is missing, return HOLD rather than fabricate persuasion.

## Canonical dependency
Always apply `skills/AFFINITY_SKILL.md` for affiliate/commercial experiences. AFFINITY decides the funnel architecture from the buyer problem, product, economics, evidence and trust requirements. Never force every product into the same landing-page template.

## Supported output types
- product/pain-gap landing page
- single-product microsite
- multi-page mini-site
- comparison page/experience
- buying guide
- editorial review
- ROI/savings calculator
- quiz/recommender/configurator when justified
- SEO article/post
- social-ready article derivative
- campaign hero/creative concept
- product hero image brief
- infographic/data-visual asset brief
- social card/carousel/post creative
- short-form video/storyboard brief
- email/newsletter creative module when requested by the Orchestrator.

## Page strategy
The shortest honest persuasive path wins. Select structure from AFFINITY funnel analysis. Typical flow may include:
1. buyer problem/outcome
2. high-signal evidence or quantified context
3. why current/local alternatives leave a gap
4. product/solution mechanism
5. proof/specifications/comparison
6. economics/ROI when defensible
7. trust: warranty, returns, delivery, support, installation burden
8. clear CTA through verified affiliate/tracking URL.

Do not add sections, popups, animations, calculators or interaction merely to appear premium.

## Web design framework policy
Choose the smallest high-quality implementation stack that matches the existing project and deployment adapter.

Preferred patterns:
- Existing Next.js/React project: Next.js App Router + TypeScript where already used; Tailwind CSS when project-standard; shadcn/ui or Radix primitives for accessible UI patterns when compatible.
- Content-heavy/mostly static public experience where a new stack is actually warranted: Astro or static semantic HTML/CSS with minimal JavaScript, subject to the existing deployment architecture.
- Existing vanilla microsite: semantic HTML + modern CSS + minimal JS; do not rewrite to React only for fashion.
- Existing Webflow/Lovable/ChatGPT/other builder: preserve native design-system primitives and use the platform adapter rather than recreating the site elsewhere.

Motion:
- Prefer CSS transitions or native platform motion for small effects.
- Framer Motion in React only where it materially improves comprehension or interaction.
- GSAP only for justified high-value storytelling/animation and only when performance budget permits.
- Avoid animation that delays CTA comprehension or worsens Core Web Vitals.

## Design quality standard
Every page must be:
- mobile-first and responsive
- visually distinctive for the actual product/audience, not a repeated house template
- fast and lightweight
- accessible by keyboard and screen reader where interactive
- high-contrast and readable
- clear in hierarchy and scanning behavior
- conversion-focused without deceptive dark patterns
- trustworthy near conversion points
- consistent in spacing, typography and component behavior
- robust at common mobile widths and large desktop widths.

Use a deliberate design system per experience:
- typography scale
- spacing scale
- grid/container rules
- radius/border/shadow rules
- iconography rule
- CTA hierarchy
- motion rule
- responsive breakpoints
- reusable component tokens.

Do not use random visual treatments section by section.

## Art direction
Art direction is derived from the market/product/use case. Examples: premium editorial, industrial precision, technical utility, B2B procurement, Mediterranean lifestyle, hospitality, automotive diagnostic, home-efficiency, travel, etc.

Do not mechanically reuse one hero style, gradient, card layout or color identity across unrelated sites.

## Creative marketing assets
For each asset, define:
- objective
- audience/use case
- single dominant message
- verified product/market claim set
- visual concept
- composition/layout
- product prominence
- CTA or next action
- dimensions/channel variants
- text-safe zones
- accessibility/readability constraints
- source/provenance for product media.

Creative must be generated from real product/evidence inputs. Never invent testimonials, customer counts, ratings, awards, scarcity, medical/scientific claims, discounts or before/after performance.

When AI-generated visuals are used, they must not misrepresent the real product's shape, controls, accessories, dimensions or results. For exact product representation, prefer verified merchant/manufacturer imagery or use supplied product imagery as the reference.

## Copy standard
Follow AFFINITY copy hierarchy:
Outcome/problem -> defensible context -> mechanism -> evidence -> economic comparison -> risk reduction -> CTA.

Writing rules:
- human, specific, concise
- avoid generic AI filler
- match buyer sophistication and purchase mode
- state disadvantages/material limitations when relevant
- use Greek or English according to target market/search intent
- preserve claim/evidence classes internally
- affiliate disclosure must be clear but should not dominate the buyer experience.

## SEO page/post production
For articles and posts:
- target validated search intent, not arbitrary keyword stuffing
- satisfy the query first; commercial CTA second
- use semantic headings and strong information architecture
- add internal links only when topically useful
- use FAQ/schema only when content actually supports it
- use original synthesis/evidence; do not mass-produce near-duplicate pages
- align title/meta/intro with actual page promise
- create comparison tables only with honest comparable dimensions
- maintain crawlability, canonical and sitemap integration.

## Conversion instrumentation
Every new or materially changed commercial page must expose the agreed GrowthOps events when supported:
- pageview
- session_start
- CTA exposure/click where instrumented
- affiliate_click
- calculator/quiz completion when present
- lead/key_event/purchase when reliably available
- share event where useful.

The page must have a defined primary conversion metric and baseline/measurement window when launched as an experiment.

## Performance budget
Default goals unless the existing project imposes stricter limits:
- minimize blocking JavaScript
- responsive optimized images
- lazy-load noncritical media
- no oversized hero video by default
- avoid unnecessary third-party scripts
- preserve or improve Core Web Vitals
- no visual library added for one trivial component.

A design enhancement that materially degrades performance requires explicit evidence that the tradeoff is worthwhile; otherwise reject it.

## QA gates before production
PASS only when applicable checks succeed:
- page/build renders without error
- mobile and desktop layout reviewed
- no horizontal overflow
- CTA and affiliate destination correct
- tracking URL remains verified
- no unsupported or deceptive claims
- metadata/canonical/schema valid
- image/media provenance acceptable
- links work
- accessibility basics pass
- Core Web Vitals/performance not materially regressed
- analytics events fire as designed
- no duplicate/conflicting conversion tracking.

## GrowthOps handoff
Return to the Growth Orchestrator:
- output_type
- site_key/page
- chosen AFFINITY funnel architecture
- design/art-direction rationale
- framework/components used
- claims/evidence used
- files/change reference
- assets created/referenced
- SEO intent
- target KPI
- analytics events
- QA result
- deployment reference
- rollback reference
- measurement window.

## Non-negotiable rules
- AFFINITY is the commercial/funnel design authority for affiliate experiences.
- SocialMarket demand/competition/pain truth is never replaced by creative inference.
- Best design means best fit + clarity + trust + performance + conversion, not maximum visual complexity.
- Never generate fake proof or deceptive urgency.
- Never expose secrets or internal commission economics to consumer pages unless specifically required.
- Reuse existing project stack when sound; do not create framework churn.
