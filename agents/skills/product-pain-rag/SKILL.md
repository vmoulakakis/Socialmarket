# Skill: Product Pain-Gap RAG

## Purpose
Determine whether a commission-eligible product is a real, evidence-backed pain-gap solver.

## Retrieval corpus
Use the existing generic evidence layer only:
- validated pain clusters
- unmet needs
- alternative requests
- complaints when they describe a solvable product need
- merchant/category evidence
- social/review evidence summarized into validated clusters

## Retrieval rules
1. Prefer validated clusters with source diversity, demand evidence and pain severity.
2. Use product title, description, brand, model and category as retrieval text.
3. Product/service complaints must not be confused with unmet product needs.
4. Keyword overlap is only a retrieval prior, never validation.
5. AI may select only RAG cluster IDs actually supplied to it.
6. Unsupported product features are forbidden.
7. If no supplied cluster is a credible fit, return no pain match and let the Product Audit Agent reject or review the product.

## Outputs
- accepted pain_cluster_ids
- pain_gap_fit_score 0–100
- rationale
- desired outcome / user intent when supported
- evidence confidence

## Principle
A high commission is not a pain gap. A popular merchant is not a pain gap. The product must plausibly solve a validated user problem.
