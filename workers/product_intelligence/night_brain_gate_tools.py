"""Bounded business-gate tools for SocialMarket Affiliate Night Brain.

Design goals:
- EUR 10 is the immutable economic floor for the candidate universe.
- A local Business Gate Agent may raise the nightly *promotion* floor, never lower it.
- Tracking validity is deterministic and merchant-domain grounded.
- Missing product imagery is recoverable only on the bounded shortlist, never by
  crawling the multi-million-row feed.
- Merchant dominance/concentration is a diversification signal, not a block reason.
"""
from __future__ import annotations

import collections
import ipaddress
import json
import math
import os
import sqlite3
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from pathlib import Path
from statistics import median
from typing import Any, Mapping

import ijson

import product_intelligence_v1 as v1
import product_local_autopilot as local_ai
from product_agents import canonical_key, parse_commission_rule
from product_safety import build_feed_safety_profile, price_integrity_allows, prune_dynamic_candidate_saturation
from stream_feed import iter_records, normalize, normalize_domain, valid_url

POLICY_VERSION = 'night-brain-gates-v1.1'
BASE_ECONOMIC_FLOOR_EUR = 10.0
DEFAULT_MAX_AGENT_FLOOR_EUR = 30.0
DEFAULT_MIN_AGENT_POOL = 1000
IMAGE_RECOVERY_WORKERS = max(1, min(8, int(os.getenv('PRODUCT_IMAGE_RECOVERY_WORKERS', '6'))))
IMAGE_FETCH_TIMEOUT = max(2.0, min(15.0, float(os.getenv('PRODUCT_IMAGE_FETCH_TIMEOUT_SECONDS', '7'))))
IMAGE_HTML_LIMIT = max(100_000, min(2_000_000, int(os.getenv('PRODUCT_IMAGE_HTML_LIMIT_BYTES', '900000'))))


def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(default if value in (None, '') else value)
    except Exception:
        return float(default)


def _pct(value: Any) -> float:
    x = _num(value)
    return x * 100 if 0 <= x <= 1 else x


def _domain_match(target: str | None, official: str | None) -> bool:
    t = normalize_domain(target)
    o = normalize_domain(official)
    if not t or not o:
        return False
    return t == o or t.endswith('.' + o)


def validate_tracking_contract(product: Mapping[str, Any], merchant: Mapping[str, Any]) -> tuple[bool, dict[str, Any]]:
    """Validate tracking structurally without making a network request.

    A Linkwise tracking URL is accepted only when it is HTTP(S), carries a decoded
    HTTP(S) merchant destination, and that destination belongs to the catalogued
    merchant domain. Network reachability is checked later only for bounded
    shortlist rows that require landing-page enrichment.
    """
    tracking = valid_url(product.get('tracking_url'))
    target = valid_url(product.get('target_url'))
    target_domain = normalize_domain(product.get('target_domain'))
    official = normalize_domain(merchant.get('official_domain'))
    if not tracking:
        return False, {'status': 'invalid', 'reason': 'missing_or_invalid_tracking_url'}
    if not target or not target_domain:
        return False, {'status': 'invalid', 'reason': 'tracking_destination_not_decodable'}
    if not official:
        return False, {'status': 'invalid', 'reason': 'merchant_official_domain_missing'}
    if not _domain_match(target_domain, official):
        return False, {
            'status': 'invalid', 'reason': 'tracking_destination_merchant_mismatch',
            'target_domain': target_domain, 'merchant_domain': official,
        }
    return True, {
        'status': 'validated_structural', 'reason': 'decoded_destination_matches_merchant_domain',
        'target_domain': target_domain, 'merchant_domain': official,
    }


