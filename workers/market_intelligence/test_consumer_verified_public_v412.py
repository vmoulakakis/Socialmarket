from __future__ import annotations

import unittest
from unittest.mock import patch

import consumer_verified_public_v412 as verified


class VerifiedPublicV418Tests(unittest.TestCase):
    def test_garden_seeds_keep_existing_cross_family_contract(self):
        seeds = verified.VERIFIED_PUBLIC_SEEDS[('Home & Garden', 'Garden & Outdoor Living')]
        families = {seed['source_family'] for seed in seeds}
        self.assertEqual(families, {'community_forum', 'marketplace_review'})

    def test_camping_has_multiple_exact_ecamping_pages_plus_lightgear(self):
        seeds = verified.VERIFIED_PUBLIC_SEEDS[('Sports & Outdoors', 'Camping & Hiking')]
        domains = [verified.consumer.host(seed['url']) for seed in seeds]
        self.assertGreaterEqual(domains.count('e-camping.gr'), 4)
        self.assertIn('lightgear.gr', domains)
        self.assertEqual({seed['source_family'] for seed in seeds}, {'community_forum', 'community_blog'})
        self.assertEqual(len({seed['url'] for seed in seeds}), len(seeds))

    def test_root_ecamping_actual_reliability_report_can_emit_pain(self):
        seed = dict(verified.VERIFIED_PUBLIC_SEEDS[('Sports & Outdoors', 'Camping & Hiking')][0])
        text = (
            'Αγορασα τέσσερα φουσκωτά στρώματα για camping και τα δύο έσκασαν μετά από δύο βράδια. '
            'Ο φίλος μου πήρε τέσσερα και δύο ξεφούσκωσαν μέσα στη δοκιμή.'
        )
        row = {'url': seed['url'], 'title': seed['title']}
        stems = (*verified.consumer.PAIN_STEMS, 'εσκα', 'ξεφουσκ')
        with patch.object(verified.consumer, 'PAIN_STEMS', stems), patch.object(
            verified.consumer, '_fetch_text', return_value=(row, text, None)
        ):
            evidence, diagnostic = verified._extract_seed(seed, ['Camping & Hiking'])
        self.assertGreaterEqual(len(evidence), 1)
        self.assertEqual(evidence[0]['metadata']['source_family'], 'community_forum')
        self.assertTrue(evidence[0]['metadata']['consumer_text'])
        self.assertTrue(evidence[0]['metadata']['eligible_for_pain_audit'])
        self.assertFalse(diagnostic['metadata']['eligible_for_pain_audit'])

    def test_page70_daily_air_loss_can_emit_separate_content_hash(self):
        seed = dict(verified.VERIFIED_PUBLIC_SEEDS[('Sports & Outdoors', 'Camping & Hiking')][1])
        text = (
            'Εχω αυτό το φουσκωτό στρώμα. Κάθε βράδυ το φουσκώνω και κάθε πρωί έχει χάσει '
            'τουλάχιστον το μισό αέρα, οπότε το πρόβλημα επαναλαμβάνεται καθημερινά.'
        )
        row = {'url': seed['url'], 'title': seed['title']}
        stems = (*verified.consumer.PAIN_STEMS, 'χανει αερ', 'μισο αερ')
        with patch.object(verified.consumer, 'PAIN_STEMS', stems), patch.object(
            verified.consumer, '_fetch_text', return_value=(row, text, None)
        ):
            evidence, _ = verified._extract_seed(seed, ['Camping & Hiking'])
        self.assertGreaterEqual(len(evidence), 1)
        self.assertTrue(evidence[0]['content_hash'])

    def test_separate_ecamping_thread_can_emit_deflation_pain(self):
        seed = dict(verified.VERIFIED_PUBLIC_SEEDS[('Sports & Outdoors', 'Camping & Hiking')][2])
        text = (
            'Πηρα φουσκωτό στρώμα camping και μετά από λίγες μέρες ξεφουσκώνει. '
            'Το βράδυ ο ύπνος γίνεται δύσκολος και χρειάζεται πάλι φούσκωμα.'
        )
        row = {'url': seed['url'], 'title': seed['title']}
        stems = (*verified.consumer.PAIN_STEMS, 'ξεφουσκ')
        with patch.object(verified.consumer, 'PAIN_STEMS', stems), patch.object(
            verified.consumer, '_fetch_text', return_value=(row, text, None)
        ):
            evidence, _ = verified._extract_seed(seed, ['Camping & Hiking'])
        self.assertGreaterEqual(len(evidence), 1)
        self.assertEqual(evidence[0]['metadata']['source_family'], 'community_forum')

    def test_lightgear_user_comment_keeps_independent_family(self):
        seed = dict(verified.VERIFIED_PUBLIC_SEEDS[('Sports & Outdoors', 'Camping & Hiking')][-1])
        text = (
            'Αγορασα πρόσφατα ένα αυτοφούσκωτο υπόστρωμα camping. Προσπαθώ να το '
            'ξεφουσκώσω και δεν ξεφουσκώνει με τίποτα, οπότε δυσκολεύομαι πολύ να το μαζέψω.'
        )
        row = {'url': seed['url'], 'title': seed['title']}
        stems = (*verified.consumer.PAIN_STEMS, 'ξεφουσκ', 'δεν ξεφουσκ')
        with patch.object(verified.consumer, 'PAIN_STEMS', stems), patch.object(
            verified.consumer, '_fetch_text', return_value=(row, text, None)
        ):
            evidence, diagnostic = verified._extract_seed(seed, ['Camping & Hiking'])
        self.assertGreaterEqual(len(evidence), 1)
        self.assertEqual(evidence[0]['metadata']['source_family'], 'community_blog')
        self.assertTrue(evidence[0]['metadata']['eligible_for_pain_audit'])
        self.assertFalse(diagnostic['metadata']['eligible_for_pain_audit'])

    def test_direct_fetch_diagnostics_precede_broad_discovery(self):
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
                'collector': 'verified_public_seed_v418',
                'body': '',
                'metadata': {'eligible_for_pain_audit': False},
            }))
        with patch.object(verified, '_ORIGINAL_COLLECT', return_value=base), patch.object(
            verified, '_extract_seed', side_effect=diagnostic_rows
        ):
            rows = verified.collect_consumer_evidence(
                'Sports & Outdoors', 'Camping & Hiking', [], ['Camping & Hiking'], max_rows=len(seeds)
            )
        self.assertEqual(len(rows), len(seeds))
        self.assertTrue(all(row.get('collector') == 'verified_public_seed_v418' for row in rows))

    def test_fetch_failure_never_creates_pain_evidence(self):
        seed = dict(verified.VERIFIED_PUBLIC_SEEDS[('Sports & Outdoors', 'Camping & Hiking')][0])
        row = {'url': seed['url'], 'title': seed['title']}
        with patch.object(verified.consumer, '_fetch_text', return_value=(row, None, 'http_403')):
            evidence, diagnostic = verified._extract_seed(seed, ['Camping & Hiking'])
        self.assertEqual(evidence, [])
        self.assertEqual(diagnostic['metadata']['fetch_error'], 'http_403')
        self.assertFalse(diagnostic['metadata']['eligible_for_pain_audit'])

    def test_collector_and_retrieval_are_versioned_v418(self):
        seed = dict(verified.VERIFIED_PUBLIC_SEEDS[('Sports & Outdoors', 'Camping & Hiking')][0])
        text = 'Αγορασα φουσκωτό στρώμα camping και ξεφούσκωσε αμέσως, μεγάλο πρόβλημα.'
        row = {'url': seed['url'], 'title': seed['title']}
        with patch.object(verified.consumer, 'PAIN_STEMS', (*verified.consumer.PAIN_STEMS, 'ξεφουσκ')), patch.object(
            verified.consumer, '_fetch_text', return_value=(row, text, None)
        ):
            evidence, diagnostic = verified._extract_seed(seed, ['Camping & Hiking'])
        self.assertGreaterEqual(len(evidence), 1)
        self.assertEqual(evidence[0]['collector'], 'verified_public_extract_v418')
        self.assertEqual(evidence[0]['metadata']['retrieval_version'], 'verified_public_v4.18')
        self.assertEqual(diagnostic['collector'], 'verified_public_seed_v418')


if __name__ == '__main__':
    unittest.main()
