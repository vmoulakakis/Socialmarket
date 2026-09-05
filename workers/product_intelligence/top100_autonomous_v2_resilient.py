#!/usr/bin/env python3
"""Resilient launcher for the Greece Top100 V2 pipeline.

The business policy remains owned by top100_autonomous_v2.py. This launcher routes
AI ranking through a dedicated robust gateway and enforces lifecycle exclusion: once
a product enters the SocialScheduler/provider pipeline it cannot be selected again.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

import top100_autonomous_v2 as core

_BASE_GATEWAY = core.gateway
_MAX_RANK_BATCH = 10
STATE_ENDPOINT = os.getenv(
    'TOP100_PUBLICATION_STATE_URL',
    'https://rpfadpdnnxequgvdcfoq.supabase.co/functions/v1/top100-publication-state',
)
RANK_ENDPOINT = os.getenv(
    'TOP100_RANK_GATEWAY',
    'https://rpfadpdnnxequgvdcfoq.supabase.co/functions/v1/top100-rank-gateway',
)


def _post_oidc(url: str, payload: dict[str, Any], timeout: int = 210) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode(),
        headers={
            'Authorization': 'Bearer ' + core.oidc_token(),
            'Content-Type': 'application/json',
        },
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            result = json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode(errors='replace')
        raise RuntimeError(f'endpoint failed {exc.code}: {raw[:1000]}') from exc
    if not result.get('ok'):
        raise RuntimeError(str(result.get('error') or 'endpoint_error'))
    return result


def _pipeline_exclusions() -> set[str]:
    payload = _post_oidc(STATE_ENDPOINT, {}, timeout=60)
    return {str(x) for x in (payload.get('pipeline_source_hashes') or []) if str(x).strip()}


def _rank_chunk(items: list[dict[str, Any]], markets: list[dict[str, Any]], feedback: list[dict[str, Any]], depth: int = 0) -> list[dict[str, Any]]:
    if not items:
        return []
    try:
        response = _post_oidc(
            RANK_ENDPOINT,
            {'action': 'rank', 'items': items, 'markets': markets, 'feedback': feedback},
            timeout=240,
        )
        return list(response.get('items') or [])
    except Exception as exc:
        if len(items) == 1:
            print({
                'warning': 'top100_ai_candidate_skipped_after_transport_failure',
                'source_record_hash': items[0].get('source_record_hash'),
                'error': str(exc)[:500],
                'depth': depth,
            }, flush=True)
            return []
        midpoint = max(1, len(items) // 2)
        time.sleep(min(1.5, 0.25 * (depth + 1)))
        return (
            _rank_chunk(items[:midpoint], markets, feedback, depth + 1)
            + _rank_chunk(items[midpoint:], markets, feedback, depth + 1)
        )


def resilient_gateway(action: str, **payload: Any) -> dict[str, Any]:
    if action == 'candidate_pool':
        result = _BASE_GATEWAY(action, **payload)
        excluded = _pipeline_exclusions()
        before = list(result.get('items') or [])
        result['items'] = [x for x in before if str(x.get('source_record_hash') or '') not in excluded]
        result['pipeline_excluded'] = len(before) - len(result['items'])
        return result

    if action != 'rank':
        return _BASE_GATEWAY(action, **payload)

    items = list(payload.get('items') or [])
    markets = list(payload.get('markets') or [])[:30]
    feedback = list(payload.get('feedback') or [])[:20]
    ranked: list[dict[str, Any]] = []

    for start in range(0, len(items), _MAX_RANK_BATCH):
        ranked.extend(_rank_chunk(items[start:start + _MAX_RANK_BATCH], markets, feedback))

    return {
        'ok': True,
        'items': ranked,
        'transport_policy': 'dedicated-rank-gateway-plus-bisect-v3',
        'requested': len(items),
        'recovered': len(ranked),
    }


core.gateway = resilient_gateway

if __name__ == '__main__':
    raise SystemExit(core.main())
