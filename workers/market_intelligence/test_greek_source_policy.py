import unittest

from greek_source_policy import annotate_evidence, beacon_policy, cap_beacon_concentration, is_demand_beacon


class GreekSourcePolicyTests(unittest.TestCase):
    def test_major_greek_sites_are_beacons_not_competitors(self):
        for domain in ("skroutz.gr", "bestprice.gr", "public.gr", "plaisio.gr", "kotsovolos.gr", "shopflix.gr", "temu.com", "trendyol.com", "aliexpress.com", "lagonika.gr"):
            policy = beacon_policy(domain)
            self.assertEqual(policy["source_role"], "demand_beacon")
            self.assertFalse(policy["competitor_eligible"])
            self.assertTrue(is_demand_beacon("https://www." + domain + "/x"))

    def test_catalogue_presence_is_not_pain_but_review_text_may_be(self):
        catalogue = annotate_evidence({"source_kind": "demand", "source_url": "https://public.gr/p/1", "metadata": {}})
        self.assertFalse(catalogue["metadata"]["pain_eligible_from_catalogue"])
        review = annotate_evidence({"source_kind": "pain_candidate", "source_url": "https://skroutz.gr/s/1", "metadata": {"consumer_text": True, "source_family": "marketplace_review"}})
        self.assertTrue(review["metadata"]["pain_eligible"])

    def test_per_domain_cap_prevents_beacon_flood(self):
        rows = [{"source_url": f"https://skroutz.gr/s/{i}", "metadata": {}} for i in range(10)]
        rows += [{"source_url": "https://independent-shop.gr/p/1", "metadata": {}}]
        capped = cap_beacon_concentration(rows, per_domain=3)
        self.assertEqual(len(capped), 4)


if __name__ == "__main__":
    unittest.main()
