#!/usr/bin/env python3
"""Resilient launcher for the Greece Top100 V2 pipeline.

The business policy remains owned by top100_autonomous_v2.py. This launcher only
hardens the AI-rank transport: it keeps the normal 10-product batch for speed,
reduces repeated context size, recursively retries smaller batches when the model
returns malformed/truncated JSON, and skips only an irrecoverable single candidate
instead of aborting the entire daily run.
"""
from __future__ import annotations

import time
from typing import Any

import top100_autonomous_v2 as core

_BASE_GATEWAY = core.gateway
_MAX_RANK_BATCH = 10
_MARKET_CONTEXT_LIMIT = 30
_FEEDBACK_LIMIT = 20


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
