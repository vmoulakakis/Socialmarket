import collections
import heapq
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import product_intelligence_v1 as v1
from product_agents import clamp, commission_score, discount_score
from runtime_config import apply_runtime_config, load_runtime_config

ENGINE_VERSION = 'ranking_v3.0'
PRESELECT = max(500, int(os.getenv('PRODUCT_RANK_PRESELECT', '4000')))
AI_MAX = max(20, int(os.getenv('PRODUCT_RANK_AI_MAX', '240')))
AI_BATCH = max(1, min(10, int(os.getenv('PRODUCT_RANK_AI_BATCH', '8'))))
MAX_PER_MERCHANT = max(2, int(os.getenv('PRODUCT_RANK_MAX_PER_MERCHANT', '18')))
MAX_PER_CATEGORY = max(4, int(os.getenv('PRODUCT_RANK_MAX_PER_CATEGORY', '36')))
SAVE_LIMIT = max(20, int(os.getenv('PRODUCT_RANK_SAVE_LIMIT', '200')))
PROFILE = Path(os.getenv('PRODUCT_RANK_PROFILE_PATH', 'product-ranking-v3-profile.json'))


def num(v, default=0.0):
    try:
        if v is None or v == '':
            return float(default)
        return float(v)
    except Exception:
        return float(default)


def purchase_signal(times_bought):
    value = max(0.0, num(times_bought))
    if value <= 0:
        return 0.0
    return clamp(22.0 * math.log1p(value))


def pain_signal(item):
    pains = item.get('_pains') or []
    if not pains:
        return 0.0
    best = 0.0
    for p in pains:
        score = (
            clamp(num(p.get('retrieval_score'))) * 0.45
            + clamp(num(p.get('pain_severity'))) * 0.25
            + clamp(num(p.get('demand_score'))) * 0.20
            + clamp(num(p.get('commercial_intent'))) * 0.10
        )
        best = max(best, score)
    return round(best, 3)


def seasonal_signal(item):
    themes = item.get('_themes') or []
    if not themes:
        return 0.0
    return round(max(
        clamp(num(t.get('retrieval_score'))) * 0.45
        + clamp(num(t.get('seasonal_curve_score'))) * 0.55
        for t in themes
    ), 3)


def deterministic_metrics(item):
    raw = item.get('_raw') or {}
    merchant = item.get('merchant') or {}
    demand = clamp(num(merchant.get('demand_score')))
    competition = merchant.get('competition_score')
    inverse_competition = 0.0 if competition is None else clamp(100.0 - num(competition))
    whitespace = clamp(num(merchant.get('solution_whitespace_score')))
    trust = clamp(num(merchant.get('trust_score')))
    commission = commission_score(raw.get('expected_commission_eur'))
    discount = discount_score(raw.get('discount_pct'))
    purchase = purchase_signal(raw.get('times_bought'))
    pain = pain_signal(item)
    seasonal = seasonal_signal(item)

    # Ranking is deliberately available even when pain evidence is absent.
    base = (
        demand * 0.22
        + whitespace * 0.18
        + commission * 0.17
        + inverse_competition * 0.12
        + trust * 0.10
        + discount * 0.07
        + purchase * 0.06
        + pain * 0.04
        + seasonal * 0.04
    )
    return {
        'merchant_demand_score': round(demand, 3),
        'competition_score': None if competition is None else round(clamp(num(competition)), 3),
        'inverse_competition_score': round(inverse_competition, 3),
        'merchant_whitespace_score': round(whitespace, 3),
        'merchant_trust_score': round(trust, 3),
        'commercial_score': round(commission, 3),
        'discount_score': round(discount, 3),
        'purchase_signal_score': round(purchase, 3),
        'pain_signal_score': round(pain, 3),
        'seasonal_score': round(seasonal, 3),
        'deterministic_rank_score': round(clamp(base), 3),
    }


def preselect(products, context):
    heap = []
    seq = 0
    considered = 0
    for product in products:
        considered += 1
        item = v1.build_ai_item(product, context)
        metrics = deterministic_metrics(item)
        item['_rank_metrics'] = metrics
        score = metrics['deterministic_rank_score']
        seq += 1
        entry = (score, seq, item)
        if len(heap) < PRESELECT:
            heapq.heappush(heap, entry)
        elif score > heap[0][0]:
            heapq.heapreplace(heap, entry)
    ordered = sorted(heap, key=lambda x: (x[0], x[1]), reverse=True)

    selected = []
    merchant_counts = collections.Counter()
    category_counts = collections.Counter()
    for _, _, item in ordered:
        merchant_id = str((item.get('merchant') or {}).get('merchant_id') or 'unknown')
        category = str((item.get('_raw') or {}).get('category_raw') or 'unknown').lower()
        if merchant_counts[merchant_id] >= MAX_PER_MERCHANT:
            continue
        if category_counts[category] >= MAX_PER_CATEGORY:
            continue
        selected.append(item)
        merchant_counts[merchant_id] += 1
        category_counts[category] += 1
        if len(selected) >= AI_MAX:
            break

    # If diversity caps leave unused capacity, fill from the strongest remaining candidates.
    if len(selected) < AI_MAX:
        chosen = {str(x['product']['source_record_hash']) for x in selected}
        for _, _, item in ordered:
            h = str(item['product']['source_record_hash'])
            if h in chosen:
                continue
            selected.append(item)
            chosen.add(h)
            if len(selected) >= AI_MAX:
                break

    return selected, {
        'eligible_candidates_considered': considered,
        'preselected': len(ordered),
        'ai_shortlist': len(selected),
        'unique_merchants': len({str((x.get('merchant') or {}).get('merchant_id')) for x in selected}),
        'unique_categories': len({str((x.get('_raw') or {}).get('category_raw')) for x in selected}),
    }


