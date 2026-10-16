import unittest
from datetime import datetime, timezone

from workers.product_intelligence.linkwise_weekly_policy import (
    canonical_product_key, content_fingerprint, classify_offer
)


class LinkwiseWeeklyPolicyTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 16, tzinfo=timezone.utc)
        self.product = {
            "product_name": "Cabin suitcase",
            "price_eur": 150,
            "currency": "EUR",
            "in_stock": None,
            "valid_to": "2026-11-01T00:00:00Z",
            "tracking_url": "https://example.invalid/affiliate",
        }

    def test_stable_identity_does_not_include_price(self):
        self.assertEqual(canonical_product_key("205", "P123"), "205:P123")
        with self.assertRaises(ValueError):
            canonical_product_key("unknown", "P123")

    def test_new_then_unchanged(self):
        self.assertEqual(classify_offer(self.product, None, now=self.now), "NEW")
        fingerprint = content_fingerprint(self.product)
        self.assertEqual(classify_offer(self.product, fingerprint, now=self.now), "UNCHANGED")

    def test_price_change_is_changed(self):
        fingerprint = content_fingerprint(self.product)
        updated = {**self.product, "price_eur": 135}
        self.assertEqual(classify_offer(updated, fingerprint, now=self.now), "CHANGED")

    def test_expired_is_not_published(self):
        expired = {**self.product, "valid_to": "2026-10-15T23:59:59Z"}
        self.assertEqual(classify_offer(expired, None, now=self.now), "EXPIRED")

    def test_bad_date_needs_review(self):
        invalid = {**self.product, "valid_to": "not-a-date"}
        self.assertEqual(classify_offer(invalid, None, now=self.now), "NEEDS_REVIEW")

    def test_unknown_stock_is_not_equated_to_false(self):
        self.assertIsNone(self.product["in_stock"])


if __name__ == "__main__":
    unittest.main()
