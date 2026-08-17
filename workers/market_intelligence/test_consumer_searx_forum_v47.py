from __future__ import annotations

import unittest
from unittest.mock import patch

import consumer_searx_forum_v47 as v47


class SearxForumV47Tests(unittest.TestCase):
    def test_domain_match_is_strict(self):
        self.assertTrue(v47._domain_match('https://www.bonsaiforum.gr/viewtopic.php?t=9956', 'bonsaiforum.gr'))
        self.assertTrue(v47._domain_match('https://forum.example.gr/x', 'example.gr'))
        self.assertFalse(v47._domain_match('https://public.gr/product/123', 'bonsaiforum.gr'))
        self.assertFalse(v47._domain_match('https://evil-bonsaiforum.gr/x', 'bonsaiforum.gr'))

    def test_result_relevance_rejects_wrong_domain(self):
        row = {
            'url': 'https://public.gr/product/123',
            'title': 'Αυτόματο πότισμα',
            'snippet': 'μπαλκόνι',
        }
        self.assertFalse(v47._result_relevant(row, 'αυτόματο πότισμα μπαλκονιού', 'bonsaiforum.gr'))

    def test_result_relevance_requires_anchor_binding(self):
        good = {
            'url': 'https://bonsaiforum.gr/viewtopic.php?t=9956',
            'title': 'Αυτόματο πότισμα - Ζεστή - Διακοπές',
            'snippet': 'πότισμα σε γλάστρες στο μπαλκόνι',
        }
        bad = {
            'url': 'https://bonsaiforum.gr/viewtopic.php?t=12',
            'title': 'Κλάδεμα πεύκου',
            'snippet': 'συζήτηση για κλάδεμα',
        }
        self.assertTrue(v47._result_relevant(good, 'αυτόματο πότισμα μπαλκονιού', 'bonsaiforum.gr'))
        self.assertFalse(v47._result_relevant(bad, 'αυτόματο πότισμα μπαλκονιού', 'bonsaiforum.gr'))

    def test_fetched_greek_forum_pain_becomes_candidate(self):
        row = {
            'url': 'https://bonsaiforum.gr/viewtopic.php?t=9956',
            'title': 'Αυτόματο πότισμα - Ζεστή - Διακοπές',
            'snippet': '',
            'query': 'site:bonsaiforum.gr αυτόματο πότισμα πρόβλημα',
            'query_term': 'αυτόματο πότισμα',
            'expected_domain': 'bonsaiforum.gr',
        }
        text = (
            'Πρώτη φορά έστησα αυτόματο πότισμα στο μπαλκόνι. '
            'Έβαλα ρυθμιζόμενους σταλάκτες και το μετάνιωσα γιατί με παίδεψαν στη ρύθμιση. '
            'Σε μερικές γλάστρες έπεφτε πολύ νερό και μία σάπισε, οπότε δυσκολεύτηκα να βρω σωστή ροή.'
        )
        keywords = ['αυτόματο πότισμα', 'σταλάκτες', 'μπαλκόνι']
        with patch.object(v47.consumer, '_fetch_text', return_value=(row, text, None)):
            evidence, diagnostic = v47._extract_one(row, keywords)
        self.assertGreaterEqual(len(evidence), 1)
        item = evidence[0]
        self.assertEqual(item['source_kind'], 'pain_candidate')
        self.assertTrue(item['metadata']['consumer_text'])
        self.assertTrue(item['metadata']['eligible_for_pain_audit'])
        self.assertEqual(item['metadata']['source_family'], 'community_forum')
        self.assertGreaterEqual(item['metadata']['consumer_language_score'], 10)
        self.assertGreaterEqual(diagnostic['metadata']['pain_candidates_emitted'], 1)

    def test_fetched_nonpain_forum_text_is_diagnostic_only(self):
        row = {
            'url': 'https://bonsaiforum.gr/viewtopic.php?t=1',
            'title': 'Όμορφα μπονσάι',
            'snippet': '',
            'query': 'site:bonsaiforum.gr μπονσάι',
            'query_term': 'μπονσάι',
            'expected_domain': 'bonsaiforum.gr',
        }
        text = 'Μου αρέσει πολύ το μπονσάι που αγόρασα και το έχω στο μπαλκόνι. Είναι όμορφο και είμαι πολύ ευχαριστημένος.'
        with patch.object(v47.consumer, '_fetch_text', return_value=(row, text, None)):
            evidence, diagnostic = v47._extract_one(row, ['μπονσάι', 'μπαλκόνι'])
        self.assertEqual(evidence, [])
        self.assertEqual(diagnostic['metadata']['pain_candidates_emitted'], 0)
        self.assertGreaterEqual(diagnostic['metadata']['reject_reasons'].get('no_pain_language', 0), 1)


if __name__ == '__main__':
    unittest.main()
