from __future__ import annotations

import os
import time
from urllib.parse import quote

import requests

AUDIENCE = "socialmarket-v2-worker"
FUNCTION_URL = os.getenv(
    "MERCHANT_INTELLIGENCE_GATEWAY",
    "https://rpfadpdnnxequgvdcfoq.supabase.co/functions/v1/merchant-intelligence-gateway",
)
_token: str | None = None
_token_at = 0.0


def _oidc_token(force: bool = False) -> str:
    global _token, _token_at
    if _token and not force and time.time() - _token_at < 180:
        return _token
    url = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_URL")
    request_token = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN")
    if not url or not request_token:
        raise RuntimeError("GitHub OIDC unavailable; workflow requires permissions: id-token: write")
    sep = "&" if "?" in url else "?"
    response = requests.get(
        f"{url}{sep}audience={quote(AUDIENCE)}",
        headers={"Authorization": f"Bearer {request_token}"},
        timeout=30,
    )
    response.raise_for_status()
    _token = response.json()["value"]
    _token_at = time.time()
    return _token


def call(action: str, **params):
    payload = {"action": action, "params": params}
    for attempt in range(2):
        response = requests.post(
            FUNCTION_URL,
            headers={
                "Authorization": f"Bearer {_oidc_token(force=attempt > 0)}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=180,
        )
        if response.status_code == 401 and attempt == 0:
            continue
        response.raise_for_status()
        body = response.json()
        if not body.get("ok"):
            raise RuntimeError(body)
        return body.get("result")
    raise RuntimeError("OIDC gateway authentication failed")
