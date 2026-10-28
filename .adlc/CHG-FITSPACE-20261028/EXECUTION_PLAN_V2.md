# FitSpace AI — Execution and release gates V2
Date: 2026-10-28 | Status: PLAN ONLY | Change ID CHG-FITSPACE-20261028.

## Phase P0 — Reliable interactive geometry WITHOUT AI inference dependency
- New isolated FitSpace package/repo; preserve SocialMarket main, CarCare PR #96 and all live sites.
- Implement mobile-first PWA scaffold with camera/upload/manual fallback and opt-in image handling; manifest and install icon.
- Build 2D parametric editor for rectangles, L-shapes and niches: anchored scale, draggable walls, opening positions, numeric centimeter editing, constraint validation, undo/redo, save/load revision.
- Implement immutable geometry schema + solver + category clearances, then render same revision in 2D and React Three Fiber 3D.
- Create two embed demos (HomeFit and FitMatch) with separate test tenants, without modifying their live code.
- P0 test acceptance: dimension correction 260→240cm changes geometry/area/clearances/verdict consistently; impossible locked anchors trigger conflict; stale inference messages cannot overwrite latest edits; phone camera denied still works with manual mode.
- UI/UX review via Product Design Work mode with 3 visual directions before code; apply project DESIGN.md and UX-CONTRACT.md using frontend-design-premium; browser QA mobile and desktop.

## Phase P1 — Real multi-view AI
- Curate licensed, consented photographs and tape/laser ground truth on 30–50 diverse spaces; include poor light, occlusions, blank walls, mirrors and complex shapes.
- Benchmark exact licensed weights MapAnything Apache vs DA3-BASE and manually anchored baseline; optional MoGe3 as single-view fallback; Florence2 for object labels and SAM2 for corrections. Pin all revisions, record hardware requirements and inference euros/job.
- Adaptive photo coach: pose overlap/coverage map, reshoot guidance; fallback to manual anchors if tracking fails.
- Private async GPU job; normalize point clouds/depth to walls/doors/windows; calibrate and produce editable parametric proposal, never immutable uneditable meshes.
- Per-mode P50/P95 absolute error, false fits, user corrections and privacy tests; calibrate uncertainty intervals. Published claims must be based on independent held-out evaluation.

## Phase P2 — Native enhancement / progressive install
- Native Swift iOS RoomPlan LiDAR bridge; Android Kotlin ARCore Depth adapter with runtime feature checks. Neither available for all phones or generic mobile browsers.
- Normalize both into the exact same scene schema; native is enhanced capture, not a second recommendation or data system.
- Installable PWA remains default and includes photo-based guided capture and manual edit.

## Phase P3 — Real commerce and full ecosystem
- Verified manufacturer product dimensions and clearance envelopes, offer feed + merchant approval, totals incl delivery where available, affiliate disclosure and safe tracking.
- Integrate HomeFit/other relevant sites with isolated SDK and shared price intelligence; use separate per-site tenant scopes, access controls and CORS allowlist.
- Compare 3 eligible products, style/fit/price and alternatives; never present partial merchant catalog as universal best price.
- Optional photo export/space account and price-drop alert with clear consent. Publish commercial affiliate offers only after review of agreements, valid tracking, uptime and commercial hosting policy.

## Governance and design/tool order
- Read Myagenticteam universal-creation-orchestrator, canonical agentic-development-lifecycle, agent-runtime-2026, web-design-intelligence, ui-craft-quality and ai-ui-production-toolchain; do not install every discovered skill.
- Product Design plugin: in chat the connected skill router is Work-only for actual visual ideation/prototypes; use Work mode for three image directions/browser QA.
- frontend-design + frontend-design-premium: product taste, DESIGN.md, UX-CONTRACT.md, i18n Greek, accessible interaction states, no fake precision, on-device mobile UX.
- GitHub & Hugging Face tools: check exact checkpoint licenses and weights and runtime support; do not claim models installed by model card lookup.
- Independent verification for security/privacy and model performance; artifact trail intent → spec → plan → code/tests → review → authorized deployment → production signals. No merging or production deployment based on the docs-only PR.

## Cost reality
Current Vercel Hobby serves noncommercial preview only; cannot be treated as allowed revenue-generating hosting. Supabase already has two active projects and photo storage quota is limited. Paid or separately hosted GPU time for MapAnything-class 1.2B models is an operational dependency; P0 deterministic manual/editor can run without GPU. Establish a budget after running benchmark jobs; no fake free forever promise.

## Measurable success gates
- P0: all dimension edit and undo fixtures pass, zero stale revision overwrites, no false definitive fit when evidence missing, completed critical path in mobile web, accessibility and privacy review.
- P1: ground-truth errors reported by device and capture mode; credible abstention on unsupported scenes and tested safe clearances; consent/retention verified and compute cost measured.
- P2/P3: same scene works across Web/iOS/Android; host isolation test; approved feed to verified product match to safe clickout and real analytics; lawful commercial hosting.

Existing docs: intent.md, spec.md, plan.md. These remain historical design stages; this file and UX_ARCHITECTURE_V2.md plus MODEL_EVALUATION_2026.md supersede model choice and step ordering. Research/licensing conclusions are not executable model tests.