def wire_item(item):
    metrics = item['_rank_metrics']
    return {
        'product': item['product'],
        'merchant': item['merchant'],
        'pain_rag': item.get('pain_rag') or [],
        'theme_rag': item.get('theme_rag') or [],
        'deterministic_metrics': metrics,
        'ranking_semantics': {
            'objective': 'probability-weighted promotion opportunity in Greece',
            'pain_missing_is_not_rejection': True,
            'missing_competition_gets_no_inverse_bonus': True,
        },
    }


def rank_with_ai(items):
    outputs = {}
    stats = collections.Counter()
    for start in range(0, len(items), AI_BATCH):
        batch = items[start:start + AI_BATCH]
        wire = [wire_item(x) for x in batch]
        stats['ai_rank_batches'] += 1
        try:
            ranked = v1.gateway('rank', items=wire, thinking='auto').get('items', [])
            by_hash = {str(x.get('source_record_hash')): x for x in ranked}
            audit_wire = []
            for x in wire:
                h = str(x['product']['source_record_hash'])
                if h in by_hash:
                    audit_wire.append({**x, 'ranking': by_hash[h]})
            audited = v1.gateway('rank_audit', items=audit_wire, thinking='auto').get('items', []) if audit_wire else []
            audit_by = {str(x.get('source_record_hash')): x for x in audited}
            for h, result in by_hash.items():
                outputs[h] = {'ranking': result, 'audit': audit_by.get(h, {})}
                stats['ai_ranked'] += 1
        except Exception as exc:
            stats['ai_rank_failures'] += len(batch)
            print(json.dumps({'warning': 'ranking_ai_batch_failed', 'error': str(exc)[:500], 'items': len(batch)}), flush=True)
    return outputs, dict(stats)


def final_row(item, ai):
    raw = item['_raw']
    merchant = item['merchant']
    m = item['_rank_metrics']
    ranking = ai.get('ranking') or {}
    audit = ai.get('audit') or {}

    product_fit = clamp(num(ranking.get('product_market_fit_score')))
    creative = clamp(num(ranking.get('creative_potential_score')))
    value = clamp(num(ranking.get('value_score')))
    confidence = clamp(num(ranking.get('confidence_score')))
    risk = clamp(num(audit.get('risk_score'), 50.0))

    raw_score = (
        m['merchant_demand_score'] * 0.20
        + m['merchant_whitespace_score'] * 0.15
        + m['commercial_score'] * 0.12
        + m['inverse_competition_score'] * 0.10
        + m['merchant_trust_score'] * 0.08
        + m['discount_score'] * 0.07
        + m['purchase_signal_score'] * 0.05
        + m['pain_signal_score'] * 0.05
        + m['seasonal_score'] * 0.05
        + product_fit * 0.05
        + creative * 0.04
        + value * 0.02
        + confidence * 0.02
    )
    score = clamp(raw_score * (0.85 + 0.15 * (100.0 - risk) / 100.0))
    if score >= 82:
        band = 'PROMOTE_NOW'
    elif score >= 72:
        band = 'HIGH_POTENTIAL'
    elif score >= 62:
        band = 'TEST'
    else:
        band = 'WATCHLIST'

    channels = ranking.get('recommended_channels') or []
    if not isinstance(channels, list):
        channels = [str(channels)] if channels else []
    risk_flags = audit.get('risk_flags') or ranking.get('risk_flags') or []
    if not isinstance(risk_flags, list):
        risk_flags = [str(risk_flags)]

    return {
        'source_record_hash': raw['source_record_hash'],
        'canonical_key': raw['canonical_key'],
        'external_product_id': raw.get('external_product_id'),
        'merchant_id': merchant['merchant_id'],
        'merchant_program_id': merchant.get('merchant_program_id'),
        'merchant_name': raw.get('merchant_name') or merchant.get('canonical_name'),
        'product_name': raw.get('product_name') or item['product'].get('product_name') or 'Product',
        'brand_name': raw.get('brand_name'),
        'model_name': raw.get('model_name'),
        'category': ranking.get('category') or raw.get('category_raw'),
        'subcategory': ranking.get('subcategory'),
        'effective_price': raw.get('price'),
        'full_price': raw.get('full_price'),
        'discount_pct': raw.get('discount_pct'),
        'expected_commission_eur': raw.get('expected_commission_eur'),
        'tracking_url': raw.get('tracking_url'),
        'image_url': raw.get('image_url') or raw.get('thumb_url'),
        'in_stock': raw.get('in_stock'),
        'times_bought': raw.get('times_bought'),
        'merchant_demand_score': m['merchant_demand_score'],
        'competition_score': m['competition_score'],
        'merchant_whitespace_score': m['merchant_whitespace_score'],
        'merchant_trust_score': m['merchant_trust_score'],
        'pain_signal_score': m['pain_signal_score'],
        'seasonal_score': m['seasonal_score'],
        'commercial_score': m['commercial_score'],
        'purchase_signal_score': m['purchase_signal_score'],
        'ai_product_fit_score': product_fit,
        'ai_creative_score': creative,
        'ai_value_score': value,
        'ai_confidence': confidence,
        'ai_risk_score': risk,
        'rank_score': round(score, 3),
        'rank_band': band,
        'promotion_angle': ranking.get('promotion_angle'),
        'promotion_reason': ranking.get('promotion_reason') or ranking.get('rationale'),
        'audience': ranking.get('audience'),
        'recommended_channels': channels,
        'risk_flags': risk_flags,
        'evidence_summary': {
            'pain_matches': len(item.get('_pains') or []),
            'theme_matches': len(item.get('_themes') or []),
            'deterministic_rank_score': m['deterministic_rank_score'],
            'audit_reasons': audit.get('reasons') or [],
        },
        'ai_summary': audit.get('audit_summary') or ranking.get('rationale'),
    }


