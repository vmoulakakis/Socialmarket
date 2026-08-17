from __future__ import annotations

import unittest
from unittest.mock import patch

import consumer_verified_public_v412 as verified


class VerifiedPublicV412Tests(unittest.TestCase):
    def test_garden_seeds_span_forum_and_marketplace_families(self):
        seeds = verified.VERIFIED_PUBLIC_SEEDS[('Home & Garden', 'Garden & Outdoor Living')]
        families = {seed['source_family'] for seed in seeds}
        domains = {verified.consumer.host(seed['url']) for seed in seeds}
        self.assertIn('community_forum', families)
        self.assertIn('marketplace_review', families)
        self.assertIn('2019.kalliergo.gr', domains)
        self.assertIn('skroutz.gr', domains)

    def test_kalliergo_actual_text_can_emit_clogging_pain_after_lexicon_extension(self):
        seed = dict(verified.VERIFIED_PUBLIC_SEEDS[('Home & Garden', 'Garden & Outdoor Living')][0])
        text = (
            'Από την εμπειρία μου οι σταλάκτες βουλώνουν πολύ εύκολα και χρειάζεται '
            'να τους ελέγχω συχνά στο αυτόματο πότισμα.'
        )
        row = {'url': seed['url'], 'title': seed['title']}
        with patch.object(verified.consumer, 'PAIN_STEMS', (*verified.consumer.PAIN_STEMS, 'βουλ')):
            with patch.object(verified.consumer, '_fetch_text', return_value=(row, text, None)):
                evidence, diagnostic = verified._extract_seed(seed, ['Garden & Outdoor Living'])
        self.assertGreaterEqual(len(evidence), 1)
        self.assertEqual(evidence[0]['metadata']['source_family'], 'community_forum')
        self.assertTrue(evidence[0]['metadata']['consumer_text'])
        self.assertTrue(evidence[0]['metadata']['eligible_for_pain_audit'])
        self.assertFalse(diagnostic['metadata']['eligible_for_pain_audit'])

    def test_skroutz_actual_review_keeps_marketplace_review_family(self):
        seed = dict(verified.VERIFIED_PUBLIC_SEEDS[('Home & Garden', 'Garden & Outdoor Living')][1])
        text = (
            'Επιβεβαιωμένη αγορά. Έσπασαν στο χρόνο πάνω οι λόγχες και βουλώνουν '
            'πολύ εύκολα οι σταλάκτες από χώμα.'
        )
        row = {'url': seed['url'], 'title': seed['title']}
        with patch.object(verified.consumer, '_fetch_text', return_value=(row, text, None)):
            evidence, diagnostic = verified._extract_seed(seed, ['Garden & Outdoor Living'])
        self.assertGreaterEqual(len(evidence), 1)
        self.assertEqual(evidence[0]['metadata']['source_family'], 'marketplace_review')
        self.assertTrue(evidence[0]['metadata']['consumer_text'])
        self.assertEqual(diagnostic['metadata']['source_family'], 'marketplace_review')

    def test_fetch_failure_never_creates_pain_evidence(self):
        seed = dict(verified.VERIFIED_PUBLIC_SEEDS[('Home & Garden', 'Garden & Outdoor Living')][1])
        row = {'url': seed['url'], 'title': seed['title']}
        with patch.object(verified.consumer, '_fetch_text', return_value=(row, None, 'http_403')):
            evidence, diagnostic = verified._extract_seed(seed, ['Garden & Outdoor Living'])
        self.assertEqual(evidence, [])
        self.assertEqual(diagnostic['metadata']['fetch_error'], 'http_403')
        self.assertFalse(diagnostic['metadata']['eligible_for_pain_audit'])


if __name__ == '__main__':
    unittest.main()
