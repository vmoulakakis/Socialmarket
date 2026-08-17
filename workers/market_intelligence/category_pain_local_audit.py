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
Extract ONLY product-related consumer problems, unmet needs, alternative requests or purchase frictions actually supported by REAL EXTRACTED CONSUMER TEXT for the EXACT canonical category/subcategory.
Reject navigation text, product descriptions, SEO copy, generic articles, news, social problems, merchant/company complaints unrelated to product need, locations, brands, campaign themes, keyword coincidences and pure positive reviews.
Do not infer population prevalence from one review. Do not invent search volume, market share, competition, features, prices or popularity.
A cluster can be validated only when at least 3 relevant consumer evidence rows support the SAME commercially meaningful need and support is independent: at least 2 domains AND either at least 2 source families or at least 3 domains.
Prefer recurring desired outcomes and solvable product frictions.
Return strict JSON with keys clusters, audit_summary, rejected_patterns.
Each cluster must contain canonical_text, cluster_type (pain|unmet_need|alternative_request|complaint), evidence_indices, pain_severity 0-100, commercial_intent 0-100, audit_score 0-100, confidence 0-1, rationale, verdict (validated|needs_review|rejected).
If evidence does not meet the standard, return no validated cluster."""


def _host(url: str | None) -> str:
    try:
        from urllib.parse import urlsplit

        return (urlsplit(url or "").hostname or "").lower().removeprefix("www.")
    except Exception:
        return ""


def _pain_evidence(item: Mapping[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for evidence in item.get("evidence") or []:
        metadata = evidence.get("metadata") or {}
        if evidence.get("source_kind") != "pain_candidate":
            continue
        if metadata.get("consumer_text") is not True:
            continue
        if metadata.get("eligible_for_pain_audit") is False:
            continue
        out.append(
            {
                "i": len(out),
                "source_url": evidence.get("source_url"),
                "source_domain": _host(evidence.get("source_url")),
                "source_family": metadata.get("source_family") or "public_web",
                "title": evidence.get("title"),
                "body": str(evidence.get("body") or "")[:1100],
                "confidence": evidence.get("confidence"),
                "consumer_language_score": metadata.get("consumer_language_score"),
                "pain_language": metadata.get("pain_language"),
            }
        )
    return out[:60]


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
            "market_evidence_quality": ((item.get("market") or {}).get("evidence_quality") or {}),
            "evidence": evidence,
        },
        required_keys=("clusters", "audit_summary", "rejected_patterns"),
        prompt_version="category-pain-local-v1",
        max_tier=2,
        cacheable=True,
        material_change_capable=True,
        metadata={"evidence_count": len(evidence), "geography": "GR"},
    )


def _validate_nested(data: Mapping[str, Any], evidence_count: int) -> tuple[bool, str | None]:
    clusters = data.get("clusters")
    if not isinstance(clusters, list):
        return False, "clusters_not_array"
    if not isinstance(data.get("rejected_patterns"), list):
        return False, "rejected_patterns_not_array"
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
    return True, None


def _models() -> tuple[str, str]:
    # Qwen3.5 4B is the smallest model that passed the SocialMarket local AI V2
    # qualification suite 5/5 on the real GitHub-hosted runner. Smaller tested
    # models remain unqualified and are intentionally not production defaults.
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
        OllamaExecutor(name="category-pain-tier1", tier=1, model=tier1, endpoint=endpoint, timeout_seconds=180),
    ]
    if tier2 and tier2 != tier1:
        executors.append(
            OllamaExecutor(name="category-pain-tier2", tier=2, model=tier2, endpoint=endpoint, timeout_seconds=240)
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
