import unittest

import affiliate_night_brain as nb


class NightBrainPolicyTests(unittest.TestCase):
    def test_runtime_policy_defaults(self):
        p = nb._cfg({'night_brain': {}})
        self.assertEqual(p['top_n'], 100)
        self.assertEqual(p['winner_target'], 55)
        self.assertEqual(p['opportunity_target'], 30)
        self.assertEqual(p['must_buy_target'], 15)
        self.assertEqual(p['max_per_merchant'], 8)
        self.assertEqual(p['max_per_category'], 15)

    def test_portfolio_completes_with_soft_mix_and_diversity(self):
        policy = nb._cfg({'night_brain': {}})
        rows = []
        segments = ['WINNER'] * 70 + ['OPPORTUNITY'] * 45 + ['MUST_BUY'] * 25
        for i, segment in enumerate(segments):
            rows.append({
                'source_record_hash': f'h{i}',
                'merchant_id': f'm{i % 24}',
                'merchant_name': f'Merchant {i % 24}',
                '_top_category': f'category-{i % 18}',
                '_strategy_segment': segment,
                'rank_score': 100 - i * .1,
                'ai_confidence': 80,
                'expected_commission_eur': 10 + (i % 10),
                'evidence_summary': {},
            })
        selected, stats = nb.portfolio_select(rows, policy)
        self.assertEqual(len(selected), 100)
        self.assertGreaterEqual(stats['renewal_count'], 25)
        self.assertLessEqual(max(
            sum(1 for r in selected if r['merchant_id'] == merchant)
            for merchant in {r['merchant_id'] for r in selected}
        ), policy['max_per_merchant'])

    def test_commission_is_not_used_as_portfolio_sort_override(self):
        policy = nb._cfg({'night_brain': {}})
        rows = [
            {'source_record_hash':'better','merchant_id':'m1','_top_category':'a','_strategy_segment':'WINNER','rank_score':90,'ai_confidence':80,'expected_commission_eur':10,'evidence_summary':{}},
            {'source_record_hash':'bigger-commission','merchant_id':'m2','_top_category':'b','_strategy_segment':'WINNER','rank_score':70,'ai_confidence':80,'expected_commission_eur':100,'evidence_summary':{}},
        ]
        selected, _ = nb.portfolio_select(rows, {**policy, 'top_n':100})
        self.assertEqual(selected[0]['source_record_hash'], 'better')


if __name__ == '__main__':
    unittest.main()
