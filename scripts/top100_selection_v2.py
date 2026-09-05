#!/usr/bin/env python3
"""Deterministic Top-100 Greece opportunity optimizer.

Consumes a JSON array (or object with `products`) and emits a ranked active set.
The script is intentionally provider-agnostic so it can be used by GitHub Actions,
Supabase jobs, or local validation. It enforces the commercial invariants required
by SocialMarket AI before records are allowed into the active Top-100.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

ACTIVE_LIMIT = 100
MAX_CATEGORIES = 5
COMMISSION_FLOOR_EUR = 20.0
PUBLISHED_STATES = {"published", "retired"}


def num(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "verified", "rare", "scarce"}


def get(item: dict[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if name in item and item[name] is not None:
            return item[name]
    return default


def commission_eur(item: dict[str, Any]) -> float:
    direct = num(get(item, "commission_eur", "expected_commission_eur", "commission_value_eur"))
    if direct > 0:
        return direct
    price = num(get(item, "price_eur", "price", "sale_price_eur"))
    rate = num(get(item, "commission_rate", "commission_pct"))
    if rate > 1:
        rate /= 100.0
    return price * rate if price > 0 and rate > 0 else 0.0


def greece_scarcity(item: dict[str, Any]) -> float:
    score = num(get(item, "greece_scarcity", "scarcity_score", "gr_scarcity"), -1)
    if score >= 0:
        return max(0.0, min(1.0, score if score <= 1 else score / 100.0))
    unavailable = truthy(get(item, "not_available_greece", "greece_unavailable", default=False))
    rare = truthy(get(item, "rare_in_greece", "greece_rare", default=False))
    return 1.0 if unavailable else 0.8 if rare else 0.0


def norm(item: dict[str, Any], *names: str) -> float:
    value = num(get(item, *names), 0)
    if value > 1:
        value /= 100.0
    return max(0.0, min(1.0, value))


def lifecycle_state(item: dict[str, Any]) -> str:
    return str(get(item, "lifecycle_state", "state", "status", default="candidate")).strip().lower()


def provider_confirmed_published(item: dict[str, Any]) -> bool:
    if lifecycle_state(item) in PUBLISHED_STATES:
        return True
    if truthy(get(item, "provider_confirmed_published", "published_confirmed", default=False)):
        return True
    provider_ids = get(item, "provider_post_ids", default=[])
    published_at = get(item, "published_at")
    return bool(published_at and provider_ids)


def eligible(item: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if provider_confirmed_published(item):
        reasons.append("already_published")
    commission = commission_eur(item)
    if commission <= COMMISSION_FLOOR_EUR:
        reasons.append("commission_below_floor")
    scarcity = greece_scarcity(item)
    if scarcity < 0.6:
        reasons.append("weak_greece_scarcity")
    if truthy(get(item, "blocked", default=False)) or lifecycle_state(item) == "blocked":
        reasons.append("blocked")
    if truthy(get(item, "regulatory_block", default=False)):
        reasons.append("regulatory_block")
    if get(item, "affiliate_link_valid") is False:
        reasons.append("invalid_affiliate_link")
    return (len(reasons) == 0, reasons)


def score(item: dict[str, Any]) -> float:
    commission = commission_eur(item)
    commission_score = min(1.0, math.log1p(max(0.0, commission - COMMISSION_FLOOR_EUR)) / math.log1p(180.0))
    demand = norm(item, "demand_now", "demand_score", "demand")
    momentum7 = norm(item, "demand_momentum_7d", "momentum_7d")
    momentum30 = norm(item, "demand_momentum_30d", "momentum_30d")
    forecast = norm(item, "forecast_demand", "forecast_score", "demand_forecast")
    scarcity = greece_scarcity(item)
    conversion = norm(item, "conversion_ease", "conversion_score", "sellability_score")
    organic = norm(item, "organic_potential", "viral_score", "social_score")
    ads = norm(item, "ads_viability", "ad_score", "paid_score")
    pain = norm(item, "pain_severity", "pain_score")
    landed = norm(item, "landed_cost_attractiveness", "price_advantage_score")
    freshness = norm(item, "evidence_freshness", "freshness_score")
    scheduler = norm(item, "scheduler_feedback", "historical_feedback_score")
    competition = norm(item, "competitive_intensity", "competition_score")
    risk = norm(item, "seller_logistics_risk", "risk_score")
    duplicate_penalty = norm(item, "duplicate_similarity", "near_duplicate_score")

    weighted = (
        0.13 * demand
        + 0.05 * momentum7
        + 0.06 * momentum30
        + 0.13 * forecast
        + 0.12 * scarcity
        + 0.12 * commission_score
        + 0.10 * conversion
        + 0.07 * organic
        + 0.05 * ads
        + 0.07 * pain
        + 0.04 * landed
        + 0.03 * freshness
        + 0.03 * scheduler
    )
    penalty = 0.04 * competition + 0.06 * risk + 0.08 * duplicate_penalty
    return round(max(0.0, min(1.0, weighted - penalty)), 6)


def category(item: dict[str, Any]) -> str:
    raw = get(item, "category", "product_category", "family", "vertical", default="uncategorized")
    return str(raw).strip() or "uncategorized"


def product_key(item: dict[str, Any]) -> str:
    raw = get(item, "product_id", "id", "sku", "slug", "source_hash", "url", default="")
    return str(raw).strip()


def optimize(items: list[dict[str, Any]]) -> dict[str, Any]:
    rejected: list[dict[str, Any]] = []
    candidates_by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for item in items:
        ok, reasons = eligible(item)
        if not ok:
            rejected.append({"id": product_key(item), "reasons": reasons})
            continue
        enriched = dict(item)
        enriched["commission_eur"] = round(commission_eur(item), 2)
        enriched["greece_scarcity"] = round(greece_scarcity(item), 4)
        enriched["selection_score"] = score(item)
        enriched["lifecycle_state"] = "eligible"
        candidates_by_category[category(item)].append(enriched)

    for rows in candidates_by_category.values():
        rows.sort(key=lambda row: (row["selection_score"], row["commission_eur"]), reverse=True)

    category_scores: list[tuple[str, float, int]] = []
    for cat, rows in candidates_by_category.items():
        top = rows[: min(20, len(rows))]
        if not top:
            continue
        mean = sum(r["selection_score"] for r in top) / len(top)
        depth_bonus = min(0.08, len(rows) / 1000.0)
        category_scores.append((cat, mean + depth_bonus, len(rows)))

    category_scores.sort(key=lambda x: (x[1], x[2]), reverse=True)
    selected_categories = [cat for cat, _, _ in category_scores[:MAX_CATEGORIES]]

    selected: list[dict[str, Any]] = []
    if selected_categories:
        base_quota = ACTIVE_LIMIT // len(selected_categories)
        extra = ACTIVE_LIMIT % len(selected_categories)
        leftovers: list[dict[str, Any]] = []
        for idx, cat in enumerate(selected_categories):
            quota = base_quota + (1 if idx < extra else 0)
            rows = candidates_by_category[cat]
            take = rows[:quota]
            selected.extend(take)
            leftovers.extend(rows[quota:])
        if len(selected) < ACTIVE_LIMIT:
            leftovers.sort(key=lambda row: (row["selection_score"], row["commission_eur"]), reverse=True)
            selected.extend(leftovers[: ACTIVE_LIMIT - len(selected)])

    selected = selected[:ACTIVE_LIMIT]
    selected.sort(key=lambda row: (row["selection_score"], row["commission_eur"]), reverse=True)
    for rank, row in enumerate(selected, start=1):
        row["rank"] = rank
        row["lifecycle_state"] = "selected_top100"
        row["selection_reasons"] = [
            "commission_gt_20_eur",
            "greece_scarcity_verified_or_high",
            "top_category_allocation",
            "composite_demand_forecast_score",
        ]

    return {
        "version": "top100-v2",
        "market": "GR",
        "active_limit": ACTIVE_LIMIT,
        "max_categories": MAX_CATEGORIES,
        "selected_categories": selected_categories,
        "selected_count": len(selected),
        "selected": selected,
        "rejected_count": len(rejected),
        "rejected": rejected,
    }


def load(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for key in ("products", "candidates", "items", "opportunities"):
            value = data.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
    raise SystemExit("Input must be a JSON array or object containing products/candidates/items/opportunities")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = optimize(load(Path(args.input)))
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("version", "selected_count", "selected_categories", "rejected_count")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
