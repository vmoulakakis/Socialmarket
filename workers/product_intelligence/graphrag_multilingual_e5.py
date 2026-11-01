#!/usr/bin/env python3
"""SocialMarket-only multilingual E5 embedding worker and server-side query encoder.

Model: intfloat/multilingual-e5-small; 384 dimensions. Greek and English.
Database writes only through sm_intel private, lease-protected claim/ack RPCs.
No cross-tenant, no external merchant claims, no paid provider keys.
"""
from __future__ import annotations
import argparse
import json
import math
import os
import sys
import uuid
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODEL_ID = "intfloat/multilingual-e5-small"
DIMS = 384
MAX_QUERY = 600
MAX_BATCH = 32

def normalize_vector(vector):
    arr = [float(x) for x in vector]
    if len(arr) != DIMS or any(not math.isfinite(x) for x in arr):
        raise ValueError("invalid_embedding_dimension_or_values")
    norm = math.sqrt(sum(v * v for v in arr))
    if not (0.95 <= norm <= 1.05):
        raise ValueError("embedding_not_unit_normalized")
    return arr

def encode_query(model, query):
    if not isinstance(query, str) or not 2 <= len(query.strip()) <= MAX_QUERY:
        raise ValueError("invalid_query")
    return normalize_vector(model.encode(["query: " + query.strip()], normalize_embeddings=True)[0])

def encode_passages(model, documents):
    if not 1 <= len(documents) <= MAX_BATCH:
        raise ValueError("invalid_batch_size")
    values = ["passage: " + str(document)[:1200] for document in documents]
    vectors = model.encode(values, batch_size=min(MAX_BATCH, len(values)), normalize_embeddings=True)
    return [normalize_vector(vec) for vec in vectors]

def build_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(MODEL_ID, device="cpu", trust_remote_code=False)

def run_backfill(model, max_docs):
    """Lease, encode, and acknowledge in independent short transactions.

    At most 3 claims per document are allowed by the DB; stale leases are
    recoverable. A failure on one row cannot undo successful ACKs for others.
    """
    import psycopg
    url = os.getenv("SOCIALMARKET_DB_URL")
    if not url:
        raise RuntimeError("missing_database_connection")
    if not isinstance(max_docs, int) or max_docs < 1:
        raise ValueError("invalid_max_docs")
    name = "sm-e5-" + uuid.uuid4().hex[:12]
    completed = 0
    failed = 0
    conflicted = 0
    with psycopg.connect(url, sslmode="require", autocommit=True) as conn:
        while completed + failed + conflicted < max_docs:
            size = min(MAX_BATCH, max_docs-completed-failed-conflicted)
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "select doc_id,doc_text,doc_hash from sm_intel.claim_embeddings(%s,%s)",
                        (name,size),
                    )
                    jobs = cur.fetchall()
            if not jobs:
                break
            try:
                vectors = encode_passages(model,[row[1] for row in jobs])
            except Exception as exc:
                for doc_id,_,content_hash in jobs:
                    with conn.transaction():
                        with conn.cursor() as cur:
                            cur.execute(
                                "select sm_intel.ack_embedding(%s,%s,%s,null,%s)",
                                (doc_id,name,content_hash,type(exc).__name__),
                            )
                            cur.fetchone()
                    failed += 1
                continue
            for (doc_id,_,content_hash),vector in zip(jobs,vectors):
                try:
                    with conn.transaction():
                        with conn.cursor() as cur:
                            cur.execute(
                                "select sm_intel.ack_embedding(%s,%s,%s,%s,null)",
                                (doc_id,name,content_hash,json.dumps(vector)),
                            )
                            accepted = bool(cur.fetchone()[0])
                    if accepted:
                        completed += 1
                    else:
                        conflicted += 1
                except Exception as exc:
                    failed += 1
                    # Any failed write can safely be retried only if the
                    # DB lease/content hash remains current. Never pretend
                    # that a vector was saved.
                    try:
                        with conn.transaction():
                            with conn.cursor() as cur:
                                cur.execute(
                                    "select sm_intel.ack_embedding(%s,%s,%s,null,%s)",
                                    (doc_id,name,content_hash,type(exc).__name__),
                                )
                    except Exception:
                        pass
    print(json.dumps({
        "model": MODEL_ID,"completed":completed,
        "failed":failed,"lease_conflicts":conflicted,
        "max_docs":max_docs,"real_embeddings_written":completed,
    }))
    return 0 if failed==0 and conflicted==0 else 2


def run_query_service(model):
    token = os.environ.get("SOCIALMARKET_EMBED_QUERY_TOKEN","")
    if len(token) < 32:
        raise RuntimeError("missing_server_query_token")
    port = int(os.getenv("PORT", "8091"))
    # Bounded inference on a 2-OCPU ARM worker: avoid unbounded concurrent model calls.
    inference_slots = threading.BoundedSemaphore(value=2)
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != "/health":
                self.send_error(404)
                return
            payload = json.dumps({"ok":True,"model":MODEL_ID,"dimensions":DIMS}).encode()
            self.send_response(200)
            self.send_header("Content-Type","application/json")
            self.send_header("Cache-Control","no-store")
            self.send_header("Content-Length",str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        def do_POST(self):
            import hmac
            if self.path != "/embed" or not hmac.compare_digest(self.headers.get("Authorization",""),"Bearer "+token):
                self.send_error(401)
                return
            size = int(self.headers.get("Content-Length",0))
            if size<1 or size>4096:
                self.send_error(413)
                return
            if not inference_slots.acquire(blocking=False):
                self.send_error(503,"inference_capacity_exceeded")
                return
            try:
                data = json.loads(self.rfile.read(size))
                if not isinstance(data,dict):
                    raise ValueError("request_must_be_json_object")
                vec = encode_query(model,data.get("query"))
                reply = json.dumps({"model":MODEL_ID,"dimensions":DIMS,"embedding":vec}).encode()
                self.send_response(200)
                self.send_header("Content-Type","application/json")
                self.send_header("Cache-Control","no-store")
                self.send_header("Content-Length",str(len(reply)))
                self.end_headers()
                self.wfile.write(reply)
            except (ValueError,TypeError,KeyError):
                self.send_error(400)
            finally:
                inference_slots.release()
        def log_message(self, *_):
            return
    # Bind loopback by default; expose only behind an authenticated reverse proxy/TLS.
    host = os.getenv("SOCIALMARKET_EMBED_BIND","127.0.0.1")
    class LimitedHTTPServer(ThreadingHTTPServer):
        request_queue_size = 8
        daemon_threads = True
    LimitedHTTPServer((host,port),Handler).serve_forever()

def main():
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["backfill","query-service","local-query"])
    p.add_argument("--limit", type=int, default=256)
    p.add_argument("--query", default=None)
    args = p.parse_args()
    if args.mode=="backfill" and not 1<=args.limit<=100000:
        p.error("limit_out_of_range")
    model = build_model()
    if args.mode=="backfill":
        return run_backfill(model,args.limit)
    if args.mode=="query-service":
        run_query_service(model)
        return 0
    print(json.dumps({"model":MODEL_ID,"embedding":encode_query(model,args.query)}))
    return 0
if __name__ == "__main__":
    sys.exit(main())
