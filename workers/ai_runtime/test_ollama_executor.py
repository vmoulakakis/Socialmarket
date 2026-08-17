from __future__ import annotations

import unittest

from ollama_executor import OllamaExecutor
from task_contract import AITask


class FakeOllamaExecutor(OllamaExecutor):
    def __init__(self, responses):
        super().__init__(name="fake", tier=1, model="qwen-test", endpoint="http://local.invalid")
        self.responses = list(responses)

    def _request_json(self, path, payload=None):
        del path, payload
        if not self.responses:
            raise AssertionError("unexpected Ollama request")
        return self.responses.pop(0)


class OllamaExecutorTests(unittest.TestCase):
    def task(self):
        return AITask(
            task_type="unit_test",
            role="Test Skeptic",
            instructions="Return the supplied fact only.",
            payload={"fact": "grounded"},
            required_keys=("verdict",),
        )

    def test_available_requires_model_tag(self):
        executor = FakeOllamaExecutor([
            {"models": [{"name": "qwen-test"}]},
        ])
        self.assertTrue(executor.available(self.task()))

    def test_run_returns_structured_json_and_zero_cost(self):
        executor = FakeOllamaExecutor([
            {
                "message": {"content": '{"verdict":"VALIDATED"}'},
                "prompt_eval_count": 12,
                "eval_count": 3,
                "total_duration": 9000,
            }
        ])
        data, telemetry = executor.run(self.task())
        self.assertEqual(data["verdict"], "VALIDATED")
        self.assertEqual(telemetry["cost_usd"], 0)
        self.assertEqual(telemetry["route"], "local_ollama")
        self.assertFalse(telemetry["thinking"])

    def test_invalid_model_json_fails_closed(self):
        executor = FakeOllamaExecutor([
            {"message": {"content": "not-json"}},
        ])
        with self.assertRaises(RuntimeError):
            executor.run(self.task())


if __name__ == "__main__":
    unittest.main()
