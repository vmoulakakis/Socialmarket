import unittest

from product_ranking_v3 import deterministic_metrics, kpi_snapshot, product_attributes
import product_ranking_v32 as v32


class RankingV3Tests(unittest.TestCase):
    def item(self, *, commission=15, demand=70, competition=40, pains=None, deep_score=0, program_score=None, program_confidence=None):
        return {
            '_raw': {'expected_commission_eur': commission, 'discount_pct': 10, 'times_bought': 5},
            'merchant': {'demand_score': demand, 'competition_score': competition, 'solution_whitespace_score': 65, 'trust_score': 80},
            '_pains': pains or [],
            '_themes': [],
            '_deep_demand': {'matched': deep_score > 0, 'score': deep_score, 'status': 'completed' if deep_score > 0 else 'unavailable'},
            '_program_kpi': {'commercial_score': program_score, 'data_confidence': program_confidence} if program_score is not None else {},
            '_first_party_kpi': {},
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

    def test_network_commercial_evidence_improves_deterministic_rank(self):
        without_network = deterministic_metrics(self.item(program_score=None))
        with_network = deterministic_metrics(self.item(program_score=88, program_confidence=.9))
        self.assertEqual(without_network['network_performance_score'], 0)
        self.assertGreater(with_network['network_performance_score'], 80)
        self.assertGreater(with_network['deterministic_rank_score'], without_network['deterministic_rank_score'])

    def test_kpi_snapshot_separates_observed_and_modeled_metrics(self):
        item = self.item(commission=20, program_score=80, program_confidence=.9)
        item['_program_kpi'].update({'conversion_rate': 4, 'epc': 0.75, 'approval_rate': 80, 'approval_days': 10, 'observed_at': '2026-08-16T00:00:00Z'})
        item['_first_party_kpi'] = {'impressions': 1000, 'outbound_clicks': 50, 'conversions_approved': 2, 'commission_approved_eur': 40, 'media_spend_eur': 10, 'content_cost_eur': 0}
        snap = kpi_snapshot(item)
        self.assertEqual(snap['network_baseline']['status'], 'observed_program_baseline')
        self.assertEqual(snap['modeled_product_economics']['expected_approved_commission_per_100_clicks_eur'], 64)
        self.assertEqual(snap['modeled_product_economics']['break_even_cpc_eur'], .64)
        self.assertEqual(snap['first_party_30d']['approved_cvr_pct'], 4)
        self.assertEqual(snap['first_party_30d']['epc_eur'], .8)
        self.assertEqual(snap['first_party_30d']['roi_pct'], 300)

    def test_product_attributes_preserve_feed_facts(self):
        attrs = product_attributes({'description': 'Original', 'colour': 'Black', 'size': 'L', 'gtin': '123', 'extra_images': ['https://a', 'https://b'], 'extra_json': {'material': 'cotton'}})
        self.assertEqual(attrs['original_description'], 'Original')
        self.assertEqual(attrs['colour'], 'Black')
        self.assertEqual(attrs['extra_attributes']['material'], 'cotton')

    def test_failed_large_ai_batch_is_recovered_by_split_retry(self):
        original = v32._run_ai_batch_once
        try:
            def fake_once(batch):
                if len(batch) > 2: raise RuntimeError('simulated structured-output failure')
                return {str(x['product']['source_record_hash']): {'ranking': {'ok': True}, 'audit': {}} for x in batch}
            v32._run_ai_batch_once = fake_once
            batch = [{'product': {'source_record_hash': f'p{i}'}} for i in range(8)]
            output, failed, splits = v32._run_ai_batch_resilient(batch)
            self.assertEqual(len(output), 8);self.assertEqual(failed, 0);self.assertGreaterEqual(splits, 3)
        finally:v32._run_ai_batch_once = original

    def test_failed_large_seo_batch_is_recovered_by_split_retry(self):
        original = v32._run_seo_batch_once
        try:
            def fake_once(batch):
                if len(batch) > 2: raise RuntimeError('simulated SEO JSON failure')
                return {str(x['source_record_hash']): {'source_record_hash': x['source_record_hash'], 'title': 'ok'} for x in batch}
            v32._run_seo_batch_once = fake_once
            batch = [{'source_record_hash': f'p{i}'} for i in range(8)]
            output, failed, splits = v32._run_seo_batch_resilient(batch)
            self.assertEqual(len(output), 8);self.assertEqual(failed, 0);self.assertGreaterEqual(splits, 3)
        finally:v32._run_seo_batch_once = original


if __name__ == '__main__':
    unittest.main()
