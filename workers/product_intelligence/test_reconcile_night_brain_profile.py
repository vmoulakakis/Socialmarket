from __future__ import annotations

import copy
import unittest

from reconcile_night_brain_profile import reconcile


class ReconcileNightBrainProfileTests(unittest.TestCase):
    def base_profile(self):
        return {
            "engine_version": "affiliate_night_brain_v1",
            "saved_rankings": 100,
            "owner_min_expected_commission_eur": 10,
            "effective_promotion_commission_floor_eur": 10,
            "bulk_feed_to_llm": False,
            "paid_llm_required": False,
            "paid_inference_cost_usd": 0,
            "creative": {
                "creative_status": "completed",
                "creative_ready": 20,
                "creative_rankings_persisted": 20,
                "creative_asset_packs": 16,
                "creative_assets": 48,
                "final_contract": {
                    "ok": True,
                    "ranked": 100,
                    "creatives": 20,
                    "content_packs": 20,
                    "creative_assets": 60,
                },
            },
        }

    def test_final_contract_reconciles_recovered_assets(self):
        profile = reconcile(self.base_profile())
        creative = profile["creative"]
        self.assertEqual(creative["creative_assets"], 60)
        self.assertEqual(creative["creative_asset_packs"], 20)
        self.assertTrue(creative["asset_count_reconciled_from_final_contract"])
        self.assertEqual(
            creative["pre_finalize_asset_counts"],
            {"creative_assets": 48, "creative_asset_packs": 16},
        )
        self.assertEqual(profile["contract_validation"]["status"], "PASS")

    def test_does_not_reconcile_an_invalid_final_contract(self):
        profile = self.base_profile()
        profile["creative"]["final_contract"]["creative_assets"] = 59
        with self.assertRaises(RuntimeError):
            reconcile(profile)

    def test_business_floor_remains_fail_closed(self):
        profile = self.base_profile()
        profile["owner_min_expected_commission_eur"] = 9.99
        with self.assertRaises(RuntimeError):
            reconcile(profile)

    def test_clean_profile_is_not_marked_reconciled(self):
        profile = self.base_profile()
        profile["creative"]["creative_asset_packs"] = 20
        profile["creative"]["creative_assets"] = 60
        result = reconcile(copy.deepcopy(profile))
        self.assertFalse(result["creative"]["asset_count_reconciled_from_final_contract"])
        self.assertNotIn("pre_finalize_asset_counts", result["creative"])


if __name__ == "__main__":
    unittest.main()
