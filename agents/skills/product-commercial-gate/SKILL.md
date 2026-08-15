# Skill: Product Commercial Gate

## Purpose
Reject economically weak offers before any expensive AI reasoning. This skill never estimates consumer demand from affiliate commission.

## Inputs
- effective/sale price
- full/list price
- raw percentage commission rule from the canonical merchant program
- raw flat commission rule from the canonical merchant program
- currency
- merchant promotion policy

## Rules
1. Recompute discount from effective price versus full price when both are valid.
2. Percentage commission is treated as the sale commission when present; a simultaneous flat amount is not added automatically because it may represent another conversion action.
3. Exact percentage: `expected_commission = effective_price * pct / 100`.
4. Percentage range: use the **minimum rate** for automatic eligibility. Preserve the maximum only as potential upside.
5. Flat exact: expected commission is the flat amount.
6. Flat range: use the minimum amount for automatic eligibility.
7. Currency must be EUR unless a separately validated FX conversion layer is available.
8. Hard eligibility gate: **expected commission >= EUR 10**.
9. Never reintroduce a minimum product-price rule. A EUR 40 product at 30% commission is eligible; a EUR 300 product at 2% is not.
10. Dominant/demand-beacon-only merchant offers are excluded from promotion even when commission passes.

## Output
- expected_commission_eur
- potential_commission_eur
- commission_rule
- commission_confidence
- commercial_gate_pass
- rejection_reason

## Safety
Do not infer a commission tier that is absent from the affiliate program evidence. Ambiguity reduces confidence; it never increases expected earnings.
