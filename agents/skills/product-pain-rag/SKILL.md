# Skill: Product Pain-Gap RAG

## Purpose
Determine whether a commission-eligible product is a real, evidence-backed pain-gap solver using only semantically clean, validated evidence.

## Retrieval corpus
Use the generic evidence layer only when the cluster is currently trusted:
- `validation_status=validated`
- canonical product category/subcategory or explicit category-level pain
- validated pain / unmet need / alternative request
- complaints only when they describe a solvable product need
- sufficient source/entity relevance and audit evidence

Never retrieve `stale`, rejected or taxonomy-contaminated clusters.

## Semantic retrieval rules
1. Resolve the product to canonical category/subcategory before pain retrieval.
2. Prefer same-subcategory pains; allow same-category cross-subcategory retrieval only when semantic similarity and desired outcome support it.
3. Brand, campaign/theme, navigation, geography and service-policy labels are not product taxonomy and cannot create a pain-match shortcut.
4. Use product title, factual description, brand, model, canonical taxonomy and merchant context as retrieval text.
5. Keyword overlap is only a retrieval prior, never validation.
6. AI may select only RAG cluster IDs actually supplied.
7. Unsupported product features are forbidden.
8. If no supplied cluster is a credible functional fit, return no pain match and let the Product Skeptic reject/review it.

## Evidence quality preference
Prefer clusters with:
- source diversity
- stronger entity/category relevance
- demand evidence
- pain severity/commercial intent
- recent collection timestamp
- high audit confidence

## Outputs
accepted pain_cluster_ids, pain_gap_fit_score 0–100, rationale, desired outcome/user intent when supported, evidence confidence, taxonomy_coherence, contradictions[].

## Principle
A high commission is not a pain gap. A popular merchant is not a pain gap. A shared keyword is not a pain gap. The product must plausibly solve a validated user problem.
