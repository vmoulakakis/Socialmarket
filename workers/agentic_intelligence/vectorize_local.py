import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Iterable

import requests

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "workers" / "market_intelligence"))
from gateway import db_call  # noqa: E402

OLLAMA_URL = os.getenv("LOCAL_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
EMBED_MODEL = os.getenv("LOCAL_EMBED_MODEL", "qwen3-embedding:0.6b")
EMBED_DB_NAME = "Qwen/Qwen3-Embedding-0.6B"


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()


def get(resource: str, params: dict[str, str]):
    return db_call("GET", resource, params=params) or []


def post(resource: str, data, prefer="return=minimal"):
    return db_call("POST", resource, data=data, prefer=prefer)


def patch(resource: str, params: dict[str, str], data: dict):
    return db_call("PATCH", resource, params=params, data=data, prefer="return=minimal")


def split_chunks(text: str, size=1400, overlap=180) -> Iterable[str]:
    text = " ".join(str(text or "").split())
    pos, n = 0, len(text)
    while pos < n:
        end = min(n, pos + size)
        if end < n:
            cut = text.rfind(" ", pos + int(size * 0.65), end)
            if cut > pos:
                end = cut
        piece = text[pos:end].strip()
        if piece:
            yield piece
        if end >= n:
            break
        pos = max(pos + 1, end - overlap)


def embed_batch(texts: list[str]) -> list[list[float]]:
    r = requests.post(
        f"{OLLAMA_URL}/api/embed",
        json={"model": EMBED_MODEL, "input": texts, "truncate": True},
        timeout=180,
    )
    r.raise_for_status()
    vectors = r.json().get("embeddings") or []
    if len(vectors) != len(texts):
        raise RuntimeError(f"embedding count mismatch {len(vectors)} != {len(texts)}")
    for vector in vectors:
        if len(vector) != 1024:
            raise RuntimeError(f"expected vector(1024), got {len(vector)}")
    return vectors


def pgvector(vector: list[float]) -> str:
    return "[" + ",".join(f"{float(x):.8f}" for x in vector) + "]"


def latest_completed_run():
    rows = get("intelligence_runs", {
        "select": "id,created_at,status,config",
        "status": "eq.completed",
        "order": "created_at.desc",
        "limit": "1",
    })
    return rows[0] if rows else None


def ensure_research_chunks(run_id: str):
    docs = get("research_documents", {
        "select": "id,clean_text,title,canonical_url",
        "intelligence_run_id": f"eq.{run_id}",
        "status": "in.(parsed,embedded)",
        "order": "created_at.asc",
        "limit": "200",
    })
    created = 0
    for doc in docs:
        existing = get("research_chunks", {
            "select": "id",
            "document_id": f"eq.{doc['id']}",
            "limit": "1",
        })
        if existing:
            continue
        rows = []
        for index, content in enumerate(split_chunks(doc.get("clean_text") or "")):
            rows.append({
                "document_id": doc["id"],
                "chunk_index": index,
                "content": content,
                "content_hash": digest(content),
                "token_estimate": max(1, len(content) // 4),
                "embedding_model": EMBED_DB_NAME,
                "metadata": {"title": doc.get("title"), "url": doc.get("canonical_url")},
            })
        if rows:
            post("research_chunks", rows, "resolution=merge-duplicates,return=minimal")
            created += len(rows)
    return created


def embed_research(run_id: str, batch_size=12):
    doc_ids = {x["id"] for x in get("research_documents", {
        "select": "id",
        "intelligence_run_id": f"eq.{run_id}",
        "limit": "500",
    })}
    rows = get("research_chunks", {
        "select": "id,document_id,content",
        "embedding": "is.null",
        "order": "created_at.asc",
        "limit": "500",
    })
    rows = [row for row in rows if row.get("document_id") in doc_ids]
    done = 0
    for offset in range(0, len(rows), batch_size):
        batch = rows[offset:offset + batch_size]
        vectors = embed_batch([str(row.get("content") or "") for row in batch])
        for row, vector in zip(batch, vectors):
            patch("research_chunks", {"id": f"eq.{row['id']}"}, {
                "embedding": pgvector(vector),
                "embedding_model": EMBED_DB_NAME,
            })
            done += 1
    if done:
        for document_id in doc_ids:
            remaining = get("research_chunks", {
                "select": "id",
                "document_id": f"eq.{document_id}",
                "embedding": "is.null",
                "limit": "1",
            })
            if not remaining:
                patch("research_documents", {"id": f"eq.{document_id}"}, {"status": "embedded"})
    return done


def product_text(product: dict) -> str:
    fields = [
        product.get("product_name"), product.get("brand_name"), product.get("category_raw"),
        product.get("description"), product.get("merchant_name"),
        f"price {product.get('price')}" if product.get("price") is not None else None,
        f"availability {product.get('availability')}" if product.get("availability") else None,
    ]
    return " | ".join(str(x).strip() for x in fields if x not in (None, ""))[:6000]


def embed_products(limit=500, batch_size=12):
    products = get("products", {
        "select": "id,product_name,brand_name,category_raw,description,merchant_name,price,availability,in_stock,is_active",
        "is_active": "eq.true",
        "order": "updated_at.desc.nullslast,created_at.desc",
        "limit": str(limit),
    })
    todo = []
    for product in products:
        text = product_text(product)
        content_hash = digest(text)
        existing = get("product_embeddings", {
            "select": "id,content_hash,model_name",
            "product_id": f"eq.{product['id']}",
            "embedding_type": "eq.product_semantic_v2",
            "limit": "1",
        })
        existing = existing[0] if existing else None
        if existing and existing.get("content_hash") == content_hash and existing.get("model_name") == EMBED_DB_NAME:
            continue
        todo.append((product, text, content_hash, existing))

    done = 0
    for offset in range(0, len(todo), batch_size):
        batch = todo[offset:offset + batch_size]
        vectors = embed_batch([item[1] for item in batch])
        for (product, _text, content_hash, existing), vector in zip(batch, vectors):
            data = {
                "embedding_type": "product_semantic_v2",
                "embedding": pgvector(vector),
                "model_name": EMBED_DB_NAME,
                "content_hash": content_hash,
            }
            if existing:
                patch("product_embeddings", {"id": f"eq.{existing['id']}"}, data)
            else:
                post("product_embeddings", {"product_id": product["id"], **data})
            done += 1
    return done, len(products), len(todo)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="")
    parser.add_argument("--product-limit", type=int, default=500)
    args = parser.parse_args()
    run = {"id": args.run_id} if args.run_id else latest_completed_run()
    if not run:
        raise SystemExit("No completed intelligence run found")
    run_id = run["id"]
    created = ensure_research_chunks(run_id)
    research_embedded = embed_research(run_id)
    products_embedded, products_seen, products_needed = embed_products(args.product_limit)
    print(json.dumps({
        "status": "completed",
        "run_id": run_id,
        "model": EMBED_DB_NAME,
        "dimensions": 1024,
        "research_chunks_created": created,
        "research_chunks_embedded": research_embedded,
        "products_seen": products_seen,
        "products_needing_embedding": products_needed,
        "products_embedded": products_embedded,
        "paid_llm_calls": 0,
        "paid_llm_cost_usd": 0,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
