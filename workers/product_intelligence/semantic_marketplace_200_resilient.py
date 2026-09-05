#!/usr/bin/env python3
"""Production launcher for Semantic Marketplace 200.

Adds two transport/integration guarantees without changing the core business policy:
1. AliExpress API credentials are preflighted. If unavailable, the AliExpress
   portfolio is explicitly marked API_BLOCKED and the Linkwise portfolio may still
   complete; cached AliExpress products are never substituted.
2. Every AliExpress candidate must have a generated affiliate promotion link before
   it can continue to AI selection/persistence.
"""
from __future__ import annotations

import json
import urllib.request
from typing import Any

import semantic_marketplace_200 as core

_ORIGINAL_DISCOVER = core.discover_aliexpress


def _health() -> dict[str, Any]:
    try:
        with urllib.request.urlopen(core.ALI_GATEWAY, timeout=30) as response:
            return json.loads(response.read().decode())
    except Exception as exc:
        return {'ok': False, 'configured': False, 'tracking_configured': False, 'error': str(exc)[:400]}


def _find_tracking_url(value: Any) -> str:
    if isinstance(value, str):
        if value.startswith('https://s.click.aliexpress.com/') or value.startswith('http://s.click.aliexpress.com/'):
            return value
        return ''
    if isinstance(value, dict):
        # Prefer explicitly named promotion fields before walking everything.
        for key in ('promotion_link', 'promotion_url', 'tracking_url'):
            url = _find_tracking_url(value.get(key))
            if url:
                return url
        for child in value.values():
            url = _find_tracking_url(child)
            if url:
                return url
    if isinstance(value, list):
        for child in value:
            url = _find_tracking_url(child)
            if url:
                return url
    return ''


def discover_aliexpress_safe(clusters, excluded):
    health = _health()
    if not health.get('configured') or not health.get('tracking_configured'):
        print(json.dumps({
            'warning': 'aliexpress_api_blocked',
            'configured': bool(health.get('configured')),
            'tracking_configured': bool(health.get('tracking_configured')),
            'policy': 'no_cache_fallback',
        }), flush=True)
        return (
            {str(c.get('cluster_key')): [] for c in clusters},
            {
                'api_blocked': True,
                'configured': bool(health.get('configured')),
                'tracking_configured': bool(health.get('tracking_configured')),
                'commission_gt30_unique': 0,
                'ai_shortlist': 0,
                'greek_research': {},
                'policy': 'authenticated_api_required_no_cached_substitute',
            },
        )

    buckets, stats = _ORIGINAL_DISCOVER(clusters, excluded)
    generated = 0
    dropped = 0
    for key, rows in list(buckets.items()):
        valid = []
        for row in rows:
            if not row.get('tracking_url') and row.get('detail_url'):
                try:
                    result = core.ali('generate_link', url=row['detail_url'])
                    row['tracking_url'] = _find_tracking_url(result.get('data'))
                    if row['tracking_url']:
                        generated += 1
                except Exception as exc:
                    row.setdefault('evidence_summary', {})['tracking_generation_error'] = str(exc)[:400]
            if not row.get('tracking_url'):
                dropped += 1
                continue
            row.setdefault('evidence_summary', {})['affiliate_tracking_verified_source'] = 'AliExpress Affiliate API promotion link'
            valid.append(row)
        buckets[key] = valid
    stats.update({
        'api_blocked': False,
        'tracking_links_generated': generated,
        'missing_tracking_dropped': dropped,
        'ai_shortlist': sum(len(v) for v in buckets.values()),
    })
    return buckets, stats


core.discover_aliexpress = discover_aliexpress_safe

if __name__ == '__main__':
    raise SystemExit(core.main())
