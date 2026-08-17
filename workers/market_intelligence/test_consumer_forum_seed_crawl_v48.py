from __future__ import annotations

import unittest
from unittest.mock import patch

import consumer_forum_seed_crawl_v48 as v48


class ForumSeedCrawlV48Tests(unittest.TestCase):
    def test_same_domain_blocks_external_links(self):
        seed = 'https://www.e-camping.gr/forum'
        self.assertTrue(v48._same_domain('https://e-camping.gr/forum?catid=46&view=category', seed))
        self.assertFalse(v48._same_domain('https://example.com/forum?catid=46', seed))

    def test_topic_classifier_does_not_confuse_catid_with_id(self):
        category = 'https://www.e-camping.gr/forum?catid=46&view=category'
        topic = 'https://www.e-camping.gr/forum?catid=46&id=12390&view=topic'
        self.assertFalse(v48._topic_url(category))
        self.assertTrue(v48._topic_url(topic))

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

    def test_known_camping_seed_is_registered(self):
        seeds = v48.SEEDS[('Sports & Outdoors', 'Camping & Hiking')]
        self.assertIn('https://www.e-camping.gr/forum', seeds)


if __name__ == '__main__':
    unittest.main()
