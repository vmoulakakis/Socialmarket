import unittest
from product_agents import parse_commission_rule,commission_score,canonical_key,final_opportunity_score
from stream_feed import normalize,target_domain,linkwise_route
from product_intelligence_v1 import merchant_maps,resolve_merchant
from product_safety import classify_price_sample,price_integrity_allows


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

    def test_real_linkwise_url_extracts_destination_and_route(self):
        url='https://go.linkwi.se/z/205-0/CD104/?lnkurl=https%3A%2F%2Fwww.xenodoxeio.gr%2Fprosfores%2Fdeal%2Fsample%3Fafn%3DLW'
        self.assertEqual(target_domain(url),'xenodoxeio.gr')
        self.assertEqual(linkwise_route(url),'205-0/CD104')
        p=normalize({'product_id':'1','product_name':'Test','tracking_url':url,'price':'400','image_url':'https://www.xenodoxeio.gr/a.jpg'})
        self.assertEqual(p['target_domain'],'xenodoxeio.gr')
        self.assertIsNone(p['program_name'])

    def test_resolver_uses_authoritative_domain_before_name(self):
        row={
          'merchant_program_id':'program-1','merchant_id':'merchant-1','program_name':'Xenodoxeio',
          'canonical_name':'Xenodoxeio','official_domain':'xenodoxeio.gr','aliases':[]
        }
        by_program,aliases,by_domain=merchant_maps({'programs':[row]})
        merchant,method=resolve_merchant({'target_domain':'www.xenodoxeio.gr','program_name':None},by_program,aliases,by_domain)
        self.assertEqual(merchant['merchant_id'],'merchant-1')
        self.assertEqual(method,'target_domain_exact')

    def test_resolver_does_not_use_broad_fuzzy_name_matching(self):
        row={
          'merchant_program_id':'program-1','merchant_id':'merchant-1','program_name':'Unique Shop',
          'canonical_name':'Unique Shop','official_domain':'unique-shop.gr','aliases':[]
        }
        by_program,aliases,by_domain=merchant_maps({'programs':[row]})
        merchant,method=resolve_merchant({'target_domain':None,'program_name':'Unique'},by_program,aliases,by_domain)
        self.assertIsNone(merchant)
        self.assertIsNone(method)

    def test_price_integrity_quarantines_minor_unit_pattern(self):
        info=classify_price_sample([3501+i for i in range(30)])
        self.assertEqual(info['status'],'minor_unit_risk')
        ok,reason,_=price_integrity_allows(3501,{'price_integrity':info})
        self.assertFalse(ok)
        self.assertEqual(reason,'price_scale_unverified')

    def test_price_integrity_allows_plausible_major_units(self):
        info=classify_price_sample([19.99,25.5,40.0,75.9,120.0]*5)
        self.assertEqual(info['status'],'major_unit_probable')
        ok,reason,_=price_integrity_allows(120,{'price_integrity':info})
        self.assertTrue(ok)
        self.assertEqual(reason,'price_major_unit_probable')


if __name__=='__main__':unittest.main()
