"""Greek/EU audited conversion scoring for SocialMarket AI.

This module is deliberately deterministic and cheap. It does not call paid LLMs.
It converts the owner's strategy into machine-readable audit signals that can be
stored in product payload/evidence and used by ranking/creative selection.

Core strategy:
- Greece or EU logistics only.
- No customs/import surprise.
- Prefer middle-ticket pain-commerce products.
- AliExpress/Geekbuying only for EU warehouse + scarcity in Greece.
- Rank by expected revenue per post, not raw commission alone.
"""
from __future__ import annotations

import math
import re
from typing import Any, Mapping

from product_agents import clamp

EU_COUNTRY_HINTS = {
    "greece", "ελλαδα", "ellada", "gr", "greek", "hellas",
    "germany", "de", "poland", "pl", "spain", "es", "france", "fr",
    "italy", "it", "czech", "cz", "netherlands", "nl", "belgium", "be",
    "austria", "at", "bulgaria", "bg", "romania", "ro", "cyprus", "cy",
    "portugal", "pt", "sweden", "se", "denmark", "dk", "finland", "fi",
    "ireland", "ie", "slovakia", "sk", "slovenia", "si", "hungary", "hu",
    "croatia", "hr", "estonia", "ee", "latvia", "lv", "lithuania", "lt",
    "luxembourg", "lu", "malta", "mt",
}

CHINA_IMPORT_HINTS = {
    "china", "cn", "shenzhen", "guangzhou", "hong kong", "hk", "asia warehouse",
    "import duties", "customs", "τελων", "φόροι ενδέχεται", "taxes may apply",
}

GREEK_MERCHANT_HINTS = {
    ".gr", "skroutz", "bestprice", "public", "plaisio", "kotsovolos",
    "e-shop", "you.gr", "praktiker", "leroy", "media markt", "cosmossport",
}

EU_DISCOVERY_MERCHANT_HINTS = {"aliexpress", "geekbuying", "banggood", "temu"}

CORE_PAIN_PATTERNS = {
    "student_home": r"(φοιτητ|student|dorm|small space|γραφειο|desk|chair|καρεκλ|ραφι|organizer|air fryer|lamp|φωτισ)",
    "back_to_school": r"(school|σχολ|back.?to.?school|παιδ|τσάντα|γραφική|playmobil|laptop)",
    "home_office": r"(office|γραφειο|ergonomic|εργονομ|chair|καρεκλ|laptop stand|mouse|keyboard|φωτιστικ)",
    "security": r"(cctv|camera|κάμερα|security|ασφαλ|sensor|nvr|ip66|alarm|συναγερ)",
    "pet_cleaning": r"(pet|dog|cat|σκυλ|γατ|τριχ|hair remover|vacuum|σκούπα|roller)",
    "home_organization": r"(organizer|storage|οργάνω|κουτι|ραφι|ντουλαπ|καλαθ|shelf)",
    "energy_saving": r"(led|smart plug|energy|solar|ηλιακ|θερμοστ|inverter|power station)",
    "car_daily": r"(car|auto|αυτοκιν|dashcam|inverter|bluetooth|organizer|ανεμοθραυσ|gps)",
    "travel_light": r"(cabin|luggage|samsonite|travel|ταξιδ|βαλίτ|organizer|adapter|power bank)",
    "small_business": r"(barcode|pos|label|business|shop|μαγαζ|επαγγελματικ|πινακίδα|sign)",
}

LUXURY_FASHION_PATTERN = re.compile(
    r"(elisa|franchi|tory burch|aigner|luxury|premium|τσάντα|handbag|bag|φόρεμα|dress|μπουφάν|jacket)",
    re.I,
)
OCCASION_PATTERN = re.compile(r"(γάμ|βαφτισ|gift|δώρο|office|γραφείο|travel|ταξιδ|black friday|έκπτωση|sale)", re.I)


def _num(v: Any, default: float = 0.0) -> float:
    try:
        return float(default if v in (None, "") else v)
    except Exception:
        return float(default)


def _text(*parts: Any) -> str:
    return " ".join(str(p or "") for p in parts).lower()


def _contains_any(text: str, hints: set[str]) -> bool:
    return any(h in text for h in hints)


