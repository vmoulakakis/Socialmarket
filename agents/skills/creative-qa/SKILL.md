---
name: creative-qa
description: Audit affiliate creatives for product fidelity, factual consistency, QR correctness, legibility and platform readiness.
---
# Creative QA

## Gates
- product image is the real selected product and remains recognizable
- displayed price/discount matches evidence
- QR payload exactly equals the selected tracking URL when QR is used
- headline and CTA are legible on a mobile-sized preview
- no unsupported superlatives, guarantees, scarcity or review claims
- safe margins and platform aspect ratio are correct
- TikTok creative defaults to no QR/baked tracking URL
- affiliate disclosure is available in accompanying copy

## Verdict
Return `pass`, `revise` or `block` plus structured issues and suggested remediation. A blocked asset must never move automatically to publishing.
