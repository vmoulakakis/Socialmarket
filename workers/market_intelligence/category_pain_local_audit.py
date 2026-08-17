from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Mapping

_AI_RUNTIME = Path(__file__).resolve().parents[1] / "ai_runtime"
if str(_AI_RUNTIME) not in sys.path:
    sys.path.insert(0, str(_AI_RUNTIME))

from ollama_executor import OllamaExecutor  # noqa: E402
from router import AITaskRouter, InMemoryTaskCache  # noqa: E402
from task_contract import AITask  # noqa: E402


INSTRUCTIONS = """You are SocialMarket Greek Consumer Pain Skeptic.
Use ONLY the supplied real extracted consumer-text rows for the exact category/subcategory. Identify product problems, unmet needs, alternative requests or purchase frictions. Reject navigation, SEO/product copy, generic articles, unrelated merchant complaints, keyword coincidences and pure praise. Never invent demand, prevalence, prices, features or popularity.
A candidate cluster needs at least 3 supplied rows supporting the SAME commercially meaningful need. Validated also requires independent support: at least 2 domains AND either 2 source families or 3 domains. NEVER output a cluster with fewer than 3 evidence_indices; omit it instead. If nothing qualifies, return clusters: [].
Return strict JSON only, no markdown, with keys clusters, audit_summary, rejected_patterns. Return at most 2 clusters. Each cluster requires canonical_text, cluster_type (pain|unmet_need|alternative_request|complaint), evidence_indices, pain_severity 0-100, commercial_intent 0-100, audit_score 0-100, confidence 0-1, rationale, verdict (validated|needs_review|rejected). Keep canonical_text <=180 characters, rationale <=160 characters, audit_summary <=220 characters, and rejected_patterns to at most 4 strings <=80 characters each."""


def _host(url: str | None) -> str:
    try:
        from urllib.parse import urlsplit

        return (urlsplit(url or "").hostname or "").lower().removeprefix("www.")
    except Exception:
        return ""


def _bounded_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)).strip())
    except Exception:
        value = default
    return max(minimum, min(maximum, value))


