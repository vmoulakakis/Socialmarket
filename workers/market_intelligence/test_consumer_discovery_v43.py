import unittest
from unittest.mock import patch

import category_pain_intelligence_v43 as v43


class ConsumerDiscoveryV43Tests(unittest.TestCase):
    def test_one_domain_cannot_monopolize_discovery(self):
        def fake_search(query,limit=8):
            if 'avsite.gr' in query:
                return [
                    {'url':f'https://www.avsite.gr/forum/threads/smartphone-{i}','title':f'Smartphone εμπειρίες {i}','snippet':'smartphone πρόβλημα αγορά'}
                    for i in range(20)
                ]
            if 'myphone.gr' in query:
                return [
                    {'url':f'https://myphone.gr/forum/topic/smartphone-{i}','title':f'Smartphone γνώμες {i}','snippet':'smartphone μπαταρία αγορά'}
                    for i in range(8)
                ]
            if 'thelab.gr' in query:
                return [
                    {'url':f'https://www.thelab.gr/forums/topic/smartphone-{i}','title':f'Smartphone thread {i}','snippet':'smartphone χρήση πρόβλημα'}
                    for i in range(8)
                ]
            return []
        with patch.object(v43.consumer,'search',side_effect=fake_search):
            rows=v43.discover_urls_v43(['smartphone'])
        domains=[v43.consumer.host(x['url']) for x in rows]
        self.assertLessEqual(domains.count('avsite.gr'),v43.PER_DOMAIN_CAP)
        self.assertIn('myphone.gr',domains)
        self.assertIn('thelab.gr',domains)
        self.assertGreaterEqual(len(set(domains)),3)

    def test_later_domain_survives_even_when_first_domain_has_many_hits(self):
        def fake_search(query,limit=8):
            if 'avsite.gr' in query:
                return [{'url':f'https://avsite.gr/forum/threads/tv-{i}','title':f'Τηλεοράσεις εμπειρίες {i}','snippet':'τηλεοράσεις πρόβλημα'} for i in range(50)]
            if 'adslgr.com' in query:
                return [{'url':'https://www.adslgr.com/forum/threads/tv-1','title':'Τηλεοράσεις και ήχος εμπειρίες','snippet':'τηλεοράσεις αγορά πρόβλημα'}]
            return []
        with patch.object(v43.consumer,'search',side_effect=fake_search):
            rows=v43.discover_urls_v43(['τηλεοράσεις'])
        domains={v43.consumer.host(x['url']) for x in rows}
        self.assertIn('adslgr.com',domains)

    def test_irrelevant_site_result_is_dropped_before_fetch(self):
        def fake_search(query,limit=8):
            if 'myphone.gr' in query:
                return [
                    {'url':'https://myphone.gr/forum/topic/food','title':'Τι φάγαμε σήμερα','snippet':'άσχετη συζήτηση για φαγητό'},
                    {'url':'https://myphone.gr/forum/topic/phone','title':'Smartphone προβλήματα','snippet':'smartphone αγορά μπαταρία'},
                ]
            return []
        with patch.object(v43.consumer,'search',side_effect=fake_search):
            rows=v43.discover_urls_v43(['smartphone'])
        urls={x['url'] for x in rows}
        self.assertNotIn('https://myphone.gr/forum/topic/food',urls)
        self.assertIn('https://myphone.gr/forum/topic/phone',urls)

    def test_exact_phrase_queries_are_used_for_high_value_sources(self):
        queries=[]
        def fake_search(query,limit=8):
            queries.append(query);return []
        with patch.object(v43.consumer,'search',side_effect=fake_search):
            v43.discover_urls_v43(['γυαλιά ηλίου'])
        self.assertTrue(any('site:forum.4troxoi.gr "γυαλιά ηλίου"' in q for q in queries))
        self.assertTrue(any('site:myphone.gr "γυαλιά ηλίου"' in q for q in queries))


if __name__=='__main__':
    unittest.main()
