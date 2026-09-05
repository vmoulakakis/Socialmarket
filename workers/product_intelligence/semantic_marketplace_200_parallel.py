#!/usr/bin/env python3
"""Parallel production launcher for SocialMarket AFFINITY QA.

Keeps the deterministic evidence plan and independent Research -> Skeptic chain,
but evaluates bounded two-item batches concurrently across semantic clusters.
"""
from __future__ import annotations

import collections
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import semantic_marketplace_200_resilient as resilient

core = resilient.core
MAX_WORKERS = max(2, min(8, int(os.getenv('MARKETPLACE200_AI_WORKERS', '6'))))


def evaluate_buckets_parallel(buckets):
    core.oidc_token()  # warm one shared GitHub OIDC token before worker threads
    jobs = []
    ordered = collections.defaultdict(list)
    for key, items in buckets.items():
        for start in range(0, len(items), core.AI_BATCH):
            jobs.append((key, start, items[start:start + core.AI_BATCH]))
    print(json.dumps({'phase': 'qa_parallel_start', 'batches': len(jobs), 'workers': MAX_WORKERS, 'batch_size': core.AI_BATCH}), flush=True)
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
