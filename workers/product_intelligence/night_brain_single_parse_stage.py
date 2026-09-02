"""Single-parse materialized feed staging for Affiliate Night Brain.

The legacy production gate read the multi-gigabyte Linkwise JSON twice: once to
build merchant price-integrity baselines and again to apply product gates. This
module preserves the same fail-closed candidate contract while parsing the raw
JSON exactly once.

During that one parse we:
1. observe every resolved merchant row for the same reservoir-sampled safety profile;
2. apply safety-independent hard gates, including the immutable EUR10 commission floor;
3. materialize only provisional commission-eligible rows in the existing SQLite
   candidates table.

After the raw feed is closed, merchant price baselines are authoritative. A bounded
SQLite replay then applies price-integrity checks and annotates resolved feed share.
The final candidate set therefore still requires BOTH commission and price-integrity
gates; only the order of those independent predicates is commuted for throughput.
Set PRODUCT_SINGLE_PARSE_STAGE=false to use the legacy two-parse implementation.
"""
from __future__ import annotations

import collections
import json
import os
import random
import time
from typing import Any, Mapping

import ijson

import night_brain_gate_tools as legacy
import product_intelligence_v1 as v1
import product_safety as safety
from creative_contract_v10 import excluded_vertical
from product_agents import canonical_key, parse_commission_rule
from stream_feed import iter_records, normalize, valid_url

BASE_ECONOMIC_FLOOR_EUR = legacy.BASE_ECONOMIC_FLOOR_EUR
POLICY_VERSION = legacy.POLICY_VERSION + '+single-parse-v1'
SINGLE_PARSE_ENABLED = os.getenv('PRODUCT_SINGLE_PARSE_STAGE', 'true').lower() in ('1', 'true', 'yes', 'on')
REVALIDATE_BATCH = max(500, min(20000, int(os.getenv('PRODUCT_STAGE_REVALIDATE_BATCH', '5000'))))

# Re-export the frontier hook so the production entrypoint can keep one policy import.
build_frontier_with_business_gates = legacy.build_frontier_with_business_gates


def _num(value: Any, default: float = 0.0) -> float:
    return legacy._num(value, default)


def _observe_price(
    mid: str,
    product: Mapping[str, Any],
    price_seen: collections.Counter,
    samples: dict[str, list[float]],
    rng: random.Random,
) -> None:
    price = _num(product.get('price'))
    if price <= 0 or str(product.get('currency') or 'EUR').upper() != 'EUR':
        return
    price_seen[mid] += 1
    arr = samples[mid]
    if len(arr) < safety.PRICE_SAMPLE_PER_MERCHANT:
        arr.append(price)
        return
    j = rng.randint(0, price_seen[mid] - 1)
    if j < safety.PRICE_SAMPLE_PER_MERCHANT:
        arr[j] = price


