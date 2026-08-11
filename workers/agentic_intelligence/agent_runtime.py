import json
from typing import Any

from model_router import BASE_URL, FreeModelRouter


class FreeAgentRuntime:
    """Real OpenAI Agents SDK agents running on GitHub Models free quota.

    The orchestration framework is OpenAI Agents SDK, but the model endpoint is
    GitHub Models and the router excludes OpenAI and DeepSeek publishers. If the
    free model path is unavailable, callers fall back to deterministic logic;
    this class never invokes paid providers.
    """

    def __init__(self, router: FreeModelRouter):
        self.router = router

    def run_json(self, name: str, instructions: str, payload: Any) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        if not self.router.available:
            return None, {"route": "github_models_free", "status": "unavailable_or_cap"}
        model_id = self.router.discover_model()
        if not model_id:
            return None, {"route": "github_models_free", "status": "no_model"}

        with self.router._lock:
            if not self.router.available:
                return None, {"route": "github_models_free", "status": "cap"}
            self.router.calls += 1
            call_no = self.router.calls

        try:
            from agents import Agent, OpenAIChatCompletionsModel, Runner, set_tracing_disabled
            from openai import AsyncOpenAI

            set_tracing_disabled(True)
            client = AsyncOpenAI(api_key=self.router.token, base_url=BASE_URL)
            model = OpenAIChatCompletionsModel(model=model_id, openai_client=client)
            agent = Agent(
                name=name,
                instructions=(
                    instructions
                    + "\nNever invent sources, observations, numbers, competitors, features or evidence. "
                    + "Use only the supplied payload. Return strict JSON only."
                ),
                model=model,
            )
            result = Runner.run_sync(agent, json.dumps(payload, ensure_ascii=False), max_turns=2)
            text = str(result.final_output or "").strip()
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
                "model": model_id,
                "call_no": call_no,
                "cost_usd": 0,
                "runtime": "openai_agents_sdk",
            }
        except Exception as exc:
            # The direct free endpoint is a compatibility fallback, not a paid
            # fallback. It consumes one more free call only if quota remains.
            fallback, telemetry = self.router.complete_json(instructions, payload)
            telemetry["agents_sdk_error"] = str(exc)[:300]
            telemetry["runtime"] = "direct_github_models_fallback"
            return fallback, telemetry
