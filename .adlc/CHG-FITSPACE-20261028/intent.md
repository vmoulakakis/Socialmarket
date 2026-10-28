# CHG-FITSPACE-20261028 — Intent

Status: SPECIFICATION ONLY (not implemented, tested or deployed). Date: 2026-10-28.

## User request
FitSpace AI is a shared spatial-measurement and product-fit service used across HomeFit, FitMatch, SocialMarket and any other appropriate site. Avoid mandatory app installation: mobile web capture first, optional native scan for supported iOS/Android. The system itself chooses and guides the visitor through the additional photographic viewpoints needed to estimate a room as reliably as feasible.

Every measurement shown on a 2D plan or 3D scene must be editable. A correction triggers consistent recalculation of the entire room, remaining derived dimensions, object positions, fit verdict, visual overlay and product recommendations. Users must be able to undo changes and recognize which measurements were estimated versus physically confirmed.

## Jobs to be done
- Measure a difficult room using guided photos + a scale reference, with no misleading centimetre-precision claims from a single picture.
- Correct an inaccurate detected wall, corner, door, window, obstacle or product measurement and see the downstream effects.
- Test whether products actually fit, including clearance/door swing, then compare up to three verified merchant offers without hiding better verified non-affiliate results.
- Reuse the same spatial service, editor and geometry model across many independent sites.

## Hard limits / preservation
- No fabricated room dimensions, product dimensions, merchant stock, commissions or price guarantees.
- No promise of absolute metric scale from uncalibrated ordinary monocular photographs. Require at least one known anchor / manual measurement / supported hardware depth signal.
- No automatic purchases, third-party uploads or sharing photos between brands. Separate site/customer data by tenant and purpose.
- Preserve current SocialMarket production and the unmerged CarCare pilot. No shared DB schema change, credential access or production rollout without a reviewable plan and approval.

## Success criteria (provisional acceptance targets)
- Guided acquisition can explain which specific view is missing and why; user can skip camera and type dimensions.
- All geometry-critical measures editable in centimetres, with source, uncertainty, audit history, undo.
- A single edited measurement invalidates stale mesh/area/fit/product offers and recomputes them via a consistent constraint graph.
- 2D/3D outputs agree within an explicit published tolerance for calibrated test rooms; conflicting anchors fail visibly, not silently.
- Fit verdict always specifies provenance: verified / estimated / unresolved, with bounded safety clearances.
- SDK mounts in two separate host apps without sharing user photos or affiliate credentials.
