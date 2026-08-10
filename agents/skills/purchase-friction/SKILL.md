---
name: purchase-friction
description: Estimate whether a high-ticket product can be bought confidently online without physical inspection.
---
# Purchase Friction

## Mission
Estimate the amount of fit, touch, installation, visual inspection or expert reassurance needed before purchase.

## Core rule
Default maximum friction is 0.40. A verified discount >=30% may relax it to 0.60; >=40% may relax it to 0.75. These thresholds remain configurable and must be validated with outcomes later.

## Consider
fit/size risk, material/touch need, installation complexity, compatibility uncertainty, return burden, trust requirement and visual-decision dependence.

## Output
JSON: friction_score_0_1, drivers[], discount_exception, allowed_threshold, decision, confidence.