def stage_feed(feed: str, context: Mapping[str, Any]):
    """Night Brain candidate staging with simplified, auditable hard gates.

    Price positivity remains a parser/data-integrity invariant, not a strategic
    business gate. Missing images are *not* rejected here; image recovery is
    deferred to the bounded shortlist.
    """
    safety = build_feed_safety_profile(feed, context, iter_records, normalize, v1.resolve_merchant, v1.merchant_maps)
    by_program, aliases, by_domain = v1.merchant_maps(context)
    db = v1.init_stage(v1.STAGE_DB, reset=True)
    reasons = collections.Counter(); resolution_methods = collections.Counter(); seen = eligible = 0
    image_recovery_deferred = 0; dominant_eligible = 0
    try:
        iterator = iter_records(feed)
        while True:
            try:
                raw = next(iterator)
            except StopIteration:
                break
            except ijson.common.IncompleteJSONError as exc:
                reasons['feed_truncated_after_complete_records'] += 1
                print(json.dumps({'warning': 'truncated_feed_salvaged', 'error': str(exc)[:300], 'seen': seen}), flush=True)
                break
            seen += 1
            p = normalize(raw)
            merchant, resolution_method = v1.resolve_merchant(p, by_program, aliases, by_domain)
            if not merchant:
                reasons['merchant_unresolved'] += 1; continue
            resolution_methods[resolution_method] += 1
            p['merchant_resolution_method'] = resolution_method
            mid = str(merchant.get('merchant_id'))
            merchant_safety = safety.get('merchants', {}).get(mid, {})

            # Only an explicit, evidenced merchant policy block is a hard merchant reject.
            # Dominance/high concentration is retained as a diversification signal.
            if str(merchant.get('promotion_mode') or 'eligible') == 'blocked':
                reasons['merchant_blocked_explicit'] += 1; continue
            if merchant.get('dominant_market') or str(merchant.get('promotion_mode') or '') == 'demand_beacon_only':
                dominant_eligible += 1

            trust = _num(merchant.get('trust_score'))
            if trust < _num(v1.MIN_MERCHANT_TRUST, 30):
                reasons['merchant_trust_below_gate'] += 1; continue
            if p.get('in_stock') is False:
                reasons['out_of_stock'] += 1; continue

            tracking_ok, tracking_validation = validate_tracking_contract(p, merchant)
            if not tracking_ok:
                reasons[str(tracking_validation.get('reason') or 'tracking_invalid')] += 1; continue
            p['tracking_validation'] = tracking_validation

            # This is data hygiene, not affiliate strategy. A non-positive/missing price
            # cannot produce a valid offer row or reliable percentage commission.
            price = _num(p.get('price'))
            if price <= 0:
                reasons['data_integrity_invalid_price'] += 1; continue
            if str(p.get('currency') or 'EUR').upper() != 'EUR':
                reasons['non_eur_currency'] += 1; continue

            price_ok, price_reason, price_info = price_integrity_allows(price, merchant_safety)
            if not price_ok:
                reasons[price_reason] += 1; continue
            p['price_integrity'] = {
                'status': price_reason, 'confidence': price_info.get('confidence'),
                'merchant_sample_count': price_info.get('sample_count'), 'merchant_median': price_info.get('median'),
                'merchant_p90': price_info.get('p90'), 'auto_scaled': False,
            }

            comm = parse_commission_rule(merchant.get('raw_commission_pct'), merchant.get('raw_flat_commission'), price)
            p.update(comm)
            if _num(p.get('expected_commission_eur')) + 1e-9 < BASE_ECONOMIC_FLOOR_EUR:
                reasons['commission_below_immutable_10_eur_floor'] += 1; continue
            p['expected_commission_eur'] = round(_num(p.get('expected_commission_eur')), 4)
            p['potential_commission_eur'] = round(_num(p.get('potential_commission_eur')), 4)

            if not (p.get('image_url') or p.get('thumb_url') or any(valid_url(x) for x in (p.get('extra_images') or []))):
                p['image_recovery_required'] = True
                image_recovery_deferred += 1
            else:
                p['image_recovery_required'] = False

            p['merchant_name'] = merchant.get('canonical_name') or p.get('program_name') or p.get('target_domain')
            p['merchant_context'] = {k: merchant.get(k) for k in (
                'merchant_id', 'merchant_program_id', 'canonical_name', 'official_domain', 'solution_whitespace_score',
                'demand_beacon_score', 'demand_score', 'competition_score', 'trust_score', 'confidence',
                'promotion_mode', 'dominant_market'
            )}
            p['merchant_context']['resolved_feed_share'] = merchant_safety.get('resolved_feed_share')
            p['merchant_context']['dominance_semantics'] = 'diversity_signal_not_block'
            p['canonical_key'] = canonical_key(p)
            pre = v1.preliminary_score(p, merchant)
            db.execute(
                'insert or replace into candidates(source_hash,canonical_key,merchant_id,merchant_name,competition_score,payload,expected_commission,preliminary_score) values(?,?,?,?,?,?,?,?)',
                (p['source_record_hash'], p['canonical_key'], mid, p['merchant_name'], _num(merchant.get('competition_score'), 50),
                 json.dumps(p, ensure_ascii=False, default=str), p['expected_commission_eur'], pre)
            )
            eligible += 1
            if eligible % 5000 == 0:
                db.commit()
            if seen % 250000 == 0:
                print(json.dumps({
                    'phase': 'stream', 'seen': seen, 'economic_floor_eligible': eligible,
                    'image_recovery_deferred': image_recovery_deferred,
                    'merchant_resolution_methods': resolution_methods.most_common(), 'excluded': reasons.most_common(8)
                }), flush=True)
    finally:
        db.commit()

    removed, saturated = prune_dynamic_candidate_saturation(db, reasons)
    eligible = max(0, eligible - removed)
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
        'price_integrity_policy': 'data-integrity invariant; suspicious price scales quarantined; no automatic cents/EUR conversion',
        'gate_policy_version': POLICY_VERSION,
        'safety_profile_path': 'product-feed-safety-profile.json',
    }


