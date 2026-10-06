from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from gap_solver_scoring import (
    GapSolverPolicy,
    paid_required_commission,
    score_problem_evidence,
    score_product_candidate,
)


NOW = datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc)


def evidence_row(
    idx: int,
    claim_type: str,
    strength: float,
    *,
    family: str = "consumer_forum",
    domain: str | None = None,
    tier: str = "full_text",
    polarity: str = "supports",
    competitor: str | None = None,
):
    domain = domain or f"source{idx}.gr"
    return {
        "id": f"e{idx}",
        "content_hash": f"hash-{idx}",
        "claim_type": claim_type,
        "strength_score": strength,
        "relevance_score": 94,
        "confidence": 0.90,
        "source_family": family,
        "source_domain": domain,
        "source_independence_key": f"{domain}:doc-{idx}",
        "evidence_tier": tier,
        "provenance_class": "inferred",
        "polarity": polarity,
        "facts": {"competitor_key": competitor} if competitor else {},
        "observed_at": NOW.isoformat(),
    }


def strong_problem_evidence():
    return [
        evidence_row(1, "pain", 92, family="consumer_forum"),
        evidence_row(2, "pain", 86, family="marketplace_review"),
        evidence_row(3, "purchase_intent", 90, family="consumer_forum"),
        evidence_row(4, "purchase_intent", 84, family="search_intent"),
        evidence_row(5, "search_interest", 78, family="search_intent", tier="snippet"),
        evidence_row(6, "availability_gap", 96, family="greek_retail", competitor="shop-a"),
        evidence_row(7, "market_gap", 94, family="greek_retail", competitor="shop-b"),
        evidence_row(8, "exact_solution", 5, family="marketplace_supply", competitor="shop-a"),
        evidence_row(9, "exact_solution", 8, family="marketplace_supply", competitor="shop-b"),
        evidence_row(10, "competitor", 10, family="greek_retail", competitor="shop-c"),
        evidence_row(11, "price_friction", 92, family="greek_retail", competitor="shop-c"),
    ]


def valid_problem(**overrides):
    values = {
        "eligible_to_source": True,
        "strong_gap": True,
        "demand_score": 88,
        "gap_score": 91,
        "competition_score": 12,
        "evidence_score": 95,
        "confidence": 0.88,
        "contradiction_ratio": 0.02,
        "solution_requirements": [
            {"id": "r1", "text": "automatic watering timer", "required": True, "weight": 1},
            {"id": "r2", "text": "adjustable drip irrigation", "required": True, "weight": 1},
        ],
        "problem_title": "Reliable automatic watering while away",
        "problem_description": "Users need adjustable drip irrigation for balcony plants.",
    }
    values.update(overrides)
    return values


def valid_product(**overrides):
    values = {
        "source_key": "aliexpress",
        "source_product_id": "100500123",
        "title": "Automatic Watering Timer Adjustable Drip Irrigation Kit",
        "category": "Garden irrigation",
        "product_url": "https://www.aliexpress.com/item/100500123.html",
        "image_url": "https://ae01.alicdn.com/kf/example.jpg",
        "promotion_url": "https://s.click.aliexpress.com/e/example",
        "price_eur": 200,
        "commission_rate": 0.30,
        "expected_commission_eur": 60,
        "offer_observed_at": NOW.isoformat(),
        "seller_evidence": {"evaluate_rate": "98%"},
        "review_evidence": {"review_count": 1200},
        "offer_raw_payload": {
            "product_title": "Automatic Watering Timer Adjustable Drip Irrigation Kit",
            "sale_price_currency": "EUR",
            "lastest_volume": 12000,
        },
        "product_raw_payload": {
            "product_title": "Automatic Watering Timer Adjustable Drip Irrigation Kit",
            "second_level_category_name": "Garden irrigation",
        },
    }
    values.update(overrides)
    return values


class ProblemEvidenceScoringTests(unittest.TestCase):
    def test_triangulated_full_text_evidence_validates_strong_gap(self):
        result = score_problem_evidence(strong_problem_evidence(), now=NOW)
        self.assertTrue(result["eligible_to_source"])
        self.assertTrue(result["strong_gap"])
        self.assertGreaterEqual(result["demand_score"], 72)
        self.assertGreaterEqual(result["gap_score"], 85)
        self.assertGreaterEqual(result["competitors_audited"], 3)
        self.assertGreaterEqual(result["source_family_count"], 2)

    def test_snippets_cannot_prove_pain_or_buyer_intent(self):
        rows = [
            evidence_row(i, "pain" if i % 2 else "purchase_intent", 95, tier="snippet", family=f"family-{i % 3}")
            for i in range(1, 10)
        ]
        rows.extend([
            evidence_row(20, "availability_gap", 95, competitor="a"),
            evidence_row(21, "market_gap", 95, competitor="b"),
            evidence_row(22, "competitor", 5, competitor="c"),
        ])
        result = score_problem_evidence(rows, now=NOW)
        self.assertFalse(result["eligible_to_source"])
        self.assertFalse(result["gate_results"]["full_text_pain_proof"])
        self.assertFalse(result["gate_results"]["full_text_buyer_or_first_party_proof"])

    def test_contradictions_remain_visible_and_withhold_sourcing(self):
        rows = strong_problem_evidence()
        rows.extend([
            evidence_row(30 + i, "contradiction", 90, polarity="contradicts", family="counter_evidence")
            for i in range(7)
        ])
        result = score_problem_evidence(rows, now=NOW)
        self.assertFalse(result["eligible_to_source"])
        self.assertFalse(result["gate_results"]["contradiction_limit"])
        self.assertGreater(result["contradiction_ratio"], 0.35)

    def test_stale_evidence_does_not_count(self):
        rows = strong_problem_evidence()
        for row in rows:
            row["observed_at"] = (NOW - timedelta(days=130)).isoformat()
        result = score_problem_evidence(rows, now=NOW)
        self.assertEqual(result["evidence_count"], 0)
        self.assertFalse(result["eligible_to_source"])


