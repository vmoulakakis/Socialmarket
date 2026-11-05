# CarCare GR — Product Reality, Pain Gap and Design Contract
Date: 2026-11-05
Scope: Existing Vercel project `carcare-gr-lab` in `vmoulakakis/Socialmarket/apps/carcare`, NOT a new website.

## Evidence hierarchy
1. Primary product evidence: actual Linkwise JSON from server-side Vercel feed audit (HTTP 200, valid JSON).
2. Secondary intelligence: existing VMDB SocialMarket AI tables (`market_problem_clusters`, `commerce_feed_eligible_offers`, `ai_product_candidates`).
3. External Greek market interest is contextual; claims of actual search volumes, competitiveness or conversions are NOT established by these two data sources.

## Feed audit — before filtering
- First observed snapshot: 24,394 raw products; subsequent refresh: 23,900 raw products; 24,777,850 bytes. The feed is dynamic, so counts are snapshots, not constants.
- About 10,359 entries have automotive-related categories by a broad keyword filter. THIS IS NOT THE NUMBER OF VALID LIVE OFFERS.
- Examples: 1,369 in `Ανταλλακτικά Αυτοκινήτων`; 859 in automotive lamps; 607 automotive gadgets; 537 automotive cleaning/utility; 466 window switches; 378 wiper category.
- Significant additional automotive categories: floor mats, key shells, oils, car batteries, trunk struts, car covers, car window regulators, parking systems.
- Non-auto products are present (hotels, jewellery, household products) and MUST NOT appear on CarCare.
- All raw entries had an image URL and tracking URL field, but functioning links and image HTTP responses are not implied.
- Actual fields include `program` (sometimes object-shaped, not `program_name`); price is decimal comma, e.g. `44,99`; `in_stock` uses Y/N; availability includes human-readable Greek strings.
- Feed category names include HTML entities encoded more than once.
- Later audit: 7,627 automotive products passed base checks (price, stock, link, date, category), before refined pain-fit deduplication and suitability checks. Initial loose problem matches were 448 visibility, 917 lighting, 1,173 cleaning, 996 electrical, 340 gadgets, 2,895 maintenance; there may be overlap and were subsequently tightened to reduce false positives.
- Source URLs should be used **unchanged** for affiliate destination and image (no mock images, QR tracking substitutions or direct merchant URLs).

## Real products observed
- Bosch H250 rear windscreen wiper, 250mm, €6.00
- OSRAM LEDriving HL EASY LED H7/H18 set, €55.00 (legal/vehicle suitability NOT verified)
- FIAMM Titanium Pro L2 64P 64Ah 610A battery, €90.00
- Topdon V2200Air jump starter and air compressor, €155.00
- Carmotion polishing sponges, €11.99
- NTY VW throttle-body part, €145.00
Examples are audit snapshots, not claims of current availability, fit or recommendation.

## Actual pain-fit opportunities — site journey priorities
1. Poor visibility in rain -> wipers, compatible pumps, windshield cleaning (fit: length and connector type).
2. Weak/failed lighting -> bulb specification / legal upgrade (fit: socket, OEM and approvals).
3. Vehicle cleaning / protection -> surface-safe products (fit: material, directions).
4. Power-window or door-electrical failure -> switches, window regulator kits, actuator components (fit: part/OEM number, model/year).
5. Everyday car convenience -> chargers, organizers, parking equipment, practical gadgets (fit: device and electrical spec).
6. Routine maintenance -> battery, oil, filters and spare parts (fit: manufacturer specification, battery polarity/dimensions, approvals).

## VMDB SocialMarket AI corroboration and limitations
- 23,495 eligible feed offers across the existing general SocialMarket DB; this is a separate catalog and not equal to the linked CarCare feed.
- The stored `carcare_offers` table was empty at inspection.
- Four automotive problem clusters exist: EV battery health (severity 93), DPF diagnosis (88), recurring A/C refrigerant leakage (86), parasitic battery drain (84); confidence 0.55 each.
- These are unvalidated internal heuristics, NOT measured Greek search demand and not product matches by themselves. Product recommendation must be withheld without a functional fit and appropriate technical evidence.
- Product conversion scoring must prioritize user need and safety; commission cannot override compatibility or generate unsupported product claims.

## UI design contract
- Intent: **Problem -> practical checklist -> safe product shortlist -> budget calculation -> merchant through intact tracking URL**.
- Palette: deep petrol #081513, surfaces #20382d, neon sage #c6f675, secondary text #a5bdac, warm caution #ffcc88.
- Typography: Manrope with Greek support, 16px+ reading where appropriate.
- Desktop: header + hero + 6 journey cards + advisor + transparent calculator + social action.
- Mobile: 2-column quick choices, stacked advisor/calculator, large tap targets and readable product details.
- Motion: low-cost hover and reveal transitions and progressive calculation bar; honor prefers-reduced-motion.
- Data safety: no raw third-party feed on client. API serves selected, normalized offers only; source credentials via server env var.
- Never mark keyword similarity as verified technical fit; warn on OEM, wiper size, lighting homologation and electrical repairs.
- Empty, loading and error states should be user-facing; no fabricated ratings, sales volumes, inventory or market sizes.

## QA gates
- npm test passes including Greek price normalization, URL allowlisting, automotive-only taxonomy, stock and expiry.
- Next.js production build passes in `apps/carcare`.
- Vercel preview is READY and feed endpoint is tested if accessible. SSO-protected previews may require authenticated browser testing.
- Responsive and actual click-through QA required before production release.
- Production alias `carcare-gr-lab.vercel.app` stays untouched until verified.

## Greek market background (external evidence, not causal conversion proof)
- 2026 reporting of ACEA 2024 estimates puts the Greek passenger car fleet mean age at 17.8 years (EU 12.7), around 4.53 million of 5.7 million cars over ten years old. Source: eKathimerini, 2026-08-12, https://www.ekathimerini.com/economy/1312230/car-sales-rise-but-fleet-remains-aged/.
- Greek passenger-car replacement parts market value grew at estimated ~7% average annual rate over 2023-2025, according to an ICAP CRIF study reported by Kathimerini in 2026. This supports aftermarket opportunity, but does NOT establish search demand, gaps in competition or conversion by SKU. Source: https://www.kathimerini.gr/society/564224713/aytokinita-i-ereyna-gia-tis-poliseis-antallaktikon-kai-ta-meridia-gia-gnisia-kai-after-market/.

## UI/UX Pro Max polish — 2026-11-05
- Preserve the same Vercel project/domain and all existing relevant routes.
- Selected category, selected product and budget scenario have separate explicit states.
- Search and budget filters debounce by 380ms before expensive remote retrieval.
- Fetch failures use same-category retry; no silent category switching.
- Product-specific price reference updates the cost calculator and scrolls to it.
- Progressive offer reveal uses a real show-more control rather than an inert product cap.
- Touch controls and visible focus; responsive layout from existing styles; motion reduced when requested.
- The model/year and quick answers currently guide user data collection but DO NOT establish verified vehicle/part compatibility. Maintain explicit disclaimer.
- Observed latest feed audit: 7,627 candidate automotive products passed base gates on a previous snapshot. Treat as dynamic, never display as fixed current volume.
- Release verification gates: all 12 automated tests, optimized Next build, Vercel READY, verified production alias, no invented product images/tracking.
