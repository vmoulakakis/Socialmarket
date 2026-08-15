import os
import sys
import unittest

HERE=os.path.dirname(__file__)
if HERE not in sys.path: sys.path.insert(0,HERE)

from fuzzy_fusion import whitespace_inference,market_structure
from forecast_ensemble import history_gate,run_lab
from graph_rag import build
from causal_skeptic import audit


class DeepDemandV31Tests(unittest.TestCase):
    def test_supply_does_not_modify_canonical_demand(self):
        low=whitespace_inference(82,78,25,20,.9)
        high=whitespace_inference(82,78,25,90,.9)
        self.assertEqual(low['canonical_demand_unchanged'],82)
        self.assertEqual(high['canonical_demand_unchanged'],82)
        self.assertGreater(low['score'],high['score'])

    def test_missing_competition_is_not_zero(self):
        result=whitespace_inference(75,70,None,None,.8)
        self.assertEqual(result['canonical_demand_unchanged'],75)
        self.assertFalse(any('low competition' in r['rule'] for r in result['rules']))

    def test_market_structure_contract(self):
        result=market_structure(80,40,72,.85,5,75,60,.8,evidence_count=10)
        self.assertEqual(result['contract']['canonical_demand'],80)
        self.assertFalse(result['contract']['canonical_demand_modified'])
        self.assertTrue(result['contract']['supply_is_separate_dimension'])

    def test_neural_and_production_forecast_withheld_on_short_history(self):
        history=[{'observed_at':'2026-08-15T10:00:00+00:00','demand_score':60},{'observed_at':'2026-08-16T10:00:00+00:00','demand_score':63}]
        gate=history_gate(history)
        lab=run_lab(history)
        self.assertFalse(gate['neural_ready'])
        self.assertEqual(gate['status'],'WITHHELD')
        self.assertEqual(lab['decision'],'WITHHOLD_PRODUCTION_FORECAST')
        self.assertIsNone(lab['production_forecast'])

    def test_graph_is_lineage_not_demand(self):
        graph=build({'taxonomy_id':'t1','market':{'category_name':'Pets'},'retrieved_evidence':[{'id':'e1','source_domain':'example.gr','title':'Evidence','retrieval':{'score':.8}}],'validated_pains':[{'id':'p1','canonical_text':'Pain'}],'supply_context':[{'merchant_id':'m1','canonical_name':'Merchant'}]})
        self.assertEqual(graph['status'],'DERIVED')
        self.assertIn('never interpreted as demand',graph['semantics'])
        self.assertGreaterEqual(graph['summary']['edge_count'],3)

    def test_causal_claims_are_withheld_without_identification(self):
        context={'history':[{'observed_at':f'2026-06-{(i%28)+1:02d}T00:00:00+00:00','demand_score':50+i%7} for i in range(65)],'retrieved_evidence':[],'supply_context':[]}
        result=audit(context)
        self.assertFalse(result['readiness']['can_claim_causality'])
        self.assertIn(result['readiness']['status'],{'WITHHELD','READY_FOR_CAUSAL_REFUTATION'})


if __name__=='__main__':
    unittest.main()
