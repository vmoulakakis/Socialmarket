# CHG-FITSPACE-20261028 — Product & Technical Specification (v0.1)

Status: ARCHITECTURE / REVIEW REQUIRED. This document does not imply that any reconstruction AI is operational.

## Core proposition
**FitSpace AI: capture → measure → correct → recalculate → visualize → compare → visit merchant.**
The same engine handles rooms, fixtures, furniture, appliances, fitness equipment and other spatially constrained goods, with separate category fit-rule plugins.

## UX: guided capture protocol (mobile web default)
1. Visitor opens a session via host site's FitSpace widget, without downloading an app. Offer camera, photo-upload, floor-plan and manual-entry entry points.
2. Ask room type and intended purchase; show an example of suitable framing and a privacy notice.
3. Instruct a sequence of overlapping viewpoints that include both corners of each wall, floor-wall and ceiling-wall boundaries, doors/windows, and relevant obstructions. Start with an overview from a doorway or room corner, then adjacent and opposite viewpoints. **Do not fix an arbitrary photo count:** the coverage agent requests additional views only as necessary. Guidance adapts to occlusions, glare, blur and lack of parallax.
4. Coverage UI shows known/unknown surfaces and specific reshoot requests: e.g. «Στρέψε λίγο δεξιά ώστε να φαίνεται η γωνία πίσω από το γραφείο» or «Η πόρτα κρύβεται· φωτογράφισε από την απέναντι γωνία». Allow retake and upload, do not upload unnecessary video by default.
5. Obtain one or more trustworthy *metric scale anchors*: measure a wall span with tape, identify a known object with correct orientation and manually confirmed size, or use an eligible native AR/LiDAR reading. Do not assume a door is universally 80 cm or an A4 is upright without checking.
6. Vision estimates object masks, walls, vanishing points, camera relationships, planar boundaries and 3D geometry. Quality score is calibrated against validation data: show a **measurement uncertainty interval** for each important dimension, not an invented global accuracy percentage.
7. User reviews a **2D plan and 3D editable scene**. Critical dimensions are tagged ESTIMATED, ANCHORED, or CONFIRMED, with origin (photo #n, calibrated measurement, manual).
8. Tapping any wall, edge, window/door span, opening position, clearance or movable object opens in-place measurement editing; keyboard and touch supported; cm/m units, validation ranges, visual handles and undo/redo.
9. Upon edit, solve geometric constraints and dependent calculations, rerender plans and image overlays, run category fit rules and regenerate up to three eligible product choices. Show a visible «Ενημερώθηκαν 6 διαστάσεις / 2 προτάσεις» change summary; explain conflicts before applying adjustments.
10. Output: saved room plan, confidence/provenance, 3D scene, shortlist, fitted dimensions, product caveats, full delivered price where available, affiliate disclosure, merchant click-through only when verified.

## Geometry, scale and source-of-truth model
- Define immutable photo captures and image metadata; derived 3D observations separate from confirmed user anchors.
- Use a constraint graph of vertices, wall segments, planes, openings, obstacles, scale anchors and placed products in world coordinates (metres internally, centimetres in UI).
- Each constraint has source, timestamp, confidence/calibrated uncertainty, status (inferred/anchored/confirmed), tolerance and provenance IDs.
- Multi-view reconstruction strategy: device camera metadata + pose/overlap estimation when supported, segmentation/line detection, planar geometry, depth priors, robust multi-view fitting; fallback to guided 2D polygon with explicitly entered scale if reconstruction unreliable.
- Monocular RGB **without a known distance/scale is ambiguous**; prohibit absolute fit claims in that state.
- For manual corrections, lock the explicit edited constraint, adjust only compatible unconfirmed geometry using a weighted constrained optimization; re-check polygon closure and physical bounds. Never silently override confirmed references.
- Conflicts (e.g. locked adjacent wall lengths cannot close polygon) produce a conflict dialog showing the competing dimensions and choices: edit anchor, unlock inferred geometry, or manual floor-plan mode.
- Derived outputs (perimeter, area, openings, unused space, clearance, product placement, top-3 product fit and price ranks) are invalidated and recomputed by a versioned deterministic dependency DAG. AI proposes interpretations, not physically inconsistent authoritative measurements.
- Each recalculation writes model_revision_id, based_on_revision, changed_constraints, fit rule version and data provenance. Prevent stale asynchronous AI results from overwriting a newer manual edit.

## Fit engine requirements
- Product dimensions include width/depth/height, clearance envelope and orientation options; require verified vendor dimensions or user-verified values.
- Fit check: geometric intersection, door swing/opening, circulation envelope and operational access; thresholds depend on category and local requirements; do not reuse a generic one-size-fits-all safety gap.
- Verdict: FITS_VERIFIED, FITS_ESTIMATED, NEEDS_CONFIRMATION, DOES_NOT_FIT. Any critical unresolved dimension forces NEEDS_CONFIRMATION.
- Rankings: user fit/constraints and total price (incl shipping where available) before affiliate payout; no fake cheapest-in-Greece claim. Include verified merchant non-affiliate offer where possible.
- Changing a wall from 260 to 240 cm must recompute layout, clearance and eligibility, and invalidate old fit evidence. A price/stock update can change offer ranking without changing geometry.

## Suggested reusable technical boundaries
- Web SDK: `@fitspace/embed` (script/React widget) with session and tenant ID.
- APIs: `POST /sessions`, `POST /sessions/:id/captures`, `POST /sessions/:id/scale-anchors`, `PATCH /sessions/:id/constraints/:constraintId`, `POST /sessions/:id/recalculate`, `GET /sessions/:id/geometry`, `GET /sessions/:id/fit?catalog=...`.
- Runtime schema: tenants, spatial_sessions, captures, calibration_anchors, observations, constraints, geometry_revisions, placed_objects, fit_evaluations, vendor_product_geometry, merchant_offer_evidence.
- Frontend: Next.js PWA, mobile capture flow, 2D plan editor and React Three Fiber 3D viewer; asynchronous job queue for inference with progress and cancellation. Native bridge optional: Apple RoomPlan where supported, Android ARCore Depth if supported.
- Never expose API/service secrets or raw customer photos to a merchant or affiliate network. Supabase private buckets, signed short-lived URL access, tenant-scoped RLS, retention/deletion controls and documented photo consent.
- Awin/Linkwise and alternative networks remain behind a separate Product Intelligence service; FitSpace owns geometry/fit, not advertiser joining or payment processing.

## Example acceptance scenarios
A. Room wall estimated 260 cm; user changes to tape-measured 240 cm. Revision increments; connected wall endpoints, area, furniture clearance, all applicable placements and offers recompute, and UI shows exactly what changed.
B. One photo, no scale anchor: can show qualitative arrangement; **cannot claim measured 3D fit or actual centimetres**.
C. Conflicting user-confirmed lengths: show conflict, preserve both anchors pending resolution and prevent definitive FITS_VERIFIED.
D. Product dimensions missing: warn and withhold definitive fit badge despite a visually plausible 3D placeholder.
E. Across two separate sites, the same SDK works with separate tenant settings; capture data and affiliate credentials do not cross tenants.
F. User corrects room while inference is running: outdated result does not replace current revision; editor supports undo.
G. Camera denied or unsupported AR: photo upload and manually measured floor plan remain fully usable.
H. Merchant has no valid approved tracking link / stale price: no clickable product CTA is shown as verified.

## Evidence / accuracy programme
- Collect user-consented *test* rooms measured with tape/laser reference, including irregular walls, doors, reflective surfaces and occlusions, across supported device models.
- Evaluate median and 95th percentile absolute dimension error **by mode** (calibrated multi-view, manually anchored plan, native depth), scale-error, reconstruction coverage, collision false-negatives and user correction burden. Set explicit user-visible tolerances only after empirical evaluation.
- Do not present theoretical model confidence as verified empirical accuracy.
