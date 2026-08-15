import unittest

from consumer_evidence_v4 import _consumer_score, _split_segments, source_family


class ConsumerEvidenceV4Tests(unittest.TestCase):
    def test_marketplace_review_with_real_pain_and_category_binding_passes(self):
        text='Αγόρασα το κινητό πριν έναν μήνα αλλά η μπαταρία τελειώνει πολύ γρήγορα και υπερθερμαίνεται.'
        score,pain,purchase,first=_consumer_score(text,'Smartphone 5G αξιολογήσεις',['κινητα','smartphone'],'marketplace_review')
        self.assertGreaterEqual(score,9)
        self.assertTrue(pain)
        self.assertTrue(purchase)
        self.assertTrue(first)

    def test_navigation_boilerplate_is_rejected(self):
        text='Μετάβαση στο περιεχόμενο. Κανένα προϊόν στο καλάθι. Δημιουργία λογαριασμού.'
        score,_,_,_=_consumer_score(text,'Παιδικά ρούχα',['παιδικα ρουχα'],'public_web')
        self.assertEqual(score,0)

    def test_generic_problem_without_taxonomy_binding_is_rejected(self):
        text='Αγόρασα το προϊόν και έχω μεγάλο πρόβλημα με την παράδοση και θέλω επιστροφή.'
        score,_,_,_=_consumer_score(text,'Γενική είδηση αγοράς',['αντηλιακα','αντηλιακο'],'public_web')
        self.assertEqual(score,0)

    def test_source_family_is_explicit(self):
        self.assertEqual(source_family('https://www.skroutz.gr/s/123/test')[0],'marketplace_review')
        self.assertEqual(source_family('https://www.insomnia.gr/forums/topic/123')[0],'community_forum')
        self.assertEqual(source_family('https://www.reddit.com/r/greece/comments/abc')[0],'social_forum')

    def test_segmenter_keeps_real_review_units(self):
        text='Πρώτη σύντομη πρόταση.\nΑγόρασα τη συσκευή και μετά από λίγες μέρες εμφάνισε πρόβλημα με θόρυβο και διαρροή νερού.\nΆλλη παράγραφος που είναι αρκετά μεγάλη για να θεωρηθεί πραγματικό consumer text και όχι navigation.'
        segments=_split_segments(text)
        self.assertTrue(any('διαρροή' in x for x in segments))


if __name__=='__main__':
    unittest.main()
