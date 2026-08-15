import unittest

from semantic_taxonomy import classify_label, resolve_taxonomy
from audit_agent import _taxonomy_audit


class SemanticTaxonomyTests(unittest.TestCase):
    def test_navigation_noise(self):
        for label in [
            'Sign Up','Skip to content','Skip to the content','Skip to main content',
            'Μετάβαση στο περιεχόμενο','Παράλειψη','Σύνδεση','Εγγραφή','Ο Λογαριασμός μου',
            'Όροι Χρήσης','πολιτική απορρήτου','cookies'
        ]:
            self.assertNotEqual(classify_label(label)['role'], 'product_taxonomy', label)

    def test_location_theme_brand_language_are_not_taxonomy(self):
        expected = {
            'Αθήνα':'location',
            'Back To School':'theme',
            'TOMMY HILFIGER':'brand_or_collection',
            'English':'language',
        }
        for label, role in expected.items():
            self.assertEqual(classify_label(label)['role'], role, label)

    def test_real_product_labels_map_to_canonical_taxonomy(self):
        cases = {
            'Αντηλιακά':('Beauty & Personal Care','Sun Care'),
            'Μπλούζες με στάμπα':('Fashion & Accessories','Apparel'),
            'Πίνακες σε καμβα':('Home & Garden','Home Decor'),
            'Σχολικά είδη και τετράδια':('Kids & Baby','School Supplies'),
            'Laptop και υπολογιστές':('Electronics & Technology','Computers & Laptops'),
        }
        for label, target in cases.items():
            got = classify_label(label)
            self.assertEqual(got['role'], 'product_taxonomy', label)
            self.assertEqual((got['category'],got['subcategory']), target, label)

    def test_resolver_ignores_navigation_and_campaign_labels(self):
        anchors = ['Sign Up','Skip to content','Αθήνα','Back To School','TOMMY HILFIGER','Μπλούζες με στάμπα','SALE -50%']
        r = resolve_taxonomy('Example Store','ρούχα μπλούζες clothing apparel fashion',anchors,'Fashion',None)
        self.assertEqual(r.category,'Fashion & Accessories')
        self.assertEqual(r.subcategory,'Apparel')
        accepted = [x['label'] for x in r.label_audit if x.get('role')=='product_taxonomy']
        self.assertIn('Μπλούζες με στάμπα',accepted)
        self.assertNotIn('Sign Up',accepted)
        self.assertNotIn('Back To School',accepted)

    def test_unknown_site_does_not_promote_raw_anchor_to_subcategory(self):
        anchors=['Sign Up','Skip to content','English','Αθήνα','Company Company Company']
        r=resolve_taxonomy('Unknown Merchant','generic company page',anchors,None,None)
        self.assertEqual(r.category,'Other')
        self.assertIsNone(r.subcategory)

    def test_audit_blocks_semantically_invalid_subcategory(self):
        score,reasons,contradictions=_taxonomy_audit({'category':'Travel','subcategory':'Sign Up'})
        self.assertLess(score,65)
        self.assertTrue(any('invalid_taxonomy_role' in x for x in contradictions))

    def test_audit_accepts_canonical_pair(self):
        score,reasons,contradictions=_taxonomy_audit({'category':'Home & Garden','subcategory':'Home Decor'})
        self.assertEqual(score,100)
        self.assertFalse(contradictions)


if __name__ == '__main__':
    unittest.main()
