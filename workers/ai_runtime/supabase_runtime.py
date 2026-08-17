from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Mapping

from task_contract import AITask, AITaskAttempt, AITaskResult, sha256_json


DEFAULT_ENDPOINT = "https://rpfadpdnnxequgvdcfoq.supabase.co/functions/v1/ai-task-runtime-gateway"
DEFAULT_AUDIENCE = "socialmarket-ai-runtime"


class AITaskRuntimeGatewayError(RuntimeError):
    pass


def github_oidc_token(audience: str = DEFAULT_AUDIENCE) -> str:
    request_url = os.getenv("ACTIONS_ID_TOKEN_REQUEST_URL", "").strip()
    request_token = os.getenv("ACTIONS_ID_TOKEN_REQUEST_TOKEN", "").strip()
    if not request_url or not request_token:
        raise AITaskRuntimeGatewayError("GitHub Actions OIDC environment unavailable")
    parsed = urllib.parse.urlsplit(request_url)
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    query = [(key, value) for key, value in query if key != "audience"] + [("audience", audience)]
    oidc_url = urllib.parse.urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, urllib.parse.urlencode(query), parsed.fragment)
    )
    req = urllib.request.Request(
        oidc_url,
        headers={"authorization": f"Bearer {request_token}", "user-agent": "socialmarket-ai-runtime/1.0"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    token = str(payload.get("value") or "").strip()
    if not token:
        raise AITaskRuntimeGatewayError("GitHub OIDC response missing token")
    return token


@dataclass
class AITaskRuntimeClient:
    endpoint: str = ""
    audience: str = DEFAULT_AUDIENCE
    timeout_seconds: float = 30.0
    token_provider: Any = None

    def __post_init__(self) -> None:
        self.endpoint = (self.endpoint or os.getenv("AI_TASK_RUNTIME_GATEWAY", DEFAULT_ENDPOINT)).rstrip("/")

    def _token(self) -> str:
        if self.token_provider:
            return str(self.token_provider())
        return github_oidc_token(self.audience)

    def post(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        req = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "authorization": "Bearer " + self._token(),
                "content-type": "application/json",
                "user-agent": "socialmarket-ai-runtime/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
                result = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise AITaskRuntimeGatewayError(f"AI task runtime gateway request failed: {exc}") from exc
        if not result.get("ok"):
            raise AITaskRuntimeGatewayError(str(result.get("error") or "AI task runtime gateway returned error"))
        return dict(result)


class SupabaseTaskCache:
    """Durable immutable-hash cache; raw prompts/evidence never leave the task worker."""

    def __init__(self, client: AITaskRuntimeClient | None = None) -> None:
        self.client = client or AITaskRuntimeClient()

    def get(self, task: AITask) -> Mapping[str, Any] | None:
        result = self.client.post(
            {
                "action": "cache_get",
                "cache_key": task.cache_key,
                "task_type": task.task_type,
                "input_hash": task.input_hash,
                "contract_hash": task.contract_hash,
            }
        )
        if not result.get("hit"):
            return None
        output = result.get("output")
        return dict(output) if isinstance(output, Mapping) else None

    def set(
        self,
        task: AITask,
        value: Mapping[str, Any],
        *,
        attempt: AITaskAttempt | None = None,
    ) -> None:
        provenance = attempt or AITaskAttempt(
            task_type=task.task_type,
            executor="deterministic",
            tier=0,
            status="ok",
            input_hash=task.input_hash,
            contract_hash=task.contract_hash,
            latency_ms=0,
            route="deterministic",
            output_hash=sha256_json(value),
        )
        self.client.post(
            {
                "action": "cache_put",
                "cache_key": task.cache_key,
                "task_type": task.task_type,
                "input_hash": task.input_hash,
                "contract_hash": task.contract_hash,
                "output": dict(value),
                "output_hash": provenance.output_hash or sha256_json(value),
                "executor": provenance.executor,
                "tier": provenance.tier,
                "route": provenance.route,
                "model": provenance.model,
            }
        )


class SupabaseTaskResultSink:
    """Persists attempts + one final result record without raw semantic payloads."""

    def __init__(self, client: AITaskRuntimeClient | None = None) -> None:
        self.client = client or AITaskRuntimeClient()

    def record(self, result: AITaskResult) -> None:
        self.client.post(
            {
                "action": "record_result",
                "task_type": result.task_type,
                "input_hash": result.input_hash,
                "contract_hash": result.contract_hash,
                "status": result.status,
                "from_cache": result.from_cache,
                "reason": result.reason,
                "attempts": [attempt.as_dict() for attempt in result.attempts],
                "output_hash": sha256_json(result.data) if result.data is not None else None,
            }
        )
