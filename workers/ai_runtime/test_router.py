import unittest

from router import AITaskRouter, CallableExecutor, InMemoryTaskCache
from task_contract import AITask


class FakeExecutor:
    def __init__(self, name, tier, result=None, telemetry=None, error=None, available=True):
        self.name = name
        self.tier = tier
        self.result = result
        self.telemetry = telemetry or {}
        self.error = error
        self.is_available = available
        self.calls = 0

    def available(self, task):
        return self.is_available

    def run(self, task):
        self.calls += 1
        if self.error:
            raise RuntimeError(self.error)
        return self.result, self.telemetry


def task(**overrides):
    values = {
        "task_type": "product_fit",
        "role": "Product Solution Analyst",
        "instructions": "Judge only supplied evidence.",
        "payload": {"product": "p1", "pain": "x"},
        "required_keys": ("decision", "confidence"),
    }
    values.update(overrides)
    return AITask(**values)


class AITaskRouterTests(unittest.TestCase):
    def test_deterministic_result_short_circuits_models(self):
        model = FakeExecutor("local-small", 1, {"decision": "yes", "confidence": 90})
        router = AITaskRouter(
            [model],
            deterministic_handlers={
                "product_fit": lambda _: {"decision": "no", "confidence": 100}
            },
        )
        result = router.execute(task())
        self.assertTrue(result.ok)
        self.assertEqual(result.data["decision"], "no")
        self.assertEqual(model.calls, 0)
        self.assertEqual(result.attempts[0].executor, "deterministic")

    def test_invalid_small_model_escalates_to_stronger_tier(self):
        small = FakeExecutor("local-small", 1, {"decision": "yes"}, {"model": "small"})
        strong = FakeExecutor(
            "local-strong",
            2,
            {"decision": "yes", "confidence": 84},
            {"model": "strong", "route": "local"},
        )
        result = AITaskRouter([strong, small]).execute(task())
        self.assertTrue(result.ok)
        self.assertEqual(small.calls, 1)
        self.assertEqual(strong.calls, 1)
        self.assertEqual([x.status for x in result.attempts], ["invalid", "ok"])

    def test_cache_prevents_repeat_inference(self):
        cache = InMemoryTaskCache()
        model = FakeExecutor(
            "local-small", 1, {"decision": "yes", "confidence": 77}, {"model": "small"}
        )
        router = AITaskRouter([model], cache=cache)
        first = router.execute(task())
        second = router.execute(task())
        self.assertTrue(first.ok)
        self.assertTrue(second.ok)
        self.assertFalse(first.from_cache)
        self.assertTrue(second.from_cache)
        self.assertEqual(model.calls, 1)

    def test_input_change_invalidates_cache(self):
        cache = InMemoryTaskCache()
        model = FakeExecutor(
            "local-small", 1, {"decision": "yes", "confidence": 77}, {"model": "small"}
        )
        router = AITaskRouter([model], cache=cache)
        router.execute(task())
        router.execute(task(payload={"product": "p2", "pain": "x"}))
        self.assertEqual(model.calls, 2)

    def test_task_max_tier_blocks_unapproved_escalation(self):
        strong = FakeExecutor(
            "local-strong", 2, {"decision": "yes", "confidence": 99}, {"model": "strong"}
        )
        result = AITaskRouter([strong]).execute(task(max_tier=1))
        self.assertTrue(result.safe_hold)
        self.assertEqual(strong.calls, 0)

    def test_all_routes_fail_closed(self):
        small = FakeExecutor("local-small", 1, error="runtime down")
        strong = FakeExecutor("local-strong", 2, {"unexpected": True})
        result = AITaskRouter([small, strong]).execute(task())
        self.assertTrue(result.safe_hold)
        self.assertIsNone(result.data)
        self.assertEqual(len(result.attempts), 2)
        self.assertEqual(result.reason, "no_validated_execution_route_produced_a_valid_result")

    def test_unavailable_route_is_skipped(self):
        unavailable = FakeExecutor(
            "local-small", 1, {"decision": "yes", "confidence": 50}, available=False
        )
        fallback = FakeExecutor(
            "local-strong", 2, {"decision": "yes", "confidence": 82}, {"model": "strong"}
        )
        result = AITaskRouter([unavailable, fallback]).execute(task())
        self.assertTrue(result.ok)
        self.assertEqual(unavailable.calls, 0)
        self.assertEqual(fallback.calls, 1)

    def test_callable_adapter_supports_existing_runtime(self):
        adapter = CallableExecutor(
            name="compat-local",
            tier=1,
            fn=lambda _: (
                {"decision": "hold", "confidence": 71},
                {"route": "local", "model": "compat"},
            ),
        )
        result = AITaskRouter([adapter]).execute(task())
        self.assertTrue(result.ok)
        self.assertEqual(result.attempts[-1].model, "compat")
        self.assertEqual(result.attempts[-1].route, "local")


if __name__ == "__main__":
    unittest.main()
