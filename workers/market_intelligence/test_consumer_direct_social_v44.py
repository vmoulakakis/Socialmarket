from __future__ import annotations

import unittest

import consumer_source_expansion_v43 as expansion
expansion.apply()
import consumer_direct_social_v44 as social


class DirectSocialV44Test(unittest.TestCase):
    def test_product_bound_first_person_pain_survives(self):
        row=social._row(
            'https://www.reddit.com/r/greece/comments/test',
            'Ακουστικά Bluetooth εμπειρία',
            'Αγόρασα αυτά τα ακουστικά και μετά από δύο μήνες χάλασε η μπαταρία και αποσυνδέονται συνέχεια.',
            ['ακουστικά','bluetooth','ηχεία'],
            'social_forum','test',{},.76
        )
        self.assertIsNotNone(row)
        self.assertTrue(row['metadata']['consumer_text'])
        self.assertEqual(row['metadata']['source_family'],'social_forum')

    def test_service_only_complaint_without_taxonomy_is_rejected(self):
        row=social._row(
            'https://www.reddit.com/r/greece/comments/test2',
            'Κακή εξυπηρέτηση',
            'Παρήγγειλα και άργησαν πολύ να απαντήσουν στο τηλέφωνο, απαράδεκτη εξυπηρέτηση.',
            ['ακουστικά','bluetooth','ηχεία'],
            'social_forum','test',{},.76
        )
        self.assertIsNone(row)

    def test_generic_praise_is_not_pain(self):
        row=social._row(
            'https://www.youtube.com/watch?v=test',
            'Review ακουστικά',
            'Έχω αυτά τα ακουστικά και είμαι πολύ ευχαριστημένος, όλα λειτουργούν τέλεια.',
            ['ακουστικά','bluetooth','ηχεία'],
            'social_video','test',{},.74
        )
        self.assertIsNone(row)


if __name__=='__main__':
    unittest.main()
