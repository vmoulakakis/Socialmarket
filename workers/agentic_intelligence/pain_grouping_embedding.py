import math
import os
from collections import defaultdict

import requests

OLLAMA_URL = os.getenv("LOCAL_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
EMBED_MODEL = os.getenv("LOCAL_EMBED_MODEL", "qwen3-embedding:0.6b")


def _embed(texts):
    r = requests.post(
        f"{OLLAMA_URL}/api/embed",
        json={"model": EMBED_MODEL, "input": texts, "truncate": True},
        timeout=180,
    )
    r.raise_for_status()
    vectors = r.json().get("embeddings") or []
    if len(vectors) != len(texts):
        raise RuntimeError("embedding_count_mismatch")
    return vectors


def _cos(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def _mean(vectors):
    n = len(vectors)
    return [sum(row[i] for row in vectors) / n for i in range(len(vectors[0]))]


def embedding_group_pains(core, evidence_rows, agent_runtime, run_id, fallback_group=None):
    if not evidence_rows:
        return []
    rows = evidence_rows[:96]
    texts = [str(x.get("statement") or "")[:700] for x in rows]
    try:
        vectors = _embed(texts)
    except Exception as exc:
        core.audit(run_id, "embedding_pain_cluster_failed", {"error": str(exc)[:300]}, actor="pain-miner", severity="warning")
        return fallback_group(rows, agent_runtime, run_id) if fallback_group else []

    # Greedy semantic clustering. A higher threshold prevents generic same-topic
    # sentences from being merged merely because both discuss sunglasses/home.
    threshold = float(os.getenv("PAIN_CLUSTER_COSINE", "0.76"))
    clusters = []
    for idx, vector in enumerate(vectors):
        best_index, best_score = None, -1.0
        for ci, cluster in enumerate(clusters):
            score = _cos(vector, cluster["centroid"])
            if score > best_score:
                best_index, best_score = ci, score
        if best_index is not None and best_score >= threshold:
            cluster = clusters[best_index]
            cluster["indices"].append(idx)
            cluster["vectors"].append(vector)
            cluster["centroid"] = _mean(cluster["vectors"])
        else:
            clusters.append({"indices": [idx], "vectors": [vector], "centroid": vector})

    # Rank for cross-source evidence first, then evidence volume/cohesion.
    def rank(cluster):
        sources = {rows[i].get("source_independence_key") for i in cluster["indices"] if rows[i].get("source_independence_key")}
        return (len(sources), len(cluster["indices"]))

    clusters.sort(key=rank, reverse=True)
    clusters = clusters[:12]
    draft = []
    for ci, cluster in enumerate(clusters):
        items = [rows[i] for i in cluster["indices"]]
        sources = sorted({x.get("source_independence_key") for x in items if x.get("source_independence_key")})
        # Representative = statement closest to centroid.
        best_local = max(range(len(cluster["indices"])), key=lambda j: _cos(cluster["vectors"][j], cluster["centroid"]))
        rep = str(items[best_local].get("statement") or "")[:700]
        draft.append({
            "index": ci,
            "representative": rep,
            "evidence_count": len(items),
            "independent_sources": len(sources),
            "sample_statements": [str(x.get("statement") or "")[:300] for x in items[:6]],
        })

    # One bounded local/free model call labels the already-computed clusters.
    # It cannot create clusters, evidence, counts or scores.
    parsed, telemetry = agent_runtime.run_json(
        "Pain Label Agent",
        "For each supplied evidence cluster, write one specific neutral customer pain label of at most 12 words. Do not repeat article headings. Do not claim a pain that the sample statements do not show. Return labels:[{index,label,pain_type,target_segment}].",
        {"clusters": draft},
    )
    core.log_model_usage(run_id, telemetry, "pain_cluster_labeling")
    labels = {}
    if parsed and isinstance(parsed.get("labels"), list):
        for item in parsed["labels"]:
            try:
                labels[int(item.get("index"))] = item
            except Exception:
                pass

    result = []
    for ci, cluster in enumerate(clusters):
        items = [rows[i] for i in cluster["indices"]]
        label = str((labels.get(ci) or {}).get("label") or draft[ci]["representative"])[:220]
        result.append({
            "representative": draft[ci]["representative"],
            "items": items,
            "label": label,
            "pain_type": str((labels.get(ci) or {}).get("pain_type") or "friction")[:80],
            "target_segment": str((labels.get(ci) or {}).get("target_segment") or "")[:200] or None,
        })
    core.audit(run_id, "embedding_pain_clusters", {
        "model": EMBED_MODEL,
        "threshold": threshold,
        "input_evidence": len(rows),
        "clusters_retained": len(result),
        "cross_source_clusters": sum(1 for g in result if len({x.get('source_independence_key') for x in g['items'] if x.get('source_independence_key')}) >= 2),
    }, actor="pain-miner")
    return result
