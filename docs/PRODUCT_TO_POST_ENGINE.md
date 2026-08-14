# SocialMarket Product-to-Post Engine

## Goal
Turn a verified affiliate product into evidence-bound, platform-specific marketing content and a 30-day publishing plan without copying merchant copy or inventing claims.

## End-to-end workflow

1. **Product intake**
   - `manual`: the admin supplies a product ID from `products`.
   - `auto`: the engine selects from `opportunity_scores` using the existing market-eligibility, preferred-offer, competition, HIGO and confidence signals.
   - Hard gate: product must be active, have a usable image and a non-empty affiliate `tracking_url`.

2. **Offer evidence / landing-page enrichment**
   - Resolve the public affiliate URL and collect only factual metadata: canonical URL, title/meta, JSON-LD Product/Offer data, price/currency, availability, images and concise structured facts.
   - Never copy page prose into social copy. Merchant text is evidence, not output.
   - Persist an evidence snapshot and content hash for auditability.

3. **Marketing strategy**
   - `offer-architect` creates evidence-grounded value propositions and objections.
   - Generate candidate angles using PAS, AIDA, 4Ps, JTBD, value/price, utility, lifestyle and urgency only when the offer facts justify urgency.
   - Score each angle for product fit, offer strength, social fit, novelty and evidence quality.

4. **Platform copy variants**
   - `conversion-copywriter` + `social-platform-strategist` produce multiple variants per platform.
   - Instagram: visual benefit + save/share orientation.
   - Facebook: clear offer/problem-solution and direct CTA.
   - TikTok: fast hook, short caption/script direction, no baked-in QR requirement.
   - LinkedIn: useful/professional recommendation rather than consumer-ad spam.
   - Affiliate disclosure is explicit/configurable; claims and prices must trace to current evidence.

5. **Creative brief + deterministic renderer**
   - Reuse the real product image; preserve product fidelity.
   - Apply a differentiated art direction (premium minimal, utility, editorial, bold offer, lifestyle framing).
   - Render platform-sized first-pass assets with product, hook, offer, CTA and QR where appropriate.
   - QR encodes the exact affiliate `tracking_url`; TikTok defaults to no QR in the visual.
   - Save to the private `creatives` bucket and create `creative_jobs` / `creative_assets` records.

6. **Creative QA**
   - Check image availability, product fidelity, safe margins, mobile legibility, price consistency, QR payload, disclosure and unsupported claims.
   - Fail closed when evidence or media is missing.

7. **30-day calendar**
   - `calendar-strategist` spaces variants to avoid creative fatigue.
   - Default weekly cadence: Instagram 4, Facebook 4, TikTok 5, LinkedIn 2. All are configurable.
   - Rotate frameworks/angles and avoid repeating the same product/angle on adjacent slots.
   - Store calendar items independently of the publisher so scheduling remains auditable.

8. **Approval and publisher handoff**
   - Content is generated as `needs_approval`.
   - Approved items can be promoted to the existing Social Scheduler / publishing routes.
   - The Product-to-Post engine never bypasses the human approval gate by default.

9. **Performance feedback**
   - Store impressions, engagement, outbound clicks, conversions and revenue when available.
   - Future runs may increase/decrease angle weights based on observed CTR/conversion performance, never on engagement alone.

## Model routing

- Deterministic rules and existing database evidence first.
- Existing `FreeModelRouter` (GitHub Models included quota) for semantic strategy/copy.
- Paid DeepSeek/OpenAI remains behind the existing explicit escalation gate and is not required for normal runs.
- If the free model is unavailable, the engine produces conservative deterministic variants instead of returning an empty result.

## Safety / quality invariants

- Exact affiliate link is immutable after intake unless a newer validated tracking URL is explicitly selected.
- No invented price, discount, stock, review, warranty, shipping or scarcity claim.
- No verbatim merchant marketing paragraphs in generated content.
- No publication before approval.
- No QR on TikTok creative by default.
- Every generated angle, copy variant and creative is linked to product + evidence + run for traceability.

## Worker lifecycle

`queued → processing → generated → needs_approval → scheduled → completed`

Failures retain structured error details and may be retried idempotently.
