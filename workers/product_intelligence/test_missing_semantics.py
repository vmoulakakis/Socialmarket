import unittest

from product_agents import final_opportunity_score


class MissingMetricSemanticsTests(unittest.TestCase):
    def test_missing_competition_is_preserved_and_inverse_bonus_withheld(self):
        common = dict(
            pain_gap_fit=85,
            merchant_opportunity=75,
            greek_demand=80,
            seasonal_theme=50,
            merchant_trust=85,
            expected_commission=25,
            discount=15,
            evidence_confidence=82,
        )
        observed_score, observed = final_opportunity_score(competition=20, **common)
        missing_score, missing = final_opportunity_score(competition=None, **common)

        self.assertEqual(observed['competition_score'], 20.0)
        self.assertIsNone(missing['competition_score'])
        self.assertTrue(missing['competition_inverse_bonus_withheld'])
        self.assertIn('competition_score', missing['missing_components'])
        self.assertGreater(observed_score, missing_score)

    def test_missing_competition_does_not_equal_zero_competition(self):
        common = dict(
            pain_gap_fit=80,
            merchant_opportunity=70,
            greek_demand=75,
            seasonal_theme=40,
            merchant_trust=80,
            expected_commission=20,
            discount=10,
            evidence_confidence=80,
        )
        missing_score, _ = final_opportunity_score(competition=None, **common)
        zero_score, _ = final_opportunity_score(competition=0, **common)
        self.assertGreater(zero_score, missing_score)


if __name__ == '__main__':
    unittest.main()
