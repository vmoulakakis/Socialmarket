import json
import os
import threading
from typing import Any

import requests

CATALOG_URL = "https://models.github.ai/catalog/models"
BASE_URL = "https://models.github.ai/inference"
API_VERSION = "2026-03-10"
# Included-quota GitHub Models are always preferred over direct paid APIs.
# OpenAI stays last inside the free catalog as well as in direct escalation.
EXCLUDED_PUBLISHERS: set[str] = set()
PREFERRED_PUBLISHERS = ["mistral ai", "microsoft", "meta", "cohere", "ai21 labs", "deepseek", "openai"]


def adaptive_reasoning_policy(
    task_type: str,
    *,
    complexity: float = 0.0,
    confidence: float = 1.0,
    contradiction_count: int = 0,
) -> dict[str, Any]:
    """Choose DeepSeek V4 tier/thinking without spending or invoking a model."""
    task = str(task_type or "").lower()
    score = max(0.0, min(1.0, float(complexity or 0)))
    if confidence < 0.60:
        score += 0.18
    if contradiction_count:
        score += min(0.25, int(contradiction_count) * 0.08)
    if any(x in task for x in ("audit", "skeptic", "forecast", "contradiction", "recovery")):
        score += 0.15
    score = min(1.0, score)
    if score < 0.45:
        return {"model": "deepseek-v4-flash", "thinking": False, "reasoning_effort": "none", "complexity_score": round(score, 3)}
    if score < 0.78:
        return {"model": "deepseek-v4-flash", "thinking": True, "reasoning_effort": "high", "complexity_score": round(score, 3)}
    return {"model": "deepseek-v4-pro", "thinking": True, "reasoning_effort": "max", "complexity_score": round(score, 3)}


def routing_plan(task_type: str, *, complexity: float = 0.0, confidence: float = 1.0,
                 contradiction_count: int = 0, paid_approved: bool = False) -> list[dict[str, Any]]:
    """Canonical cheapest-valid route. This function never executes a provider."""
    deepseek = adaptive_reasoning_policy(
        task_type, complexity=complexity, confidence=confidence,
        contradiction_count=contradiction_count,
    )
    routes = [
        {"tier": 0, "route": "deterministic_or_local", "cost_class": "zero"},
        {"tier": 1, "route": "github_models_included_quota", "cost_class": "included", "max_calls": 8},
    ]
    if not paid_approved:
        routes.append({"tier": 2, "route": "paid_escalation", "status": "blocked_pending_cost_approval"})
        return routes
    routes.extend([
        {"tier": 2, "route": "deepseek_official_api", "cost_class": "paid", **deepseek},
        {"tier": 3, "route": "openai_api_last_resort", "cost_class": "paid", "model": "gpt-5.6-sol" if deepseek["complexity_score"] >= 0.78 else "gpt-5.6-luna", "reasoning_effort": "high" if deepseek["complexity_score"] >= 0.78 else "low"},
    ])
    return routes


