# AFFINITY Page Engine — Production QA Gates

Version: 1.0
Status: Canonical

This QA is mandatory for new/materially rebuilt commercial pages and campaign assets governed by the AFFINITY Page Engine.

---

## 1. Truth & claim gate — HARD

FAIL if any of the following occurs:
- unsupported factual claim presented as verified
- fabricated review/testimonial/rating
- fake scarcity or fake countdown
- false comparison
- unsupported percentage/statistic
- unverified medical/scientific/safety claim
- generated image presented as real customer/documentary proof
- merchant identity, offer, price, warranty, returns or delivery misrepresented.

Every conversion-critical claim must map to an evidence ID or be clearly non-factual creative language.

---

## 2. Product-media fidelity gate — HARD

For exact product representation verify:
- product shape/model is correct
- controls/ports/buttons are not invented
- included accessories are not added/removed by generation
- scale/dimensions are not misleading
- safety configuration is not altered
- packaging/certification marks are genuine when shown
- before/after results are real and supportable when used.

Generated lifestyle/context imagery may supplement exact product media but cannot silently redefine the real product.

---

## 3. Message-match gate

For campaign traffic verify:
- source hook/problem is recognizable on landing
- source promise and landing promise are compatible
- source offer and landing offer match
- CTA expectation is continuous
- hero does not introduce a competing unrelated angle
- first proof sequence supports the campaign promise.

A material mismatch should trigger a separate landing variant rather than generic compromise copy.

---

## 4. Decision-path gate

For every primary section ask:
1. What decision barrier or promised content value does this section resolve?
2. Is another section already doing the same job better?
3. Does the visitor need this before the target action?

Remove sections that have no clear answer.

Default page-length guidance:
- impulse: 5–8 primary sections
- considered: 7–11
- high-ticket considered: 9–14
- professional procurement: 9–15
- lead-gen: 4–9.

Longer pages require explicit rationale, not filler.

---

## 5. Copy-quality gate

Check:
- one dominant message per section
- hero can be understood quickly without scrolling
- headlines are specific, not generic AI slogans
- benefits are tied to supported mechanism/features
- no repeated claim across many sections without purpose
- no jargon unless audience expects it
- Greek/localized copy reads natively
- buttons describe the real next action
- long copy does not force unreadably small typography.

---

## 6. Component-contract gate

Every major section must:
- map to a Component Registry ID or justified custom component
- satisfy its required inputs
- satisfy evidence requirements
- obey mobile behavior
- obey accessibility requirements
- use defined analytics events when applicable.

FAIL when a component requiring unavailable proof is used anyway.

---

## 7. Responsive visual QA gate — HARD for breakage

Review at minimum these viewport widths:
- 360 px
- 390 px
- 768 px
- 1024 px
- 1440 px
- 1920 px.

Check:
- no horizontal overflow
- no clipped text/buttons
- intentional headline wrapping
- media subject remains visible after crop
- tables have mobile strategy
- sticky CTA does not cover interactive content
- dialogs/drawers remain usable
- cards/grids do not collapse awkwardly
- section spacing remains coherent
- CTA is easy to find and tap
- fixed/sticky UI does not hide focused elements.

---

## 8. Accessibility gate

Target: WCAG 2.2 AA.

At minimum verify:
- keyboard navigation
- visible focus
- focused elements not obscured by sticky content
- logical heading hierarchy
- accessible names for controls
- meaningful alt text; decorative images hidden appropriately
- form labels/error messaging
- color contrast
- no interaction that requires dragging without alternative
- pointer targets satisfy WCAG 2.2 target-size requirements or allowed spacing exceptions
- reduced-motion preference respected for nonessential motion.

Do not claim formal conformance from automated checks alone; manual review remains required for material pages.

---

## 9. Performance gate

Use current Core Web Vitals “good” field targets as goals at p75:
- LCP ≤ 2.5 s
- INP ≤ 200 ms
- CLS ≤ 0.1.

Implementation checks:
- hero/LCP media appropriately sized and prioritized
- explicit width/height/aspect ratio where possible
- noncritical media lazy loaded
- third-party scripts minimized
- no oversized autoplay hero video by default
- no dependency added for one trivial effect
- animations use transform/opacity where appropriate
- expensive client JS deferred or removed
- responsive image delivery implemented.

A lab result is diagnostic; field data remains the strongest performance truth when available.

---

## 10. Commerce / affiliate action gate — HARD

Affiliate pages:
- CTA uses verified tracking URL
- final destination is correct product/offer
- merchant is clearly distinct from affiliate publisher
- no fake local cart unless checkout is actually owned by the site.

Owned ecommerce:
- variants/quantity/cart work
- totals are correct
- checkout action works
- upsells do not block purchase
- free-shipping threshold is real
- countdown/reservation logic is genuine if present.

---

## 11. SEO / discovery gate

When search indexing matters:
- title/meta match real page promise
- semantic headings
- canonical URL
- robots/indexing state intentional
- Open Graph/social metadata
- image alt text
- schema only when valid for actual page content
- no mass near-duplicate campaign variants indexed without canonical/noindex strategy
- localized versions use correct canonical/hreflang strategy where implemented.

Paid-only experiment variants should not accidentally create duplicate indexed pages.

---

## 12. Analytics / experiment gate

Verify relevant events:
- page_view
- qualified_view where defined
- component/section exposure when useful
- affiliate_cta_view
- affiliate_click
- add_to_cart / checkout / purchase when owned and reliable
- lead form start/submit
- calculator/quiz completion
- experiment assignment.

Attach stable IDs where lawful/useful:
- page_id
- variant_id
- product_id
- angle_id
- archetype
- component_id
- campaign/source
- locale
- device class.

Do not send secrets or sensitive personal data into telemetry.

---

## 13. Variant-isolation gate

Every experiment needs:
- parent page ID
- variant ID
- one primary hypothesis
- locked fields
- changed fields
- primary metric
- guardrail metrics
- measurement window
- rollback reference.

Reject experiments where so many variables change that the result cannot teach anything useful.

---

## 14. QA score

Score 0–100:
- Message match: 12
- Evidence/claim integrity: 12
- Product/offer clarity: 10
- Hero comprehension: 10
- Decision-path completeness: 10
- Trust/risk reduction: 10
- Visual hierarchy: 8
- Mobile UX: 8
- Performance: 6
- CTA clarity: 6
- SEO/metadata: 4
- Analytics readiness: 4.

Default production threshold: **85/100** plus zero hard failures.

---

## 15. Automated vs manual checks

Automate where reliable:
- missing files/schema validity
- link status
- route HTTP status
- structured metadata shape
- duplicate component IDs
- obvious overflow screenshots/diffing when test tooling exists
- Lighthouse/performance lab checks
- accessibility scanner
- analytics event smoke tests.

Manual/AI-render review still required for:
- visual hierarchy
- product-image fidelity
- misleading persuasion
- nuanced message match
- copy repetition
- mobile composition quality
- genuine usefulness of each section.

---

## 16. Release result

Return:

```yaml
production_qa:
  page_id:
  variant_id:
  score:
  truth_gate:
  media_fidelity_gate:
  message_match_gate:
  decision_path_gate:
  responsive_gate:
  accessibility_gate:
  performance_gate:
  destination_tracking_gate:
  seo_gate:
  analytics_gate:
  hard_failures: []
  warnings: []
  result: PASS|FAIL
  deployment_allowed: true|false
```