class UnitEconomicsTests(unittest.TestCase):
    def test_paid_floor_uses_cpc_cvr_approval_creative_and_margin(self):
        result = paid_required_commission(GapSolverPolicy())
        self.assertTrue(result["valid"])
        self.assertAlmostEqual(result["paid_cost_per_approved_order_eur"], 29.17, places=2)
        self.assertAlmostEqual(result["required_commission_eur"], 45.56, places=2)
        self.assertEqual(result["provenance"], "policy_assumption")

    def test_invalid_paid_inputs_fail_closed(self):
        result = paid_required_commission(
            GapSolverPolicy(), {"click_to_order_rate": 0, "provenance": "observed_first_party"}
        )
        self.assertFalse(result["valid"])
        self.assertIsNone(result["required_commission_eur"])


class ProductLaneScoringTests(unittest.TestCase):
    def test_complete_consumer_solver_enters_paid_test(self):
        result = score_product_candidate(valid_product(), valid_problem(), now=NOW)
        self.assertEqual(result["lane"], "PAID_TEST")
        self.assertEqual(result["verdict"], "ELIGIBLE")
        self.assertGreaterEqual(result["expected_commission_eur"], result["paid_required_commission_eur"])

    def test_medium_commission_stays_organic(self):
        product = valid_product(price_eur=100, commission_rate=0.20, expected_commission_eur=20)
        product["offer_raw_payload"]["sale_price_currency"] = "EUR"
        problem = valid_problem(strong_gap=False, gap_score=78)
        result = score_product_candidate(product, problem, now=NOW)
        self.assertEqual(result["lane"], "ORGANIC_TEST")
        self.assertIn("paid_gate:strong_gap", result["reason_codes"])

    def test_high_commission_never_overrides_missing_problem_proof(self):
        problem = valid_problem(eligible_to_source=False, strong_gap=False, evidence_score=20)
        result = score_product_candidate(valid_product(), problem, now=NOW)
        self.assertEqual(result["lane"], "WATCH")
        self.assertEqual(result["verdict"], "WITHHELD")
        self.assertIn("problem_not_validated", result["reason_codes"])

    def test_linkwise_is_rejected_by_construction(self):
        result = score_product_candidate(valid_product(source_key="linkwise"), valid_problem(), now=NOW)
        self.assertEqual(result["lane"], "REJECT")
        self.assertIn("hard_gate:aliexpress_only", result["reason_codes"])

    def test_missing_tracking_url_is_rejected(self):
        result = score_product_candidate(valid_product(promotion_url=None), valid_problem(), now=NOW)
        self.assertEqual(result["lane"], "REJECT")
        self.assertIn("hard_gate:identity_complete", result["reason_codes"])

    def test_non_aliexpress_tracking_domain_is_rejected(self):
        result = score_product_candidate(
            valid_product(promotion_url="https://tracking.example.test/click"), valid_problem(), now=NOW
        )
        self.assertEqual(result["lane"], "REJECT")
        self.assertFalse(result["gate_results"]["identity"]["promotion_url"])

    def test_technical_product_routes_to_b2b_search(self):
        product = valid_product(
            title="Digital Oscilloscope Industrial Measurement Diagnostic Kit",
            category="Measurement instruments",
            product_raw_payload={
                "product_title": "Digital Oscilloscope Industrial Measurement Diagnostic Kit",
                "second_level_category_name": "Measurement instruments",
            },
            offer_raw_payload={
                "product_title": "Digital Oscilloscope Industrial Measurement Diagnostic Kit",
                "sale_price_currency": "EUR",
                "lastest_volume": 9000,
            },
        )
        problem = valid_problem(solution_requirements=[
            {"id": "r1", "text": "digital oscilloscope", "required": True},
            {"id": "r2", "text": "industrial measurement diagnostic", "required": True},
        ])
        result = score_product_candidate(product, problem, now=NOW)
        self.assertEqual(result["lane"], "B2B_SEARCH")
        self.assertEqual(result["verdict"], "ELIGIBLE")


if __name__ == "__main__":
    unittest.main()
