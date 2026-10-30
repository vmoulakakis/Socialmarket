import unittest
from workers.product_intelligence.socialmarket_model_router import select_model
class ModelRouterTests(unittest.TestCase):
 def test_all_feed_operations_are_deterministic(self):
  for t in ('feed_delta','identity','commission'):
   d=select_model(task=t,confidence=0.1,source_count=100,independent_verified_sources=100)
   self.assertEqual(d.tier,'sql_rules')
   self.assertFalse(d.charges_remote_tokens)
 def test_embedding_is_local(self):
  d=select_model(task='semantic_matching')
  self.assertEqual(d.tier,'cpu_embedding')
  self.assertFalse(d.charges_remote_tokens)
 def test_unverified_research_does_not_spend(self):
  d=select_model(task='greek_market_research',source_count=10,independent_verified_sources=0,
                 contradictory_evidence=True)
  self.assertEqual(d.tier,'evidence_queue')
 def test_verified_clear_research_no_llm(self):
  d=select_model(task='greek_market_research',source_count=5,
   independent_verified_sources=3,confidence=.91)
  self.assertEqual(d.tier,'sql_graph')
 def test_real_contradictions_escalate(self):
  d=select_model(task='contradiction_review',source_count=4,
   independent_verified_sources=2,confidence=.5,contradictory_evidence=True)
  self.assertEqual(d.tier,'remote_bounded')
  self.assertTrue(d.charges_remote_tokens)
 def test_local_small_only_if_validated(self):
  a=select_model(task='category_tagging',confidence=.3,local_model_validated=False)
  b=select_model(task='category_tagging',confidence=.3,local_model_validated=True)
  self.assertEqual(a.tier,'evidence_queue')
  self.assertEqual(b.tier,'local_small')
 def test_high_impact_policy_review_does_not_remote_autodecide(self):
  d=select_model(task='compliance_review',source_count=3,independent_verified_sources=3,
   contradictory_evidence=True,hard_policy_question=True)
  self.assertTrue(d.requires_approval)
  self.assertFalse(d.charges_remote_tokens)
if __name__=='__main__':
 unittest.main()
