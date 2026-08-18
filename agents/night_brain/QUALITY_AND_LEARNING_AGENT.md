# Quality + Learning Agent

## Purpose
Improve the affiliate strategy every day from observed outcomes without allowing self-modifying code or unconstrained weight drift.

## Evidence order
1. First-party observed performance: impressions, outbound clicks, approved conversions, approved commission, spend/cost.
2. Network/program commercial evidence: conversion rate, EPC, approval rate, approval delay and data confidence.
3. Demand/supply and merchant intelligence.
4. Optional Deep Demand / seasonal / pain context.
5. AI interpretation.

Observed evidence outranks modeled evidence.

## Daily learning
The Night Brain automatically re-evaluates candidates with the latest 30-day first-party window. Better CTR/CVR/EPC/approved commission raises the conversion signal; poor real performance removes theoretical advantage over time.

New products use merchant/category/program priors until enough product-level evidence exists. They are not penalized simply because they are new.

## Bounded adaptation
The runtime may adapt portfolio composition within configured bounds, but may not:
- lower the EUR10 commission gate
- bypass merchant/price/stock/tracking/image safety
- send the bulk feed to a model
- modify repository code or MD policy files automatically
- turn missing data into positive evidence

## Quality rule
`fresh != good`.

A new product must have credible value, demand-gap, quality and/or pain-solving evidence. A proven winner is not removed merely to satisfy a renewal percentage.

## Failure learning
Every run records stage, candidate counts, segment composition, model/cache usage and creative degradation. Downstream creative/publishing failures are operational learning signals and do not invalidate the ranking.
