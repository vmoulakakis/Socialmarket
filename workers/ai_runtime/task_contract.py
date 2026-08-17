from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Mapping


ROUTER_CONTRACT_VERSION = "autopilot-ai-task-v1"


def _stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def sha256_json(value: Any) -> str:
    return hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AITask:
    """Provider-neutral unit of semantic work.

    Tasks contain only bounded evidence/context prepared by deterministic code.
    The router decides which execution tier/model to use; callers never select a
    provider. A task cannot override owner hard gates or write production state.
    """

    task_type: str
    role: str
    instructions: str
    payload: Mapping[str, Any]
    required_keys: tuple[str, ...] = ()
    prompt_version: str = "v1"
    max_tier: int = 3
    cacheable: bool = True
    material_change_capable: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.task_type.strip():
            raise ValueError("task_type is required")
        if not self.role.strip():
            raise ValueError("role is required")
        if not self.instructions.strip():
            raise ValueError("instructions are required")
        if self.max_tier < 0:
            raise ValueError("max_tier must be >= 0")

    @property
    def input_hash(self) -> str:
        return sha256_json(self.payload)

    @property
    def contract_hash(self) -> str:
        return sha256_json(
            {
                "contract_version": ROUTER_CONTRACT_VERSION,
                "task_type": self.task_type,
                "role": self.role,
                "instructions": self.instructions,
                "required_keys": self.required_keys,
                "prompt_version": self.prompt_version,
                "max_tier": self.max_tier,
            }
        )

    @property
    def cache_key(self) -> str:
        return sha256_json(
            {
                "contract": self.contract_hash,
                "input": self.input_hash,
            }
        )


@dataclass(frozen=True)
class AITaskAttempt:
    task_type: str
    executor: str
    tier: int
    status: str
    input_hash: str
    contract_hash: str
    latency_ms: int
    model: str | None = None
    route: str | None = None
    output_hash: str | None = None
    error: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "task_type": self.task_type,
            "executor": self.executor,
            "tier": self.tier,
            "status": self.status,
            "input_hash": self.input_hash,
            "contract_hash": self.contract_hash,
            "latency_ms": self.latency_ms,
            "model": self.model,
            "route": self.route,
            "output_hash": self.output_hash,
            "error": self.error,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class AITaskResult:
    status: str
    data: Mapping[str, Any] | None
    task_type: str
    input_hash: str
    contract_hash: str
    attempts: tuple[AITaskAttempt, ...] = ()
    from_cache: bool = False
    reason: str | None = None

    @property
    def ok(self) -> bool:
        return self.status == "ok" and self.data is not None

    @property
    def safe_hold(self) -> bool:
        return self.status == "safe_hold"
