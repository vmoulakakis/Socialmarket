from __future__ import annotations

"""SocialMarket Deep Demand Intelligence V3.

This module NEVER replaces observed production metrics. It adds a second analytical
layer around them: fuzzy whitespace inference, temporal diagnostics, statistical /
neural forecasts when history is sufficient, change-point detection, graph context,
and causal-readiness checks. Missing inputs stay missing.
"""

import json
import math
import sys
from dataclasses import dataclass
from typing import Any, Iterable

import numpy as np
import pandas as pd


def n(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        out = float(value)
        return out if math.isfinite(out) else None
    except (TypeError, ValueError):
        return None


def clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, float(value)))


def tri(x: float, a: float, b: float, c: float) -> float:
    if x <= a or x >= c:
        return 0.0
    if x == b:
        return 1.0
    return (x - a) / (b - a) if x < b else (c - x) / (c - b)


def shoulder_low(x: float, full: float, zero: float) -> float:
    if x <= full:
        return 1.0
    if x >= zero:
        return 0.0
    return (zero - x) / (zero - full)


def shoulder_high(x: float, zero: float, full: float) -> float:
    if x <= zero:
        return 0.0
    if x >= full:
        return 1.0
    return (x - zero) / (full - zero)


def fuzzy_whitespace(
    demand: float | None,
    pain: float | None,
    supply: float | None,
    competition: float | None,
    confidence: float | None,
) -> dict[str, Any]:
    """Mamdani-style inference. Demand is an input, never reduced by supply.

    The result describes exploitable whitespace, NOT demand itself.
    """
    if demand is None or pain is None:
        return {"score": None, "state": "insufficient", "reason": "demand_and_pain_required", "rules": []}

    d, p = clamp(demand), clamp(pain)
    s = clamp(supply) if supply is not None else None
    c = clamp(competition) if competition is not None else None
    conf = clamp((confidence or 0.0) * 100 if (confidence or 0.0) <= 1 else (confidence or 0.0))

    d_hi, p_hi = shoulder_high(d, 48, 75), shoulder_high(p, 45, 72)
    d_mid, p_mid = tri(d, 25, 52, 78), tri(p, 20, 50, 78)
    s_low = shoulder_low(s, 25, 58) if s is not None else None
    s_hi = shoulder_high(s, 48, 78) if s is not None else None
    c_low = shoulder_low(c, 30, 62) if c is not None else None
    c_hi = shoulder_high(c, 48, 78) if c is not None else None

    rules: list[tuple[str, float, float]] = []
    # name, activation, consequent centroid
    if s_low is not None:
        rules.append(("high demand + high pain + low supply", min(d_hi, p_hi, s_low), 92.0))
        rules.append(("mid demand + high pain + low supply", min(max(d_mid, d_hi), p_hi, s_low), 78.0))
        rules.append(("high demand + high supply", min(d_hi, s_hi or 0.0), 45.0))
    if c_low is not None:
        rules.append(("high demand + high pain + low competition", min(d_hi, p_hi, c_low), 88.0))
        rules.append(("high demand + high competition", min(d_hi, c_hi or 0.0), 42.0))
    rules.append(("high demand + high pain", min(d_hi, p_hi), 72.0))
    rules.append(("medium evidence opportunity", min(max(d_mid, 0.05), max(p_mid, 0.05)), 55.0))

    active = [(name, strength, center) for name, strength, center in rules if strength > 0]
    if not active:
        return {"score": None, "state": "insufficient", "reason": "no_active_fuzzy_rule", "rules": []}

    raw = sum(strength * center for _, strength, center in active) / sum(strength for _, strength, _ in active)
    # Confidence attenuates inference certainty, not observed demand.
    certainty = 0.55 + 0.45 * (conf / 100.0)
    score = clamp(raw * certainty)
    return {
        "score": round(score, 2),
        "raw_score": round(raw, 2),
        "certainty_multiplier": round(certainty, 3),
        "state": "inferred",
        "rules": [{"rule": name, "activation": round(strength, 3), "target": center} for name, strength, center in active],
        "semantics": "fuzzy solution-whitespace inference; does not modify observed demand",
    }


