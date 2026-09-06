#!/usr/bin/env python3
"""Parallel production launcher for SocialMarket AFFINITY QA.

Keeps the deterministic evidence plan and independent Research -> Skeptic chain,
but evaluates bounded two-item batches concurrently across semantic clusters.
Long-running source scans refresh GitHub OIDC credentials before protected calls.
"""
from __future__ import annotations

import base64
import collections
import json
import os
import threading
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

import semantic_marketplace_200_resilient as resilient

core = resilient.core
MAX_WORKERS = max(2, min(8, int(os.getenv('MARKETPLACE200_AI_WORKERS', '6'))))
# The base worker intentionally has conservative minimums. The production
# accelerator can lower only shortlist depth; all commercial/quality gates stay unchanged.
core.LINKWISE_PER_CLUSTER_AI = max(4, min(12, int(os.getenv('MARKETPLACE200_LINKWISE_AI_PER_CLUSTER', '8'))))
core.ALI_PER_CLUSTER_RESEARCH = max(4, min(12, int(os.getenv('MARKETPLACE200_ALI_RESEARCH_PER_CLUSTER', '8'))))

_OIDC_LOCK = threading.Lock()
_OIDC_TOKEN = None
_OIDC_EXP = 0.0
_OIDC_REFRESH_MARGIN = 120.0


def _jwt_exp(token: str) -> float:
    """Read exp only to manage our cache; signature validation remains server-side."""
    try:
        payload = token.split('.')[1]
        payload += '=' * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload.encode()).decode())
        return float(data.get('exp') or 0)
    except Exception:
        return 0.0


def refreshing_oidc_token(force: bool = False) -> str:
    """Return a GitHub OIDC token that will remain valid for the next request.

    The full Linkwise feed can take many minutes to download and scan. GitHub OIDC
    JWTs are intentionally short-lived, so a token captured before the scan may be
    expired by the time Research/Skeptic/persist calls begin.
    """
    global _OIDC_TOKEN, _OIDC_EXP
    now = time.time()
    with _OIDC_LOCK:
        if not force and _OIDC_TOKEN and _OIDC_EXP > now + _OIDC_REFRESH_MARGIN:
            return _OIDC_TOKEN
        base = os.environ['ACTIONS_ID_TOKEN_REQUEST_URL']
        sep = '&' if '?' in base else '?'
        url = base + sep + 'audience=' + urllib.parse.quote(core.AUDIENCE)
        req = urllib.request.Request(
            url,
            headers={'Authorization': 'Bearer ' + os.environ['ACTIONS_ID_TOKEN_REQUEST_TOKEN']},
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            token = str(json.loads(response.read().decode())['value'])
        exp = _jwt_exp(token)
        _OIDC_TOKEN = token
        _OIDC_EXP = exp if exp > now else now + 240.0
        return token


# All protected gateway paths in core + resilient resolve this function dynamically.
core.oidc_token = refreshing_oidc_token


def evaluate_buckets_parallel(buckets):
    # Warm a fresh token immediately before the parallel QA phase, not before the
    # multi-GB source scan. The cache then self-refreshes as expiry approaches.
    core.oidc_token()
    jobs = []
    ordered = collections.defaultdict(list)
    for key, items in buckets.items():
        for start in range(0, len(items), core.AI_BATCH):
            jobs.append((key, start, items[start:start + core.AI_BATCH]))
    print(json.dumps({
        'phase': 'qa_parallel_start',
        'batches': len(jobs),
        'workers': MAX_WORKERS,
        'batch_size': core.AI_BATCH,
        'linkwise_shortlist_per_cluster': core.LINKWISE_PER_CLUSTER_AI,
        'ali_research_per_cluster': core.ALI_PER_CLUSTER_RESEARCH,
        'oidc_refresh': 'expiry_aware',
    }), flush=True)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(core.evaluate_resilient, batch): (key, start) for key, start, batch in jobs}
        completed = 0
        for fut in as_completed(futures):
            key, start = futures[fut]
            result = fut.result()
            ordered[key].append((start, result))
            completed += 1
            if completed % 10 == 0 or completed == len(jobs):
                print(json.dumps({'phase': 'qa_parallel_progress', 'completed': completed, 'total': len(jobs)}), flush=True)
    out = {}
    for key in buckets:
        merged = []
        for _, rows in sorted(ordered.get(key, []), key=lambda x: x[0]):
            merged.extend(rows)
        out[key] = merged
    return out


core.evaluate_buckets = evaluate_buckets_parallel

if __name__ == '__main__':
    raise SystemExit(core.main())
