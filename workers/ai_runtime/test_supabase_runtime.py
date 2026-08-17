from __future__ import annotations

import unittest

from supabase_runtime import SupabaseTaskCache, SupabaseTaskResultSink
from task_contract import AITask, AITaskAttempt, AITaskResult


class FakeClient:
    def __init__(self, responses=None):
        self.responses = list(responses or [])
        self.calls = []

    def post(self, payload):
        self.calls.append(dict(payload))
        return self.responses.pop(0) if self.responses else {"ok": True}


def task():
    return AITask(
        task_type="category_pain_audit",
        role="Skeptic",
        instructions="Use bounded evidence only.",
        payload={"evidence_ids": ["e1", "e2"]},
        required_keys=("clusters",),
    )


class SupabaseRuntimeTests(unittest.TestCase):
    def test_cache_get_uses_hashes_not_raw_payload(self):
        client = FakeClient([{"ok": True, "hit": True, "output": {"clusters": []}}])
        cache = SupabaseTaskCache(client)
        t = task()
        out = cache.get(t)
        self.assertEqual(out, {"clusters": []})
        call = client.calls[0]
        self.assertEqual(call["action"], "cache_get")
        self.assertEqual(call["input_hash"], t.input_hash)
        self.assertNotIn("payload", call)
        self.assertNotIn("instructions", call)

    def test_cache_put_includes_provenance_without_raw_task(self):
        client = FakeClient()
        cache = SupabaseTaskCache(client)
        t = task()
        attempt = AITaskAttempt(
            task_type=t.task_type,
            executor="local-tier2",
            tier=2,
            status="ok",
            input_hash=t.input_hash,
            contract_hash=t.contract_hash,
            latency_ms=101,
            model="qwen-test",
            route="local_ollama",
            output_hash="a" * 64,
        )
        cache.set(t, {"clusters": []}, attempt=attempt)
        call = client.calls[0]
        self.assertEqual(call["executor"], "local-tier2")
        self.assertEqual(call["model"], "qwen-test")
        self.assertNotIn("payload", call)
        self.assertNotIn("instructions", call)

    def test_result_sink_records_safe_hold_even_without_output(self):
        client = FakeClient()
        sink = SupabaseTaskResultSink(client)
        t = task()
        result = AITaskResult(
            status="safe_hold",
            data=None,
            task_type=t.task_type,
            input_hash=t.input_hash,
            contract_hash=t.contract_hash,
            attempts=(),
            reason="no_validated_execution_route_produced_a_valid_result",
        )
        sink.record(result)
        call = client.calls[0]
        self.assertEqual(call["action"], "record_result")
        self.assertEqual(call["status"], "safe_hold")
        self.assertIsNone(call["output_hash"])
        self.assertEqual(call["attempts"], [])


if __name__ == "__main__":
    unittest.main()
