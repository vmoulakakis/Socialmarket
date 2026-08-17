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

    def test_camping_seeds_span_three_domains_and_two_source_families(self):
        seeds = verified.VERIFIED_PUBLIC_SEEDS[('Sports & Outdoors', 'Camping & Hiking')]
        domains = {verified.consumer.host(seed['url']) for seed in seeds}
        families = {seed['source_family'] for seed in seeds}
        self.assertEqual(len(seeds), 3)
        self.assertEqual(domains, {'e-camping.gr', 'insomnia.gr', 'lightgear.gr'})
        self.assertEqual(families, {'community_forum', 'community_blog'})
        self.assertTrue(any('χάνει αέρα' in seed['binding_terms'] for seed in seeds))
        self.assertTrue(any('δεν ξεφουσκώνει' in seed['binding_terms'] for seed in seeds))

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

    def test_insomnia_actual_experience_can_emit_daily_reinflation_pain(self):
        seed = dict(verified.VERIFIED_PUBLIC_SEEDS[('Sports & Outdoors', 'Camping & Hiking')][1])
        text = (
            'Έχοντας κοιμηθεί σε φουσκωτό στρώμα, από τη φύση τους χάνουν αέρα κάθε μέρα. '
            'Κάθε βράδυ θέλει πάλι φούσκωμα για να είναι έτοιμο για ύπνο.'
        )
        row = {'url': seed['url'], 'title': seed['title']}
        pain_stems = (*verified.consumer.PAIN_STEMS, 'χανει αερ', 'χανουν αερ', 'ξεφουσκ')
        first_stems = (*verified.consumer.FIRST_PERSON_STEMS, 'εχοντας')
        with patch.object(verified.consumer, 'PAIN_STEMS', pain_stems), patch.object(
            verified.consumer, 'FIRST_PERSON_STEMS', first_stems
        ), patch.object(verified.consumer, '_fetch_text', return_value=(row, text, None)):
            evidence, diagnostic = verified._extract_seed(seed, ['Camping & Hiking'])
        self.assertGreaterEqual(len(evidence), 1)
        self.assertEqual(evidence[0]['metadata']['source_family'], 'community_forum')
        self.assertTrue(evidence[0]['metadata']['consumer_text'])
        self.assertTrue(evidence[0]['metadata']['first_person_signal'])
        self.assertFalse(diagnostic['metadata']['eligible_for_pain_audit'])

    def test_lightgear_user_comment_can_emit_deflation_setup_pain(self):
        seed = dict(verified.VERIFIED_PUBLIC_SEEDS[('Sports & Outdoors', 'Camping & Hiking')][2])
        text = (
            'Αγορασα πρόσφατα ένα αυτοφούσκωτο υπόστρωμα camping. Προσπαθώ να το '
            'ξεφουσκώσω και δεν ξεφουσκώνει με τίποτα, οπότε δυσκολεύομαι πολύ να το μαζέψω.'
        )
        row = {'url': seed['url'], 'title': seed['title']}
        pain_stems = (*verified.consumer.PAIN_STEMS, 'ξεφουσκ', 'δεν ξεφουσκ', 'δυσκολ')
        with patch.object(verified.consumer, 'PAIN_STEMS', pain_stems), patch.object(
            verified.consumer, '_fetch_text', return_value=(row, text, None)
        ):
            evidence, diagnostic = verified._extract_seed(seed, ['Camping & Hiking'])
        self.assertGreaterEqual(len(evidence), 1)
        self.assertEqual(evidence[0]['metadata']['source_family'], 'community_blog')
        self.assertTrue(evidence[0]['metadata']['consumer_text'])
        self.assertTrue(evidence[0]['metadata']['eligible_for_pain_audit'])
        self.assertFalse(diagnostic['metadata']['eligible_for_pain_audit'])

    def test_direct_fetch_diagnostics_precede_broad_discovery_when_bounded(self):
        seeds = verified.VERIFIED_PUBLIC_SEEDS[('Sports & Outdoors', 'Camping & Hiking')]
        base = [
            {'source_kind': 'consumer_discovery', 'source_url': f'https://broad{i}.gr/x', 'body': '', 'metadata': {}}
            for i in range(20)
        ]
        diagnostic_rows = []
        for seed in seeds:
            diagnostic_rows.append(([], {
                'source_kind': 'consumer_discovery',
                'source_url': seed['url'],
                'collector': 'verified_public_seed_v416',
                'body': '',
                'metadata': {'eligible_for_pain_audit': False},
            }))
        with patch.object(verified, '_ORIGINAL_COLLECT', return_value=base), patch.object(
            verified, '_extract_seed', side_effect=diagnostic_rows
        ):
            rows = verified.collect_consumer_evidence(
                'Sports & Outdoors', 'Camping & Hiking', [], ['Camping & Hiking'], max_rows=5
            )
        self.assertEqual(len(rows), 5)
        self.assertTrue(all(row.get('collector') == 'verified_public_seed_v416' for row in rows[:3]))

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
