# CHG-FITSPACE-20261028 — Implementation Plan

Status: PLANNED ONLY, no frontend/ML/runtime shipped as part of this change. Parent app: SocialMarket; new shared module should become isolated package/service with independent deployments, not a hard-coded HomeFit widget.

## P0 — first independently testable slice
- Create private isolated development service / package (separate from current SocialMarket production release path).
- Capture wizard: photo/upload, overview + guided missing-angle requests, blur and coverage evaluation; optional manual dimensions, metadata and calibrated scale anchor.
- Editable 2D room plan: drag vertices/edges; select a dimension; edit exact centimetres; state inferred/confirmed; undo, redo, conflict feedback.
- Deterministic geometry + revisioned dependency graph; 3D rendering from same world coordinate model; no fake scan precision.
- Product fit adapter: rectangle/polygon footprints, confirmed vendor dimensions, openings, circulation, verdict and explanation. Price feed integration comes only after verified affiliate contracts.

## P1 — progressively enhanced AI
- Replace/manual augment geometry suggestions with multi-view vision processing and confidence-tested room reconstruction; quality-based request for more photo angles. Human confirmation always supported.
- Robust native adapters for supported iOS LiDAR/RoomPlan and Android ARCore Depth; no blanket phone-compatibility claims.
- Save project to user account; session export with measured and unverified dimensions, revision history.

## P2 — ecosystem and conversion
- Embeddable SDK with tenant host allowlisting, consent isolation, style tokens, per-category fit rules.
- Integrate HomeFit and FitMatch in staging independently; do not redeploy existing apps in this specification change.
- Link to SocialMarket's price+feed intelligence, refreshed stock/shipping/commission verification, affiliate disclosure; no fabricated price superiority.
- Funnel A/B tests for photo-first versus dimensions-first, completion, fit-confidence and affiliate-click events (only with proper consent).

## Quality gates
- Geometry unit tests: polygon closure, constraint solver, scale consistency, 260→240 cm recomputation, conflicted anchors, undo, stale AI result rejection.
- Privacy/security: uploads private, tenant isolation, TTL deletion, no implicit photo model-training consent, no secrets in logs.
- Mobile UX: camera permissions, incomplete angle guidance, low light, motion blur, screen readers and manual fallback.
- E2E: verified 2D and 3D share geometry revision; product fit changes appropriately; no approved merchant -> no commercial clickout.
- Independently review architecture and AI accuracy; never mark production verified without published evaluation data, browser QA and approval.

## Explicit non-goals for first slice
No centimeter-guarantee from generic single images, no autonomous merchant joins, no commercial publication on Vercel Hobby, no price claim for products outside known supplier coverage, no automatic AR app installation.

## Unchanged
SocialMarket main and CarCare PR #96 remain unchanged. This change creates documentation only; no database migration, hosted service, photo upload or commercial release.