def _median(values: list[float]) -> float | None:
    vals = [x for x in values if math.isfinite(x)]
    return float(median(vals)) if vals else None


def _commission_agent_payload(decision_index: Mapping[str, Any], cfg: Mapping[str, Any]) -> dict[str, Any]:
    programs = list((decision_index.get('program_kpi_by_id') or {}).values())
    fp_rows = list((decision_index.get('first_party_by_program') or {}).values())
    clicks = sum(max(0, int(_num(x.get('outbound_clicks')))) for x in fp_rows)
    conversions = sum(max(0, int(_num(x.get('conversions_approved')))) for x in fp_rows)
    revenue = sum(max(0.0, _num(x.get('commission_approved_eur'))) for x in fp_rows)
    cost = sum(max(0.0, _num(x.get('media_spend_eur'))) + max(0.0, _num(x.get('content_cost_eur'))) for x in fp_rows)
    observed_epc = revenue / clicks if clicks else None
    observed_cvr = conversions / clicks * 100 if clicks else None
    roi = (revenue - cost) / cost * 100 if cost > 0 else None
    return {
        'immutable_floor_eur': BASE_ECONOMIC_FLOOR_EUR,
        'program_baselines': {
            'programs': len(programs),
            'median_conversion_rate_pct': _median([_pct(x.get('conversion_rate')) for x in programs if x.get('conversion_rate') not in (None, '')]),
            'median_epc_eur': _median([_num(x.get('epc')) for x in programs if x.get('epc') not in (None, '')]),
            'median_approval_rate_pct': _median([_pct(x.get('approval_rate')) for x in programs if x.get('approval_rate') not in (None, '')]),
        },
        'first_party_30d': {
            'programs_with_rows': len(fp_rows), 'clicks': clicks, 'approved_conversions': conversions,
            'approved_commission_eur': round(revenue, 2), 'observed_epc_eur': None if observed_epc is None else round(observed_epc, 4),
            'observed_cvr_pct': None if observed_cvr is None else round(observed_cvr, 3),
            'known_cost_eur': round(cost, 2), 'roi_pct': None if roi is None else round(roi, 2),
        },
        'rules': {
            'never_below_eur': BASE_ECONOMIC_FLOOR_EUR,
            'raise_only_for_economic_reason': True,
            'do_not_raise_just_to_prefer_high_commission': True,
            'preserve_opportunistic_low_history_products': True,
        },
        'config': cfg,
    }


