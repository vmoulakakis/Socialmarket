"""Reconcile and validate the Affiliate Night Brain decision profile.

The creative pipeline can recover/re-render missing durable assets at the canonical
persistence boundary. In that case the final Supabase contract is authoritative,
while earlier in-process counters may be stale. This module makes the persisted
final contract the source of truth for CI and diagnostic artifacts without relaxing
any business gate.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

DEFAULT_PROFILE = Path("product-ranking-v3-profile.json")
MIN_RANKED = 100
MIN_CREATIVES = 20
MIN_CONTENT_PACKS = 20
VARIANTS_PER_CREATIVE = 3
MIN_EXPECTED_COMMISSION_EUR = 10.0


def _as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _as_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def reconcile(profile: dict[str, Any]) -> dict[str, Any]:
    if profile.get("engine_version") != "affiliate_night_brain_v1":
        raise RuntimeError(f"unexpected engine_version: {profile.get('engine_version')!r}")
    if _as_int(profile.get("saved_rankings")) < MIN_RANKED:
        raise RuntimeError(f"saved rankings below contract: {profile.get('saved_rankings')!r}")
    if _as_float(profile.get("owner_min_expected_commission_eur")) < MIN_EXPECTED_COMMISSION_EUR:
        raise RuntimeError("owner commission floor dropped below EUR10")
    effective_floor = profile.get("effective_promotion_commission_floor_eur")
    if effective_floor is not None and _as_float(effective_floor) < MIN_EXPECTED_COMMISSION_EUR:
        raise RuntimeError("effective promotion commission floor dropped below EUR10")
    if profile.get("bulk_feed_to_llm") is not False:
        raise RuntimeError("bulk_feed_to_llm must remain false")
    if profile.get("paid_llm_required") is not False:
        raise RuntimeError("paid_llm_required must remain false")
    if _as_float(profile.get("paid_inference_cost_usd")) != 0:
        raise RuntimeError("paid inference cost must remain zero")

    creative = profile.get("creative")
    if not isinstance(creative, dict):
        raise RuntimeError("creative profile missing")
    if creative.get("creative_status") != "completed":
        raise RuntimeError(f"creative_status is not completed: {creative.get('creative_status')!r}")
    if _as_int(creative.get("creative_ready")) < MIN_CREATIVES:
        raise RuntimeError(f"creative_ready below contract: {creative.get('creative_ready')!r}")
    if _as_int(creative.get("creative_rankings_persisted")) < MIN_CREATIVES:
        raise RuntimeError(
            f"creative rankings persisted below contract: {creative.get('creative_rankings_persisted')!r}"
        )

    final_contract = creative.get("final_contract")
    if not isinstance(final_contract, dict):
        raise RuntimeError("final creative contract missing")
    if final_contract.get("ok") is not True:
        raise RuntimeError(f"final creative contract not ok: {final_contract!r}")
    if _as_int(final_contract.get("ranked")) < MIN_RANKED:
        raise RuntimeError(f"final ranked count below contract: {final_contract!r}")
    if _as_int(final_contract.get("creatives")) < MIN_CREATIVES:
        raise RuntimeError(f"final creative count below contract: {final_contract!r}")
    if _as_int(final_contract.get("content_packs")) < MIN_CONTENT_PACKS:
        raise RuntimeError(f"final content pack count below contract: {final_contract!r}")

    final_assets = _as_int(final_contract.get("creative_assets"))
    expected_assets = MIN_CREATIVES * VARIANTS_PER_CREATIVE
    if final_assets < expected_assets:
        raise RuntimeError(
            f"final durable asset count below contract: {final_assets}/{expected_assets}"
        )

    # A recovery at canonical persistence can make earlier counters stale. Preserve
    # the original values for auditability, then reconcile the public profile to the
    # authoritative final contract so downstream validation cannot fail after a
    # successful persistence recovery.
    before_assets = _as_int(creative.get("creative_assets"))
    before_packs = _as_int(creative.get("creative_asset_packs"))
    final_creatives = _as_int(final_contract.get("creatives"))
    if before_assets != final_assets or before_packs != final_creatives:
        creative["pre_finalize_asset_counts"] = {
            "creative_assets": before_assets,
            "creative_asset_packs": before_packs,
        }
        creative["creative_assets"] = final_assets
        creative["creative_asset_packs"] = final_creatives
        creative["asset_count_reconciled_from_final_contract"] = True
    else:
        creative["asset_count_reconciled_from_final_contract"] = False

    profile["creative"] = creative
    profile["contract_validation"] = {
        "status": "PASS",
        "source_of_truth": "creative.final_contract",
        "ranked": _as_int(final_contract.get("ranked")),
        "creatives": final_creatives,
        "content_packs": _as_int(final_contract.get("content_packs")),
        "creative_assets": final_assets,
        "expected_assets": expected_assets,
    }
    return profile


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()

    profile = json.loads(args.profile.read_text(encoding="utf-8"))
    profile = reconcile(profile)
    if not args.check_only:
        args.profile.write_text(
            json.dumps(profile, ensure_ascii=False, indent=2, default=str) + "\n",
            encoding="utf-8",
        )

    print(json.dumps(profile["contract_validation"], ensure_ascii=False))


if __name__ == "__main__":
    main()
