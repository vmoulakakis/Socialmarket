import json
import tempfile
import unittest
from pathlib import Path
from all_feed_opportunity_discovery import amount,scan,score_product,normalize_signals,FLOOR

def product(pid,price,stock=None,times_bought=None,route=23,name="Water leak sensor"):
    return {
        "product_id":pid,"product_name":name,"price":price,
        "category":"Home sensors","tracking_url":f"https://go.linkwi.se/z/{route}-0/CD104/?lnkurl=https%3A%2F%2Fexample.com%2Fitem%2F{pid}",
        "image_url":"https://example.com/sample.jpg",
        "in_stock":stock,"times_bought":times_bought
    }

class DiscoveryContractTests(unittest.TestCase):
    def test_conservative_commission_and_unknown(self):
        self.assertEqual(amount(200,{"percent_commission_min":10})[0],20)
        self.assertEqual(amount(200,{"flat_commission_min_eur":12,"percent_commission_min":10})[0],12)
        self.assertEqual(amount(200,{"percent_commission_min":None})[0],None)
    def test_only_eur15_filters_research_stock_unknown_accepted(self):
        rows=[
           product("1",160,None),product("2",149,False),
           product("3",150,False),
           product("4",500,True,route=399),
           product("5",999,None,route=23),
        ]
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"feed.json"
            p.write_text(json.dumps(rows),encoding="utf-8")
            found=scan(p,{"23":{"percent_commission_min":10,"source":"historical"}},{},top=30)
            self.assertEqual(found["counts"]["scanned"],5)
            self.assertEqual(found["counts"]["commission_eligible"],3)
            self.assertEqual(found["counts"]["below_15"],1)
            self.assertEqual(found["counts"]["commission_unknown"],1)
            by_id={x["source_product_id"]:x for x in found["products"]}
            self.assertEqual(set(by_id),{"1","3","5"})
            self.assertEqual(by_id["1"]["stock_state"],"unknown")
            self.assertEqual(by_id["3"]["stock_state"],"out_of_stock")
            self.assertTrue(all(p["calculated_commission_eur"]>=FLOOR for p in found["products"]))
    def test_no_fake_demand_conversion_or_competition(self):
        out=score_product({"product_name":"Soil sensor","category_raw":"agriculture","times_bought":None},{})
        self.assertEqual(out["evidence_coverage"],0)
        self.assertEqual(out["components"]["demand"],None)
        self.assertEqual(out["components"]["conversion"],None)
        self.assertEqual(out["evidence_level"],"hypothesis_only")
    def test_real_independent_evidence_ranks_better(self):
        evidence=normalize_signals({"soil":{"pain_fit":90,"demand":95,"competition":12,"conversion":80,"source_kind":"independent_observation","evidence_refs":["https://research.example/soil"]}})
        researched=score_product({"product_name":"soil moisture sensor","times_bought":None},evidence)
        unknown=score_product({"product_name":"other random product","times_bought":None},evidence)
        self.assertGreater(researched["opportunity_score"],unknown["opportunity_score"])
        self.assertEqual(researched["evidence_level"],"source_observed")
        self.assertEqual(researched["components"]["low_competition"],88)
    def test_conversion_feed_buy_count_is_not_observed_affiliate_cvr(self):
        out=score_product({"product_name":"product","times_bought":150},{})
        self.assertIsNotNone(out["components"]["conversion"])
        self.assertIn("feed:times_bought_proxy_not_CVR",out["evidence_refs"])
        self.assertEqual(out["evidence_level"],"hypothesis_only")

if __name__=="__main__":unittest.main()