def source_profile(product: Mapping[str, Any], merchant: Mapping[str, Any]) -> dict[str, Any]:
    text = _text(
        product.get("merchant_name"), product.get("program_name"), product.get("target_domain"),
        product.get("tracking_url"), product.get("target_url"), product.get("category_raw"),
        product.get("availability"), product.get("description"), merchant.get("canonical_name"),
        merchant.get("official_domain"), product.get("warehouse"), product.get("shipping_origin"),
        product.get("ship_from"), product.get("delivery"), product.get("extra_json"),
    )
    is_greek = _contains_any(text, GREEK_MERCHANT_HINTS)
    is_eu_hint = _contains_any(text, EU_COUNTRY_HINTS) or is_greek
    is_discovery = _contains_any(text, EU_DISCOVERY_MERCHANT_HINTS)
    china_or_customs = _contains_any(text, CHINA_IMPORT_HINTS)
    return {
        "is_greek_merchant_hint": is_greek,
        "is_eu_logistics_hint": is_eu_hint,
        "is_aliexpress_geekbuying_like": is_discovery,
        "customs_or_china_hint": china_or_customs,
        "source_text_sample": text[:500],
    }


def shipping_score(product: Mapping[str, Any], cfg: Mapping[str, Any]) -> tuple[float, list[str]]:
    reasons: list[str] = []
    price = _num(product.get("price") or product.get("effective_price"))
    raw_ship = product.get("shipping_cost") or product.get("shipping_eur") or product.get("delivery_cost")
    shipping_known = raw_ship not in (None, "")
    shipping = _num(raw_ship, 0.0)

    # Feed often lacks shipping. For Greek merchant feeds we do not hard fail here;
    # we score uncertainty and let social thresholds decide.
    if not shipping_known:
        reasons.append("shipping_cost_unknown")
        return 55.0, reasons

    if price <= 30:
        threshold = _num(cfg.get("max_shipping_under_30"), 4.99)
    elif price <= 80:
        threshold = _num(cfg.get("max_shipping_30_80"), 6.99)
    elif price <= 200:
        threshold = _num(cfg.get("max_shipping_80_200"), 9.99)
    else:
        threshold = _num(cfg.get("max_shipping_200_plus"), 14.99)
    if shipping > threshold:
        reasons.append("shipping_above_threshold")
        return max(0.0, 65.0 - (shipping - threshold) * 6), reasons
    if shipping <= 0:
        return 100.0, ["free_shipping"]
    return clamp(92.0 - max(0.0, shipping - threshold * 0.5) * 3), reasons


def logistics_score(product: Mapping[str, Any], merchant: Mapping[str, Any], cfg: Mapping[str, Any]) -> dict[str, Any]:
    profile = source_profile(product, merchant)
    reasons: list[str] = []

    eu_gr = profile["is_eu_logistics_hint"] or profile["is_greek_merchant_hint"]
    customs_safe = not profile["customs_or_china_hint"]
    ship_score, ship_reasons = shipping_score(product, cfg)
    reasons.extend(ship_reasons)

    if profile["customs_or_china_hint"]:
        reasons.append("customs_or_non_eu_hint")
    if not eu_gr:
        reasons.append("eu_gr_logistics_not_proven")

    base = 0.0
    base += 35.0 if eu_gr else 0.0
    base += 30.0 if customs_safe else 0.0
    base += ship_score * 0.20
    base += 10.0 if product.get("in_stock") is not False else 0.0
    base += 5.0 if product.get("tracking_url") else 0.0
    status = "LOGISTICS_OK" if base >= 80 and customs_safe and eu_gr else "LOGISTICS_UNKNOWN" if base >= 55 and customs_safe else "LOGISTICS_REJECTED"
    return {
        "score": round(clamp(base), 3),
        "status": status,
        "reasons": reasons,
        **profile,
    }


def pain_cluster_match(product: Mapping[str, Any]) -> dict[str, Any]:
    text = _text(product.get("product_name"), product.get("category_raw"), product.get("description"), product.get("brand"))
    matched = []
    for cluster, pattern in CORE_PAIN_PATTERNS.items():
        if re.search(pattern, text, re.I):
            matched.append(cluster)
    score = min(100.0, 25.0 + len(matched) * 18.0) if matched else 20.0
    if LUXURY_FASHION_PATTERN.search(text) and not OCCASION_PATTERN.search(text):
        score = min(score, 35.0)
    return {"score": round(clamp(score), 3), "clusters": matched, "luxury_without_occasion": bool(LUXURY_FASHION_PATTERN.search(text) and not OCCASION_PATTERN.search(text))}


