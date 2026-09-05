#!/usr/bin/env python3
"""Resilient launcher for the Greece Top100 V2 pipeline.

The business policy remains owned by top100_autonomous_v2.py. This launcher hardens
AI-rank transport and enforces lifecycle exclusion: once a product has entered the
SocialScheduler/provider pipeline it cannot be selected again by a later daily run.
"""
from __future__ import annotations

import json
import os
import time
import urllib.request
from typing import Any

import top100_autonomous_v2 as core

_BASE_GATEWAY = core.gateway
_MAX_RANK_BATCH = 10
_MARKET_CONTEXT_LIMIT = 30
_FEEDBACK_LIMIT = 20
STATE_ENDPOINT = os.getenv(
    'TOP100_PUBLICATION_STATE_URL',
    'https://rpfadpdnnxequgvdcfoq.supabase.co/functions/v1/top100-publication-state',
)


def _pipeline_exclusions() -> set[str]:
    req = urllib.request.Request(
        STATE_ENDPOINT,
        data=b'{}',
        headers={
            'Authorization': 'Bearer ' + core.oidc_token(),
            'Content-Type': 'application/json',
        },
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        payload = json.loads(response.read().decode())
    if not payload.get('ok'):
        raise RuntimeError(f'publication state unavailable: {payload}')
    return {str(x) for x in (payload.get('pipeline_source_hashes') or []) if str(x).strip()}


def _rank_chunk(items: list[dict[str, Any]], markets: list[dict[str, Any]], feedback: list[dict[str, Any]], depth: int = 0) -> list[dict[str, Any]]:
    if not items:
        return []
    try:
        response = _BASE_GATEWAY(
            'rank',
            items=items,
            markets=markets[:_MARKET_CONTEXT_LIMIT],
            feedback=feedback[:_FEEDBACK_LIMIT],
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
    markets = list(payload.get('markets') or [])
    feedback = list(payload.get('feedback') or [])
    ranked: list[dict[str, Any]] = []

    for start in range(0, len(items), _MAX_RANK_BATCH):
        ranked.extend(_rank_chunk(items[start:start + _MAX_RANK_BATCH], markets, feedback))

    return {
        'ok': True,
        'items': ranked,
        'transport_policy': 'normal10-bisect-on-failure-v2',
        'requested': len(items),
        'recovered': len(ranked),
    }


core.gateway = resilient_gateway

if __name__ == '__main__':
    raise SystemExit(core.main())
