---
name: category-discovery
description: Build a commercially useful category tree from messy product-feed labels.
---
# Category Discovery

## Mission
Create stable categories that are meaningful for Greek demand analysis, competition research and campaign planning.

## Rules
- Normalize synonyms before creating new nodes.
- Do not create a category only because the feed used a different label.
- Category boundaries should reflect materially different buyer intent or market behavior.
- Return examples and confidence for each proposed category.

## Output
JSON: canonical_category, aliases[], rationale, representative_products[], confidence.
