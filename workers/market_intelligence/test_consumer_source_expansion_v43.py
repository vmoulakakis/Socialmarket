import unittest
from unittest.mock import patch

import consumer_evidence_v4 as consumer
import consumer_source_expansion_v43 as expansion


class BalancedSourceExpansionV43Tests(unittest.TestCase):
    def setUp(self):
        expansion.apply()

    def test_prolific_domain_is_capped_and_later_sources_survive(self):
        def fake_search(query,limit=8):
            if 'avsite' in query:
                return [{'url':f'https://www.avsite.gr/forum/threads/tv-{i}','title':f'Τηλεοράσεις εμπειρίες {i}','snippet':'τηλεοράσεις πρόβλημα αγορά'} for i in range(30)]
            if 'adslgr' in query:
                return [{'url':f'https://www.adslgr.com/forum/threads/tv-{i}','title':f'Τηλεοράσεις γνώμες {i}','snippet':'τηλεοράσεις πρόβλημα αγορά'} for i in range(6)]
            if 'thelab' in query:
                return [{'url':f'https://www.thelab.gr/forums/topic/tv-{i}','title':f'Τηλεοράσεις thread {i}','snippet':'τηλεοράσεις εμπειρία'} for i in range(6)]
            return []
        with patch.object(consumer,'search',side_effect=fake_search):
            rows=consumer.discover_urls(['τηλεοράσεις'])
        domains=[consumer.host(x['url']) for x in rows]
        self.assertLessEqual(domains.count('avsite.gr'),expansion.PER_DOMAIN_CAP)
        self.assertIn('adslgr.com',domains)
        self.assertIn('thelab.gr',domains)

    def test_irrelevant_results_are_removed_before_fetch(self):
        def fake_search(query,limit=8):
            if 'myphone' in query:
                return [
                    {'url':'https://myphone.gr/forum/topic/food','title':'Τι φάγαμε σήμερα','snippet':'άσχετο θέμα'},
                    {'url':'https://myphone.gr/forum/topic/phone','title':'Smartphone προβλήματα','snippet':'smartphone μπαταρία αγορά'},
                ]
            return []
        with patch.object(consumer,'search',side_effect=fake_search):
            rows=consumer.discover_urls(['smartphone'])
        urls={x['url'] for x in rows}
        self.assertNotIn('https://myphone.gr/forum/topic/food',urls)
        self.assertIn('https://myphone.gr/forum/topic/phone',urls)

    def test_generic_domains_have_stricter_cap(self):
        def fake_search(query,limit=8):
            if 'smartphone' not in query:return []
            return [{'url':f'https://generic-{i}.example.com/smartphone','title':'Smartphone εμπειρία','snippet':'smartphone πρόβλημα αγορά'} for i in range(20)]
        with patch.object(consumer,'search',side_effect=fake_search):
            rows=consumer.discover_urls(['smartphone'])
        generic=[x for x in rows if '.example.com' in x['url']]
        self.assertLessEqual(len(generic),expansion.GENERIC_TOTAL_CAP)

    def test_discovery_rows_are_marked_balanced_v43(self):
        def fake_search(query,limit=8):
            if 'reviewit' in query:
                return [{'url':'https://reviewit.gr/smartphone-review','title':'Smartphone εμπειρία','snippet':'smartphone αγορά πρόβλημα'}]
            return []
        with patch.object(consumer,'search',side_effect=fake_search):
            rows=consumer.discover_urls(['smartphone'])
        self.assertTrue(rows)
        self.assertTrue(all(x.get('discovery_version')=='expanded_balanced_v43' for x in rows))


if __name__=='__main__':
    unittest.main()