class FreeModelRouter:
    """Canonical zero-paid-token semantic route.

    Order:
      0. deterministic/vector/RAG logic in the caller
      1. local open-weight runtime when configured by LocalFirstAgentRuntime
      2. GitHub Models included quota (non-OpenAI preferred; OpenAI last)
      3. DeepSeek V4 direct only through explicit paid reservation
      4. OpenAI direct as final explicitly-approved fallback

    Paid DeepSeek/OpenAI requests require a DB reservation and explicit
    ENABLE_PAID_REMOTE=1. Product Intelligence itself uses its OIDC gateway,
    which applies the same DB policy server-side.
    """

    def __init__(self, max_calls: int | None = None):
        self.token = os.getenv("GITHUB_TOKEN", "").strip()
        self.max_calls = max_calls if max_calls is not None else int(os.getenv("MAX_FREE_MODEL_CALLS", "8"))
        self.calls = 0
        self._model: str | None = None
        self._lock = threading.Lock()

    @property
    def available(self) -> bool:
        return bool(self.token) and self.calls < self.max_calls

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": API_VERSION,
            "Content-Type": "application/json",
        }

    def discover_model(self) -> str | None:
        if self._model:
            return self._model
        if not self.token:
            return None
        try:
            r = requests.get(CATALOG_URL, headers=self._headers(), timeout=30)
            r.raise_for_status()
            models = r.json()
        except Exception:
            return None

        candidates: list[tuple[int, int, str]] = []
        for m in models if isinstance(models, list) else []:
            publisher = str(m.get("publisher") or "").strip().lower()
            model_id = str(m.get("id") or "").strip()
            if not model_id or publisher in EXCLUDED_PUBLISHERS:
                continue
            modalities = {str(x).lower() for x in (m.get("supported_output_modalities") or [])}
            if modalities and "text" not in modalities:
                continue
            capabilities = {str(x).lower() for x in (m.get("capabilities") or [])}
            tool_rank = 0 if "tool-calling" in capabilities else 1
            try:
                pub_rank = PREFERRED_PUBLISHERS.index(publisher)
            except ValueError:
                pub_rank = len(PREFERRED_PUBLISHERS) + 1
            candidates.append((pub_rank, tool_rank, model_id))
        candidates.sort()
        self._model = candidates[0][2] if candidates else None
        return self._model

    def complete_json(self, system: str, payload: Any, *, temperature: float = 0.0) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        """One bounded included-quota semantic call. Returns (parsed_json, telemetry)."""
        with self._lock:
            if not self.available:
                return None, {"route": "github_models_free", "status": "unavailable_or_cap"}
            model = self.discover_model()
            if not model:
                return None, {"route": "github_models_free", "status": "no_model"}
            self.calls += 1
            call_no = self.calls

        body = {
            "model": model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system + " Return strict JSON only. Do not invent evidence."},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
        }
        try:
            r = requests.post(f"{BASE_URL}/chat/completions", headers=self._headers(), json=body, timeout=90)
            r.raise_for_status()
            data = r.json()
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage") or {}
            if isinstance(content, list):
                content = "".join(str(x.get("text") or x) if isinstance(x, dict) else str(x) for x in content)
            text = str(content).strip()
            if text.startswith("```"):
                text = text.strip("`")
                if text.lower().startswith("json"):
                    text = text[4:].lstrip()
            parsed = json.loads(text)
            if not isinstance(parsed, dict):
                parsed = {"result": parsed}
            return parsed, {
                "route": "github_models_free",
                "status": "ok",
                "model": model,
                "call_no": call_no,
                "input_tokens": int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0),
                "output_tokens": int(usage.get("completion_tokens") or usage.get("output_tokens") or 0),
                "cost_usd": 0,
            }
        except Exception as exc:
            return None, {
                "route": "github_models_free",
                "status": "error",
                "model": model,
                "call_no": call_no,
                "error": str(exc)[:300],
                "cost_usd": 0,
            }


def reserve_paid_escalation(
    db_call,
    provider: str,
    model_name: str,
    complexity: float,
    reason: str,
    task_id: str | None = None,
    task_type: str = "merchant_research",
):
    """Only legal doorway to a paid remote model for Python workers.

    The database policy enforces task-specific provider enablement, complexity,
    monthly shared caps and OpenAI daily caps. A reservation does not itself
    invoke a model.
    """
    if os.getenv("ENABLE_PAID_REMOTE", "0") != "1":
        raise RuntimeError("paid remote inference disabled")
    if provider not in {"deepseek", "openai"}:
        raise RuntimeError("unsupported paid provider")
    return db_call(
        "POST",
        "rpc/reserve_remote_model_request",
        data={
            "p_task_id": task_id,
            "p_task_type": task_type,
            "p_provider": provider,
            "p_model_name": model_name,
            "p_complexity_score": float(complexity),
            "p_escalation_reason": reason,
        },
    )
