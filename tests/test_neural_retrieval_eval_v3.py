import unittest
from workers.product_intelligence.neural_retrieval_eval_v3 import evaluate, dot, DIMENSIONS, FIXTURES
class MockEncoder:
 def encode(self, rows, normalize_embeddings=True):
  assert normalize_embeddings
  n=len(rows)//3
  e=[]
  for i,x in enumerate(rows):
   z=[0.0]*DIMENSIONS
   z[i%n]=1.0 if i<2*n else -1.0
   e.append(z)
  return e
class NeuralEvaluationContract(unittest.TestCase):
 def test_positive_pair_baseline_mock(self):
  r=evaluate(MockEncoder())
  self.assertEqual(r['pair_recall_at_1'],1.0)
  self.assertEqual(r['evaluation_type'],'synthetic_smoke_only')
  self.assertTrue(r['not_production_quality_proof'])
 def test_query_variants_present(self):
  q=[x[0] for x in FIXTURES]
  self.assertTrue(any('pos na' in s for s in q))
  self.assertTrue(any('how do' in s for s in q))
 def test_no_short_vectors(self):
  with self.assertRaises(ValueError):dot([1.0],[1.0,0.0])
 def test_empty_gold_not_allowed(self):
  with self.assertRaises(ValueError):evaluate(MockEncoder(),[])
if __name__=="__main__":
 unittest.main()
