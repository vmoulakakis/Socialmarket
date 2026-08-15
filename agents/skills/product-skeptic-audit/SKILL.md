# Skill: Product Skeptic / Audit

## Purpose
Actively try to disprove Product Research Agent conclusions before a product becomes a validated pain-gap solver.

## Audit gates
- product identity is coherent
- merchant/program resolution is canonical
- effective price and commission gate were deterministic and preserved
- no dominant merchant offer slipped through
- canonical title/category/subcategory are supported
- proposed features are present in source product facts
- accepted pain IDs are from supplied validated RAG only
- accepted theme IDs are from supplied active theme RAG only
- pain match is causal/functional, not keyword coincidence
- demand and competition claims are supported by retrieved evidence
- description is human-readable but does not add unsupported claims

## Verdicts
- `validated`: genuinely evidence-backed solver
- `needs_review`: plausible but evidence/identity/taxonomy remains ambiguous
- `rejected`: no credible pain solution, unsupported claims, mismatch, or contradiction

## Required scoring dimensions
identity, source quality, source diversity, contradiction, taxonomy, demand validation, competition validation, pain validation, social validation, overall confidence.

## Critical invariant
The Audit Agent cannot override hard deterministic exclusions to promote a product. It can only be stricter.
