import unittest

import product_intelligence_v1 as v1
import product_local_autopilot as local


class ExplodingRouter:
    def execute(self, task):
        raise AssertionError('AI router must not be called for deterministic hard-gate rejection')


class ProductLocalAutopilotTests(unittest.TestCase):
    def sample_item(self, commission=18.0):
        return {
            'product':{'source_record_hash':'a'*64,'product_name':'Test Product','brand_name':'Brand','model_name':'M1'},
            'merchant':{'canonical_name':'Merchant','trust_score':80,'demand_score':70,'competition_score':40,'solution_whitespace_score':65},
            '_raw':{'source_record_hash':'a'*64,'product_name':'Test Product','brand_name':'Brand','model_name':'M1','category_raw':'Home','price':120,'full_price':140,'discount_pct':14,'expected_commission_eur':commission,'in_stock':True,'times_bought':5,'description':'X'*10000},
            '_rank_metrics':{'merchant_demand_score':70,'competition_score':40,'inverse_competition_score':60,'merchant_whitespace_score':65,'merchant_trust_score':80,'commercial_score':70,'network_performance_score':50,'discount_score':14,'purchase_signal_score':20,'pain_signal_score':30,'seasonal_score':10,'deep_demand_score':25,'deterministic_rank_score':62},
            '_deep_demand':{'matched':True,'score':25,'status':'canonical_only','category_name':'Home','subcategory_name':'Furniture','canonical_demand_score':70,'canonical_competition_score':40,'canonical_confidence':80},
            'pain_rag':[{'id':str(i),'canonical_text':f'pain {i}','pain_severity':70,'commercial_intent':60,'confidence':80,'retrieval_score':75,'source_diversity':2,'evidence_count':5} for i in range(8)],
            'theme_rag':[{'id':str(i),'name':f'theme {i}','semantic_brief':'brief','retrieval_score':70,'seasonal_curve_score':60} for i in range(5)],
        }

    def test_compact_packet_never_contains_bulk_description(self):
        old=v1.MIN_COMMISSION
        try:
            v1.MIN_COMMISSION=15
            packet=local._compact_product(self.sample_item())
            encoded=str(packet)
            self.assertNotIn('X'*500,encoded)
            self.assertEqual(packet['hard_constraints']['min_expected_commission_eur'],15)
            self.assertLessEqual(len(packet['pain_evidence']),3)
            self.assertLessEqual(len(packet['themes']),2)
        finally:v1.MIN_COMMISSION=old

    def test_commission_floor_rejects_before_any_ai_call(self):
        old=v1.MIN_COMMISSION
        try:
            v1.MIN_COMMISSION=15
            h,data,stats=local._rank_one(self.sample_item(14.99),ExplodingRouter())
            self.assertEqual(h,'a'*64)
            self.assertIsNone(data)
            self.assertEqual(stats['status'],'hard_gate_reject')
        finally:v1.MIN_COMMISSION=old

    def test_deterministic_seo_uses_no_llm(self):
        rows=[{'source_record_hash':'b'*64,'product_name':'Καρέκλα Γραφείου','merchant_name':'Merchant','brand_name':'Brand','category':'Furniture','effective_price':99.9,'discount_pct':10,'product_attributes':{'colour':'Black'}}]
        out,stats=local.enrich_seo_deterministic(rows)
        self.assertEqual(stats['seo_llm_calls'],0)
        self.assertEqual(stats['seo_failures'],0)
        self.assertTrue(out[0]['seo_content']['title'])
        self.assertIn('Χρώμα: Black',out[0]['seo_content']['feature_bullets'])

    def test_creative_normalization_forces_exact_three_formats(self):
        row={'source_record_hash':'c'*64}
        data={'source_record_hash':'c'*64,'campaign_theme':'Theme','emotional_angle':'Angle','audience':'Audience','primary_message':'Message','variants':[
            {'id':'feed_4x5','headline':'H1','caption':'C1','cta':'CTA','hashtags':['#a']},
            {'id':'reel_9x16','headline':'H2','caption':'C2','cta':'CTA','hashtags':['#b'],'hook':'Hook'},
            {'id':'square_1x1','headline':'H3','caption':'C3','cta':'CTA','hashtags':['#c']},
        ]}
        pack=local._normalize_pack(row,data)
        self.assertIsNotNone(pack)
        self.assertEqual([x['id'] for x in pack['variants']],['feed_4x5','reel_9x16','square_1x1'])
        self.assertTrue(all(x['qr_spec']['payload_rule']=='exact_tracking_url' for x in pack['variants']))


if __name__=='__main__':unittest.main()