def history_quality(history: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = [r for r in history if n(r.get("demand_score")) is not None and r.get("observed_at")]
    if not rows:
        return {"points": 0, "span_days": 0, "forecast_tier": "none", "reason": "no_history"}
    ts = pd.to_datetime([r["observed_at"] for r in rows], utc=True, errors="coerce")
    ts = ts[~pd.isna(ts)]
    span = int((ts.max() - ts.min()).total_seconds() / 86400) if len(ts) > 1 else 0
    points = len(rows)
    # Conservative readiness gates to prevent deep-learning theatre.
    tier = "neural" if points >= 30 and span >= 21 else "statistical" if points >= 8 and span >= 5 else "descriptive"
    return {"points": points, "span_days": span, "forecast_tier": tier}


def _series(history: Iterable[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for r in history:
        y = n(r.get("demand_score"))
        if y is None or not r.get("observed_at"):
            continue
        rows.append({"ds": pd.to_datetime(r["observed_at"], utc=True), "y": y})
    if not rows:
        return pd.DataFrame(columns=["ds", "y"])
    df = pd.DataFrame(rows).dropna().sort_values("ds")
    # Multiple runs in one day become one daily observation; no fake interpolation.
    df["day"] = df["ds"].dt.floor("D")
    return df.groupby("day", as_index=False)["y"].mean().rename(columns={"day": "ds"})


def statistical_forecast(history: Iterable[dict[str, Any]], horizon: int = 14) -> dict[str, Any]:
    df = _series(history)
    if len(df) < 8:
        return {"state": "unavailable", "reason": "minimum_8_daily_observations", "points": len(df)}
    try:
        from statsforecast import StatsForecast
        from statsforecast.models import AutoETS, Theta

        work = df.copy()
        work["unique_id"] = "demand"
        sf = StatsForecast(models=[AutoETS(season_length=7), Theta(season_length=7)], freq="D")
        fc = sf.forecast(df=work[["unique_id", "ds", "y"]], h=horizon, level=[80, 95])
        model_cols = [c for c in fc.columns if c not in {"unique_id", "ds"} and "-lo-" not in c and "-hi-" not in c]
        model = model_cols[0] if model_cols else None
        if not model:
            raise RuntimeError("forecast_model_output_missing")
        values = [round(float(x), 2) for x in fc[model].tolist()]
        return {
            "state": "forecasted",
            "method": f"StatsForecast:{model}",
            "horizon_days": horizon,
            "forecast": values,
            "dates": [x.isoformat() for x in fc["ds"]],
            "semantics": "forecast of the existing evidence-derived demand index, not search volume",
        }
    except Exception as exc:
        # A transparent statistical fallback is preferable to silently failing.
        x = np.arange(len(df), dtype=float)
        slope, intercept = np.polyfit(x, df["y"].to_numpy(dtype=float), 1)
        future = [clamp(intercept + slope * (len(df) + i)) for i in range(horizon)]
        return {
            "state": "forecasted",
            "method": "robust_linear_fallback",
            "horizon_days": horizon,
            "forecast": [round(v, 2) for v in future],
            "warning": f"statsforecast_unavailable:{type(exc).__name__}",
            "semantics": "fallback forecast of evidence-derived demand index",
        }


def neural_forecast(history: Iterable[dict[str, Any]], horizon: int = 14) -> dict[str, Any]:
    df = _series(history)
    if len(df) < 30:
        return {"state": "unavailable", "reason": "minimum_30_daily_observations", "points": len(df)}
    try:
        from neuralforecast import NeuralForecast
        from neuralforecast.models import NHITS

        work = df.copy()
        work["unique_id"] = "demand"
        model = NHITS(h=horizon, input_size=min(28, len(work) - horizon if len(work) > horizon else 14), max_steps=250)
        nf = NeuralForecast(models=[model], freq="D")
        nf.fit(df=work[["unique_id", "ds", "y"]])
        fc = nf.predict().reset_index()
        col = next(c for c in fc.columns if c not in {"unique_id", "ds"})
        return {
            "state": "forecasted",
            "method": "NeuralForecast:NHITS",
            "horizon_days": horizon,
            "forecast": [round(float(x), 2) for x in fc[col].tolist()],
            "dates": [pd.Timestamp(x).isoformat() for x in fc["ds"]],
            "semantics": "neural forecast of evidence-derived demand index; never treated as observed demand",
        }
    except Exception as exc:
        return {"state": "unavailable", "reason": f"neural_runtime:{type(exc).__name__}", "points": len(df)}


def change_points(history: Iterable[dict[str, Any]]) -> dict[str, Any]:
    df = _series(history)
    if len(df) < 12:
        return {"state": "unavailable", "reason": "minimum_12_daily_observations", "points": len(df)}
    try:
        import ruptures as rpt

        signal = df["y"].to_numpy(dtype=float)
        algo = rpt.Pelt(model="rbf", min_size=3).fit(signal)
        bkps = [i for i in algo.predict(pen=max(2.0, math.log(len(signal)) * 2.0)) if i < len(df)]
        return {
            "state": "derived",
            "method": "ruptures:PELT-rbf",
            "breakpoints": [{"index": i, "date": df.iloc[i]["ds"].isoformat()} for i in bkps],
        }
    except Exception as exc:
        return {"state": "unavailable", "reason": f"changepoint_runtime:{type(exc).__name__}"}


def causal_readiness(history: Iterable[dict[str, Any]], exogenous: dict[str, list[Any]] | None = None) -> dict[str, Any]:
    q = history_quality(history)
    exogenous = exogenous or {}
    usable = {k: [n(v) for v in values] for k, values in exogenous.items() if values}
    if q["points"] < 30:
        return {"state": "unavailable", "reason": "minimum_30_observations", "can_claim_causality": False}
    if len(usable) < 2:
        return {"state": "unavailable", "reason": "minimum_2_exogenous_series", "can_claim_causality": False}
    return {
        "state": "ready_for_refutation",
        "framework": "DoWhy-compatible causal graph + refutation",
        "can_claim_causality": False,
        "required_next": ["declare causal DAG", "estimate effect", "run placebo/refutation", "sensitivity analysis"],
        "warning": "correlation remains non-causal until explicit identification and refutation pass",
    }


def graph_context(category: dict[str, Any], pains: list[dict[str, Any]], merchants: list[dict[str, Any]]) -> dict[str, Any]:
    """Lightweight GraphRAG-style context map; no LLM indexing cost required."""
    nodes = [{"id": str(category.get("taxonomy_id") or category.get("id")), "type": "taxonomy", "label": category.get("subcategory_name") or category.get("category_name") or category.get("taxonomy_name")}]
    edges = []
    root = nodes[0]["id"]
    for p in pains[:25]:
        pid = str(p.get("id") or f"pain:{len(nodes)}")
        nodes.append({"id": pid, "type": "pain", "label": p.get("canonical_text") or p.get("representative_pain") or p.get("cluster_label")})
        edges.append({"source": root, "target": pid, "relation": "HAS_VALIDATED_PAIN"})
    for m in merchants[:25]:
        mid = str(m.get("merchant_id") or m.get("id") or f"merchant:{len(nodes)}")
        nodes.append({"id": mid, "type": "merchant", "label": m.get("canonical_name")})
        edges.append({"source": root, "target": mid, "relation": "HAS_SUPPLY"})
    return {
        "state": "derived",
        "pattern": "lightweight_graph_rag",
        "nodes": nodes,
        "edges": edges,
        "semantics": "relationship context only; graph degree is not demand",
    }


def analyze_category(payload: dict[str, Any]) -> dict[str, Any]:
    category = payload.get("category") or {}
    history = payload.get("history") or []
    pains = payload.get("pains") or []
    merchants = payload.get("merchants") or []
    supply = payload.get("supply") or {}

    observed = {
        "demand_score": n(category.get("demand_score")),
        "competition_score": n(category.get("competition_score")),
        "pain_gap_score": n(category.get("pain_gap_score")),
        "confidence": n(category.get("confidence")),
        "validated_pain_clusters": n(category.get("validated_pain_clusters")),
        "observed_at": category.get("observed_at"),
        "methodology_version": category.get("methodology_version"),
    }
    supply_index = n(supply.get("supply_index"))
    whitespace = fuzzy_whitespace(observed["demand_score"], observed["pain_gap_score"], supply_index, observed["competition_score"], observed["confidence"])
    quality = history_quality(history)

    stat = statistical_forecast(history) if quality["forecast_tier"] in {"statistical", "neural"} else {"state": "unavailable", "reason": "history_not_ready", **quality}
    neural = neural_forecast(history) if quality["forecast_tier"] == "neural" else {"state": "unavailable", "reason": "history_not_ready", **quality}

    return {
        "version": "deep_demand_v3",
        "taxonomy_id": category.get("taxonomy_id"),
        "label": category.get("subcategory_name") or category.get("category_name") or category.get("taxonomy_name"),
        "observed": observed,
        "supply": {
            "supply_index": supply_index,
            "merchant_count": supply.get("merchant_count"),
            "trusted_merchant_count": supply.get("trusted_merchant_count"),
            "program_count": supply.get("program_count"),
            "semantics": "supply is modeled separately and never subtracted from observed demand",
        },
        "inferred": {"fuzzy_whitespace": whitespace, "graph_context": graph_context(category, pains, merchants)},
        "temporal": {
            "quality": quality,
            "change_points": change_points(history),
            "statistical_forecast": stat,
            "neural_forecast": neural,
        },
        "causal": causal_readiness(history, payload.get("exogenous")),
        "guardrails": [
            "observed demand is never overwritten by supply or model output",
            "forecast values are indices, not search volume",
            "neural forecasting is disabled until history is sufficient",
            "causal claims are disabled until identification and refutation pass",
            "missing competition/supply remains missing",
        ],
    }


def main() -> None:
    payload = json.load(sys.stdin)
    print(json.dumps(analyze_category(payload), ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
