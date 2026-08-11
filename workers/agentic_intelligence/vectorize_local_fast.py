import vectorize_local as v


def fast_embed_research(run_id: str, batch_size=16):
    doc_ids = {x["id"] for x in v.get("research_documents", {
        "select": "id",
        "intelligence_run_id": f"eq.{run_id}",
        "limit": "500",
    })}
    rows = v.get("research_chunks", {
        "select": "id,document_id,content",
        "embedding": "is.null",
        "order": "created_at.asc",
        "limit": "1000",
    })
    rows = [row for row in rows if row.get("document_id") in doc_ids]
    done = 0
    for offset in range(0, len(rows), batch_size):
        batch = rows[offset:offset + batch_size]
        vectors = v.embed_batch([str(row.get("content") or "") for row in batch])
        items = [{
            "id": row["id"],
            "embedding": v.pgvector(vector),
            "embedding_model": v.EMBED_DB_NAME,
        } for row, vector in zip(batch, vectors)]
        result = v.db_call("POST", "rpc/bulk_set_research_embeddings", data={"p_items": items})
        done += int(result or len(items))
    if done:
        for document_id in doc_ids:
            remaining = v.get("research_chunks", {
                "select": "id",
                "document_id": f"eq.{document_id}",
                "embedding": "is.null",
                "limit": "1",
            })
            if not remaining:
                v.patch("research_documents", {"id": f"eq.{document_id}"}, {"status": "embedded"})
    return done


def fast_embed_products(limit=500, batch_size=16):
    products = v.get("products", {
        "select": "id,product_name,brand_name,category_raw,description,merchant_name,price,availability,in_stock,is_active",
        "is_active": "eq.true",
        "order": "updated_at.desc.nullslast,created_at.desc",
        "limit": str(limit),
    })
    existing_rows = v.get("product_embeddings", {
        "select": "product_id,content_hash,model_name",
        "embedding_type": "eq.product_semantic_v2",
        "limit": str(max(1000, limit * 2)),
    })
    existing = {row["product_id"]: row for row in existing_rows}
    todo = []
    for product in products:
        text = v.product_text(product)
        content_hash = v.digest(text)
        ex = existing.get(product["id"])
        if ex and ex.get("content_hash") == content_hash and ex.get("model_name") == v.EMBED_DB_NAME:
            continue
        todo.append((product, text, content_hash))

    done = 0
    for offset in range(0, len(todo), batch_size):
        batch = todo[offset:offset + batch_size]
        vectors = v.embed_batch([item[1] for item in batch])
        items = [{
            "product_id": product["id"],
            "embedding_type": "product_semantic_v2",
            "embedding": v.pgvector(vector),
            "model_name": v.EMBED_DB_NAME,
            "content_hash": content_hash,
        } for (product, _text, content_hash), vector in zip(batch, vectors)]
        result = v.db_call("POST", "rpc/bulk_upsert_product_embeddings", data={"p_items": items})
        done += int(result or len(items))
    return done, len(products), len(todo)


v.embed_research = fast_embed_research
v.embed_products = fast_embed_products

if __name__ == "__main__":
    v.main()