def _build_safety_profile(
    context: Mapping[str, Any],
    counts: collections.Counter,
    resolution: collections.Counter,
    samples: dict[str, list[float]],
    seen: int,
    resolved: int,
    truncated: bool,
) -> dict[str, Any]:
    """Build the same safety-profile shape as product_safety.build_feed_safety_profile."""
    by_mid = {str(row.get('merchant_id')): row for row in context.get('programs', [])}
    merchants: dict[str, dict[str, Any]] = {}
    for mid, count in counts.items():
        row = by_mid.get(mid, {})
        share = (count / resolved) if resolved else 0.0
        competition = _num(row.get('competition_score'), 50)
        concentrated = (
            share >= safety.MAX_MERCHANT_FEED_SHARE
            or (share >= safety.SECONDARY_FEED_SHARE and competition >= safety.FEED_COMPETITION_GATE)
        )
        merchants[mid] = {
            'merchant_id': mid,
            'merchant_name': row.get('canonical_name'),
            'official_domain': row.get('official_domain'),
            'resolved_records': int(count),
            'resolved_feed_share': round(share, 6),
            'competition_score': competition,
            'feed_concentrated': concentrated,
            'feed_concentration_reason': (
                'feed_share'
                if share >= safety.MAX_MERCHANT_FEED_SHARE
                else ('feed_share_plus_observed_competition' if concentrated else None)
            ),
            'feed_saturated': False,
            'feed_saturation_policy': 'disabled_as_kill_switch; Linkwise feed share is not Greek market share',
            'price_integrity': safety.classify_price_sample(samples.get(mid, [])),
        }

    profile = {
        'records_seen': seen,
        'resolved_records': resolved,
        'truncated_tail': truncated,
        'resolution_methods': resolution.most_common(),
        'thresholds': {
            'max_merchant_feed_share': safety.MAX_MERCHANT_FEED_SHARE,
            'secondary_feed_share': safety.SECONDARY_FEED_SHARE,
            'feed_competition_gate': safety.FEED_COMPETITION_GATE,
            'price_integer_ratio_risk': safety.PRICE_INTEGER_RATIO_RISK,
            'price_minor_risk_median': safety.PRICE_MINOR_RISK_MEDIAN,
            'price_minor_risk_p90': safety.PRICE_MINOR_RISK_P90,
        },
        'feed_concentration_semantics': 'diagnostic/source-diversity only; never market share and never a standalone product rejection',
        'merchants': merchants,
        'raw_feed_parse_passes': 1,
        'materialization_policy': 'commission-eligible candidates first; price-integrity replay from local SQLite',
    }
    safety.SAFETY_PROFILE_PATH.write_text(
        json.dumps(profile, ensure_ascii=False, indent=2, default=str), encoding='utf-8'
    )
    return profile


def _finalize_price_integrity(
    db,
    context: Mapping[str, Any],
    safety_profile: Mapping[str, Any],
    reasons: collections.Counter,
) -> tuple[int, int]:
    """Apply price-integrity locally after merchant baselines are known.

    Returns (rows_checked, rows_removed). Keyset pagination avoids keeping hundreds
    of thousands of candidate payloads in RAM and remains stable while rows are
    updated/deleted in the same table.
    """
    by_mid = {str(row.get('merchant_id')): row for row in context.get('programs', [])}
    checked = removed = 0
    last_hash = ''
    while True:
        rows = db.execute(
            'select source_hash,merchant_id,payload from candidates '
            'where source_hash>? order by source_hash limit ?',
            (last_hash, REVALIDATE_BATCH),
        ).fetchall()
        if not rows:
            break
        last_hash = str(rows[-1][0])
        deletes: list[tuple[str]] = []
        updates: list[tuple[str, str]] = []
        for source_hash, mid, payload in rows:
            checked += 1
            merchant = by_mid.get(str(mid))
            if not merchant:
                reasons['merchant_context_lost_after_materialization'] += 1
                deletes.append((str(source_hash),))
                removed += 1
                continue
            p = json.loads(payload)
            merchant_safety = (safety_profile.get('merchants') or {}).get(str(mid), {})
            price = _num(p.get('price'))
            price_ok, price_reason, price_info = safety.price_integrity_allows(price, merchant_safety)
            if not price_ok:
                reasons[price_reason] += 1
                deletes.append((str(source_hash),))
                removed += 1
                continue
            p['price_integrity'] = {
                'status': price_reason,
                'confidence': price_info.get('confidence'),
                'merchant_sample_count': price_info.get('sample_count'),
                'merchant_median': price_info.get('median'),
                'merchant_p90': price_info.get('p90'),
                'auto_scaled': False,
            }
            merchant_context = p.get('merchant_context') if isinstance(p.get('merchant_context'), dict) else {}
            merchant_context['resolved_feed_share'] = merchant_safety.get('resolved_feed_share')
            merchant_context['dominance_semantics'] = 'diversity_signal_not_block'
            p['merchant_context'] = merchant_context
            p.pop('price_integrity_pending', None)
            updates.append((json.dumps(p, ensure_ascii=False, default=str), str(source_hash)))
        if deletes:
            db.executemany('delete from candidates where source_hash=?', deletes)
        if updates:
            db.executemany('update candidates set payload=? where source_hash=?', updates)
        db.commit()
    return checked, removed


