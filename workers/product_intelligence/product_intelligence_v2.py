import collections
import json
import sys
from pathlib import Path

import product_intelligence_v1 as v1
from candidate_shortlist import select_ai_shortlist
from runtime_config import apply_runtime_config, load_runtime_config, save_run_profile


_original_gateway = v1.gateway


def fresh_gateway(action, **payload):
    """Force a fresh short-lived GitHub OIDC token for every gateway request."""
    v1._TOKEN = None
    return _original_gateway(action, **payload)


v1.gateway = fresh_gateway


def main(feed):
    cfg = load_runtime_config(v1)
    apply_runtime_config(v1, cfg)
    print(json.dumps({
        'runtime_product_config': {
            'version': cfg.get('_version'),
            'profile_name': cfg.get('profile_name'),
            'updated_at': cfg.get('_updated_at'),
            'updated_by': cfg.get('_updated_by'),
            'ai_max_candidates': v1.AI_MAX_CANDIDATES,
            'ai_batch': v1.AI_BATCH,
            'ai_max_per_merchant': int(cfg.get('ai_max_per_merchant', 20)),
            'ai_max_per_category': int(cfg.get('ai_max_per_category', 40)),
        }
    }, ensure_ascii=False), flush=True)

    health = v1.gateway('health')
    if not health.get('deepseek_configured'):
        raise SystemExit('Product Intelligence requires DeepSeek configuration for Phase B; refusing non-AI persistence fallback.')

    context = v1.gateway('context')
    pain_count = len(context.get('pain_clusters', []))
    if pain_count < v1.MIN_VALIDATED_PAIN_CLUSTERS:
        raise SystemExit(
            f'Product Intelligence requires at least {v1.MIN_VALIDATED_PAIN_CLUSTERS} validated pain clusters; found {pain_count}. '
            'Do not lower the audit gate: repair upstream category-pain evidence first.'
        )

    print(json.dumps({
        'phase': 'context',
        'programs': len(context.get('programs', [])),
        'pain_clusters': pain_count,
        'themes': len(context.get('themes', [])),
        'deepseek_model': health.get('deepseek_model'),
        'ai_max_candidates': v1.AI_MAX_CANDIDATES,
        'selection': 'pain_first_diversified_v2',
    }), flush=True)

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
        stream_stats['candidate_concentration_flags'] = stream_stats.pop('dynamic_saturated_merchants', [])

    max_per_merchant = max(1, int(cfg.get('ai_max_per_merchant', 20)))
    max_per_category = max(1, int(cfg.get('ai_max_per_category', 40)))
    shortlist, shortlist_stats = select_ai_shortlist(
        v1.iter_best_offers(db, v1.AI_OFFERS_PER_PRODUCT),
        context,
        v1.build_ai_item,
        v1.AI_MAX_CANDIDATES,
        max_per_merchant=max_per_merchant,
        max_per_category=max_per_category,
    )

    print(json.dumps({'phase': 'pre_ai_shortlist', **shortlist_stats}, ensure_ascii=False), flush=True)

    stats = collections.Counter(shortlist_stats)
    batch = []
    submitted = 0
    for item in shortlist:
        batch.append(item)
        if len(batch) >= v1.AI_BATCH:
            v1.process_batch(batch, stats)
            submitted += len(batch)
            batch = []
            print(json.dumps({'phase': 'ai', 'submitted': submitted, **stats}, ensure_ascii=False), flush=True)
    if batch:
        v1.process_batch(batch, stats)
        submitted += len(batch)

    unique_products = db.execute('select count(distinct canonical_key) from candidates').fetchone()[0]
    attempted = int(stats.get('ai_batches_attempted') or 0)
    failures = int(stats.get('ai_batch_failures') or 0)
    failure_rate = (failures / attempted) if attempted else 0.0
    stats['ai_batch_failure_rate'] = round(failure_rate, 4)

    profile = {
        **stream_stats,
        'unique_commission_eligible_products': unique_products,
        'ai_offers_submitted': submitted,
        **stats,
        'policy': {
            'commission_gate_eur': v1.MIN_COMMISSION,
            'merchant_trust_gate': v1.MIN_MERCHANT_TRUST,
            'merchant_resolution': 'Linkwise tracking_url destination domain -> authoritative merchant official_domain; exact program/alias only as secondary path',
            'dominant_merchants': 'excluded only by explicit merchant promotion policy/dominant-market evidence; feed concentration itself is not a kill-switch',
            'feed_concentration': 'diagnostic only; Linkwise feed share is not Greek market share and is controlled by shortlist diversity caps',
            'price_integrity': 'no automatic cents/EUR conversion; statistically suspicious scales are quarantined before commission',
            'selection': 'all deterministic candidates -> validated pain RAG -> pain-first score -> merchant/category diversity -> AI Research -> independent Skeptic Audit',
            'ai_max_candidates': v1.AI_MAX_CANDIDATES,
            'ai_batch': v1.AI_BATCH,
            'ai_max_per_merchant': max_per_merchant,
            'ai_max_per_category': max_per_category,
            'ai_offers_per_product': v1.AI_OFFERS_PER_PRODUCT,
            'max_ai_batch_failure_rate': v1.MAX_AI_BATCH_FAILURE_RATE,
            'persistence': 'VALIDATED only + validated pain + audit/pain/evidence thresholds',
            'ranking': 'final score unchanged: 25 pain + 20 merchant whitespace + 15 Greek demand + 12 commission + 10 inverse competition + 8 seasonal + 5 trust + 3 discount + 2 evidence confidence',
            'validation_target': 'capacity for 100+ validated products is a coverage goal, never a quota; auditor thresholds are not relaxed',
            'raw_feed_imported': False,
            'ai_fallback_allowed': False,
        },
    }

    Path(v1.PROFILE_PATH).write_text(json.dumps(profile, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    print(json.dumps({'product_intelligence_final': profile}, ensure_ascii=False, default=str), flush=True)
    db.close()

    profile['runtime_config_version'] = cfg.get('_version')
    profile['runtime_profile_name'] = cfg.get('profile_name')
    save_run_profile(v1, 'B', profile)

    if failure_rate > v1.MAX_AI_BATCH_FAILURE_RATE:
        raise SystemExit(
            f'AI batch circuit breaker: failure_rate={failure_rate:.3f} exceeds {v1.MAX_AI_BATCH_FAILURE_RATE:.3f}'
        )


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else v1.SOURCE_FEED)
