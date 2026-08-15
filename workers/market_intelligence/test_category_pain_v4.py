import unittest
from unittest.mock import patch

import category_pain_intelligence_v4 as v4


def row(kind,url,query,title='Relevant product market result'):
    return {'source_kind':kind,'source_url':url,'title':title,'body':'τιμή αγορά προϊόν Ελλάδα','collector':'test','confidence':.8,'metadata':{'query':query}}


def consumer_rows():
    return [
        {'source_kind':'pain_candidate','source_url':'https://www.skroutz.gr/s/1/x','title':'Αντηλιακό αξιολογήσεις','body':'Αγόρασα το αντηλιακό αλλά με τσούζει στα μάτια και δεν μπορώ να το χρησιμοποιήσω.','collector':'test','confidence':.9,'metadata':{'consumer_text':True,'source_family':'marketplace_review','consumer_language_score':20}},
        {'source_kind':'pain_candidate','source_url':'https://www.insomnia.gr/forums/topic/1','title':'Αντηλιακό εμπειρίες','body':'Δοκίμασα αντηλιακό και έχω πρόβλημα με ερεθισμό, ψάχνω εναλλακτική.','collector':'test','confidence':.82,'metadata':{'consumer_text':True,'source_family':'community_forum','consumer_language_score':18}},
        {'source_kind':'pain_candidate','source_url':'https://www.reddit.com/r/greece/comments/1','title':'Αντηλιακό για ευαίσθητο δέρμα','body':'Δεν βρίσκω αντηλιακό που να μην ερεθίζει και να μπορώ να αγοράσω εύκολα στην Ελλάδα.','collector':'test','confidence':.78,'metadata':{'consumer_text':True,'source_family':'social_forum','consumer_language_score':17}},
    ]


class CategoryPainV4Tests(unittest.TestCase):
    def setUp(self):
        self.job={'id':'job-1','entity_id':'tax-1','payload':{'category':'Beauty & Personal Care','subcategory':'Sun Care'}}

    def fake_useful(self,query,keys,term,kind,limit):
        if kind=='demand':
            if 'σύγκριση τιμών' in query:return []
            suffix=abs(hash(query))%7
            return [row('demand',f'https://demand{suffix}.example.gr/p/{suffix}',query)]
        domains=['skroutz.gr','bestprice.gr','pharmacy295.gr','notino.gr']
        return [row('competition',f'https://{d}/sun-care',query,d) for d in domains]

    @patch.object(v4,'authoritative_context_rows')
    @patch.object(v4,'collect_consumer_evidence')
    @patch.object(v4.base,'useful_rows')
    def test_v4_produces_market_metrics_without_using_context_as_score(self,m_useful,m_consumer,m_context):
        m_useful.side_effect=self.fake_useful
        m_consumer.return_value=consumer_rows()
        m_context.return_value=[{'source_kind':'official_context','source_url':'https://statistics.gr/x','title':'ELSTAT','body':'macro context','collector':'test','confidence':.95,'metadata':{'context_only':True,'authority_weight':1.0,'source_class':'official_statistics'}}]
        result=v4.collect_v4(self.job)
        market=result['market']
        self.assertIsNotNone(market['demand_score'])
        self.assertLess(market['demand_score'],100)
        self.assertIsNotNone(market['competition_score'])
        self.assertEqual(market['evidence_quality']['pain_consumer_rows'],3)
        self.assertEqual(len(market['evidence_quality']['pain_source_families']),3)
        self.assertEqual(market['evidence_quality']['context_rows'],1)
        self.assertIn('not search volume',market['metric_semantics']['demand'])

    @patch.object(v4,'authoritative_context_rows')
    @patch.object(v4,'collect_consumer_evidence')
    @patch.object(v4.base,'useful_rows')
    def test_macro_context_does_not_change_demand_score(self,m_useful,m_consumer,m_context):
        m_useful.side_effect=self.fake_useful
        m_consumer.return_value=consumer_rows()
        m_context.return_value=[]
        baseline=v4.collect_v4(self.job)['market']['demand_score']
        m_context.return_value=[{'source_kind':'official_context','source_url':'https://statistics.gr/x','title':'ELSTAT','body':'macro '*100,'collector':'test','confidence':.99,'metadata':{'context_only':True,'authority_weight':1.0,'source_class':'official_statistics'}}]
        with_context=v4.collect_v4(self.job)['market']['demand_score']
        self.assertEqual(baseline,with_context)

    @patch.object(v4,'authoritative_context_rows')
    @patch.object(v4,'collect_consumer_evidence')
    @patch.object(v4.base,'useful_rows')
    def test_serp_flood_cannot_crow_consumer_pain_out_of_bundle(self,m_useful,m_consumer,m_context):
        def flood(query,keys,term,kind,limit):
            count=35 if kind=='demand' else 45
            return [row(kind,f'https://{kind}-{abs(hash(query))}-{i}.example.gr/p/{i}',query) for i in range(count)]
        m_useful.side_effect=flood
        m_consumer.return_value=consumer_rows()
        m_context.return_value=[{'source_kind':'industry_context','source_url':'https://greekecommerce.gr/x','title':'GRECA','body':'context','collector':'test','confidence':.85,'metadata':{'context_only':True,'authority_weight':.88,'source_class':'industry_primary'}}]
        result=v4.collect_v4(self.job)
        kinds=[e['source_kind'] for e in result['evidence']]
        self.assertEqual(kinds[:3],['pain_candidate','pain_candidate','pain_candidate'])
        self.assertEqual(result['market']['evidence_quality']['pain_consumer_rows'],3)
        counts=result['market']['evidence_quality']['channel_counts']
        self.assertGreater(counts['demand_raw'],v4.CHANNEL_BUDGETS['demand'])
        self.assertEqual(counts['demand_retained'],v4.CHANNEL_BUDGETS['demand'])
        self.assertEqual(counts['pain_candidate_retained'],3)
        self.assertEqual(counts['context_retained'],1)

    @patch.object(v4.base,'gateway')
    @patch.object(v4,'collect_v4')
    def test_one_collection_failure_is_requeued_without_stranding_other_job(self,m_collect,m_gateway):
        jobs=[
            {'id':'bad-job','entity_id':'bad-tax','payload':{'category':'Bad','subcategory':'Broken'}},
            {'id':'good-job','entity_id':'good-tax','payload':{'category':'Good','subcategory':'Working'}},
        ]
        def collect(job):
            if job['id']=='bad-job':raise RuntimeError('collector exploded')
            return {'job_id':'good-job','entity_id':'good-tax','category':'Good','subcategory':'Working','evidence':[],'market':{'query_aliases':[],'evidence_quality':{},'competition_score':50,'demand_score':60}}
        m_collect.side_effect=collect
        def gateway(action,**payload):
            if action=='fail':return {'ok':True}
            if action=='audit_batch':return {'ok':True,'items':[{'entity_id':'good-tax','clusters':[],'audit_summary':'none','rejected_patterns':[]}]}
            if action=='save':return {'ok':True,'result':{'validated_clusters':0}}
            raise AssertionError(action)
        m_gateway.side_effect=gateway
        results=v4.process_batch_v4(jobs)
        self.assertEqual(len(results),2)
        self.assertEqual(sum(1 for x in results if x.get('ok')),1)
        failed=[x for x in results if not x.get('ok')][0]
        self.assertEqual(failed['stage'],'collect')
        self.assertTrue(any(call.args and call.args[0]=='fail' for call in m_gateway.call_args_list))


if __name__=='__main__':
    unittest.main()