def main(feed):
    cfg = load_runtime_config(v1)
    apply_runtime_config(v1, cfg)
    health = v1.gateway('health')
    if not health.get('deepseek_configured'):
        raise SystemExit('Ranking V3 requires AI for final promotion list; DeepSeek is not configured.')
    context = v1.gateway('context')

    reused = False
    if v1.REUSE_STAGE and Path(v1.STAGE_DB).exists():
        try:
            db = v1.init_stage(v1.STAGE_DB, reset=False)
            staged = db.execute('select count(*) from candidates').fetchone()[0]
            reused = staged > 0
        except Exception:
            reused = False
    if reused:
        stream_stats = {'stage_reused_from_phase_a': True, 'commission_eligible_records': staged}
    else:
        db, stream_stats = v1.stage_feed(feed, context)
        stream_stats = dict(stream_stats)

    shortlist, shortlist_stats = preselect(v1.iter_best_offers(db, v1.AI_OFFERS_PER_PRODUCT), context)
    ai_outputs, ai_stats = rank_with_ai(shortlist)
    rows = []
    for item in shortlist:
        h = str(item['product']['source_record_hash'])
        if h not in ai_outputs:
            continue
        rows.append(final_row(item, ai_outputs[h]))
    rows.sort(key=lambda x: (x['rank_score'], x['ai_confidence'], num(x['expected_commission_eur'])), reverse=True)
    rows = rows[:SAVE_LIMIT]

    run_key = os.getenv('GITHUB_RUN_ID') or datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    run_key = f"{run_key}-{os.getenv('GITHUB_RUN_ATTEMPT', '1')}"
    start = v1.gateway('ranking_start', run_key=run_key, engine_version=ENGINE_VERSION, metadata={
        'runtime_config_version': cfg.get('_version'),
        'pain_clusters_available': len(context.get('pain_clusters') or []),
        'themes_available': len(context.get('themes') or []),
        'policy': 'ranking-first; pain is optional signal, not admission gate',
    })
    run_id = start['run_id']

    saved = 0
    for i in range(0, len(rows), 40):
        result = v1.gateway('save_rankings', run_id=run_id, items=rows[i:i + 40])
        saved += int(result.get('saved') or 0)
    v1.gateway('ranking_complete', run_id=run_id, records_seen=int(stream_stats.get('records_seen') or 0),
               eligible_candidates=int(stream_stats.get('commission_eligible_records') or 0),
               ai_ranked=int(ai_stats.get('ai_ranked') or 0), saved_count=saved,
               metadata={'shortlist': shortlist_stats, 'ai': ai_stats})

    bands = collections.Counter(x['rank_band'] for x in rows)
    profile = {
        'engine_version': ENGINE_VERSION,
        'run_key': run_key,
        **stream_stats,
        **shortlist_stats,
        **ai_stats,
        'saved_rankings': saved,
        'bands': dict(bands),
        'top_20': [{k: x.get(k) for k in ('product_name','merchant_name','rank_score','rank_band','expected_commission_eur','promotion_angle','recommended_channels')} for x in rows[:20]],
        'ranking_policy': 'Every deterministic eligible product can compete. Missing pain lowers evidence strength but never causes automatic exclusion.',
    }
    PROFILE.write_text(json.dumps(profile, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    print(json.dumps({'product_ranking_v3': profile}, ensure_ascii=False, default=str), flush=True)
    db.close()


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else v1.SOURCE_FEED)
