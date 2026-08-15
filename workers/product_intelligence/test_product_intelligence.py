import unittest
from product_agents import parse_commission_rule,commission_score,canonical_key,final_opportunity_score


class ProductIntelligencePolicyTests(unittest.TestCase):
    def test_exact_percentage_gate_math(self):
        r=parse_commission_rule('30,00%',None,40)
        self.assertEqual(r['commission_rule'],'percent_exact')
        self.assertAlmostEqual(r['expected_commission_eur'],12.0)

    def test_high_price_low_commission_does_not_pass_10(self):
        r=parse_commission_rule('2,00%',None,300)
        self.assertAlmostEqual(r['expected_commission_eur'],6.0)
        self.assertLess(r['expected_commission_eur'],10)

    def test_range_uses_conservative_minimum(self):
        r=parse_commission_rule('3,00% - 10,00%',None,150)
        self.assertEqual(r['commission_rule'],'percent_range_conservative_min')
        self.assertAlmostEqual(r['expected_commission_eur'],4.5)
        self.assertAlmostEqual(r['potential_commission_eur'],15.0)

    def test_flat_range_uses_conservative_minimum(self):
        r=parse_commission_rule(None,'10,00 - 25,00',99)
        self.assertAlmostEqual(r['expected_commission_eur'],10.0)
        self.assertAlmostEqual(r['potential_commission_eur'],25.0)

    def test_commission_score_has_diminishing_returns(self):
        self.assertEqual(commission_score(9.99),0)
        self.assertGreater(commission_score(20),commission_score(10))
        self.assertLess(commission_score(200)-commission_score(100),commission_score(30)-commission_score(10))

    def test_canonical_gtin_wins(self):
        a=canonical_key({'gtin':'5201234567890','product_name':'A'})
        b=canonical_key({'gtin':'5201234567890','product_name':'Completely different title'})
        self.assertEqual(a,b)

    def test_product_score_rewards_merchant_whitespace(self):
        low,_=final_opportunity_score(pain_gap_fit=80,merchant_opportunity=20,greek_demand=80,competition=40,seasonal_theme=60,merchant_trust=80,expected_commission=20,discount=20,evidence_confidence=80)
        high,_=final_opportunity_score(pain_gap_fit=80,merchant_opportunity=90,greek_demand=80,competition=40,seasonal_theme=60,merchant_trust=80,expected_commission=20,discount=20,evidence_confidence=80)
        self.assertGreater(high,low)


if __name__=='__main__':unittest.main()
