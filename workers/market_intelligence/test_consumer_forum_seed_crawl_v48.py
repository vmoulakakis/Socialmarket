from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

import consumer_forum_seed_crawl_v48 as v48


class ForumSeedCrawlV48Tests(unittest.TestCase):
    def test_same_domain_blocks_external_links(self):
        seed = 'https://www.e-camping.gr/forum'
        self.assertTrue(v48._same_domain('https://e-camping.gr/forum?catid=46&view=category', seed))
        self.assertFalse(v48._same_domain('https://example.com/forum?catid=46', seed))

    def test_topic_classifier_does_not_confuse_catid_with_id(self):
        category = 'https://www.e-camping.gr/forum?catid=46&view=category'
        topic = 'https://www.e-camping.gr/forum?catid=46&id=12390&view=topic'
        kithara = 'https://forum.kithara.gr/index.php?topic=49601.0'
        self.assertFalse(v48._topic_url(category))
        self.assertTrue(v48._topic_url(topic))
        self.assertTrue(v48._topic_url(kithara))

    def test_fetch_html_uses_canonical_consumer_requests_stack(self):
        response = Mock()
        response.status_code = 200
        response.headers = {'content-type': 'text/html; charset=utf-8'}
        response.text = '<html><body>forum</body></html>'
        response.raise_for_status.return_value = None
        with patch.object(v48.consumer.requests, 'get', return_value=response) as get:
            html, error = v48._fetch_html('https://www.e-camping.gr/forum')
        self.assertIsNone(error)
        self.assertIn('forum', html)
        get.assert_called_once_with(
            'https://www.e-camping.gr/forum',
            headers=v48.consumer.UA,
            timeout=18,
            allow_redirects=True,
        )

    def test_fetch_html_fails_closed_on_403(self):
        response = Mock()
        response.status_code = 403
        response.headers = {'content-type': 'text/html'}
        with patch.object(v48.consumer.requests, 'get', return_value=response):
            html, error = v48._fetch_html('https://www.e-camping.gr/forum')
        self.assertIsNone(html)
        self.assertEqual(error, 'http_403')

    def test_index_discovers_relevant_same_domain_topic(self):
        html = '''
        <html><body>
          <a href="/forum?catid=46&view=category">Εξοπλισμός κάμπινγκ και συμπράγκαλα</a>
          <a href="/forum?catid=46&id=12390&view=topic">ΑΓΟΡΑ ΕΞΟΠΛΙΣΜΟΥ 1η ΦΟΡΑ</a>
          <a href="https://example.com/camping">Εξωτερικό camping κατάστημα</a>
        </body></html>
        '''
        rows = v48._extract_links(html, 'https://www.e-camping.gr/forum', ['camping', 'εξοπλισμος'], 20)
        urls = {row['url'] for row in rows}
        self.assertIn('https://www.e-camping.gr/forum?catid=46&id=12390&view=topic', urls)
        self.assertNotIn('https://example.com/camping', urls)
        topic = next(row for row in rows if 'id=12390' in row['url'])
        self.assertTrue(v48._topicish(topic))

    def test_shallow_seed_crawl_follows_relevant_category_then_topic(self):
        seed = 'https://www.e-camping.gr/forum'
        root = '<a href="/forum?catid=46&view=category">Εξοπλισμός camping</a>'
        category = '<a href="/forum?catid=46&id=12390&view=topic">Πρόβλημα με εξοπλισμό camping</a>'

        def fake_fetch(url):
            if url == seed:
                return root, None
            if 'catid=46&view=category' in url:
                return category, None
            return None, 'unexpected'

        with patch.object(v48, '_fetch_html', side_effect=fake_fetch):
            rows, diagnostics = v48._crawl_seed(seed, ['camping', 'εξοπλισμος'])
        self.assertEqual(len(rows), 1)
        self.assertIn('id=12390', rows[0]['url'])
        self.assertGreaterEqual(len(diagnostics), 2)
        self.assertEqual(diagnostics[0]['metadata']['topic_urls_selected'], 1)

    def test_verified_camping_direct_seeds_span_two_extra_domains(self):
        rows, diagnostics = v48._direct_candidates(
            'Sports & Outdoors', 'Camping & Hiking', ['camping', 'power', 'bank']
        )
        domains = {v48._host(row['url']) for row in rows}
        self.assertIn('insomnia.gr', domains)
        self.assertIn('forum.kithara.gr', domains)
        self.assertEqual(len(rows), len(diagnostics))
        self.assertTrue(all(not d['metadata']['eligible_for_pain_audit'] for d in diagnostics))

    def test_verified_garden_direct_seeds_span_two_extra_domains(self):
        rows, _ = v48._direct_candidates(
            'Home & Garden', 'Garden & Outdoor Living', ['ποτισμα', 'μπαλκονι']
        )
        domains = {v48._host(row['url']) for row in rows}
        self.assertIn('insomnia.gr', domains)
        self.assertIn('kalliergo.gr', domains)

    def test_direct_seed_metadata_never_becomes_pain_proof(self):
        rows, diagnostics = v48._direct_candidates(
            'Sports & Outdoors', 'Camping & Hiking', ['camping']
        )
        self.assertGreaterEqual(len(rows), 2)
        self.assertTrue(all(d['source_kind'] == 'consumer_discovery' for d in diagnostics))
        self.assertTrue(all(d['body'] == '' for d in diagnostics))
        self.assertTrue(all(d['metadata']['evidence_mode'] == 'discovery_only' for d in diagnostics))

    def test_known_camping_seed_is_registered(self):
        seeds = v48.SEEDS[('Sports & Outdoors', 'Camping & Hiking')]
        self.assertIn('https://www.e-camping.gr/forum', seeds)


if __name__ == '__main__':
    unittest.main()
