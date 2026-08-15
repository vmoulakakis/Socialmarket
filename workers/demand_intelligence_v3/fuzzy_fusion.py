"""Demand Intelligence V3 fuzzy analytical state engine.

This module never overwrites canonical demand/competition/pain metrics. It converts
read-only inputs into qualitative membership strengths for analyst explanations.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from math import exp
from typing import Optional


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(v)))


def trap(x: Optional[float], a: float, b: float, c: float, d: float) -> Optional[float]:
    if x is None:
        return None
    x = float(x)
    if x <= a:
        return 1.0 if a == b and x == a else 0.0
    if x >= d:
        return 1.0 if c == d and x == d else 0.0
    if b <= x <= c:
        return 1.0
    if a < x < b:
        return _clamp((x-a)/(b-a))
    return _clamp((d-x)/(d-c))


def tri(x: Optional[float], a: float, b: float, c: float) -> Optional[float]:
    if x is None:
        return None
    x = float(x)
    if x == b:
        return 1.0
    if x <= a or x >= c:
        return 0.0
    return _clamp((x-a)/(b-a) if x < b else (c-x)/(c-b))


def _and(*values: Optional[float]) -> Optional[float]:
    if any(v is None for v in values):
        return None
    return min(float(v) for v in values if v is not None)


def _or(*values: Optional[float]) -> float:
    return max([float(v) for v in values if v is not None] or [0.0])


@dataclass(frozen=True)
class FuzzyState:
    state: str
    membership: dict[str, float]
    semantics: str = "DERIVED fuzzy state; canonical metrics are immutable."


def classify(
    demand: Optional[float],
    competition: Optional[float],
    pain: Optional[float],
    confidence: Optional[float],
    supply_strength: Optional[float],
    evidence_count: int = 0,
) -> FuzzyState:
    """Return qualitative state memberships. Confidence accepts 0..1 or 0..100."""
    conf = None if confidence is None else float(confidence) * (100 if float(confidence) <= 1 else 1)
    d_high = trap(demand, 55, 72, 100, 100)
    d_mid = tri(demand, 25, 55, 82)
    c_low = trap(competition, 0, 0, 30, 55)
    c_high = trap(competition, 50, 72, 100, 100)
    p_high = trap(pain, 48, 68, 100, 100)
    cf_high = trap(conf, 55, 72, 100, 100)
    cf_low = trap(conf, 0, 0, 45, 65)
    s_low = trap(supply_strength, 0, 0, 30, 58)
    s_high = trap(supply_strength, 48, 70, 100, 100)
    raw = {
        "validated_unmet_need": _and(d_high, p_high, cf_high),
        "whitespace": _and(d_high, s_low, c_low, cf_high),
        "emerging": _and(_or(d_mid, d_high), s_low, cf_high),
        "crowded_demand": _and(d_high, _or(c_high, s_high), cf_high),
        "balanced": _and(_or(d_mid, d_high), _or(s_high, tri(supply_strength, 25, 55, 80)), cf_high),
        "uncertain": _or(cf_low, 1.0 if competition is None else 0.0, .75 if pain is None else 0.0, .85 if evidence_count < 3 else 0.0),
    }
    membership = {k: round(float(v or 0.0), 3) for k, v in raw.items()}
    state = max(membership, key=membership.get)
    return FuzzyState(state=state, membership=membership)


def supply_strength(merchant_count: int, trust: Optional[float], commercial: Optional[float], research_confidence: Optional[float]) -> Optional[float]:
    count_component = 1 - exp(-max(0, merchant_count)/8)
    parts = [count_component]
    if trust is not None:
        parts.append(_clamp(float(trust)/100))
    if commercial is not None:
        parts.append(_clamp(float(commercial)/100))
    if research_confidence is not None:
        parts.append(_clamp(float(research_confidence)))
    return round(sum(parts)/len(parts)*100, 1) if parts else None


def as_json(state: FuzzyState) -> dict:
    return asdict(state)
