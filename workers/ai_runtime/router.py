from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol, Sequence

from task_contract import AITask, AITaskAttempt, AITaskResult, sha256_json


class TaskExecutor(Protocol):
    """Adapter contract for any local/open-weight execution runtime."""

    name: str
    tier: int

    def available(self, task: AITask) -> bool: ...

    def run(self, task: AITask) -> tuple[Mapping[str, Any] | None, Mapping[str, Any]]: ...


class TaskCache(Protocol):
    def get(self, key: str) -> Mapping[str, Any] | None: ...

    def set(self, key: str, value: Mapping[str, Any]) -> None: ...


class InMemoryTaskCache:
    """Test/dev cache. Production adapters should persist by immutable hash."""

    def __init__(self) -> None:
        self._items: dict[str, Mapping[str, Any]] = {}

    def get(self, key: str) -> Mapping[str, Any] | None:
        return self._items.get(key)

    def set(self, key: str, value: Mapping[str, Any]) -> None:
        self._items[key] = dict(value)


@dataclass
class CallableExecutor:
    """Small compatibility adapter around an existing runtime callable."""

    name: str
    tier: int
    fn: Callable[[AITask], tuple[Mapping[str, Any] | None, Mapping[str, Any]]]
    availability: Callable[[AITask], bool] | None = None

    def available(self, task: AITask) -> bool:
        return self.availability(task) if self.availability else True

    def run(self, task: AITask) -> tuple[Mapping[str, Any] | None, Mapping[str, Any]]:
        return self.fn(task)


DeterministicHandler = Callable[[AITask], Mapping[str, Any] | None]


class AITaskRouter:
    """Deterministic-first, tiered, provider-neutral and fail-closed router.

    The router owns selection and fallback. Individual business workflows submit
    a task and receive structured data or SAFE_HOLD. Executors may wrap Ollama,
    llama.cpp or any future local runtime, but provider names never appear in the
    business task contract.
    """

    def __init__(
        self,
        executors: Sequence[TaskExecutor] = (),
        *,
        deterministic_handlers: Mapping[str, DeterministicHandler] | None = None,
        cache: TaskCache | None = None,
    ) -> None:
        self.executors = tuple(sorted(executors, key=lambda x: (x.tier, x.name)))
        self.deterministic_handlers = dict(deterministic_handlers or {})
        self.cache = cache

    @staticmethod
    def _valid(task: AITask, data: Mapping[str, Any] | None) -> tuple[bool, str | None]:
        if data is None:
            return False, "empty_result"
        if not isinstance(data, Mapping):
            return False, "result_not_object"
        missing = [key for key in task.required_keys if key not in data]
        if missing:
            return False, "missing_required_keys:" + ",".join(sorted(missing))
        return True, None

    @staticmethod
    def _attempt(
        task: AITask,
        *,
        executor: str,
        tier: int,
        status: str,
        started: float,
        telemetry: Mapping[str, Any] | None = None,
        data: Mapping[str, Any] | None = None,
        error: str | None = None,
    ) -> AITaskAttempt:
        info = dict(telemetry or {})
        reserved = {"model", "route", "status", "error", "input_tokens", "output_tokens", "cost_usd"}
        safe_meta = {k: v for k, v in info.items() if k not in reserved}
        if "input_tokens" in info:
            safe_meta["input_tokens"] = int(info.get("input_tokens") or 0)
        if "output_tokens" in info:
            safe_meta["output_tokens"] = int(info.get("output_tokens") or 0)
        if "cost_usd" in info:
            safe_meta["cost_usd"] = float(info.get("cost_usd") or 0)
        return AITaskAttempt(
            task_type=task.task_type,
            executor=executor,
            tier=tier,
            status=status,
            input_hash=task.input_hash,
            contract_hash=task.contract_hash,
            latency_ms=max(0, round((time.monotonic() - started) * 1000)),
            model=str(info.get("model")) if info.get("model") else None,
            route=str(info.get("route")) if info.get("route") else None,
            output_hash=sha256_json(data) if data is not None else None,
            error=(error or (str(info.get("error")) if info.get("error") else None)),
            metadata=safe_meta,
        )

    def execute(self, task: AITask) -> AITaskResult:
        attempts: list[AITaskAttempt] = []

        # Tier 0: deterministic answer if the task can be resolved without an LLM.
        handler = self.deterministic_handlers.get(task.task_type)
        if handler is not None:
            started = time.monotonic()
            try:
                data = handler(task)
                valid, reason = self._valid(task, data)
                attempts.append(
                    self._attempt(
                        task,
                        executor="deterministic",
                        tier=0,
                        status="ok" if valid else "not_applicable",
                        started=started,
                        data=data if valid else None,
                        error=None if valid else reason,
                    )
                )
                if valid:
                    if task.cacheable and self.cache is not None:
                        self.cache.set(task.cache_key, data)
                    return AITaskResult(
                        status="ok",
                        data=data,
                        task_type=task.task_type,
                        input_hash=task.input_hash,
                        contract_hash=task.contract_hash,
                        attempts=tuple(attempts),
                    )
            except Exception as exc:
                attempts.append(
                    self._attempt(
                        task,
                        executor="deterministic",
                        tier=0,
                        status="error",
                        started=started,
                        error=str(exc)[:500],
                    )
                )

        # Immutable-result cache is checked before any generative inference.
        if task.cacheable and self.cache is not None:
            cached = self.cache.get(task.cache_key)
            valid, _ = self._valid(task, cached)
            if valid:
                return AITaskResult(
                    status="ok",
                    data=cached,
                    task_type=task.task_type,
                    input_hash=task.input_hash,
                    contract_hash=task.contract_hash,
                    attempts=tuple(attempts),
                    from_cache=True,
                )

        for executor in self.executors:
            if executor.tier <= 0 or executor.tier > task.max_tier:
                continue
            try:
                if not executor.available(task):
                    continue
            except Exception:
                continue

            started = time.monotonic()
            try:
                data, telemetry = executor.run(task)
                valid, reason = self._valid(task, data)
                attempts.append(
                    self._attempt(
                        task,
                        executor=executor.name,
                        tier=executor.tier,
                        status="ok" if valid else "invalid",
                        started=started,
                        telemetry=telemetry,
                        data=data if valid else None,
                        error=None if valid else reason,
                    )
                )
                if not valid:
                    continue
                if task.cacheable and self.cache is not None:
                    self.cache.set(task.cache_key, data)
                return AITaskResult(
                    status="ok",
                    data=data,
                    task_type=task.task_type,
                    input_hash=task.input_hash,
                    contract_hash=task.contract_hash,
                    attempts=tuple(attempts),
                )
            except Exception as exc:
                attempts.append(
                    self._attempt(
                        task,
                        executor=executor.name,
                        tier=executor.tier,
                        status="error",
                        started=started,
                        error=str(exc)[:500],
                    )
                )

        return AITaskResult(
            status="safe_hold",
            data=None,
            task_type=task.task_type,
            input_hash=task.input_hash,
            contract_hash=task.contract_hash,
            attempts=tuple(attempts),
            reason="no_validated_execution_route_produced_a_valid_result",
        )
