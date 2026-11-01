import unittest
from workers.product_intelligence.market_brain_v3 import keywords,candidate_gate,shortlist,normalize

class MarketBrainSafetyTests(unittest.TestCase):
 def test_unicode_greek(self):
  self.assertIn("διαρρο",keywords("Διαρροής νερού"))
 def test_matching_real_solution(self):
  p={"id":"1","title":"Κρυφές διαρροές σε τοίχους","description":"Ανίχνευση διαρροής νερού"}
  d={"id":"2","title":"Ανιχνευτής διαρροής νερού σε τοίχους"}
  m=candidate_gate(p,d)
  self.assertIsNotNone(m)
  self.assertEqual(m.status,"needs_evidence")
  self.assertGreaterEqual(len(m.shared_concepts),2)
 def test_prevent_hallucinated_furniture_leak_link(self):
  p={"id":"1","title":"Κρυφές διαρροές σε τοίχους","description":"Ανίχνευση διαρροής νερού"}
  for title in ["Σκουλαρίκια Κόμπος Ηρακλή μεγάλο μέγεθος","Ρουστίκ κρεβάτι από ξύλο","Καναπές με τη καλύτερη τιμή"]:
   self.assertIsNone(candidate_gate(p,{"id":"2","title":title}))
 def test_one_generic_token_is_not_enough(self):
  p={"id":"1","title":"Καλύτερη τιμή χωρίς απώλεια εμπιστοσύνης","description":""}
  self.assertIsNone(candidate_gate(p,{"id":"2","title":"Πτήση με την καλύτερη τιμή"}))
 def test_results_never_verified(self):
  xs=shortlist([{"id":"1","title":"ανίχνευση πτώσης ηλικιωμένων","description":"ειδοποίηση πτώσης"}],
    [{"id":"3","title":"Αισθητήρας πτώσης ηλικιωμένων με ειδοποίηση"}])
  self.assertTrue(xs)
  self.assertTrue(all(x.status=="needs_evidence" for x in xs))

if __name__=="__main__":unittest.main()
