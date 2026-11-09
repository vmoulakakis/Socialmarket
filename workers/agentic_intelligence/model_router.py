import json
import os
import threading
from typing import Any

import requests

# GitHub Models fully retired July 30, 2026.
def configured_free_provider(env=None):
    values = os.environ if env is None else env
    groq = str(values.get("GROQ_API_KEY") or "").strip()
    if groq and str(values.get("GROQ_FREE_TIER_CONFIRMED") or "").lower() == "true":
        return {"provider": "groq", "key": groq, "model": "openai/gpt-oss-20b", "base_url": "https://api.groq.com/openai/v1"}
    openrouter = str(values.get("OPENROUTER_API_KEY") or "").strip()
    if openrouter:
        return {"provider": "openrouter", "key": openrouter, "model": "openrouter/free", "base_url": "https://openrouter.ai/api/v1"}
    return None


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
        {"tier": 1, "route": "verified_free_tier_provider", "cost_class": "free_tier", "max_calls": 8},
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
    """Bounded verified free-tier route. No paid or deprecated GitHub Models inference."""

    def __init__(self, max_calls: int | None = None):
        self._route = configured_free_provider()
        self.token = self._route["key"] if self._route else ""
        self.provider = self._route["provider"] if self._route else "none"
        self.base_url = self._route["base_url"] if self._route else ""
        self._model = self._route["model"] if self._route else None
        self.max_calls = max_calls if max_calls is not None else max(1, min(int(os.getenv("MAX_FREE_MODEL_CALLS", "8")), 16))
        self.calls = 0
        self._lock = threading.Lock()

    @property
    def available(self) -> bool:
        return bool(self._route) and self.calls < self.max_calls

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    def discover_model(self) -> str | None:
        return self._model

    def complete_json(self, system: str, payload: Any, *, temperature: float = 0.0) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        route = f"{self.provider}_free" if self._route else "verified_free_unavailable"
        with self._lock:
            if not self.available:
                return None, {"route": route, "provider": self.provider, "status": "unavailable_or_cap"}
            self.calls += 1
            call_no = self.calls
        body = {
            "model": self._model,
            "temperature": max(0.0, min(float(temperature), 1.0)),
            "max_tokens": 700,
            "messages": [
                {"role": "system", "content": system + " Return strict JSON only. Do not invent evidence."},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
        }
        try:
            r = requests.post(f"{self.base_url}/chat/completions", headers=self._headers(), json=body, timeout=45)
            r.raise_for_status()
            data = r.json()
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage") or {}
            if isinstance(content, list):
                content = "".join(str(x.get("text") or x) if isinstance(x, dict) else str(x) for x in content)
            raw = str(content).strip()
            fence = chr(96) * 3
            if raw.startswith(fence):
                raw = raw.strip(chr(96))
                if raw.lower().startswith("json"):
                    raw = raw[4:].lstrip()
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                parsed = {"result": parsed}
            return parsed, {
                "route": route, "provider": self.provider, "status": "ok",
                "model": self._model, "call_no": call_no,
                "input_tokens": int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0),
                "output_tokens": int(usage.get("completion_tokens") or usage.get("output_tokens") or 0),
                "cost_usd": 0,
            }
        except Exception as exc:
            return None, {
                "route": route, "provider": self.provider, "status": "error",
                "model": self._model, "call_no": call_no,
                "error_class": type(exc).__name__,
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
