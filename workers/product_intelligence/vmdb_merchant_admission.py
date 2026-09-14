"""Fail-closed VMDB Merchant 360 admission gate for product staging.

Only merchants present in public.merchant_product_discovery_eligible are allowed to
enter the expensive multi-GB Linkwise product feed stage. The view already enforces
fresh Merchant 360 hard gates and the max-3-per-subcategory diversification policy.
"""
from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from typing import Any, Mapping

from product_agents import fold
from stream_feed import normalize_domain

AUDIENCE = "socialmarket-supabase-worker"
GATEWAY = os.getenv(
    "VMDB_WORKER_GATEWAY",
    "https://gqpbskssrvpfjtujwezc.supabase.co/functions/v1/github-worker-gateway",
)
_TOKEN: str | None = None
_TOKEN_AT = 0.0


def _oidc_token() -> str:
    global _TOKEN, _TOKEN_AT
    if _TOKEN and time.time() - _TOKEN_AT < 180:
        return _TOKEN
    url = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_URL")
    token = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN")
    if not url or not token:
        raise RuntimeError("vmdb_merchant_gate_requires_github_oidc")
    sep = "&" if "?" in url else "?"
    req = urllib.request.Request(
        url + sep + "audience=" + urllib.parse.quote(AUDIENCE),
        headers={"Authorization": "Bearer " + token},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        _TOKEN = json.loads(r.read().decode())["value"]
    _TOKEN_AT = time.time()
    return _TOKEN


def _gateway_get(resource: str, params: Mapping[str, Any]) -> list[dict[str, Any]]:
    payload = json.dumps(
        {"method": "GET", "resource": resource, "params": dict(params)},
        ensure_ascii=False,
    ).encode()
    req = urllib.request.Request(
        GATEWAY,
        data=payload,
        headers={
            "Authorization": "Bearer " + _oidc_token(),
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            body = json.loads(r.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise RuntimeError(f"vmdb_merchant_gate_http_{exc.code}:{detail[:800]}") from exc
    if not body.get("ok"):
        raise RuntimeError(f"vmdb_merchant_gate_failed:{body}")
    result = body.get("result") or []
    if not isinstance(result, list):
        raise RuntimeError("vmdb_merchant_gate_invalid_result")
    return result


def eligible_merchants() -> list[dict[str, Any]]:
    rows = _gateway_get(
        "merchant_product_discovery_eligible",
        {
            "select": (
                "id,merchant_name,canonical_domain,primary_category,primary_subcategory,"
                "expected_commission_eur,demand_score,competition_score,supply_gap_score,"
                "problem_solving_score,trust_score,confidence_adjusted_score,subcategory_rank"
            ),
            "order": "confidence_adjusted_score.desc",
            "limit": "100",
        },
    )
    if not rows:
        raise RuntimeError(
            "no_vmdb_eligible_merchants; product ingestion is intentionally fail-closed "
            "until Merchant 360 produces approved merchants"
        )
    return rows


def _matches(program: Mapping[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    pname = fold(program.get("canonical_name") or program.get("program_name") or "")
    pdomain = normalize_domain(program.get("official_domain"))
    for row in rows:
        rname = fold(row.get("merchant_name") or "")
        rdomain = normalize_domain(row.get("canonical_domain"))
        if pname and rname and pname == rname:
            return row
        if pdomain and rdomain and (pdomain == rdomain or pdomain.endswith("." + rdomain) or rdomain.endswith("." + pdomain)):
            return row
    return None


def filter_context(context: Mapping[str, Any]) -> dict[str, Any]:
    rows = eligible_merchants()
    selected = []
    unmatched = []
    for program in context.get("programs", []):
        match = _matches(program, rows)
        if not match:
            continue
        enriched = dict(program)
        # VMDB admission truth overrides legacy research metrics for gating/ranking context.
        enriched.update(
            {
                "vmdb_merchant_profile_id": match.get("id"),
                "demand_score": match.get("demand_score"),
                "competition_score": match.get("competition_score"),
                "solution_whitespace_score": match.get("supply_gap_score"),
                "trust_score": match.get("trust_score"),
                "confidence": min(1.0, float(match.get("confidence_adjusted_score") or 0) / 100.0),
                "vmdb_problem_solving_score": match.get("problem_solving_score"),
                "vmdb_expected_commission_eur": match.get("expected_commission_eur"),
                "vmdb_subcategory_rank": match.get("subcategory_rank"),
                "promotion_mode": "eligible",
                "dominant_market": False,
            }
        )
        selected.append(enriched)

    selected_names = {fold(x.get("canonical_name") or x.get("program_name") or "") for x in selected}
    for row in rows:
        if fold(row.get("merchant_name") or "") not in selected_names:
            unmatched.append(row.get("merchant_name"))

    if not selected:
        raise RuntimeError(
            "vmdb_eligible_merchants_do_not_match_legacy_product_context; refusing product ingestion"
        )

    gated = dict(context)
    gated["programs"] = selected
    gated["vmdb_merchant_admission"] = {
        "policy": "greece_problem_solver_v1",
        "fail_closed": True,
        "eligible_view_count": len(rows),
        "matched_program_count": len(selected),
        "unmatched_eligible_merchants": unmatched,
        "commission_floor_eur": 15,
        "max_per_subcategory": 3,
    }
    print(
        json.dumps(
            {
                "phase": "vmdb_merchant_admission",
                "eligible_view_count": len(rows),
                "matched_program_count": len(selected),
                "unmatched": unmatched,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    return gated


def gated_stage_feed(delegate, feed: str, context: Mapping[str, Any]):
    return delegate(feed, filter_context(context))
