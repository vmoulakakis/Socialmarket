import unittest

from model_router import adaptive_reasoning_policy, routing_plan


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
        self.assertEqual([x['route'] for x in plan[:2]],['deterministic_or_local','github_models_included_quota'])
        self.assertEqual(plan[-1]['status'],'blocked_pending_cost_approval')
        self.assertNotIn('deepseek_official_api',[x['route'] for x in plan])

    def test_openai_is_last_after_deepseek_when_paid_approved(self):
        plan=routing_plan('audit',complexity=.9,paid_approved=True)
        self.assertEqual(plan[-2]['route'],'deepseek_official_api')
        self.assertEqual(plan[-1]['route'],'openai_api_last_resort')


if __name__=='__main__':
    unittest.main()