def scarcity_in_greece(product: Mapping[str, Any], merchant: Mapping[str, Any], logistics: Mapping[str, Any]) -> dict[str, Any]:
    text = _text(product.get("product_name"), product.get("category_raw"), product.get("description"), merchant.get("canonical_name"), merchant.get("official_domain"))
    is_discovery = bool(logistics.get("is_aliexpress_geekbuying_like"))
    niche_terms = re.search(r"(smart|wifi|bluetooth|portable|mini|wireless|adapter|inverter|power station|dashcam|gps|special|kit|robot)", text, re.I)
    generic_terms = re.search(r"(τσάντα|bag|shoes|παπούτσι|φόρεμα|jacket|μπουφάν)", text, re.I)
    score = 50.0
    if is_discovery:
        score += 20.0
    if niche_terms:
        score += 20.0
    if generic_terms and not niche_terms:
        score -= 25.0
    return {"score": round(clamp(score), 3), "status": "scarce_or_differentiated" if score >= 60 else "generic_or_easy_to_find"}


def demand_forecast(product: Mapping[str, Any], merchant: Mapping[str, Any], pain: Mapping[str, Any], scarcity: Mapping[str, Any]) -> dict[str, Any]:
    audience = 72.0 if pain.get("clusters") else 45.0
    seasonality = 70.0 if any(c in set(pain.get("clusters") or []) for c in ("student_home", "back_to_school", "home_office")) else 55.0
    merchant_demand = _num(merchant.get("demand_score"), 50.0)
    price = _num(product.get("price") or product.get("effective_price"))
    price_acceptance = 85.0 if 25 <= price <= 250 else 65.0 if price <= 600 else 45.0
    social_curiosity = 75.0 if pain.get("clusters") else 45.0
    score = (
        _num(pain.get("score")) * 0.25
        + audience * 0.15
        + seasonality * 0.15
        + merchant_demand * 0.15
        + _num(scarcity.get("score")) * 0.15
        + social_curiosity * 0.10
        + price_acceptance * 0.05
    )
    label = "DEMAND_HIGH" if score >= 80 else "DEMAND_MEDIUM" if score >= 60 else "DEMAND_LOW"
    return {"score": round(clamp(score), 3), "label": label}


def conversion_forecast(product: Mapping[str, Any], merchant: Mapping[str, Any], logistics: Mapping[str, Any], pain: Mapping[str, Any], demand: Mapping[str, Any]) -> dict[str, Any]:
    commission = _num(product.get("expected_commission_eur"))
    commercial = min(100.0, 35.0 + max(0.0, commission - 15.0) * 1.5)
    trust = _num(merchant.get("trust_score"), 50.0)
    logistics_trust = _num(logistics.get("score"))
    pain_fit = _num(pain.get("score"))
    demand_score = _num(demand.get("score"))
    score = (
        demand_score * 0.25
        + pain_fit * 0.20
        + commercial * 0.20
        + trust * 0.15
        + logistics_trust * 0.15
        + (75.0 if pain.get("clusters") else 35.0) * 0.05
    )
    return {"score": round(clamp(score), 3), "estimated_click_probability_band": "high" if score >= 80 else "medium" if score >= 65 else "low"}


