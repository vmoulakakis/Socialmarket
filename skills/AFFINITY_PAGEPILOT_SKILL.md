# AFFINITY PAGE BUILDER SKILL

## Mission
Build premium, high-converting AFFINITY eShop pages that start from a real problem, explain the gap, present the product as the solution, and preserve evidence, tracking integrity, mobile performance and brand consistency.

This skill adapts publicly documented PagePilot-style principles such as product-link-to-page generation, modular conversion sections, niche templates, AI images/copy, editable page structure, cart/upsell thinking, on-page SEO and mobile-first publishing. Do not copy proprietary PagePilot source code, private templates, internal JSON, prompts or assets.

Canonical framework: `config/affinity-page-builder.json`.

## Public brand
- Brand: AFFINITY
- Tagline: Small Solutions. A Better You.
- Public experience: premium eShop / social commerce, never an affiliate directory.
- Internal source/provider names must not appear as product merchandising labels.
- Never expose commission or internal scoring as a consumer-facing sales claim.

## Page generation flow
1. Resolve the product and verified tracking URL.
2. Resolve the buyer job-to-be-done, pain, gap and desired outcome.
3. Select an AFFINITY angle: rare find, social pick, demand pick, or problem solver.
4. Build the page model from `config/affinity-page-builder.json`.
5. Generate or select imagery that preserves the real product. Product imagery must not invent physical properties.
6. Write benefit-led copy. Translate features into outcomes, but do not invent performance claims.
7. Add evidence/proof blocks using only real evidence.
8. Add objections and buyer checks.
9. Add offer CTA using `tracking_url` with `rel="sponsored noreferrer"`.
10. Add QR code whose destination is the affiliate tracking URL.
11. Add share buttons whose destination is the branded canonical AFFINITY landing page.
12. Add dynamic metadata, schema, canonical URL and sitemap discoverability.
13. Validate mobile layout, CTA visibility, keyboard modal close and external-link behavior.

## Required eShop surfaces
### Store homepage
- premium brand navigation
- editorial hero
- featured solution cards
- search by problem/intent
- Pain → Gap → Solution explanation
- trust/curation section
- collections by need
- social/share band
- newsletter capture slot
- premium footer

### Product card
Every product card must have:
- real product image
- product title
- short outcome/benefit line
- price indication when available
- small meaningful merchandising badge
- `Δες το case` link to AFFINITY landing page
- `Δες προσφορά` button that opens the AFFINITY commerce modal
- no raw supplier/network label on the public card

### Product landing page
Default sequence:
1. Product hero
2. Fast benefits
3. Pain / Gap / Solution
4. Visual use case
5. Why now
6. Evidence / proof
7. Best for / before you buy
8. Objection check
9. FAQ
10. Offer CTA
11. QR + share
12. Related solutions
13. Sticky mobile CTA

Reorder sections when the product or niche warrants it. There is no one-template-fits-all rule.

## Conversion modal
Use `components/affinity/AffinityCommerceModal.jsx`.

Modal rules:
- primary CTA opens the current verified `tracking_url`
- QR encodes `tracking_url`
- share buttons share the AFFINITY canonical case URL
- provide native share plus WhatsApp, Facebook, LinkedIn and X
- provide copy-offer-link action
- close on Escape and backdrop click
- lock body scroll while open
- show affiliate and price/availability disclosure

## Conversion copy
Strong copy is specific, useful and outcome-led.

Good:
- “Δες αν σε συμφέρει σήμερα”
- “Λιγότερη τριβή στο καθημερινό setup”
- “Για όσους χάνουν χρόνο κάθε μέρα με…”
- “Έλεγξε συμβατότητα και σημερινή τιμή”

Avoid:
- fake countdowns
- fake stock warnings
- fabricated review counts
- unverified “best”, “#1”, “guaranteed” or medical/performance claims
- manipulative dark patterns

Urgency must be based on a real expiring promotion, observed availability, price validity, shipping cutoff or other concrete evidence. Otherwise use neutral urgency such as “έλεγξε τι ισχύει σήμερα”.

## Social creative system
For every publishable case, prepare:
- 1080×1080 square
- 1080×1350 feed
- 1080×1920 story/reel cover
- headline/hook
- one benefit statement
- one CTA
- QR variant where appropriate

Social posts should link to the AFFINITY case page by default. The case page then converts through the affiliate modal. Use raw affiliate links only for explicit offer/QR conversion actions.

## Design language
- premium warm neutrals: ivory, parchment, charcoal, muted gold
- high-contrast editorial serif for hero/display headings
- clean sans-serif for UI and body
- spacious layouts
- rounded but restrained cards
- cinematic real product/lifestyle images
- dark promotional bands used sparingly
- no generic dropshipping visual clutter
- desktop sophistication, mobile-first interaction

## CRO modules
Use when evidence and context support them:
- hero benefit stack
- trust badges
- FAQ
- product comparison
- bundle/related solution
- objection handling
- use-case gallery
- sticky CTA
- QR/share module
- offer modal
- newsletter capture
- recent-discovery / freshness messaging

## QA checklist
Before calling a page complete verify:
- no broken images
- no public internal source names
- no commission disclosure beyond standard affiliate disclosure
- tracking URL present for every conversion CTA
- modal works on card and landing page
- share URL points to AFFINITY case page
- QR points to tracking URL
- external offer links use sponsored/noreferrer
- price is labeled as an indication if it can change
- claims are evidence-backed
- mobile layout works
- dynamic metadata exists
- sitemap includes the case when publishable
- CI/build succeeds

## Invocation
Use this skill whenever the user requests `@AFFINITY`, AFFINITY eShop, product landing pages, PagePilot-style pages, problem-solver funnels, affiliate conversion modals, QR/social product creatives or conversion-focused product presentation.
