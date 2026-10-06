from __future__ import annotations

import unittest
import sys
import types
from unittest.mock import Mock, patch

try:
    import requests  # noqa: F401
except ModuleNotFoundError:
    sys.modules["requests"] = types.SimpleNamespace(
        get=Mock(),
        post=Mock(),
        RequestException=Exception,
    )

import deep_demand_gap_harvester_v2 as harvester


class UrlSafetyTests(unittest.TestCase):
    def test_canonical_url_rejects_non_http_schemes(self):
        self.assertIsNone(harvester.canonical_url("file:///etc/passwd"))
        self.assertIsNone(harvester.canonical_url("javascript:alert(1)"))

    def test_domain_match_does_not_accept_suffix_attack(self):
        self.assertTrue(harvester.domain_matches("https://www.skroutz.gr/s/1", "skroutz.gr"))
        self.assertFalse(harvester.domain_matches("https://evil-skroutz.gr/s/1", "skroutz.gr"))
        self.assertFalse(harvester.domain_matches("https://skroutz.gr.evil.test/s/1", "skroutz.gr"))

    @patch.object(harvester.requests, "get")
    def test_redirect_outside_allowlist_is_blocked(self, get):
        response = Mock(status_code=302, headers={"location": "https://evil.test/private"})
        get.return_value = response
        text, status, error = harvester.fetch_public_text(
            "https://skroutz.gr/s/1", "skroutz.gr"
        )
        self.assertIsNone(text)
        self.assertEqual(status, "blocked")
        self.assertEqual(error, "redirect_outside_allowlist")
        self.assertEqual(get.call_count, 1)

    @patch.object(harvester.requests, "get")
    def test_full_text_fetch_removes_script_content(self, get):
        response = Mock(
            status_code=200,
            headers={"content-type": "text/html; charset=utf-8"},
            content=b"x" * 500,
            text="<html><script>ignore me</script><body>" + ("Useful customer evidence. " * 12) + "</body></html>",
        )
        get.return_value = response
        text, status, error = harvester.fetch_public_text(
            "https://www.skroutz.gr/s/1", "skroutz.gr"
        )
        self.assertEqual(status, "full_text")
        self.assertIsNone(error)
        self.assertIn("Useful customer evidence", text)
        self.assertNotIn("ignore me", text)


class QueryConstructionTests(unittest.TestCase):
    def test_source_query_is_bound_to_problem_and_domain(self):
        topic = {"problem_title": "Αυτόματο πότισμα διακοπών"}
        plan = harvester.SOURCE_PLANS[0]
        query = harvester.build_query(topic, plan)
        self.assertIn('"Αυτόματο πότισμα διακοπών"', query)
        self.assertIn("site:insomnia.gr", query)

    def test_document_budget_is_allocated_round_robin_across_sources(self):
        plans = (
            harvester.SourcePlan("consumer_forum", "forum", "forum.gr", "pain", ("pain",)),
            harvester.SourcePlan("marketplace_supply", "market", "market.gr", "price", ("competitor",)),
            harvester.SourcePlan("retailer_supply", "retailer", "retailer.gr", "stock", ("competitor",)),
        )

        def fake_search(query, limit):
            domain = query.rsplit("site:", 1)[-1]
            return [
                {"url": f"https://{domain}/p/{idx}", "title": f"doc {idx}", "content": "useful evidence text"}
                for idx in range(limit)
            ]

        with patch.object(harvester, "SOURCE_PLANS", plans), patch.object(
            harvester, "searx_search", side_effect=fake_search
        ):
            documents, _ = harvester.collect_documents(
                {"problem_title": "problem"}, per_source=2, max_documents=3
            )
        self.assertEqual(
            {row["source_name"] for row in documents},
            {"forum", "market", "retailer"},
        )


if __name__ == "__main__":
    unittest.main()
