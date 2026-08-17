import unittest
from unittest.mock import patch

import product_local_autopilot as local
import product_local_validated as validated


class ValidatedFrontierTests(unittest.TestCase):
    def test_needs_review_does_not_stop_validated_frontier(self):
        items=[
            {'product':{'source_record_hash':'a'},'score':100},
            {'product':{'source_record_hash':'b'},'score':90},
            {'product':{'source_record_hash':'c'},'score':80},
        ]

        def fake_rank(item,router):
            h=item['product']['source_record_hash']
            return h,{'source_record_hash':h,'product_market_fit_score':80,'creative_potential_score':70,'value_score':70,'confidence_score':80}, {'status':'ok','from_cache':False,'cost_usd':0}

        verdicts={'a':'NEEDS_REVIEW','b':'VALIDATED','c':'VALIDATED'}
        def fake_audit(item,ranking,router):
            h=item['product']['source_record_hash']
            return h,{'source_record_hash':h,'verdict':verdicts[h],'risk_score':20,'risk_flags':[],'reasons':[],'audit_summary':'ok'}, {'status':'ok','from_cache':False,'cost_usd':0}

        def fake_final_row(item,ai):
            return {'rank_score':item['score']}

        old_min,old_workers=local.LOCAL_MIN_FINAL,local.LOCAL_AI_WORKERS
        local.LOCAL_MIN_FINAL=2;local.LOCAL_AI_WORKERS=1
        try:
            with patch.object(local,'_router',return_value=object()), patch.object(local,'_rank_one',side_effect=fake_rank), patch.object(local,'_audit_one',side_effect=fake_audit), patch.object(validated.v3,'final_row',side_effect=fake_final_row):
                outputs,stats=validated.rank_with_validated_local_ai(items)
        finally:
            local.LOCAL_MIN_FINAL=old_min;local.LOCAL_AI_WORKERS=old_workers

        self.assertEqual(set(outputs),{'b','c'})
        self.assertEqual(stats['local_validated'],2)
        self.assertEqual(stats['local_needs_review'],1)
        self.assertEqual(stats['local_audited'],3)
        self.assertEqual(stats['paid_inference_cost_usd'],0)


if __name__=='__main__':unittest.main()
