---
name: subcategory-discovery
description: Split canonical product categories only when semantic buyer intent, demand, competition or economics materially differ.
---
# Subcategory Discovery

## Mission
Find commercially meaningful product subcategories and intent clusters without taxonomy inflation or UI-label contamination.

## Rules
- A raw anchor/menu label is evidence, never a taxonomy value by itself.
- First classify each candidate label by semantic role. Only `product_taxonomy` is eligible.
- Reject navigation, login/account, location, language, shipping/payment/returns, campaign/theme, promotion, brand and collection labels as subcategories.
- A brand may be a filter/brand dimension, never a subcategory merely because it appears in navigation.
- A seasonal theme such as `Back To School` belongs to Demand Themes, not taxonomy.
- Split only when buyer intent, purchase friction, typical price band, seasonality, conversion economics or competition differs materially.
- Prefer approved canonical labels and map aliases/synonyms into them.
- Require product-bearing evidence from feed/product titles, structured category pages or repeated semantic terms.
- If only the parent category is supported, return `subcategory=null`; never invent precision.
- Reject micro-groups that lack sufficient products or market evidence.

## Validation examples
- `Sign Up` → navigation → reject.
- `Αθήνα` → location → reject.
- `TOMMY HILFIGER` → brand_or_collection → reject as subcategory.
- `Back To School` → theme → reject as subcategory, route to seasonal demand layer.
- `Αντηλιακά` → Beauty & Personal Care / Sun Care.
- `Μπλούζες με στάμπα` → Fashion & Accessories / Apparel.
- `Πίνακες σε καμβά` → Home & Garden / Home Decor.

## Output
JSON: parent_category, canonical_subcategory|null, semantic_role, aliases[], rejected_labels[], intent_cluster, split_reason, sample_products[], evidence[], confidence.
