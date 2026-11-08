"""Contract tests: only EUR15 is an INITIAL economic hard gate."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))

from commission15_opportunity_engine import (
 BoundedPortfolio,estimate_commission,passes_initial_gate,
 build_pain_index,best_problem,score_candidate
)
from linkwise_commission15_discovery import pool_candidates,parse_route,parse_record

TRACK="https://go.linkwi.se/z/23-0/CD104/?lnkurl=https%3A%2F%2Fwww.laredoute.gr%2Ffurniture"
TERMS={"23":{"linkwise_program_id":"23","percent_commission_min":10,
            "source":"historical_catalog","imported_at":"2026-09-17"}}
PROBLEMS=[{"id":"11b7d1d0-e3c8-4c23-ad32-f9eaa866a9ae","problem_key":"home-storage",
           "problem_title":"Δύσκολη αποθήκευση στο σπίτι με ντουλάπα",
           "problem_description":"Αποθηκευση χώρου με ντουλαπα και storage cabinet",
           "pain_severity_score":85,"verified_demand_score":None,
           "verified_competition_score":None}]
def rec(pid,price,stock):
 return {"product_id":pid,"product_name":"Μεταλλική ντουλάπα για αποθήκευση storage cabinet",
         "category":"Σπίτι, Έπιπλα, Ντουλάπες","price":price,"currency":"EUR",
         "tracking_url":TRACK,"in_stock":stock}
class CommissionGateTests(unittest.TestCase):
 def test_boundary_inclusive(self):
  self.assertFalse(passes_initial_gate(14.99))
  self.assertTrue(passes_initial_gate(15))
  self.assertTrue(passes_initial_gate(16))
  self.assertFalse(passes_initial_gate(None))
 def test_commission_provenance(self):
  self.assertEqual(estimate_commission(150,TERMS["23"])[0],15)
  self.assertIsNone(estimate_commission(200,None)[0])
  self.assertEqual(estimate_commission(200,{"percent_commission_min":2,
       "percent_commission_max":10})[0],4)
 def test_original_url_unchanged(self):
  self.assertEqual(parse_route(TRACK),("23","laredoute.gr"))
  self.assertEqual(parse_record(rec("p1",200,None))["tracking_url"],TRACK)
 def test_unknown_and_false_stock_not_hard_filters(self):
  index,problems=build_pain_index(PROBLEMS)
  items,counts,_=pool_candidates([
    rec("unknownstock",200,None),rec("outstock",190,False),
    rec("exactfloor",150,True),rec("underfloor",149.99,True)
  ],TERMS,problems,index,per_problem=10)
  self.assertEqual(counts["commission15_eligible"],3)
  self.assertEqual(counts["below_15_eur"],1)
  self.assertEqual({r["source_product_id"] for r in items},
                   {"unknownstock","outstock","exactfloor"})
  self.assertEqual(next(x for x in items if x["source_product_id"]=="unknownstock")["stock_state"],"unknown")
  self.assertEqual(next(x for x in items if x["source_product_id"]=="outstock")["stock_state"],"out_of_stock")
 def test_missing_program_terms_are_unpriced_not_falsified(self):
  index,problems=build_pain_index(PROBLEMS)
  items,counts,_=pool_candidates([rec("p1",500,True)],{},problems,index)
  self.assertEqual(len(items),0)
  self.assertEqual(counts["missing_program_terms_not_evaluable"],1)
  self.assertEqual(counts["below_15_eur"],0)
 def test_no_fake_demand_competition_or_cvr(self):
  index,_=build_pain_index(PROBLEMS)
  problem,fit=best_problem("Μεταλλική ντουλάπα storage cabinet",
     "οργάνωση αντικειμένων","έπιπλα ντουλάπες",index)
  self.assertIsNotNone(problem)
  self.assertGreater(fit,0)
  score=score_candidate({"price":200,"in_stock":None,"image_url":"https://images.example/product.jpg",
    "product_name":"Μεταλλική ντουλάπα"},problem,fit)
  self.assertIsNone(score["demand_score"])
  self.assertIsNone(score["competition_score"])
  self.assertEqual(score["evidence_level"],"hypothesis_only")
  self.assertIn("no_observed_affiliate_cvr",score["unknowns"])
 def test_no_merchant_approval_filter_or_merchant_cap(self):
  index,p=build_pain_index(PROBLEMS)
  rows=[rec(str(i),200+i,None) for i in range(12)]
  items,c,_=pool_candidates(rows,TERMS,p,index,per_problem=20)
  self.assertEqual(c["commission15_eligible"],12)
  self.assertEqual(len(items),12)
 def test_expired_offer_not_screened_in_discovery(self):
  r=rec("expired",200,False)
  r["valid_to"]="2020-02-01T00:00:00Z"
  index,p=build_pain_index(PROBLEMS)
  items,c,_=pool_candidates([r],TERMS,p,index)
  self.assertEqual(c["commission15_eligible"],1)
  self.assertEqual(len(items),1)
  self.assertEqual(items[0]["stage"],"research_candidate")
 def test_portfolio_deduplicates_differing_categories(self):
  q=BoundedPortfolio(limit_per_problem=4)
  a={"source_key":"linkwise","source_product_id":"s1","problem_key":"p1","opportunity_score":60}
  q.consider(a);q.consider({**a,"opportunity_score":70})
  self.assertEqual(len(q.result()),1)
  self.assertEqual(q.result()[0]["opportunity_score"],70)

if __name__=="__main__":unittest.main()
