#!/usr/bin/env python3
"""Deterministic scoring for the AliExpress Gap Solver V2.

LLMs may extract bounded claims or propose search queries, but every demand,
gap, product and lane decision in this module is deterministic and auditable.
Unknown values fail closed; they are never silently converted to positive
evidence.
"""
from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import urlsplit


PROVENANCE_WEIGHT = {
    "observed": 1.0,
    "calculated": 0.95,
    "user_provided": 0.85,
    "inferred": 0.72,
    "unavailable": 0.0,
}
TIER_WEIGHT = {
    "structured_metric": 1.0,
    "full_text": 0.95,
    "snippet": 0.35,
    "metadata": 0.20,
}

STOPWORDS = {
    "και", "για", "απο", "από", "στο", "στη", "στην", "στον", "των", "της", "του",
    "με", "σε", "να", "που", "πως", "ένα", "μια", "the", "and", "for", "with", "from",
    "this", "that", "product", "item", "new", "best", "portable", "smart", "mini", "set",
}

B2B_TERMS = {
    "industrial", "oscilloscope", "multimeter", "borescope", "surveillance", "cctv",
    "repair", "diagnostic", "welding", "laboratory", "measurement", "inspection", "cnc",
    "βιομηχαν", "παλμογραφ", "πολυμετρ", "επισκευ", "διαγνωσ", "εργαστηρ", "μετρησ",
    "επιτηρησ", "συνεργει",
}


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, float(value)))


def number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        text = str(value).strip().replace("€", "").replace("%", "").replace(",", ".")
        if not text:
            return None
        out = float(Decimal(text))
        return out if math.isfinite(out) else None
    except (InvalidOperation, ValueError, TypeError):
        return None


def ratio(value: Any) -> float | None:
    out = number(value)
    if out is None:
        return None
    return out / 100.0 if out > 1 else out


