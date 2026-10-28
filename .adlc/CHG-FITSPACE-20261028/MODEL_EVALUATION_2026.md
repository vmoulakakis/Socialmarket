# FitSpace AI — Verified GitHub/Hugging Face model shortlist
Date: 2026-10-28 | Change: CHG-FITSPACE-20261028 | Stage: RESEARCH ONLY
Purpose: choose models for real multi-angle mobile photographs to produce an editable parametric room model with known/uncertain dimensions. No model has yet been deployed or benchmarked on real FitSpace rooms.

## Recommended primary stack
1. Meta MapAnything, commercial-friendly Apache checkpoint (https://github.com/facebookresearch/map-anything and https://huggingface.co/facebook/map-anything-apache). Multi-view 3D reconstruction using images and optional camera pose/metric data. ~1.23B parameters; GPU inference service likely required. Code Apache2; **only** the suffix -apache checkpoint is Apache2. The default facebook/map-anything checkpoint is CC-BY-NC 4.0 and NOT allowed in our commercial site.
2. ByteDance Depth Anything 3 BASE (https://github.com/ByteDance-Seed/Depth-Anything-3 and https://huggingface.co/depth-anything/DA3-BASE). Multi-view depth/pose baseline ~135M parameters and Apache2 model. DA3-LARGE is CC-BY-NC 4.0 and cannot be substituted.
3. Microsoft Florence-2-base (https://huggingface.co/microsoft/Florence-2-base) semantic object/door/window proposals, MIT model license; cannot measure metric real sizes independently.
4. Meta SAM2 Hiera Large (https://huggingface.co/facebook/sam2-hiera-large) user-correctable segmentation/masks; Apache2 weights. Only include if it adds measurable UX value over editable polygons.
5. Optional Microsoft MoGe3 ViTL (https://github.com/microsoft/MoGe and https://huggingface.co/Ruicheng/moge-3-vitl) single-frame geometry fallback; model MIT per HF, code MIT with Apache2 DINOv2 modules. Metric predictions still require scale verification.

## Research/conditional only
- Meta VGGT: https://github.com/facebookresearch/vggt . Commercial use requires specific gated model https://huggingface.co/facebook/VGGT-1B-Commercial under AUP; original VGGT-1B NOT commercial.
- Meta VGGT-Omega 2026: https://github.com/facebookresearch/vggt-omega . Gated research checkpoint; non-commercial constraints on official HF demo. Exclude from commercial MVP until legal clearance.
- Meta SAM3/3.1: https://github.com/facebookresearch/sam3 . Gated special SAM license, high GPU requirements; do not assume Apache2.
- RoomFormer: https://github.com/ywyue/RoomFormer . Converts top-down density maps from point clouds to polygonal floor plans; NOT a raw smartphone RGB estimator. Candidate only after point-cloud preprocessing and license check.

## Architectural rule
Depth/pose/point clouds are noisy **observations**, not purchase-safe dimensions. They must be fused with tape/laser-measured anchors, supported native hardware signals, calibrated scale and constraint-based geometry. The authoritative product scene is a revisioned parametric structure: floor, walls, openings, obstacles, placed product envelopes and confidence/provenance for every dimension. An impressive photorealistic point cloud is not sufficient to claim verified fit.

## Native versus web
Apple RoomPlan on compatible LiDAR iOS devices (https://developer.apple.com/documentation/roomplan) and Google ARCore Depth on supported Android devices (https://developers.google.com/ar/develop/depth) are optional native adapters. Mobile Safari/PWA cannot be assumed to expose RoomPlan or ARCore depth capabilities. MDN PWA install guidance: https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Making_PWAs_installable ; MDN WebXR limited support: https://developer.mozilla.org/en-US/docs/Web/API/WebXR_Device_API .

## Bench protocol before any accuracy marketing claim
30–50 consented representative real Greek apartments/rooms; independent tape/laser ground truth. Include alcoves, L-shaped rooms, white walls, reflective surfaces, furniture occlusions, glass, windows and door swing. Compare MapAnything Apache vs DA3 BASE vs manual anchor-based baseline on identical input sets. Report dimension p50/p95 error by device/mode, confidence calibration, dangerous false-positive FITS rate, GPU costs, runtime, user reshoots and corrections. No centimeter guarantee from one uncalibrated image. Set release safety gates from actual measured evidence.

## Hugging Face connector verification
Authenticated HF account via hf_whoami. hf model_search/paper_search endpoints returned backend tool-not-found, but hf hub_repo_details worked and confirmed exact model licenses/metadata. Repo exists/model card does not imply model installation, commercial license acceptance or inference execution. Store checkpoint digest and license before deployment.

## Infrastructure
Free Vercel Hobby is a noncommercial UI preview only, not GPU inference host or live affiliate marketplace. Dedicated budgeted GPU worker required for production AI, with privacy-safe queues, idempotency, retention controls and fail-closed manual mode. No user interior images in public third-party model demos.