def stage_feed(feed: str, context: Mapping[str, Any]):
    if not SINGLE_PARSE_ENABLED:
        return legacy.stage_feed(feed, context)

    started = time.monotonic()
    by_program, aliases, by_domain = v1.merchant_maps(context)
    db = v1.init_stage(v1.STAGE_DB, reset=True)
    reasons = collections.Counter()
    resolution_methods = collections.Counter()
    safety_counts = collections.Counter()
    price_seen = collections.Counter()
    samples: dict[str, list[float]] = collections.defaultdict(list)
    rng = random.Random(20260815)
    seen = resolved = provisional = 0
    image_recovery_deferred = dominant_eligible = 0
    truncated = False

    parse_started = time.monotonic()
    try:
        iterator = iter_records(feed)
        while True:
            try:
                raw = next(iterator)
            except StopIteration:
                break
            except ijson.common.IncompleteJSONError as exc:
                truncated = True
                reasons['feed_truncated_after_complete_records'] += 1
                print(json.dumps({
                    'warning': 'truncated_feed_salvaged', 'error': str(exc)[:300], 'seen': seen,
                    'stage_engine': 'single_parse_materialized_v1',
                }), flush=True)
                break

            seen += 1
            p = normalize(raw)
            merchant, resolution_method = v1.resolve_merchant(p, by_program, aliases, by_domain)
            if not merchant:
                reasons['merchant_unresolved'] += 1
                continue

            resolved += 1
            resolution_methods[resolution_method] += 1
            p['merchant_resolution_method'] = resolution_method
            mid = str(merchant.get('merchant_id'))
            safety_counts[mid] += 1
            _observe_price(mid, p, price_seen, samples, rng)

            # These gates do not depend on merchant-wide price statistics and can be
            # applied while the raw JSON stream is open.
            if str(merchant.get('promotion_mode') or 'eligible') == 'blocked':
                reasons['merchant_blocked_explicit'] += 1
                continue
            if merchant.get('dominant_market') or str(merchant.get('promotion_mode') or '') == 'demand_beacon_only':
                dominant_eligible += 1

            if _num(merchant.get('trust_score')) < _num(v1.MIN_MERCHANT_TRUST, 30):
                reasons['merchant_trust_below_gate'] += 1
                continue
            if p.get('in_stock') is False:
                reasons['out_of_stock'] += 1
                continue

            tracking_ok, tracking_validation = legacy.validate_tracking_contract(p, merchant)
            if not tracking_ok:
                reasons[str(tracking_validation.get('reason') or 'tracking_invalid')] += 1
                continue
            p['tracking_validation'] = tracking_validation

            price = _num(p.get('price'))
            if price <= 0:
                reasons['data_integrity_invalid_price'] += 1
                continue
            if str(p.get('currency') or 'EUR').upper() != 'EUR':
                reasons['non_eur_currency'] += 1
                continue

            # Commission and price-integrity are independent mandatory predicates.
            # Evaluating commission first dramatically shrinks materialization while
            # leaving the final candidate set unchanged.
            comm = parse_commission_rule(merchant.get('raw_commission_pct'), merchant.get('raw_flat_commission'), price)
            p.update(comm)
            if _num(p.get('expected_commission_eur')) + 1e-9 < BASE_ECONOMIC_FLOOR_EUR:
                reasons['commission_below_immutable_10_eur_floor'] += 1
                continue
            p['expected_commission_eur'] = round(_num(p.get('expected_commission_eur')), 4)
            p['potential_commission_eur'] = round(_num(p.get('potential_commission_eur')), 4)

            if not (p.get('image_url') or p.get('thumb_url') or any(valid_url(x) for x in (p.get('extra_images') or []))):
                p['image_recovery_required'] = True
                image_recovery_deferred += 1
            else:
                p['image_recovery_required'] = False

            p['merchant_name'] = merchant.get('canonical_name') or p.get('program_name') or p.get('target_domain')
            if excluded_vertical(p):
                reasons['excluded_hotel_accommodation_travel_package'] += 1
                continue

            p['merchant_context'] = {k: merchant.get(k) for k in (
                'merchant_id', 'merchant_program_id', 'canonical_name', 'official_domain', 'solution_whitespace_score',
                'demand_beacon_score', 'demand_score', 'competition_score', 'trust_score', 'confidence',
                'promotion_mode', 'dominant_market'
            )}
            p['merchant_context']['resolved_feed_share'] = None
            p['merchant_context']['dominance_semantics'] = 'diversity_signal_not_block'
            p['price_integrity_pending'] = True
            p['canonical_key'] = canonical_key(p)
            pre = v1.preliminary_score(p, merchant)
            db.execute(
                'insert or replace into candidates(source_hash,canonical_key,merchant_id,merchant_name,competition_score,payload,expected_commission,preliminary_score) '
                'values(?,?,?,?,?,?,?,?)',
                (
                    p['source_record_hash'], p['canonical_key'], mid, p['merchant_name'],
                    _num(merchant.get('competition_score'), 50),
                    json.dumps(p, ensure_ascii=False, default=str), p['expected_commission_eur'], pre,
                ),
            )
            provisional += 1
            if provisional % 5000 == 0:
                db.commit()
            if seen % 250000 == 0:
                print(json.dumps({
                    'phase': 'single_parse_stage', 'seen': seen, 'resolved': resolved,
                    'provisional_commission_eligible': provisional,
                    'image_recovery_deferred': image_recovery_deferred,
                    'merchant_resolution_methods': resolution_methods.most_common(),
                    'excluded': reasons.most_common(8),
                }), flush=True)
    finally:
        db.commit()

    parse_seconds = round(time.monotonic() - parse_started, 3)
    safety_started = time.monotonic()
    safety_profile = _build_safety_profile(
        context, safety_counts, resolution_methods, samples, seen, resolved, truncated
    )
    safety_finalize_seconds = round(time.monotonic() - safety_started, 3)

    revalidate_started = time.monotonic()
    price_rows_checked, price_rows_removed = _finalize_price_integrity(db, context, safety_profile, reasons)
    price_revalidation_seconds = round(time.monotonic() - revalidate_started, 3)

    eligible = int(db.execute('select count(*) from candidates').fetchone()[0])
    removed, saturated = safety.prune_dynamic_candidate_saturation(db, reasons)
    eligible = max(0, eligible - removed)
    total_seconds = round(time.monotonic() - started, 3)

    return db, {
        'records_seen': seen,
        'commission_eligible_records': eligible,
        'immutable_economic_floor_eur': BASE_ECONOMIC_FLOOR_EUR,
        'image_recovery_deferred_candidates': image_recovery_deferred,
        'dominant_merchant_candidates_kept': dominant_eligible,
        'merchant_resolution_methods': resolution_methods.most_common(),
        'excluded_reasons': reasons.most_common(),
        'dynamic_saturated_merchants': saturated,
        'tracking_policy': 'structural Linkwise destination + merchant-domain match; landing-page verification only on bounded shortlist',
        'image_policy': 'missing image is recoverable on bounded shortlist, not a bulk-scan reject',
        'merchant_block_policy': 'explicit evidenced blocked state only; dominance is diversification metadata',
        'vertical_exclusion_policy': 'hotels, accommodation and travel packages are removed before ranking and persistence',
        'price_integrity_policy': 'data-integrity invariant; suspicious price scales quarantined; no automatic cents/EUR conversion',
        'gate_policy_version': POLICY_VERSION,
        'safety_profile_path': str(safety.SAFETY_PROFILE_PATH),
        'stage_engine': 'single_parse_materialized_v1',
        'feed_parse_passes': 1,
        'raw_feed_reparsed': False,
        'resolved_records_for_safety': resolved,
        'materialized_commission_eligible_rows': provisional,
        'price_revalidation_rows_checked': price_rows_checked,
        'price_revalidation_rows_removed': price_rows_removed,
        'stage_parse_seconds': parse_seconds,
        'stage_safety_finalize_seconds': safety_finalize_seconds,
        'stage_price_revalidation_seconds': price_revalidation_seconds,
        'stage_total_seconds': total_seconds,
        'gate_reordering_note': 'commission and price-integrity remain mandatory AND gates; commission is evaluated first to reduce local materialization',
    }
