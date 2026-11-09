import unittest

from unittest.mock import patch
from model_router import adaptive_reasoning_policy, routing_plan, FreeModelRouter, configured_free_provider


class ModelRoutingPolicyTests(unittest.TestCase):
    def test_simple_case_uses_flash_without_thinking(self):
        decision=adaptive_reasoning_policy('label',complexity=.20,confidence=.9)
        self.assertEqual(decision['model'],'deepseek-v4-flash')
        self.assertFalse(decision['thinking'])

    def test_hard_skeptic_case_uses_pro_max(self):
        decision=adaptive_reasoning_policy('forecast_skeptic',complexity=.75,confidence=.4,contradiction_count=2)
        self.assertEqual(decision['model'],'deepseek-v4-pro')
        self.assertEqual(decision['reasoning_effort'],'max')

    def test_paid_routes_are_blocked_without_cost_approval(self):
        plan=routing_plan('audit',complexity=.8,paid_approved=False)
        self.assertEqual([x['route'] for x in plan[:2]],['deterministic_or_local','verified_free_tier_provider'])
        self.assertEqual(plan[-1]['status'],'blocked_pending_cost_approval')
        self.assertNotIn('deepseek_official_api',[x['route'] for x in plan])

    def test_openai_is_last_after_deepseek_when_paid_approved(self):
        plan=routing_plan('audit',complexity=.9,paid_approved=True)
        self.assertEqual(plan[-2]['route'],'deepseek_official_api')
        self.assertEqual(plan[-1]['route'],'openai_api_last_resort')


    def test_missing_free_keys_fails_closed(self):
        with patch.dict('os.environ', {}, clear=True):
            router = FreeModelRouter()
            self.assertFalse(router.available)
            result, meta = router.complete_json('test', {'ok': True})
            self.assertIsNone(result)
            self.assertEqual(meta['status'], 'unavailable_or_cap')

    def test_only_confirmed_groq_free_tier_is_eligible(self):
        self.assertIsNone(configured_free_provider({'GROQ_API_KEY': 'fake'}))
        cfg = configured_free_provider({'GROQ_API_KEY': 'fake', 'GROQ_FREE_TIER_CONFIRMED': 'true'})
        self.assertEqual(cfg['provider'], 'groq')

    def test_openrouter_is_forced_to_free_router(self):
        cfg = configured_free_provider({'OPENROUTER_API_KEY': 'fake'})
        self.assertEqual(cfg['model'], 'openrouter/free')


if __name__=='__main__':
    unittest.main()