def _numeric(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _selection_score(evidence: Mapping[str, Any]) -> float:
    """Cheap deterministic recall score; never becomes an opportunity score."""
    metadata = evidence.get("metadata") or {}
    language = _numeric(metadata.get("consumer_language_score"), 0.0)
    confidence = _numeric(evidence.get("confidence"), 0.0)
    pain_language = metadata.get("pain_language") or []
    if not isinstance(pain_language, list):
        pain_language = []
    first_person = 1.0 if metadata.get("first_person_signal") is True else 0.0
    return language * 10.0 + confidence * 5.0 + min(len(pain_language), 4) * 1.5 + first_person


def _pain_evidence(item: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Build a small source-diverse evidence pack before any LLM call."""
    max_rows = _bounded_int("CATEGORY_PAIN_AUDIT_MAX_EVIDENCE", 10, 6, 18)
    body_chars = _bounded_int("CATEGORY_PAIN_AUDIT_BODY_CHARS", 600, 320, 800)

    candidates: list[dict[str, Any]] = []
    for evidence in item.get("evidence") or []:
        metadata = evidence.get("metadata") or {}
        if evidence.get("source_kind") != "pain_candidate":
            continue
        if metadata.get("consumer_text") is not True:
            continue
        if metadata.get("eligible_for_pain_audit") is False:
            continue
        domain = _host(evidence.get("source_url"))
        candidates.append(
            {
                "source_url": evidence.get("source_url"),
                "source_domain": domain,
                "source_family": metadata.get("source_family") or "public_web",
                "title": str(evidence.get("title") or "")[:220],
                "body": str(evidence.get("body") or "")[:body_chars],
                "confidence": evidence.get("confidence"),
                "consumer_language_score": metadata.get("consumer_language_score"),
                "pain_language": metadata.get("pain_language"),
                "_score": _selection_score(evidence),
            }
        )

    candidates.sort(
        key=lambda row: (
            -float(row.get("_score") or 0),
            str(row.get("source_domain") or ""),
            str(row.get("source_url") or ""),
        )
    )

    selected: list[dict[str, Any]] = []
    selected_urls: set[str] = set()
    seen_domains: set[str] = set()

    for row in candidates:
        domain = str(row.get("source_domain") or "")
        url = str(row.get("source_url") or "")
        if not domain or domain in seen_domains:
            continue
        selected.append(row)
        seen_domains.add(domain)
        selected_urls.add(url)
        if len(selected) >= max_rows:
            break

    if len(selected) < max_rows:
        for row in candidates:
            url = str(row.get("source_url") or "")
            if url in selected_urls:
                continue
            selected.append(row)
            selected_urls.add(url)
            if len(selected) >= max_rows:
                break

    out: list[dict[str, Any]] = []
    for row in selected:
        clean = {key: value for key, value in row.items() if key != "_score"}
        clean["i"] = len(out)
        out.append(clean)
    return out


def build_task(item: Mapping[str, Any]) -> AITask:
    evidence = _pain_evidence(item)
    return AITask(
        task_type="category_pain_audit",
        role="Independent Greek Consumer Pain Skeptic",
        instructions=INSTRUCTIONS,
        payload={
            "entity_id": item.get("entity_id"),
            "category": item.get("category"),
            "subcategory": item.get("subcategory"),
            "evidence": evidence,
        },
        required_keys=("clusters", "audit_summary", "rejected_patterns"),
        prompt_version="category-pain-local-v3-concise",
        max_tier=2,
        cacheable=True,
        material_change_capable=True,
        metadata={
            "evidence_count": len(evidence),
            "source_domains": len({str(x.get("source_domain") or "") for x in evidence if x.get("source_domain")}),
            "geography": "GR",
            "evidence_pack": "source_diverse_compact_v2",
        },
    )


def _validate_nested(data: Mapping[str, Any], evidence_count: int) -> tuple[bool, str | None]:
    clusters = data.get("clusters")
    if not isinstance(clusters, list):
        return False, "clusters_not_array"
    if len(clusters) > 2:
        return False, "too_many_clusters"
    if not isinstance(data.get("rejected_patterns"), list):
        return False, "rejected_patterns_not_array"
    if len(data.get("rejected_patterns") or []) > 4:
        return False, "too_many_rejected_patterns"
    if not isinstance(data.get("audit_summary"), str):
        return False, "audit_summary_not_string"

    allowed_types = {"pain", "unmet_need", "alternative_request", "complaint"}
    allowed_verdicts = {"validated", "needs_review", "rejected"}
    required = {
        "canonical_text",
        "cluster_type",
        "evidence_indices",
        "pain_severity",
        "commercial_intent",
        "audit_score",
        "confidence",
        "rationale",
        "verdict",
    }
    for cluster in clusters:
        if not isinstance(cluster, Mapping):
            return False, "cluster_not_object"
        if not required.issubset(cluster):
            return False, "cluster_missing_required_fields"
        if str(cluster.get("cluster_type")) not in allowed_types:
            return False, "cluster_type_invalid"
        if str(cluster.get("verdict")) not in allowed_verdicts:
            return False, "cluster_verdict_invalid"
        indices = cluster.get("evidence_indices")
        if not isinstance(indices, list):
            return False, "evidence_indices_not_array"
        if len(indices) < 3:
            return False, "cluster_insufficient_evidence_indices"
        for idx in indices:
            if not isinstance(idx, int) or isinstance(idx, bool) or idx < 0 or idx >= evidence_count:
                return False, "evidence_index_out_of_range"
        try:
            severity = float(cluster.get("pain_severity"))
            intent = float(cluster.get("commercial_intent"))
            audit = float(cluster.get("audit_score"))
            confidence = float(cluster.get("confidence"))
        except Exception:
            return False, "cluster_score_not_numeric"
        if not (0 <= severity <= 100 and 0 <= intent <= 100 and 0 <= audit <= 100 and 0 <= confidence <= 1):
            return False, "cluster_score_out_of_range"
        if len(str(cluster.get("canonical_text") or "")) > 220:
            return False, "cluster_text_too_long"
        if len(str(cluster.get("rationale") or "")) > 220:
            return False, "cluster_rationale_too_long"
    # This is presentation metadata, not a validation dimension. Keep it bounded
    # by the already-small 500-output-token contract without rejecting an
    # otherwise valid evidence decision solely for prose length.
    if len(str(data.get("audit_summary") or "")) > 800:
        return False, "audit_summary_too_long"
    return True, None


def _models() -> tuple[str, str]:
    return (
        os.getenv("CATEGORY_PAIN_TIER1_MODEL", "qwen3.5:4b").strip(),
        os.getenv("CATEGORY_PAIN_TIER2_MODEL", "").strip(),
    )


def _cache_and_sink():
    durable = os.getenv("AI_TASK_RUNTIME_DURABLE", "false").strip().lower() in {"1", "true", "yes", "on"}
    if not durable:
        return InMemoryTaskCache(), None
    from supabase_runtime import AITaskRuntimeClient, SupabaseTaskCache, SupabaseTaskResultSink  # noqa: E402

    client = AITaskRuntimeClient()
    return SupabaseTaskCache(client), SupabaseTaskResultSink(client)


def make_router() -> AITaskRouter:
    endpoint = os.getenv("LOCAL_OLLAMA_URL", "http://127.0.0.1:11434")
    tier1, tier2 = _models()
    executors = [
        OllamaExecutor(
            name="category-pain-tier1",
            tier=1,
            model=tier1,
            endpoint=endpoint,
            timeout_seconds=180,
            max_output_tokens=500,
        ),
    ]
    if tier2 and tier2 != tier1:
        executors.append(
            OllamaExecutor(
                name="category-pain-tier2",
                tier=2,
                model=tier2,
                endpoint=endpoint,
                timeout_seconds=240,
                max_output_tokens=500,
            )
        )
    cache, sink = _cache_and_sink()
    return AITaskRouter(executors=executors, cache=cache, result_sink=sink)


def audit_items(items: list[Mapping[str, Any]], router: AITaskRouter | None = None) -> dict[str, Any]:
    active_router = router or make_router()
    audited: list[dict[str, Any]] = []
    telemetry: list[dict[str, Any]] = []

    for item in items:
        task = build_task(item)
        result = active_router.execute(task)
        telemetry.extend(attempt.as_dict() for attempt in result.attempts)
        if not result.ok or result.data is None:
            raise RuntimeError(
                f"category_pain_local_safe_hold entity={item.get('entity_id')} reason={result.reason or result.status}"
            )
        valid, reason = _validate_nested(result.data, len(task.payload.get("evidence") or []))
        if not valid:
            raise RuntimeError(f"category_pain_local_schema_invalid entity={item.get('entity_id')} reason={reason}")
        audited.append(
            {
                "entity_id": item.get("entity_id"),
                "clusters": list(result.data.get("clusters") or []),
                "audit_summary": str(result.data.get("audit_summary") or ""),
                "rejected_patterns": list(result.data.get("rejected_patterns") or []),
            }
        )

    return {"items": audited, "route": "local_ai_task_router", "telemetry": telemetry}