def final_decision(product: Mapping[str, Any], logistics: Mapping[str, Any], pain: Mapping[str, Any], scarcity: Mapping[str, Any], demand: Mapping[str, Any], conversion: Mapping[str, Any]) -> dict[str, Any]:
    commission = _num(product.get("expected_commission_eur"))
    reasons: list[str] = []
    if logistics.get("status") == "LOGISTICS_REJECTED":
        return {"decision": "REJECT", "reasons": ["logistics_rejected", *logistics.get("reasons", [])]}
    if logistics.get("is_aliexpress_geekbuying_like") and _num(scarcity.get("score")) < 60:
        return {"decision": "WATCHLIST_VERIFY", "reasons": ["discovery_source_but_low_scarcity_in_greece"]}
    if pain.get("luxury_without_occasion"):
        return {"decision": "SITE_DEAL", "reasons": ["luxury_or_fashion_without_clear_occasion"]}
    if commission >= 80 and _num(demand.get("score")) >= 65 and _num(logistics.get("score")) >= 80:
        return {"decision": "HIGH_TICKET_TEST", "reasons": ["high_ticket_with_acceptable_demand"]}
    if commission >= 25 and _num(demand.get("score")) >= 75 and _num(conversion.get("score")) >= 75 and _num(logistics.get("score")) >= 80:
        return {"decision": "PRIORITY_SOCIAL", "reasons": ["priority_middle_ticket_conversion_candidate"]}
    if commission >= 15 and _num(demand.get("score")) >= 65 and _num(conversion.get("score")) >= 68 and _num(logistics.get("score")) >= 75 and pain.get("clusters"):
        return {"decision": "SOCIAL_READY", "reasons": ["audited_social_candidate"]}
    if commission >= 10 and logistics.get("status") != "LOGISTICS_REJECTED":
        return {"decision": "SITE_DEAL", "reasons": ["site_only_not_social_ready"]}
    return {"decision": "REJECT", "reasons": ["below_commission_or_conversion_threshold"]}


def audit_candidate(product: Mapping[str, Any], merchant: Mapping[str, Any], cfg: Mapping[str, Any] | None = None) -> dict[str, Any]:
    cfg = cfg or {}
    logistics = logistics_score(product, merchant, cfg)
    pain = pain_cluster_match(product)
    scarcity = scarcity_in_greece(product, merchant, logistics)
    demand = demand_forecast(product, merchant, pain, scarcity)
    conversion = conversion_forecast(product, merchant, logistics, pain, demand)
    decision = final_decision(product, logistics, pain, scarcity, demand, conversion)
    commission = _num(product.get("expected_commission_eur"))
    expected_revenue_score = clamp(_num(conversion.get("score")) * 0.55 + min(100.0, commission * 2.0) * 0.45)
    final_score = clamp(
        _num(demand.get("score")) * 0.20
        + _num(pain.get("score")) * 0.20
        + _num(conversion.get("score")) * 0.20
        + expected_revenue_score * 0.15
        + _num(logistics.get("score")) * 0.10
        + _num(merchant.get("trust_score"), 50.0) * 0.10
        + _num(scarcity.get("score")) * 0.05
    )
    return {
        "strategy": "GREEK_EU_AUDITED_AI_CONVERSION_ENGINE",
        "logistics": logistics,
        "pain": pain,
        "scarcity_in_greece": scarcity,
        "demand_forecast": demand,
        "conversion_forecast": conversion,
        "expected_revenue_per_post_score": round(expected_revenue_score, 3),
        "final_ai_conversion_score": round(final_score, 3),
        **decision,
    }


def adjusted_preliminary_score(base_score: float, audit: Mapping[str, Any]) -> float:
    decision = str(audit.get("decision") or "")
    logistics = audit.get("logistics") or {}
    penalty = 0.0
    boost = 0.0
    if decision == "REJECT":
        penalty += 500.0
    elif decision == "WATCHLIST_VERIFY":
        penalty += 90.0
    elif decision == "SITE_DEAL":
        penalty += 25.0
    elif decision in ("SOCIAL_READY", "PRIORITY_SOCIAL"):
        boost += 25.0
    elif decision == "HIGH_TICKET_TEST":
        boost += 10.0
    if logistics.get("status") == "LOGISTICS_UNKNOWN":
        penalty += 30.0
    if logistics.get("status") == "LOGISTICS_REJECTED":
        penalty += 250.0
    return round(float(base_score) + boost - penalty, 3)


def public_audit_summary(audit: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "strategy": audit.get("strategy"),
        "decision": audit.get("decision"),
        "reasons": audit.get("reasons") or [],
        "logistics_status": (audit.get("logistics") or {}).get("status"),
        "logistics_score": (audit.get("logistics") or {}).get("score"),
        "demand_label": (audit.get("demand_forecast") or {}).get("label"),
        "demand_score": (audit.get("demand_forecast") or {}).get("score"),
        "pain_clusters": (audit.get("pain") or {}).get("clusters") or [],
        "pain_score": (audit.get("pain") or {}).get("score"),
        "scarcity_score": (audit.get("scarcity_in_greece") or {}).get("score"),
        "conversion_score": (audit.get("conversion_forecast") or {}).get("score"),
        "final_ai_conversion_score": audit.get("final_ai_conversion_score"),
    }
