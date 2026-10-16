from __future__ import annotations

import os
from urllib.parse import quote

import requests

import merchant_demand_intelligence as core

_original_judge = core.github_model_judge


def fresh_oidc_token():
    """Request a fresh GitHub OIDC token for every VMDB write/read.

    The legacy worker caches OIDC for 180s. The production gateway can return
    401 during a long merchant research cycle; a fresh token makes persistence
    fail-closed and resilient without adding any paid AI cost.
    """
    url = os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"]
    request_token = os.environ["ACTIONS_ID_TOKEN_REQUEST_TOKEN"]
    sep = "&" if "?" in url else "?"
    response = requests.get(
        f"{url}{sep}audience={quote(core.AUDIENCE)}",
        headers={"Authorization": f"Bearer {request_token}"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["value"]


def cost_first_judge(payload: dict) -> dict:
    """Spend zero model tokens when deterministic evidence already misses gates.

    The buffer is deliberately conservative: only merchants close enough to the
    production policy thresholds reach the GitHub Models verifier. Final hard
    gates remain owned by merchant_demand_intelligence.py and VMDB policy.
    """
    demand = float(payload.get("demand_score") or 0)
    competition = float(payload.get("competition_score") or 100)
    gap = float(payload.get("supply_gap_score") or 0)
    problem = float(payload.get("problem_solving_score") or 0)
    trust = float(payload.get("trust_score") or 0)
    value = float(payload.get("price_value_score") or 0)
    fulfilment = float(payload.get("greek_fulfilment_score") or 0)

    far_below = (
        demand < 62
        or competition > 53
        or gap < 52
        or problem < 62
        or trust < 57
        or value < 47
        or fulfilment < 52
    )
    if far_below:
        return {
            "verdict": "needs_review",
            "confidence_delta": 0.0,
            "why_selected": None,
            "why_rejected": "zero_token_deterministic_prefilter",
        }
    return _original_judge(payload)


core.oidc_token = fresh_oidc_token
core.github_model_judge = cost_first_judge

if __name__ == "__main__":
    core.main()
