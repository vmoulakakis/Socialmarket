# Skill: Merchant → Product Intelligence Bridge

## Purpose
Attach every feed offer to the existing canonical merchant intelligence. Product ingestion must never create a second merchant universe.

## Inputs
- feed `program_name`
- canonical merchant programs
- merchant aliases
- merchant trust
- merchant Solution Whitespace score
- Demand Beacon score
- promotion policy

## Resolution order
1. Exact normalized program name.
2. Existing canonical alias.
3. Conservative unique near-exact containment match.
4. Otherwise `merchant_unresolved`; do not auto-import.

## Product consequences
A resolved product offer inherits merchant context:
- merchant_id
- merchant_program_id
- trust_score
- solution_whitespace_score
- demand_beacon_score
- merchant/category demand evidence
- competition evidence
- audit confidence

## Dominant merchant rule
`demand_beacon_only` merchants remain fully available as RAG/evidence sources, but their product offers are excluded from the promotable Product Opportunity catalog.

## Invariant
Never modify or recompute the existing merchant research pipeline merely to accommodate products. Product Intelligence is an additive consumer of merchant truth.
