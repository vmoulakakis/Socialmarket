"""Read-only contract tests: python -m unittest discover -s tests -p test_linkwise_only_policy.py"""
import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest

P = Path(__file__).resolve().parents[1] / "workers" / "product_intelligence" / "linkwise_only_policy.py"
spec = importlib.util.spec_from_file_location("linkwise_only_policy", P)
policy = importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name] = policy
spec.loader.exec_module(policy)

LINK = "https://go.linkwi.se/z/205-0/CD104/?lnkurl=https%3A%2F%2Fxenodoxeio.gr%2Fhotels"


class LinkwiseOnlyContractTests(unittest.TestCase):
    def setUp(self):
        self.registry = {"205": policy.Program("205", "Xenodoxeio", "xenodoxeio.gr", True, True)}
        self.now = datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc)

    def test_linkwise_route_extracts_program(self):
        self.assertEqual(policy.route_program_id(LINK), "205")
        self.assertIsNone(policy.route_program_id("https://other.example/z/205-0/CD104/"))

    def test_target_domain_does_not_follow_redirects(self):
        self.assertEqual(policy.destination_domain(LINK), "xenodoxeio.gr")

    def test_exact_program_match(self):
        result = policy.match_program("205", LINK, self.registry)
        self.assertEqual(result.status, "matched")

    def test_explicit_identity_conflict_fails_closed(self):
        self.assertEqual(policy.match_program("23", LINK, self.registry).status, "conflict")

    def test_no_automatic_domain_only_approval(self):
        link = "https://go.linkwi.se/l/?lnkurl=https%3A%2F%2Fxenodoxeio.gr%2F"
        self.assertEqual(policy.match_program(None, link, self.registry).status, "review")

    def test_unknown_program_does_not_pass(self):
        self.assertEqual(policy.match_program("unknown", "https://go.linkwi.se/z/999-0/CD104/", self.registry).status, "unmatched")

    def test_approval_and_tracking_both_required(self):
        registry = {"205": policy.Program("205", "Xenodoxeio", "xenodoxeio.gr", False, True)}
        self.assertEqual(policy.match_program(None, LINK, registry).status, "verification_required")

    def test_weekly_not_daily(self):
        last = self.now - timedelta(days=6)
        self.assertFalse(policy.weekly_scan_due(last, self.now))
        self.assertTrue(policy.weekly_scan_due(last, self.now + timedelta(days=1)))
        self.assertTrue(policy.weekly_scan_due(None, self.now))

    def test_only_new_products_admitted_by_discovery(self):
        self.assertEqual(policy.discovery_decision(True, None, self.now), "SKIP_EXISTING")
        self.assertEqual(policy.discovery_decision(False, None, self.now), "INSERT_NEW")

    def test_explicit_expiry_not_inferred_from_absence(self):
        self.assertEqual(policy.discovery_decision(True, self.now, self.now), "EXPIRE")
        self.assertEqual(policy.discovery_decision(False, self.now + timedelta(days=2), self.now), "INSERT_NEW")

    def test_epc_units_and_approved_profit(self):
        self.assertAlmostEqual(policy.epc100_to_per_click(15.86), 0.1586)
        self.assertAlmostEqual(policy.approved_epc_per_click(25, 2, 80), 0.4)
        with self.assertRaises(ValueError):
            policy.epc100_to_per_click(-1)


if __name__ == "__main__":
    unittest.main()