def parse_time(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif value:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def normalize_text(value: Any) -> str:
    raw = unicodedata.normalize("NFKD", str(value or "").lower())
    return "".join(ch for ch in raw if not unicodedata.combining(ch))


def tokens(value: Any) -> set[str]:
    return {
        token
        for token in re.findall(r"[\w]+", normalize_text(value), flags=re.UNICODE)
        if len(token) >= 3 and token not in STOPWORDS and not token.isdigit()
    }


def valid_http_url(value: Any, allowed_domains: Sequence[str] | None = None) -> bool:
    try:
        parsed = urlsplit(str(value or "").strip())
    except ValueError:
        return False
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    if not allowed_domains:
        return True
    host = parsed.hostname.lower().rstrip(".")
    return any(host == domain or host.endswith("." + domain) for domain in allowed_domains)


@dataclass(frozen=True)
class GapSolverPolicy:
    policy_key: str = "aliexpress_gap_solver_v2"
    discovery_min_commission_eur: float = 10.0
    organic_min_commission_eur: float = 15.0
    paid_static_min_commission_eur: float = 35.0
    min_demand_score: float = 65.0
    min_paid_demand_score: float = 72.0
    min_gap_score: float = 70.0
    min_strong_gap_score: float = 85.0
    min_problem_fit_score: float = 72.0
    min_paid_problem_fit_score: float = 80.0
    min_organic_trust_score: float = 50.0
    min_trust_score: float = 68.0
    min_evidence_score: float = 65.0
    min_paid_evidence_score: float = 75.0
    min_problem_confidence: float = 0.60
    min_evidence_items: int = 8
    min_source_families: int = 2
    min_competitors_audited: int = 3
    max_contradiction_ratio: float = 0.35
    max_evidence_age_days: int = 120
    max_product_age_hours: int = 168
    paid_cpc_eur: float = 0.35
    paid_click_to_order_rate: float = 0.015
    paid_approval_rate: float = 0.80
    paid_creative_cost_per_approved_order_eur: float = 5.0
    paid_target_margin_rate: float = 0.25
    paid_assumption_provenance: str = "policy_assumption"
    weight_problem_fit: float = 0.25
    weight_gap: float = 0.20
    weight_demand: float = 0.18
    weight_economics: float = 0.12
    weight_trust: float = 0.10
    weight_evidence: float = 0.10
    weight_competition_inverse: float = 0.05

    @classmethod
    def from_mapping(cls, row: Mapping[str, Any] | None) -> "GapSolverPolicy":
        if not row:
            return cls()
        assumptions = row.get("paid_unit_economics_assumptions") or {}
        score_weights = row.get("score_weights") or {}
        fields: dict[str, Any] = {}
        for name in cls.__dataclass_fields__:
            if name in row and row[name] is not None:
                fields[name] = row[name]
        aliases = {
            "paid_cpc_eur": "cpc_eur",
            "paid_click_to_order_rate": "click_to_order_rate",
            "paid_approval_rate": "approval_rate",
            "paid_creative_cost_per_approved_order_eur": "creative_cost_per_approved_order_eur",
            "paid_target_margin_rate": "target_margin_rate",
            "paid_assumption_provenance": "provenance",
        }
        for field, key in aliases.items():
            if assumptions.get(key) is not None:
                fields[field] = assumptions[key]
        weight_aliases = {
            "weight_problem_fit": "problem_fit",
            "weight_gap": "gap",
            "weight_demand": "demand",
            "weight_economics": "economics",
            "weight_trust": "trust",
            "weight_evidence": "evidence",
            "weight_competition_inverse": "competition_inverse",
        }
        for field, key in weight_aliases.items():
            if score_weights.get(key) is not None:
                fields[field] = score_weights[key]
        numeric_ints = {"min_evidence_items", "min_source_families", "min_competitors_audited", "max_evidence_age_days", "max_product_age_hours"}
        for name in list(fields):
            if name in numeric_ints:
                fields[name] = int(fields[name])
            elif name != "policy_key" and name != "paid_assumption_provenance":
                parsed = number(fields[name])
                if parsed is not None:
                    fields[name] = parsed
        return cls(**fields)

    def public_snapshot(self) -> dict[str, Any]:
        return asdict(self)


def _claim_weight(row: Mapping[str, Any]) -> float:
    confidence = number(row.get("confidence"))
    relevance = number(row.get("relevance_score"))
    return (
        max(0.0, min(1.0, confidence if confidence is not None else 0.0))
        * max(0.0, min(1.0, (relevance if relevance is not None else 0.0) / 100.0))
        * TIER_WEIGHT.get(str(row.get("evidence_tier") or ""), 0.0)
        * PROVENANCE_WEIGHT.get(str(row.get("provenance_class") or ""), 0.0)
    )


def _weighted_strength(
    rows: Sequence[Mapping[str, Any]],
    claim_types: set[str],
    *,
    proof_tiers: set[str] | None = None,
) -> tuple[float | None, int]:
    weighted = 0.0
    total_weight = 0.0
    count = 0
    best_per_source: dict[tuple[str, str], tuple[float, float]] = {}
    for row in rows:
        if row.get("claim_type") not in claim_types or row.get("polarity") == "contradicts":
            continue
        if proof_tiers and row.get("evidence_tier") not in proof_tiers:
            continue
        strength = number(row.get("strength_score"))
        weight = _claim_weight(row)
        if strength is None or weight <= 0:
            continue
        key = (str(row.get("source_independence_key") or row.get("source_domain") or row.get("id")), str(row.get("claim_type")))
        current = best_per_source.get(key)
        if current is None or weight > current[1]:
            best_per_source[key] = (clamp(strength), weight)
    for strength, weight in best_per_source.values():
        weighted += strength * weight
        total_weight += weight
        count += 1
    return ((weighted / total_weight) if total_weight else None, count)


def _fresh_evidence(
    evidence: Iterable[Mapping[str, Any]],
    policy: GapSolverPolicy,
    now: datetime,
) -> list[Mapping[str, Any]]:
    cutoff = now - timedelta(days=policy.max_evidence_age_days)
    unique: dict[tuple[str, str], Mapping[str, Any]] = {}
    for row in evidence:
        observed = parse_time(row.get("observed_at"))
        stale_after = parse_time(row.get("stale_after"))
        if observed is None or observed < cutoff or (stale_after and stale_after < now):
            continue
        if number(row.get("strength_score")) is None or _claim_weight(row) <= 0:
            continue
        key = (str(row.get("content_hash") or row.get("id")), str(row.get("claim_type")))
        incumbent = unique.get(key)
        if incumbent is None or _claim_weight(row) > _claim_weight(incumbent):
            unique[key] = row
    return list(unique.values())


def score_problem_evidence(
    evidence: Iterable[Mapping[str, Any]],
    policy: GapSolverPolicy | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Create the deterministic deep-demand and market-gap scorecard."""
    policy = policy or GapSolverPolicy()
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    rows = _fresh_evidence(evidence, policy, now)
    proof_tiers = {"full_text", "structured_metric"}

    families = {str(x.get("source_family")) for x in rows if x.get("source_family")}
    independent = {str(x.get("source_independence_key")) for x in rows if x.get("source_independence_key")}
    competitor_keys: set[str] = set()
    for row in rows:
        if row.get("claim_type") not in {"exact_solution", "substitute", "competitor", "price_friction", "availability_gap"}:
            continue
        if row.get("evidence_tier") not in proof_tiers:
            continue
        facts = row.get("facts") if isinstance(row.get("facts"), Mapping) else {}
        key = facts.get("competitor_key") or facts.get("seller_key") or row.get("source_domain")
        if key:
            competitor_keys.add(str(key).lower())

    contradiction_count = sum(
        1 for x in rows if x.get("polarity") == "contradicts" or x.get("claim_type") == "contradiction"
    )
    contradiction_ratio = contradiction_count / len(rows) if rows else 0.0

    pain, pain_n = _weighted_strength(rows, {"pain"}, proof_tiers=proof_tiers)
    intent, intent_n = _weighted_strength(rows, {"purchase_intent"}, proof_tiers=proof_tiers)
    search, search_n = _weighted_strength(rows, {"search_interest"})
    first_party, first_party_n = _weighted_strength(rows, {"first_party_behavior"}, proof_tiers={"structured_metric"})

    demand_components = [
        (pain, 0.40),
        (intent, 0.35),
        (search, 0.15),
        (first_party, 0.10),
    ]
    available_demand = [(value, weight) for value, weight in demand_components if value is not None]
    demand_base = (
        sum(float(value) * weight for value, weight in available_demand)
        / sum(weight for _, weight in available_demand)
        if available_demand else 0.0
    )
    core_demand_coverage = int(pain is not None) + int(intent is not None) + int(first_party is not None)
    demand_coverage_factor = 0.70 + 0.15 * min(2, core_demand_coverage)
    demand_score = clamp(demand_base * min(1.0, demand_coverage_factor))

    exact, exact_n = _weighted_strength(rows, {"exact_solution"})
    substitute, substitute_n = _weighted_strength(rows, {"substitute"})
    competition, competition_n = _weighted_strength(rows, {"competitor"})
    availability_gap, availability_n = _weighted_strength(rows, {"availability_gap"})
    price_friction, price_n = _weighted_strength(rows, {"price_friction"})
    direct_gap, direct_gap_n = _weighted_strength(rows, {"market_gap"})

    positive_gap_values = [x for x in (availability_gap, price_friction, direct_gap) if x is not None]
    positive_gap = sum(positive_gap_values) / len(positive_gap_values) if positive_gap_values else None
    gap_components = [
        (positive_gap, 0.45),
        ((100.0 - exact) if exact is not None else None, 0.30),
        ((100.0 - substitute) if substitute is not None else None, 0.10),
        ((100.0 - competition) if competition is not None else None, 0.15),
    ]
    available_gap = [(value, weight) for value, weight in gap_components if value is not None]
    gap_base = (
        sum(float(value) * weight for value, weight in available_gap)
        / sum(weight for _, weight in available_gap)
        if available_gap else 0.0
    )
    source_counts = Counter(str(x.get("source_independence_key") or "") for x in rows)
    concentration = (max(source_counts.values()) / len(rows)) if rows and source_counts else 1.0
    concentration_penalty = max(0.0, concentration - 0.40) * 25.0
    contradiction_penalty = contradiction_ratio * 35.0
    gap_score = clamp(gap_base - concentration_penalty - contradiction_penalty)

    competition_values = [x for x in (exact, substitute, competition) if x is not None]
    competition_score = clamp(sum(competition_values) / len(competition_values)) if competition_values else 0.0
    average_confidence = (
        sum((number(x.get("confidence")) or 0.0) * TIER_WEIGHT.get(str(x.get("evidence_tier")), 0.0) for x in rows)
        / sum(TIER_WEIGHT.get(str(x.get("evidence_tier")), 0.0) for x in rows)
        if rows else 0.0
    )
    evidence_score = clamp(100.0 * (
        0.35 * min(1.0, len(rows) / policy.min_evidence_items)
        + 0.25 * min(1.0, len(families) / policy.min_source_families)
        + 0.25 * min(1.0, len(competitor_keys) / policy.min_competitors_audited)
        + 0.15 * max(0.0, min(1.0, average_confidence))
    ))
    confidence = clamp(
        average_confidence
        * min(1.0, len(rows) / policy.min_evidence_items)
        * min(1.0, len(families) / policy.min_source_families),
        0.0,
        1.0,
    )

    gates = {
        "evidence_items": len(rows) >= policy.min_evidence_items,
        "source_family_diversity": len(families) >= policy.min_source_families,
        "competitors_audited": len(competitor_keys) >= policy.min_competitors_audited,
        "full_text_pain_proof": pain_n >= 1,
        "full_text_buyer_or_first_party_proof": (intent_n + first_party_n) >= 1,
        "positive_gap_evidence": bool(positive_gap_values),
        "demand_threshold": demand_score >= policy.min_demand_score,
        "gap_threshold": gap_score >= policy.min_gap_score,
        "contradiction_limit": contradiction_ratio <= policy.max_contradiction_ratio,
        "confidence_floor": confidence >= policy.min_problem_confidence,
        "evidence_quality_threshold": evidence_score >= policy.min_evidence_score,
    }
    eligible = all(gates.values())
    strong_gap = bool(
        eligible
        and gap_score >= policy.min_strong_gap_score
        and len(rows) >= max(8, policy.min_evidence_items)
        and len(competitor_keys) >= max(3, policy.min_competitors_audited)
    )
    reason_codes = [name for name, passed in gates.items() if not passed]
    return {
        "demand_score": round(demand_score, 3),
        "pain_score": round(pain or 0.0, 3),
        "buyer_intent_score": round(intent or first_party or 0.0, 3),
        "competition_score": round(competition_score, 3),
        "gap_score": round(gap_score, 3),
        "evidence_count": len(rows),
        "source_family_count": len(families),
        "independent_source_count": len(independent),
        "competitors_audited": len(competitor_keys),
        "contradiction_ratio": round(contradiction_ratio, 4),
        "confidence": round(confidence, 4),
        "evidence_score": round(evidence_score, 3),
        "evidence_ids": [str(x.get("id")) for x in rows if x.get("id")],
        "gate_results": gates,
        "eligible_to_source": eligible,
        "strong_gap": strong_gap,
        "reason_codes": reason_codes,
        "score_provenance": {
            "class": "calculated",
            "method": "gap_solver_scoring_v2",
            "inputs": ["observed evidence", "inferred claim labels"],
            "missing_values": "fail_closed",
        },
        "diagnostics": {
            "claim_counts": {
                "pain": pain_n,
                "purchase_intent": intent_n,
                "search_interest": search_n,
                "first_party_behavior": first_party_n,
                "exact_solution": exact_n,
                "substitute": substitute_n,
                "competitor": competition_n,
                "availability_gap": availability_n,
                "price_friction": price_n,
                "market_gap": direct_gap_n,
            },
            "source_concentration": round(concentration, 4),
            "contradiction_penalty": round(contradiction_penalty, 3),
            "concentration_penalty": round(concentration_penalty, 3),
        },
    }


def paid_required_commission(
    policy: GapSolverPolicy,
    overrides: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    values = {
        "cpc_eur": policy.paid_cpc_eur,
        "click_to_order_rate": policy.paid_click_to_order_rate,
        "approval_rate": policy.paid_approval_rate,
        "creative_cost_per_approved_order_eur": policy.paid_creative_cost_per_approved_order_eur,
        "target_margin_rate": policy.paid_target_margin_rate,
        "provenance": policy.paid_assumption_provenance,
    }
    if overrides:
        for key in values:
            if overrides.get(key) is not None:
                values[key] = overrides[key]
    cpc = number(values["cpc_eur"])
    conversion = ratio(values["click_to_order_rate"])
    approval = ratio(values["approval_rate"])
    creative = number(values["creative_cost_per_approved_order_eur"])
    margin = ratio(values["target_margin_rate"])
    valid = (
        cpc is not None and cpc >= 0
        and conversion is not None and 0 < conversion <= 1
        and approval is not None and 0 < approval <= 1
        and creative is not None and creative >= 0
        and margin is not None and 0 <= margin < 1
    )
    if not valid:
        return {
            **values,
            "valid": False,
            "required_commission_eur": None,
            "reason": "invalid_or_missing_paid_unit_economics",
        }
    paid_cost_per_approved_order = cpc / conversion / approval
    modeled = (paid_cost_per_approved_order + creative) / (1.0 - margin)
    required = max(policy.paid_static_min_commission_eur, modeled)
    return {
        **values,
        "valid": True,
        "paid_cost_per_approved_order_eur": round(paid_cost_per_approved_order, 2),
        "required_commission_eur": round(required, 2),
        "static_floor_eur": policy.paid_static_min_commission_eur,
        "formula": "max(static_floor,(cpc/cvr/approval+creative_cost)/(1-target_margin))",
    }


def _flatten_product_facts(row: Mapping[str, Any]) -> str:
    values: list[str] = []
    allowed = {
        "product_title", "title", "canonical_title", "category", "category_name",
        "second_level_category_name", "attributes", "attribute", "properties",
        "product_properties", "specifications", "description", "feature", "features",
        "source_payload",
    }

    def visit(value: Any, key: str = "", depth: int = 0) -> None:
        if depth > 4 or sum(len(x) for x in values) > 20000:
            return
        if isinstance(value, Mapping):
            for child_key, child in value.items():
                normalized_key = str(child_key).lower()
                if normalized_key in allowed or key in allowed:
                    visit(child, normalized_key, depth + 1)
        elif isinstance(value, (list, tuple)):
            for child in value[:80]:
                visit(child, key, depth + 1)
        elif key in allowed and value not in (None, ""):
            values.append(str(value))

    for key in ("title", "canonical_title", "category"):
        if row.get(key):
            values.append(str(row[key]))
    visit(row.get("product_raw_payload") or {}, depth=0)
    visit(row.get("offer_raw_payload") or {}, depth=0)
    return " | ".join(values)


def requirement_matches(
    requirements: Sequence[Mapping[str, Any]] | Sequence[str],
    source_text: str,
    fallback_problem_text: str = "",
) -> tuple[list[dict[str, Any]], float, float]:
    normalized: list[dict[str, Any]] = []
    for idx, requirement in enumerate(requirements or []):
        if isinstance(requirement, Mapping):
            text = str(requirement.get("text") or requirement.get("requirement") or "").strip()
            rid = str(requirement.get("id") or f"r{idx + 1}")
            weight = number(requirement.get("weight")) or 1.0
            required = bool(requirement.get("required", True))
        else:
            text = str(requirement).strip()
            rid, weight, required = f"r{idx + 1}", 1.0, True
        if text:
            normalized.append({"id": rid, "text": text, "weight": max(0.01, weight), "required": required})
    if not normalized and fallback_problem_text.strip():
        normalized = [{"id": "problem", "text": fallback_problem_text, "weight": 1.0, "required": True}]
    fact_tokens = tokens(source_text)
    normalized_source = normalize_text(source_text)
    matches: list[dict[str, Any]] = []
    weighted_score = 0.0
    total_weight = 0.0
    verified_weight = 0.0
    for req in normalized:
        req_tokens = tokens(req["text"])
        overlap = sorted(req_tokens & fact_tokens)
        coverage = len(overlap) / len(req_tokens) if req_tokens else 0.0
        phrase = normalize_text(req["text"]).strip()
        phrase_match = bool(len(phrase) >= 6 and phrase in normalized_source)
        support = clamp(coverage * 100.0 + (15.0 if phrase_match else 0.0))
        verified = bool(overlap and support >= 50.0)
        weight = float(req["weight"])
        weighted_score += support * weight
        total_weight += weight
        if verified:
            verified_weight += weight
        matches.append({
            **req,
            "support_score": round(support, 3),
            "verified": verified,
            "matched_tokens": overlap[:20],
            "provenance_class": "calculated",
            "source": "aliexpress_product_facts",
        })
    coverage_ratio = verified_weight / total_weight if total_weight else 0.0
    base = weighted_score / total_weight if total_weight else 0.0
    score = clamp(base * (0.70 + 0.30 * coverage_ratio))
    return matches, round(score, 3), round(coverage_ratio, 4)


def _raw_lookup(row: Mapping[str, Any], *keys: str) -> Any:
    sources = [
        row,
        row.get("offer_raw_payload") if isinstance(row.get("offer_raw_payload"), Mapping) else {},
        row.get("product_raw_payload") if isinstance(row.get("product_raw_payload"), Mapping) else {},
    ]
    for source in sources:
        for key in keys:
            if source.get(key) not in (None, ""):
                return source.get(key)
        nested = source.get("source_payload") if isinstance(source.get("source_payload"), Mapping) else {}
        for key in keys:
            if nested.get(key) not in (None, ""):
                return nested.get(key)
    return None


def trust_score(row: Mapping[str, Any]) -> tuple[float, dict[str, Any]]:
    seller = row.get("seller_evidence") if isinstance(row.get("seller_evidence"), Mapping) else {}
    reviews = row.get("review_evidence") if isinstance(row.get("review_evidence"), Mapping) else {}
    rating = number(seller.get("evaluate_rate"))
    rating_kind = "positive_feedback_percent"
    if rating is None:
        rating = number(_raw_lookup(row, "evaluate_rate", "positive_feedback_rate"))
    if rating is not None and rating <= 1:
        rating *= 100
    if rating is None:
        star_rating = number(_raw_lookup(row, "rating"))
        if star_rating is not None and 0 <= star_rating <= 5:
            rating = star_rating / 5.0 * 100.0
            rating_kind = "five_star_rating"
    volume = number(_raw_lookup(row, "lastest_volume", "latest_volume", "sold_count", "sales"))
    review_count = number(reviews.get("review_count")) or number(_raw_lookup(row, "review_count"))

    parts: list[tuple[float, float]] = []
    if rating is not None:
        parts.append((clamp((rating - 80.0) * 5.0), 0.65))
    if volume is not None and volume >= 0:
        parts.append((clamp(math.log10(volume + 1.0) / 4.0 * 100.0), 0.25))
    if review_count is not None and review_count >= 0:
        parts.append((clamp(math.log10(review_count + 1.0) / 4.0 * 100.0), 0.10))
    if not parts:
        return 0.0, {
            "provenance_class": "unavailable",
            "rating": None,
            "rating_kind": None,
            "sold_count": None,
            "review_count": None,
        }
    total_weight = sum(weight for _, weight in parts)
    score = sum(value * weight for value, weight in parts) / total_weight
    if rating is None:
        score = min(score, 45.0)
    return round(clamp(score), 3), {
        "provenance_class": "calculated",
        "rating": rating,
        "rating_kind": rating_kind,
        "sold_count": volume,
        "review_count": review_count,
        "method": "rating_volume_log_blend_v2",
    }


def _currency(row: Mapping[str, Any]) -> str | None:
    value = _raw_lookup(
        row,
        "sale_price_currency", "target_sale_price_currency", "currency",
    )
    return str(value).upper() if value else None


def _is_b2b(text: str) -> bool:
    normalized = normalize_text(text)
    return any(term in normalized for term in B2B_TERMS)


def score_product_candidate(
    row: Mapping[str, Any],
    problem: Mapping[str, Any],
    policy: GapSolverPolicy | None = None,
    *,
    paid_overrides: Mapping[str, Any] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Assign one fail-closed commercial lane to an AliExpress candidate."""
    policy = policy or GapSolverPolicy()
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    source_key = str(row.get("source_key") or "")
    price = number(row.get("price_eur"))
    commission_rate = ratio(row.get("commission_rate"))
    expected = number(row.get("expected_commission_eur"))
    recomputed = round(price * commission_rate, 2) if price is not None and commission_rate is not None else None
    tolerance = max(0.05, (recomputed or 0.0) * 0.02)
    commission_consistent = bool(
        expected is not None and recomputed is not None and abs(expected - recomputed) <= tolerance
    )
    observed = parse_time(row.get("offer_observed_at") or row.get("product_observed_at"))
    fresh_offer = bool(observed and observed >= now - timedelta(hours=policy.max_product_age_hours))
    currency = _currency(row)

    identity_fields = {
        "source_product_id": bool(str(row.get("source_product_id") or "").strip()),
        "title": bool(str(row.get("title") or "").strip()),
        "product_url": valid_http_url(row.get("product_url"), ("aliexpress.com", "aliexpress.us")),
        "image_url": valid_http_url(row.get("image_url")),
        "promotion_url": valid_http_url(row.get("promotion_url"), ("aliexpress.com", "aliexpress.us")),
        "price": bool(price is not None and price > 0),
        "currency_eur": currency == "EUR",
        "commission_rate": bool(commission_rate is not None and commission_rate > 0),
    }
    identity_score = 100.0 * sum(identity_fields.values()) / len(identity_fields)

    problem_eligible = bool(problem.get("eligible_to_source"))
    requirements = problem.get("solution_requirements") or []
    product_facts = _flatten_product_facts(row)
    problem_text = " ".join(str(problem.get(x) or "") for x in ("problem_title", "problem_description"))
    matches, fit_score, fit_coverage = requirement_matches(requirements, product_facts, problem_text)
    trust, trust_provenance = trust_score(row)
    unit_economics = paid_required_commission(policy, paid_overrides)
    paid_required = number(unit_economics.get("required_commission_eur"))
    economics_score = (
        clamp((expected or 0.0) / paid_required * 100.0)
        if paid_required and paid_required > 0 else 0.0
    )
    problem_evidence_score = number(problem.get("evidence_score")) or 0.0
    evidence_score = clamp(
        0.65 * problem_evidence_score
        + 0.25 * (fit_coverage * 100.0)
        + 0.10 * (100.0 if trust_provenance["provenance_class"] != "unavailable" else 0.0)
    )

    hard_gates = {
        "aliexpress_only": source_key == "aliexpress",
        "identity_complete": all(identity_fields.values()),
        "commission_traceable": expected is not None and commission_rate is not None,
        "commission_consistent": commission_consistent,
        "discovery_commission_floor": bool(expected is not None and expected >= policy.discovery_min_commission_eur),
        "fresh_offer": fresh_offer,
        "problem_validated": problem_eligible,
    }
    commercial_failure = not all(
        hard_gates[x]
        for x in (
            "aliexpress_only", "identity_complete", "commission_traceable",
            "commission_consistent", "discovery_commission_floor", "fresh_offer",
        )
    )
    b2b = _is_b2b(f"{row.get('title', '')} {row.get('category', '')}")
    organic_gates = {
        "problem_validated": problem_eligible,
        "demand": (number(problem.get("demand_score")) or 0.0) >= policy.min_demand_score,
        "gap": (number(problem.get("gap_score")) or 0.0) >= policy.min_gap_score,
        "problem_fit": fit_score >= policy.min_problem_fit_score,
        "trust": trust >= policy.min_organic_trust_score,
        "evidence": evidence_score >= policy.min_evidence_score,
        "commission": bool(expected is not None and expected >= policy.organic_min_commission_eur),
    }
    paid_gates = {
        "strong_gap": bool(problem.get("strong_gap")),
        "demand": (number(problem.get("demand_score")) or 0.0) >= policy.min_paid_demand_score,
        "requirement_depth": len(requirements) >= 2,
        "problem_fit": fit_score >= policy.min_paid_problem_fit_score,
        "trust": trust >= policy.min_trust_score,
        "evidence": evidence_score >= policy.min_paid_evidence_score,
        "unit_economics_valid": bool(unit_economics.get("valid")),
        "commission": bool(expected is not None and paid_required is not None and expected >= paid_required),
        "consumer_lane": not b2b,
    }

    reason_codes: list[str] = []
    if commercial_failure:
        lane, verdict = "REJECT", "REJECTED"
        reason_codes.extend(f"hard_gate:{key}" for key, passed in hard_gates.items() if not passed and key != "problem_validated")
    elif not problem_eligible:
        lane, verdict = "WATCH", "WITHHELD"
        reason_codes.append("problem_not_validated")
    elif all(organic_gates.values()) and b2b:
        lane, verdict = "B2B_SEARCH", "ELIGIBLE"
        reason_codes.append("technical_or_b2b_intent")
    elif all(organic_gates.values()) and all(paid_gates.values()):
        lane, verdict = "PAID_TEST", "ELIGIBLE"
        reason_codes.append("paid_test_gates_passed")
    elif all(organic_gates.values()):
        lane, verdict = "ORGANIC_TEST", "ELIGIBLE"
        reason_codes.extend(f"paid_gate:{key}" for key, passed in paid_gates.items() if not passed)
    else:
        lane, verdict = "WATCH", "WITHHELD"
        reason_codes.extend(f"organic_gate:{key}" for key, passed in organic_gates.items() if not passed)

    risks: list[tuple[str, float]] = []
    if trust_provenance["provenance_class"] == "unavailable":
        risks.append(("trust_unavailable", 20.0))
    if fit_coverage < 1.0:
        risks.append(("requirement_coverage_incomplete", (1.0 - fit_coverage) * 15.0))
    contradiction_ratio = number(problem.get("contradiction_ratio")) or 0.0
    if contradiction_ratio > 0:
        risks.append(("contradictory_market_evidence", contradiction_ratio * 20.0))
    if unit_economics.get("provenance") != "observed_first_party":
        risks.append(("paid_economics_not_first_party", 5.0))
    risk_penalty = clamp(sum(value for _, value in risks))

    weights = {
        "problem_fit": policy.weight_problem_fit,
        "gap": policy.weight_gap,
        "demand": policy.weight_demand,
        "economics": policy.weight_economics,
        "trust": policy.weight_trust,
        "evidence": policy.weight_evidence,
        "competition_inverse": policy.weight_competition_inverse,
    }
    weight_total = sum(max(0.0, value) for value in weights.values()) or 1.0
    weights = {key: max(0.0, value) / weight_total for key, value in weights.items()}
    opportunity = clamp(
        fit_score * weights["problem_fit"]
        + (number(problem.get("gap_score")) or 0.0) * weights["gap"]
        + (number(problem.get("demand_score")) or 0.0) * weights["demand"]
        + economics_score * weights["economics"]
        + trust * weights["trust"]
        + evidence_score * weights["evidence"]
        + (100.0 - (number(problem.get("competition_score")) or 0.0)) * weights["competition_inverse"]
        - risk_penalty
    )
    problem_confidence = number(problem.get("confidence")) or 0.0
    product_confidence = min(1.0, identity_score / 100.0, evidence_score / 100.0, max(0.0, fit_coverage))
    confidence = max(0.0, min(1.0, 0.65 * problem_confidence + 0.35 * product_confidence))

    return {
        "source_key": source_key,
        "expected_commission_eur": expected,
        "paid_required_commission_eur": paid_required,
        "identity_score": round(identity_score, 3),
        "problem_fit_score": round(fit_score, 3),
        "trust_score": round(trust, 3),
        "economics_score": round(economics_score, 3),
        "evidence_score": round(evidence_score, 3),
        "opportunity_score": round(opportunity, 3),
        "risk_penalty": round(risk_penalty, 3),
        "lane": lane,
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "gate_results": {
            "hard": hard_gates,
            "identity": identity_fields,
            "organic": organic_gates,
            "paid": paid_gates,
        },
        "requirement_matches": matches,
        "unit_economics": unit_economics,
        "reason_codes": reason_codes,
        "risk_flags": [name for name, _ in risks],
        "score_provenance": {
            "identity": "observed_and_calculated",
            "problem_fit": "calculated_from_aliexpress_source_facts",
            "trust": trust_provenance,
            "economics": unit_economics.get("provenance"),
            "opportunity": "calculated",
            "missing_values": "fail_closed",
        },
        "assessment_version": "gap-solver-v2",
    }
