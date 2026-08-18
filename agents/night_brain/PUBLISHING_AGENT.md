# Publishing Agent — Winners + Opportunities

## Mission
Translate the completed Top-100 and Top-20 creative mix into a healthy SocialScheduler queue without confusing ranking with publishing.

A product may rank highly and still be withheld from a particular slot because of fatigue, recent exposure, platform mismatch or existing scheduled inventory.

## Supply strategy
The active outbox should contain a deliberate exploit/explore mix:
- proven/returning winners and strong core content
- fresh opportunity challengers
- must-buy pain solvers
- platform-specific manual/editorial content when explicitly prioritized

## Creative mix target
For each Night Brain run, the Top-20 creative set targets:
- 8 WINNER / CORE
- 8 OPPORTUNITY
- 4 MUST_BUY

Quality may override the exact ratio.

## Ranked-creative handoff gate
Only ranked creatives tagged with `night_brain_engine=affiliate_night_brain_v1` are eligible for the Night Brain ranked-content path. Legacy ranking runs cannot silently inject old-strategy ranked creatives into the new outbox.

## Bounded capacity reclamation
Site-awareness is valid fallback inventory, but it must not consume every future slot before fresh ranked supply arrives.

When eligible Night Brain creatives exist, the scheduler may reclaim up to **40%** of future `approved` site-awareness slots on Facebook, Instagram and TikTok, with at least **2 hours notice**. It must never reclaim leased/published/sent inventory, manual platform-specific content, CSV priority content or explicit pain-solver content through this mechanism.

If Night Brain supply is zero, reclamation is zero and the existing calendar remains untouched.

## Scheduler rules
- Never duplicate a live outbox/delivery-history slot.
- Never schedule the same product too densely across channels.
- Preserve exact affiliate tracking URL.
- Respect each ranked creative's declared platform list and native format.
- Prefer fresh challengers when existing winners are overexposed.
- Keep strong winners alive when their evidence remains superior.
- Use bounded feedback learning; freshness is a boost, never a substitute for quality.
- Keep an exploit/explore balance instead of treating all ranked creatives as equivalent.

## Failure semantics
Publishing is downstream of ranking. An outbox/provider failure must not change the completed Top-100.

When new creatives are degraded/unavailable, use existing approved site/manual/pain-solver inventory rather than presenting an empty calendar. Once valid Night Brain supply exists, bounded reclamation creates room for Winners, Opportunities and Must-Buy creatives without destructively clearing the schedule.
