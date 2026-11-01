import unittest
import torch
from models.neural_solution_matcher_v3 import NeuralSolutionMatcher,assert_training_eligible

class NeuralTwoTowerTests(unittest.TestCase):
 def test_architecture_and_gradients(self):
  net=NeuralSolutionMatcher()
  p=torch.randn(4,384); products=torch.randn(4,384)
  matrix=net(p,products)
  self.assertEqual(tuple(matrix.shape),(4,4))
  loss=net.contrastive_loss(p,products)
  self.assertTrue(torch.isfinite(loss))
  loss.backward()
  self.assertTrue(any(x.grad is not None for x in net.parameters()))
 def test_untrained_model_not_allowed_on_current_0_verified_pairs(self):
  with self.assertRaisesRegex(RuntimeError,'insufficient'):
   assert_training_eligible(0,0,0,0)
 def test_sufficient_evidence_policy(self):
  self.assertTrue(assert_training_eligible(120,25,100,3))
 def test_dimension_mismatch(self):
  with self.assertRaisesRegex(ValueError,'dimension'):
   NeuralSolutionMatcher()(torch.randn(2,1536),torch.randn(2,384))

if __name__=='__main__':unittest.main()