def decide_commission_promotion_floor(decision_index: Mapping[str, Any]) -> dict[str, Any]:
    cfg = getattr(v1, 'RUNTIME_CONFIG', {}) or {}
    nb_cfg = cfg.get('night_brain') if isinstance(cfg.get('night_brain'), dict) else {}
    gate_cfg = nb_cfg.get('commission_gate') if isinstance(nb_cfg.get('commission_gate'), dict) else {}
    max_floor = max(BASE_ECONOMIC_FLOOR_EUR, min(100.0, _num(gate_cfg.get('max_agent_floor_eur'), DEFAULT_MAX_AGENT_FLOOR_EUR)))
    payload = _commission_agent_payload(decision_index, gate_cfg)
    router = local_ai._router(260)
    task = local_ai.AITask(
        task_type='affiliate_commission_gate', role='Senior Affiliate Unit Economics Gatekeeper',
        prompt_version='night-brain-gate-v1', max_tier=2, cacheable=False, material_change_capable=True,
        required_keys=('effective_floor_eur', 'confidence_score', 'rationale'),
        instructions=(
            'Set ONE nightly promotion commission floor for the Greek affiliate portfolio. EUR 10 is immutable and you may never choose lower. '
            'Default to EUR 10. Raise it only when supplied observed economics justify needing more commission per conversion to protect profitability. '
            'Do not raise the floor merely because high commission products look attractive; conversion probability and opportunistic discovery remain primary. '
            'Use only supplied aggregate facts. effective_floor_eur must be numeric. confidence_score 0-100. Keep rationale concise.'
        ), payload=payload, metadata={'bounded_business_gate': True, 'bulk_feed_exposed': False},
    )
    try:
        data, stats = local_ai._run_task(router, task)
        proposed = _num((data or {}).get('effective_floor_eur'), BASE_ECONOMIC_FLOOR_EUR)
        effective = max(BASE_ECONOMIC_FLOOR_EUR, min(max_floor, proposed))
        return {
            'status': 'agent_decided' if data else 'fallback', 'effective_floor_eur': round(effective, 2),
            'agent_proposed_floor_eur': round(proposed, 2), 'max_agent_floor_eur': max_floor,
            'confidence_score': max(0.0, min(100.0, _num((data or {}).get('confidence_score')))),
            'rationale': str((data or {}).get('rationale') or 'AI unavailable; immutable EUR10 floor retained.')[:1000],
            'model': stats.get('model'), 'from_cache': bool(stats.get('from_cache')), 'cost_usd': _num(stats.get('cost_usd')),
            'policy_version': POLICY_VERSION,
        }
    except Exception as exc:
        return {
            'status': 'fallback', 'effective_floor_eur': BASE_ECONOMIC_FLOOR_EUR,
            'agent_proposed_floor_eur': None, 'max_agent_floor_eur': max_floor, 'confidence_score': 0,
            'rationale': f'Gate agent unavailable; EUR10 retained: {str(exc)[:300]}', 'cost_usd': 0,
            'policy_version': POLICY_VERSION,
        }


def apply_agent_commission_floor(db: sqlite3.Connection, decision: Mapping[str, Any]) -> dict[str, Any]:
    cfg = getattr(v1, 'RUNTIME_CONFIG', {}) or {}
    nb_cfg = cfg.get('night_brain') if isinstance(cfg.get('night_brain'), dict) else {}
    gate_cfg = nb_cfg.get('commission_gate') if isinstance(nb_cfg.get('commission_gate'), dict) else {}
    requested = max(BASE_ECONOMIC_FLOOR_EUR, _num(decision.get('effective_floor_eur'), BASE_ECONOMIC_FLOOR_EUR))
    min_pool = max(200, int(_num(gate_cfg.get('minimum_pool_after_raise'), DEFAULT_MIN_AGENT_POOL)))
    base_count = int(db.execute('select count(*) from candidates').fetchone()[0])
    above = int(db.execute('select count(*) from candidates where expected_commission>=?', (requested,)).fetchone()[0])
    applied = requested
    relaxed = False
    if requested > BASE_ECONOMIC_FLOOR_EUR and above < min_pool:
        applied = BASE_ECONOMIC_FLOOR_EUR
        relaxed = True
        above = base_count
    if applied > BASE_ECONOMIC_FLOOR_EUR:
        db.execute('delete from candidates where expected_commission<?', (applied,)); db.commit()
    return {
        **dict(decision), 'effective_floor_eur': round(applied, 2), 'requested_floor_eur': round(requested, 2),
        'base_eur10_candidate_pool': base_count, 'candidate_pool_after_floor': above,
        'minimum_pool_after_raise': min_pool, 'safety_relaxed_to_eur10': relaxed,
    }


class _ImageMetaParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.images: list[str] = []
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        a = {str(k).lower(): str(v or '') for k, v in attrs}
        if tag.lower() == 'meta':
            key = (a.get('property') or a.get('name') or a.get('itemprop') or '').lower()
            if key in ('og:image', 'og:image:url', 'twitter:image', 'twitter:image:src', 'image') and a.get('content'):
                self.images.append(a['content'])
        elif tag.lower() == 'link':
            rel = a.get('rel', '').lower()
            if 'image_src' in rel and a.get('href'):
                self.images.append(a['href'])


