#!/usr/bin/env python3
"""Bounded multilingual-e5-small document encoder for existing SocialMarket GraphRAG.

Production writes occur ONLY through OIDC-verified, content-hash-protected VMDB
claim/ack RPCs. No service role secret, raw tokens, or provider API key needed.
"""
from __future__ import annotations
import argparse
import json
import math
import os
import time
import uuid
from urllib.parse import quote
import requests

MODEL = "intfloat/multilingual-e5-small"
AUDIENCE = "socialmarket-e5-worker"
ENDPOINT = "https://gqpbskssrvpfjtujwezc.supabase.co/functions/v1/socialmarket-e5-worker"

def token() -> str:
    base = os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"]
    secret = os.environ["ACTIONS_ID_TOKEN_REQUEST_TOKEN"]
    sep = "&" if "?" in base else "?"
    r = requests.get(
        base + sep + "audience=" + quote(AUDIENCE),
        headers={"Authorization": "Bearer " + secret},
        timeout=15,
    )
    r.raise_for_status()
    value = r.json().get("value")
    if not value:
        raise RuntimeError("missing_fresh_github_oidc")
    return value

def request(action: str, worker: str, **payload):
    data = {"action": action, "worker": worker, **payload}
    for attempt in range(2):
        r = requests.post(
            ENDPOINT,
            headers={
                "Authorization": "Bearer " + token(),
                "Content-Type": "application/json",
            },
            json=data,
            timeout=35,
        )
        if r.status_code in (401, 403):
            raise RuntimeError("github_oidc_not_authorized")
        if r.status_code in (429, 500, 502, 503, 504) and attempt == 0:
            time.sleep(3)
            continue
        r.raise_for_status()
        data = r.json()
        if data.get("ok") is False:
            raise RuntimeError("worker_gateway_rejected")
        return data
    raise RuntimeError("worker_gateway_unavailable")

def check_vector(v) -> list[float]:
    values = [float(x) for x in v]
    if len(values) != 384 or any(not math.isfinite(x) for x in values):
        raise ValueError("not_finite_384d_e5")
    n = math.sqrt(sum(x * x for x in values))
    if n < 0.97 or n > 1.03:
        raise ValueError("not_normalized_e5")
    return values

def encode(model, documents):
    # E5 is a dual-encoder: passage: prefix is REQUIRED for stored documents.
    payload = ["passage: " + str(doc["doc_text"]) for doc in documents]
    rows = model.encode(
        payload, batch_size=8, normalize_embeddings=True,
        convert_to_numpy=True, show_progress_bar=False,
    )
    if len(rows) != len(documents):
        raise RuntimeError("embedding_count_mismatch")
    return [check_vector(x) for x in rows]

def process(model, worker: str, batches: int, batch_size: int):
    total = 0
    errors = 0
    for index in range(batches):
        batch = request("claim", worker, limit=batch_size)
        docs = batch.get("documents", [])
        if not docs:
            break
        # Never ACK a different content hash or a different worker.
        try:
            vectors = encode(model, docs)
        except Exception as exc:
            for d in docs:
                request("ack", worker, doc_id=d["doc_id"], doc_hash=d["doc_hash"],
                        embedding=None, error=str(type(exc).__name__)[:100])
                errors += 1
            break
        for doc, vector in zip(docs, vectors):
            try:
                res = request("ack", worker, doc_id=doc["doc_id"],
                              doc_hash=doc["doc_hash"], embedding=vector)
                if not res.get("ok"):
                    raise RuntimeError("stale_claim_or_content_hash")
                total += 1
            except Exception:
                errors += 1
                raise
        print(json.dumps({"batch": index + 1, "acknowledged": len(docs),
                          "total": total, "errors": errors, "model": MODEL}), flush=True)
    return {"saved": total, "errors": errors, "model": MODEL, "batches": batches}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-batches", type=int, default=1)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--smoke-only", action="store_true")
    args = ap.parse_args()
    if not 1 <= args.max_batches <= 16:
        raise SystemExit("max-batches range is 1..16")
    if not 1 <= args.batch_size <= 16:
        raise SystemExit("batch-size range is 1..16")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(MODEL, device="cpu", trust_remote_code=False)
    if model.get_sentence_embedding_dimension() != 384:
        raise SystemExit("wrong_e5_dimension")
    if args.smoke_only:
        first = check_vector(model.encode(["passage: δοκιμή προϊόντος"], normalize_embeddings=True)[0])
        second = check_vector(model.encode(["query: προϊόν"], normalize_embeddings=True)[0])
        print(json.dumps({"ok": True, "smoke": True, "dimension": len(first),
                         "query_dimension": len(second), "model": MODEL}))
        return
    worker = "gha-e5-" + str(uuid.uuid4())
    outcome = process(model,worker,args.max_batches,args.batch_size)
    print(json.dumps(outcome),flush=True)
    if outcome["errors"]:
        raise SystemExit("some_embeddings_not_stored")

if __name__=="__main__":
    main()
