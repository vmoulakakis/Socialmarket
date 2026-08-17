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

    def test_camping_has_three_independent_crawlable_forum_domains(self):
        seeds = verified.VERIFIED_PUBLIC_SEEDS[('Sports & Outdoors', 'Camping & Hiking')]
        domains = {verified.consumer.host(seed['url']) for seed in seeds}
        self.assertEqual(len(seeds), 3)
        self.assertEqual(domains, {'e-camping.gr', 'insomnia.gr', 'advride.gr'})
        self.assertTrue(all(seed['source_family'] == 'community_forum' for seed in seeds))
        self.assertTrue(any('χάνει αέρα' in seed['binding_terms'] for seed in seeds))
        self.assertTrue(any('κάθε μέρα' in seed['binding_terms'] for seed in seeds))

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

    def test_camping_forum_actual_text_can_emit_reinflation_pain(self):
        seed = dict(verified.VERIFIED_PUBLIC_SEEDS[('Sports & Outdoors', 'Camping & Hiking')][1])
        text = (
            'Έχω φουσκωτό στρώμα και ξεφουσκώνει λίγο κάθε νύχτα, οπότε κάθε βράδυ '
            'χρειάζεται πάλι φούσκωμα για να κοιμηθούμε άνετα.'
        )
        row = {'url': seed['url'], 'title': seed['title']}
        stems = (*verified.consumer.PAIN_STEMS, 'χανει αερ', 'ξεφουσκ', 'μπελ')
        with patch.object(verified.consumer, 'PAIN_STEMS', stems):
            with patch.object(verified.consumer, '_fetch_text', return_value=(row, text, None)):
                evidence, diagnostic = verified._extract_seed(seed, ['Camping & Hiking'])
        self.assertGreaterEqual(len(evidence), 1)
        self.assertEqual(evidence[0]['metadata']['source_family'], 'community_forum')
        self.assertTrue(evidence[0]['metadata']['consumer_text'])
        self.assertTrue(evidence[0]['metadata']['eligible_for_pain_audit'])
        self.assertFalse(diagnostic['metadata']['eligible_for_pain_audit'])

    def test_advride_setup_burden_is_recallable_without_lowering_score_threshold(self):
        seed = dict(verified.VERIFIED_PUBLIC_SEEDS[('Sports & Outdoors', 'Camping & Hiking')][2])
        text = (
            'Έχω ένα φουσκωτό στρώμα, αλλά είναι μεγάλος μπελάς όταν μένεις πάνω από '
            'δύο μέρες και πρέπει να φουσκώνεις και να ξεφουσκώνεις κάθε μέρα.'
        )
        row = {'url': seed['url'], 'title': seed['title']}
        stems = (*verified.consumer.PAIN_STEMS, 'μπελ')
        with patch.object(verified.consumer, 'PAIN_STEMS', stems):
            with patch.object(verified.consumer, '_fetch_text', return_value=(row, text, None)):
                evidence, _ = verified._extract_seed(seed, ['Camping & Hiking'])
        self.assertGreaterEqual(len(evidence), 1)
        self.assertGreaterEqual(evidence[0]['metadata']['consumer_language_score'], 10)

    def test_fetch_failure_never_creates_pain_evidence(self):
        seed = dict(verified.VERIFIED_PUBLIC_SEEDS[('Sports & Outdoors', 'Camping & Hiking')][0])
        row = {'url': seed['url'], 'title': seed['title']}
        with patch.object(verified.consumer, '_fetch_text', return_value=(row, None, 'http_403')):
            evidence, diagnostic = verified._extract_seed(seed, ['Camping & Hiking'])
        self.assertEqual(evidence, [])
        self.assertEqual(diagnostic['metadata']['fetch_error'], 'http_403')
        self.assertFalse(diagnostic['metadata']['eligible_for_pain_audit'])


if __name__ == '__main__':
    unittest.main()
