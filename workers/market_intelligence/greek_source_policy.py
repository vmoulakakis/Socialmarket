from __future__ import annotations

"""Canonical roles for large Greek commerce sites used as market signals.

These domains are demand beacons, not competitors. Their public catalogue/search
presence may support a *derived* demand-coverage index. It is never sales volume,
market share, or consumer pain. Only extracted first-person review text can enter
the separate pain-evidence path.
"""

from collections import Counter
from urllib.parse import urlparse


GREEK_DEMAND_BEACONS = {
    "skroutz.gr": {"kind": "marketplace", "authority_weight": 0.90},
    "bestprice.gr": {"kind": "price_comparison", "authority_weight": 0.86},
    "shopflix.gr": {"kind": "marketplace", "authority_weight": 0.76},
    "temu.com": {"kind": "marketplace", "authority_weight": 0.72},
    "trendyol.com": {"kind": "marketplace", "authority_weight": 0.70},
    "aliexpress.com": {"kind": "marketplace", "authority_weight": 0.72},
    "lagonika.gr": {"kind": "deal_community", "authority_weight": 0.72},
    "vrisko.gr": {"kind": "commerce_directory", "authority_weight": 0.66},
    "public.gr": {"kind": "major_retailer", "authority_weight": 0.78},
    "plaisio.gr": {"kind": "major_retailer", "authority_weight": 0.78},
    "kotsovolos.gr": {"kind": "major_retailer", "authority_weight": 0.78},
    "e-shop.gr": {"kind": "major_retailer", "authority_weight": 0.76},
    "germanos.gr": {"kind": "major_retailer", "authority_weight": 0.74},
    "cosmote.gr": {"kind": "major_retailer", "authority_weight": 0.74},
    "e-jumbo.gr": {"kind": "major_retailer", "authority_weight": 0.74},
    "ikea.gr": {"kind": "major_retailer", "authority_weight": 0.74},
    "jysk.gr": {"kind": "major_retailer", "authority_weight": 0.72},
    "intersport.gr": {"kind": "major_retailer", "authority_weight": 0.72},
    "cosmossport.gr": {"kind": "major_retailer", "authority_weight": 0.72},
    "notino.gr": {"kind": "major_retailer", "authority_weight": 0.72},
    "sephora.gr": {"kind": "major_retailer", "authority_weight": 0.72},
    "e-food.gr": {"kind": "marketplace", "authority_weight": 0.70},
}


def normalize_domain(value: str) -> str:
    raw = str(value or "").strip().lower()
    if "://" in raw:
        raw = urlparse(raw).hostname or ""
    raw = raw.split("/")[0].split(":")[0].removeprefix("www.")
    return raw


def beacon_policy(value: str) -> dict | None:
    domain = normalize_domain(value)
    for canonical, policy in GREEK_DEMAND_BEACONS.items():
        if domain == canonical or domain.endswith("." + canonical):
            return {
                "canonical_domain": canonical,
                "source_role": "demand_beacon",
                "competitor_eligible": False,
                "pain_eligible_from_catalogue": False,
                **policy,
            }
    return None


def is_demand_beacon(value: str) -> bool:
    return beacon_policy(value) is not None


def annotate_evidence(row: dict) -> dict:
    out = dict(row)
    metadata = dict(out.get("metadata") or {})
    policy = beacon_policy(out.get("source_url") or metadata.get("source_domain") or "")
    if policy:
        metadata.update(policy)
        metadata["role_semantics"] = (
            "Large Greek commerce site observed as a demand signal; never classified as a competitor."
        )
        if out.get("source_kind") == "pain_candidate":
            metadata["pain_eligible"] = bool(
                metadata.get("consumer_text")
                and metadata.get("source_family") in {"marketplace_review", "consumer_review"}
            )
    out["metadata"] = metadata
    return out


def cap_beacon_concentration(rows: list[dict], *, per_domain: int = 4) -> list[dict]:
    """Prevent one dominant site from manufacturing apparent demand by repetition."""
    counts: Counter[str] = Counter()
    out: list[dict] = []
    for original in rows:
        row = annotate_evidence(original)
        policy = beacon_policy(row.get("source_url") or "")
        if policy:
            domain = policy["canonical_domain"]
            if counts[domain] >= per_domain:
                continue
            counts[domain] += 1
        out.append(row)
    return out
