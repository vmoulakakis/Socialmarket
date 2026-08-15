# Skill: Seasonal / Thematic Demand

## Purpose
Attach products to current and forecast demand themes without replacing the base pain-gap score.

## Examples
- Back to School
- Christmas
- Black Friday
- Summer / travel period
- Spring cleaning
- University start
- Home heating
- Mother's Day / Father's Day

## Theme object
Each theme has:
- active_from
- peak_date
- active_to
- semantic brief
- optional parent theme
- evidence-backed demand/confidence

## Matching
1. Retrieve relevant active themes from RAG.
2. Product must match the semantic problem/use-case of the theme, not merely contain a seasonal keyword.
3. Compute a time curve: rising toward peak, decaying after peak.
4. AI returns only supplied theme IDs.
5. Seasonal relevance is a ranking modifier, not permission to bypass pain, trust, commission or competition gates.

## Back to School 2026 subthemes
- ergonomics
- study organization
- concentration
- student technology
- meal/lunch
- transport
- university
- teachers

## Output
- theme_ids
- thematic relevance
- current seasonal score
- evidence-grounded rationale
