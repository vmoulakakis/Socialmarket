---
name: category-discovery
description: Resolve messy merchant/product labels into a closed, commercially meaningful semantic product taxonomy.
---
# Category Discovery

## Mission
Create stable product categories for Greek demand, competition, affiliate conversion and campaign planning without allowing page-navigation noise, brands or seasonal campaigns to become taxonomy.

## Non-negotiable semantic roles
Before treating any label as taxonomy, classify it as one of:
- `product_taxonomy`
- `brand_or_collection`
- `theme`
- `promotion`
- `navigation`
- `service_policy`
- `location`
- `language`
- `noise`
- `unknown`

Only `product_taxonomy` may become a category/subcategory.

## Hard rejects as taxonomy
Never create categories from labels such as:
- Sign Up / Login / Register / My Account / Cart / Checkout
- Skip to content / Skip to main content / Μετάβαση στο περιεχόμενο / Παράλειψη
- city or country names such as Αθήνα
- language switches such as English / Ελληνικά
- brand names such as TOMMY HILFIGER
- campaign/season labels such as Back To School, Black Friday, Summer Sale
- shipping, payment, returns, privacy, cookies, terms or other service/policy navigation

These may remain useful evidence for another layer (brand, theme, geography, promotion, service quality), but they are not product taxonomy.

## Canonical category policy
Prefer the approved SocialMarket product taxonomy and map synonyms into it. Do not create a new root category because a merchant used a different wording.

A category must be supported by product-bearing evidence such as:
- repeated product/category terms in merchant content
- actual product-feed titles/descriptions
- structured data or category URLs
- multiple product-bearing navigation labels
- validated merchant/category evidence

## Confidence policy
- High confidence: repeated product evidence + canonical mapping.
- Medium confidence: clear category but insufficient subcategory evidence.
- Low confidence: ambiguous merchant/site. Return `Other`/unresolved rather than inventing a category.

## Output
JSON: canonical_category, semantic_role, aliases[], rejected_labels[{label,role,reason}], rationale, representative_products[], evidence[], confidence.
