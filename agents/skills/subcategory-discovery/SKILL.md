---
name: subcategory-discovery
description: Split categories only when buyer intent, demand or competition materially differs.
---
# Subcategory Discovery

## Mission
Find commercially meaningful subcategories and intent clusters without taxonomy inflation.

## Rules
- Split only when search intent, purchase friction, price band, seasonality or competition differs materially.
- Prefer stable canonical labels.
- Reject micro-groups that lack enough products or market evidence.

## Output
JSON: parent_category, subcategory, intent_cluster, split_reason, sample_products[], confidence.
