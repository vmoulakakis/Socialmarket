import unittest
from workers.product_intelligence.linkwise_delta_stream_v1 import (
    canonical_key,transform_delta,valid_source_url
)
class LinkwiseDeltaContract(unittest.TestCase):
    def setUp(self):
        self.row={"product_id":"350254919_204","product_name":"Καναπές","price":"159.00","currency":"EUR",
          "tracking_url":"https://go.linkwi.se/z/23-0/CD104/?lnkurl=https%3A%2F%2Fexample.com",
          "in_stock":"true","valid_to":None}
    def test_same_legacy_identity_does_not_hash(self):
        a=transform_delta(self.row)
        self.assertEqual(a["record_key"],"23|350254919_204")
        self.assertEqual(a["program_id"],"23")
        self.assertEqual(a["source_product_id"],"350254919_204")
    def test_price_changes_do_not_change_key(self):
        a=transform_delta(self.row)
        b=transform_delta({**self.row,"price":"119"})
        self.assertEqual(a["record_key"],b["record_key"])
        self.assertNotEqual(a["content_sha256"],b["content_sha256"])
    def test_expiry_kept_and_merchant_unresolved_quarantined(self):
        a=transform_delta({**self.row,"tracking_url":"","valid_to":"2025-01-01T00:00:00Z"})
        self.assertEqual(a["program_id"],"unknown")
        self.assertIn("unknown_linkwise_program",a["quarantine_reason"])
        self.assertIn("offer_expired",a["quarantine_reason"])
    def test_invalid_or_future_validity(self):
        malformed=transform_delta({**self.row,"valid_to":"bad-timestamp"})
        self.assertIn("invalid_valid_to",malformed["quarantine_reason"])
        future=transform_delta({**self.row,"valid_from":"2099-12-31T00:00:00Z"})
        self.assertIn("offer_not_yet_active",future["quarantine_reason"])
    def test_data_fields_preserved(self):
        a=transform_delta({**self.row,"extra_images":["a","b"],"city":"Αθήνα","latitude":"37.98"})
        self.assertEqual(a["raw_json"]["extra_images"],["a","b"])
        self.assertEqual(a["raw_json"]["city"],"Αθήνα")
    def test_source_whitelist(self):
        good="https://affiliate.linkwi.se/feeds/1.2/CD104/programs-all/columns-product_id,price/proginc-0/feed.json"
        self.assertTrue(valid_source_url(good))
        self.assertFalse(valid_source_url("http://affiliate.linkwi.se/feeds/1.2/CD104/programs-all/a/feed.json"))
        self.assertFalse(valid_source_url("https://evil.example/feeds/1.2/CD104/programs-all/a/feed.json"))
        self.assertFalse(valid_source_url("https://affiliate.linkwi.se.evil.example/feeds/1.2/CD104/programs-all/a/feed.json"))
    def test_no_product_id_fails_not_random_identity(self):
        with self.assertRaises(ValueError):
            transform_delta({**self.row,"product_id":""})
    def test_invalid_identifier_fails(self):
        with self.assertRaises(ValueError):
            canonical_key("23","id|bad")
if __name__=="__main__":
    unittest.main()