def _public_http_url(url: str | None) -> bool:
    try:
        u = urllib.parse.urlparse(str(url or '').strip())
        if u.scheme not in ('http', 'https') or not u.hostname:
            return False
        host = u.hostname.lower()
        if host in ('localhost', 'localhost.localdomain') or host.endswith('.local'):
            return False
        try:
            ip = ipaddress.ip_address(host)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False
        except ValueError:
            pass
        return True
    except Exception:
        return False


def recover_image(raw: Mapping[str, Any]) -> tuple[str | None, dict[str, Any]]:
    for extra in raw.get('extra_images') or []:
        if valid_url(extra):
            return str(extra), {'status': 'recovered', 'source': 'feed_extra_image'}
    target = str(raw.get('target_url') or '')
    validation = raw.get('tracking_validation') or {}
    if validation.get('status') != 'validated_structural' or not _public_http_url(target):
        return None, {'status': 'failed', 'reason': 'validated_public_destination_required'}
    try:
        req = urllib.request.Request(target, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; SocialMarket-NightBrain/1.1; +affiliate-product-enrichment)',
            'Accept': 'text/html,application/xhtml+xml;q=0.9,*/*;q=0.5',
        })
        with urllib.request.urlopen(req, timeout=IMAGE_FETCH_TIMEOUT) as r:
            ctype = str(r.headers.get('content-type') or '').lower()
            if 'html' not in ctype:
                return None, {'status': 'failed', 'reason': 'landing_not_html', 'http_status': getattr(r, 'status', None)}
            body = r.read(IMAGE_HTML_LIMIT).decode(r.headers.get_content_charset() or 'utf-8', errors='replace')
            final_url = r.geturl()
        parser = _ImageMetaParser(); parser.feed(body)
        for candidate in parser.images:
            absolute = urllib.parse.urljoin(final_url, candidate)
            if _public_http_url(absolute):
                return absolute, {
                    'status': 'recovered', 'source': 'merchant_landing_meta', 'landing_url': final_url,
                    'field': 'og/twitter/schema-like meta image',
                }
        return None, {'status': 'failed', 'reason': 'no_usable_product_meta_image'}
    except Exception as exc:
        return None, {'status': 'failed', 'reason': 'landing_fetch_failed', 'error': str(exc)[:300]}


def recover_shortlist_images(items: list[dict[str, Any]], final_limit: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    need = [x for x in items if not ((x.get('_raw') or {}).get('image_url') or (x.get('_raw') or {}).get('thumb_url'))]
    recovered = 0; failed = 0
    if need:
        with ThreadPoolExecutor(max_workers=IMAGE_RECOVERY_WORKERS) as pool:
            futures = {pool.submit(recover_image, x.get('_raw') or {}): x for x in need}
            for future in as_completed(futures):
                item = futures[future]; raw = item.get('_raw') or {}
                image, info = future.result(); raw['image_recovery'] = info
                if image:
                    raw['image_url'] = image; raw['image_recovery_required'] = False; recovered += 1
                else:
                    raw['image_recovery_required'] = True; failed += 1
    valid = [x for x in items if (x.get('_raw') or {}).get('image_url') or (x.get('_raw') or {}).get('thumb_url')]
    return valid[:final_limit], {
        'shortlist_missing_image': len(need), 'shortlist_images_recovered': recovered,
        'shortlist_image_recovery_failed': failed, 'shortlist_with_usable_image': len(valid),
        'image_recovery_workers': IMAGE_RECOVERY_WORKERS,
        'image_recovery_policy': 'feed extra image -> validated merchant landing og/twitter image; bounded shortlist only',
    }


def build_frontier_with_business_gates(original_build_frontier, db, context, decision_index, policy):
    decision = decide_commission_promotion_floor(decision_index)
    gate = apply_agent_commission_floor(db, decision)

    # Build extra shortlist capacity so recoverable missing imagery does not reduce
    # a healthy Top100. AI still receives only the configured final candidate limit.
    expanded = dict(policy)
    configured_limit = max(100, int(policy.get('ai_candidates') or 120))
    expanded['ai_candidates'] = min(180, max(configured_limit, 160))
    items, stats = original_build_frontier(db, context, decision_index, expanded)
    items, image_stats = recover_shortlist_images(items, configured_limit)
    if len(items) < 100:
        raise RuntimeError(f'Night Brain has only {len(items)} candidates with usable/recovered images after bounded recovery')
    return items, {
        **stats, **image_stats, 'commission_gate_agent': gate,
        'effective_promotion_commission_floor_eur': gate.get('effective_floor_eur'),
        'gate_policy_version': POLICY_VERSION,
    }
