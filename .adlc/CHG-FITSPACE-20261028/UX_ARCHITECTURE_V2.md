# FitSpace AI — UX and spatial data architecture V2
Date: 2026-10-28 | Change: CHG-FITSPACE-20261028 | STATUS: PLAN / NOT IMPLEMENTED

## Experience objective
A Greek-first, installable, app-like Web/PWA for HomeFit, FitMatch and suitable partner sites. The visitor sees a real architectural workspace, not an ordinary product catalog: upload/scan room, inspect/edit every dimension, switch 2D/3D, see what fits, compare verified products. No forced app-store download and no email wall before value.

## Main interaction: single-shell, progressive stages
A. Choose purpose: home furnishings, exercise machines, appliances or custom category; open camera/photo upload or manual plan. Explain data retention and precision.
B. Intelligent multi-view guided acquisition: overview from doorway, adjacent angle, opposite angle, low/higher view for occlusions and door/window geometry. Do NOT impose a fixed photo count: assess coverage, blur, overlapping landmarks, glare and missing walls, guide precise retakes. Show a coverage map and a reason for each requested additional frame. Permission denial always falls back to file upload or manually entered geometry.
C. Calibrate at least one actual metric anchor with user-marked endpoints: measured wall, tape-marked reference, or trusted native sensor. An uncalibrated reconstruction is labeled qualitative ONLY; no fictitious cm.
D. Confirm and correct each wall, opening, pillar, niche, door swing, room height, obstacle and movable object. The user selects the 2D annotation or 3D object and types cm, drags an accessible handle, locks confirmed measurements and has Undo/Redo.
E. On each saved change, a revisioned geometric constraint solver updates wall connectivity, adjacent unlocked lengths, floor polygon, area, opening placement, clearances, 3D geometry and eligible products. A conflict view shows precisely which confirmed constraints cannot all be honored. New AI inference results cannot override more recent manual corrections.
F. Display one source-of-truth room in two modes (2D plan + 3D scene), not separately generated fantasy pictures. If good product GLB is unavailable, use an accurate verified bounding-box representation instead of claiming realism.
G. Shopping drawer: up to 3 suitable product offers, with reason, fit verdict, clearance, manufacturer dimensions, date/stock/shipping caveats, total verified price where known, merchant coverage limitations, clearly labeled affiliate partnership and honest CTA. No approval or unverified tracking = no affiliate buy CTA.
H. Export/share: privacy-safe room layout and dimension PDF/JSON; optional signed account sync and price alerts; no implicit marketing consent.

## Status semantics
ESTIMATED: AI/model suggestion, uncertain bounds. ANCHORED: scale from verified user known measurement. CONFIRMED: user manually checked exact dimension. CONFLICT: physically inconsistent constraints. MISSING: no evidence.
FIT_VERIFIED only when all critical room and vendor dimensions + category safety clearances are known and conservative with uncertainty. FIT_ESTIMATED shows uncertainty. NEEDS_MEASUREMENT blocks decisive claim; DOES_NOT_FIT shows failed geometry.
No misleading accuracy percentage or cheapest-in-Greece promise.

## UX contract
Mobile: canvas-first composition, bottom action bar, swipeable inspector panels, camera/orientation helpers, safe-area support, accessible numerical measurement inputs and touch targets. Avoid endless scrolling as the main task-navigation model. Desktop: center live canvas, left capture/measurement queue and right detail properties/merchant drawer. Scoped scroll for long content. Accessible keyboard/touch/mouse controls, focus management, WCAG 2.2 AA target, explicit loading/offline/error/undo states, reduced motion and mobile performance fallback.

## Aesthetic direction for Work design review
Distinctive architectural instrument: gypsum white drawing surface; charcoal ink; accent amber for uncertain measurement; teal for confirmed; restrained copper/coral for important actions. Real measurement ticks, grid and dimension lines are functional, not decoration. Greek-capable sans font paired with tabular monospaced numerals; avoid generic dark gradients or sci-fi fake holograms. The signature moment is a dimension edit that synchronously moves the room geometry and updates fit. Produce three visual approaches in Product Design Work mode, choose one before implementing UI; do not claim plugin screenshot prototype in this research step.

## Modular architecture
- Shared PWA frontend in TypeScript/Next.js; offline-capable manual editor and photo capture; install manifest and home-screen prompts.
- Reusable FitSpace Web SDK as isolated package, secured tenant configuration and separate customer session scope per hosted site.
- Private photo storage in Supabase or approved equivalent with encrypted access, explicit consent and expiration/delete policies; EXIF location stripped unless explicitly needed; never send raw photos to affiliate networks.
- AI worker (private, GPU-backed and bounded by quotas) running MapAnything Apache or DA3-BASE and Florence2/SAM2 candidates; requests return observations, masks, depth, camera poses and per-item uncertainty, not trusted final room.
- Parametric Geometry Service: world coordinate graph (metres internally) of vertices/walls/openings/obstacles/anchors, plan solver, constrained fit and immutable revision IDs; deterministic geometry is authoritative.
- Real-time 2D renderer and Three.js / React Three Fiber viewer are consumers of the SAME revision; no separate AI-generated 3D truth.
- Category plug-ins for furniture, exercise equipment, appliances and future products; vendor manufacturer geometry must be verified.
- Commerce adapter separated from geometry; integrate SocialMarket/Awin/Linkwise only for joined merchants with fresh feed, validated prices and tracked link.
- iOS RoomPlan native option on LiDAR devices and Android ARCore Depth native option on supported phones may send structured data into same room schema; never necessary for web MVP.

## Shared schema sketch
Session: tenant_id, scope, consent, capture_state, revision_id, expires_at
Capture: photo_private_path, image_dimensions, camera_intrinsics, point_of_view, quality metrics, consent_version
Anchor: source type, endpoints, value_m, uncertainty_m, confirmed_by_user, locked
Scene: revisions, vertices, wall segments, openings, obstacles, ceiling_height, placed_items, constraint residuals
GeometryEdit: idempotency_key, base_revision, edits, actor, created_at
FitEvaluation: geometry_revision, product_geometry_revision, rules_revision, verdict, blockers, measured_clearances
OfferEvidence: merchant approved, feed age, dimensions source, total price/shipping, link signature, affiliate disclosure

## Deterministic correction acceptance example
Measured wall 260cm automatically estimated; visitor corrects to confirmed 240cm. Under the same new revision: polygon and adjacent unlocked geometry solve, area and clearance update, both 2D and 3D reflect changes, products previously at 250cm are marked DOES_NOT_FIT or NEEDS_MEASUREMENT, prior valid offers re-ranked, a transparent diff appears. If locked confirmed walls cannot close, show a conflict dialog, do not move anchors secretly.
