import unittest

from product_ranking_v3 import deterministic_metrics
import product_ranking_v32 as v32


class RankingV3Tests(unittest.TestCase):
    def item(self, *, commission=15, demand=70, competition=40, pains=None, deep_score=0):
        return {
            '_raw': {'expected_commission_eur': commission, 'discount_pct': 10, 'times_bought': 5},
            'merchant': {'demand_score': demand, 'competition_score': competition, 'solution_whitespace_score': 65, 'trust_score': 80},
            '_pains': pains or [],
            '_themes': [],
            '_deep_demand': {'matched': deep_score > 0, 'score': deep_score, 'status': 'completed' if deep_score > 0 else 'unavailable'},
        }

    def test_missing_pain_does_not_remove_ranking_score(self):
        result = deterministic_metrics(self.item(pains=[]))
        self.assertGreater(result['deterministic_rank_score'], 0)
        self.assertEqual(result['pain_signal_score'], 0)

    def test_missing_competition_never_gets_inverse_bonus(self):
        result = deterministic_metrics(self.item(competition=None))
        self.assertIsNone(result['competition_score'])
        self.assertEqual(result['inverse_competition_score'], 0)

    def test_stronger_demand_and_commission_improve_rank(self):
        low = deterministic_metrics(self.item(commission=10, demand=35))['deterministic_rank_score']
        high = deterministic_metrics(self.item(commission=45, demand=85))['deterministic_rank_score']
        self.assertGreater(high, low)

    def test_supported_pain_is_bonus_not_gate(self):
        no_pain = deterministic_metrics(self.item(pains=[]))['deterministic_rank_score']
        with_pain = deterministic_metrics(self.item(pains=[{
            'retrieval_score': 90, 'pain_severity': 85, 'demand_score': 80, 'commercial_intent': 90
        }]))['deterministic_rank_score']
        self.assertGreater(with_pain, no_pain)

    def test_deep_demand_is_additive_context_not_a_gate(self):
        without_lab = deterministic_metrics(self.item(deep_score=0))
        with_lab = deterministic_metrics(self.item(deep_score=88))
        self.assertEqual(without_lab['deep_demand_score'], 0)
        self.assertGreater(without_lab['deterministic_rank_score'], 0)
        self.assertGreater(with_lab['deterministic_rank_score'], without_lab['deterministic_rank_score'])

    def test_failed_large_ai_batch_is_recovered_by_split_retry(self):
        original = v32._run_ai_batch_once
        try:
            def fake_once(batch):
                if len(batch) > 2:
                    raise RuntimeError('simulated structured-output failure')
                return {
                    str(x['product']['source_record_hash']): {'ranking': {'ok': True}, 'audit': {}}
                    for x in batch
                }
            v32._run_ai_batch_once = fake_once
            batch = [{'product': {'source_record_hash': f'p{i}'}} for i in range(8)]
            output, failed, splits = v32._run_ai_batch_resilient(batch)
            self.assertEqual(len(output), 8)
            self.assertEqual(failed, 0)
            self.assertGreaterEqual(splits, 3)
        finally:
            v32._run_ai_batch_once = original


if __name__ == '__main__':
    unittest.main()
