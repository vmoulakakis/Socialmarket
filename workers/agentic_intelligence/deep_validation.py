import re

from pain_grouping_embedding import _cos, _embed


def _query_label(pain):
    label = str(pain.get("label") or pain.get("description") or "").strip()
    words = label.split()
    if len(words) > 18:
        label = " ".join(words[:18])
    return label[:180]


def deepen_pain(core, run_id, pain, max_pages=8):
    """Autonomously seek independent supporting evidence before gap creation.

    Search and crawling are deterministic. Local Qwen embeddings decide only
    semantic similarity between a stored pain and candidate evidence. Final
    pain status is recomputed by the database formula.
    """
    score_before = float(pain.get("pain_score") or 0)
    label = _query_label(pain)
    queries = [
        f'"{label}" customer complaints reviews',
        f'{label} common problem users',
        f'{label} buyers experience issue',
    ]
    existing_links = core.get("pain_evidence_links", {
        "pain_id": f"eq.{pain['id']}",
        "select": "evidence_id,relation",
        "limit": "200",
    })
    existing_evidence = []
    if existing_links:
        ids = ",".join(x["evidence_id"] for x in existing_links)
        existing_evidence = core.get("evidence_items", {
            "id": f"in.({ids})",
            "select": "id,source_independence_key,quote_hash,relation",
            "limit": "200",
        })
    seen_domains = {x.get("source_independence_key") for x in existing_evidence if x.get("source_independence_key")}
    seen_urls = set()
    documents_checked = 0
    added = 0

    try:
        pain_vec = _embed([label])[0]
    except Exception as exc:
        core.audit(run_id, "pain_deepening_embedding_failed", {"pain_id": pain["id"], "error": str(exc)[:300]}, actor="evidence-validator", severity="warning")
        return pain

    for query in queries:
        for row in core.searx(query, limit=8):
            if documents_checked >= max_pages:
                break
            if row["url"] in seen_urls or row["domain"] in seen_domains or row["domain"] in core.DISCOVERY_ONLY_DOMAINS:
                continue
            seen_urls.add(row["url"])
            page = core.fetch_page(row["url"])
            if not page:
                continue
            documents_checked += 1
            candidates = [s for s in core.sentences(page["text"]) if core.PAIN_RE.search(s)][:18]
            if not candidates:
                continue
            try:
                vecs = _embed(candidates)
            except Exception:
                continue
            scored = sorted(((float(_cos(pain_vec, vec)), sentence) for sentence, vec in zip(candidates, vecs)), reverse=True)
            accepted = [(score, sentence) for score, sentence in scored if score >= 0.68][:3]
            if not accepted:
                continue
            doc = core.create_doc(run_id, page, {"research_role": "pain_deep_validation", "pain_id": pain["id"], "query": query})
            for similarity, sentence in accepted:
                try:
                    ev = core.post_one("evidence_items", {
                        "intelligence_run_id": run_id,
                        "document_id": doc["id"],
                        "evidence_type": "pain_validation_support",
                        "entity_type": "pain",
                        "entity_key": pain["pain_key"],
                        "statement": sentence[:1800],
                        "normalized_statement": core.norm(sentence),
                        "relation": "support",
                        "severity_score": core.pain_severity(sentence),
                        "relevance_score": round(similarity * 100, 2),
                        "credibility_score": 68,
                        "confidence": min(0.92, 0.55 + similarity * 0.35),
                        "source_independence_key": doc.get("source_domain"),
                        "extraction_mode": "deterministic",
                        "quote_hash": core.h(sentence),
                        "metadata": {"semantic_similarity": similarity, "embedding_model": "Qwen/Qwen3-Embedding-0.6B", "untrusted_external_content": True},
                    })
                    core.post_one("pain_evidence_links", {"pain_id": pain["id"], "evidence_id": ev["id"], "relation": "support", "weight": round(similarity, 4)})
                    added += 1
                except Exception:
                    pass
            seen_domains.add(page["domain"])
        if documents_checked >= max_pages:
            break

    core.db_call("POST", "rpc/recompute_pain_metrics", data={"p_pain_id": pain["id"]})
    fresh_rows = core.get("pain_candidates", {"id": f"eq.{pain['id']}", "select": "*", "limit": "1"})
    fresh = fresh_rows[0] if fresh_rows else pain
    attempt_rows = core.get("pain_validation_attempts", {
        "run_id": f"eq.{run_id}", "pain_id": f"eq.{pain['id']}", "select": "attempt_no", "order": "attempt_no.desc", "limit": "1"
    })
    attempt_no = int(attempt_rows[0]["attempt_no"] + 1) if attempt_rows else 1
    core.post_one("pain_validation_attempts", {
        "run_id": run_id,
        "pain_id": pain["id"],
        "attempt_no": attempt_no,
        "queries": queries,
        "documents_checked": documents_checked,
        "new_supporting_evidence": added,
        "independent_sources_after": int(fresh.get("independent_source_count") or 0),
        "score_before": score_before,
        "score_after": float(fresh.get("pain_score") or 0),
        "status_after": fresh.get("status"),
        "execution_mode": "deterministic+local_embedding",
    })
    core.audit(run_id, "pain_deep_validation", {
        "pain_id": pain["id"], "label": pain.get("label"), "documents_checked": documents_checked,
        "new_support": added, "score_before": score_before, "score_after": fresh.get("pain_score"),
        "sources_after": fresh.get("independent_source_count"), "status_after": fresh.get("status")
    }, actor="evidence-validator")
    return fresh


def deep_then_contradict(core, original_contradiction_check, run_id, pain, max_pages=2):
    pain = deepen_pain(core, run_id, pain, max_pages=8)
    fresh, contradictions = original_contradiction_check(run_id, pain, max_pages=max_pages)
    try:
        core.db_call("POST", "rpc/recompute_pain_metrics", data={"p_pain_id": pain["id"]})
        rows = core.get("pain_candidates", {"id": f"eq.{pain['id']}", "select": "*", "limit": "1"})
        if rows:
            fresh = rows[0]
    except Exception:
        pass
    return fresh, contradictions
