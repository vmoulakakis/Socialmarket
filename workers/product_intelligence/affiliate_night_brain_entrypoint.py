"""Production entrypoint for Affiliate Night Brain with bounded business gates.

Keeps the core Night Brain orchestration single and stable while replacing only the
bulk-gate, frontier and local-AI resilience hooks with audited production policy.
"""
from __future__ import annotations

import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import affiliate_night_brain as night
import product_intelligence_v1 as v1
from night_brain_gate_tools import build_frontier_with_business_gates
from night_brain_single_parse_stage import stage_feed


_CORE_BUILD_FRONTIER = night.build_frontier
_CORE_PERSIST_CREATIVE_CONTENT = night.v32._persist_creative_content
AI_ENRICH_LIMIT = max(8, min(40, int(os.getenv('NIGHT_BRAIN_AI_ENRICH_LIMIT', '24'))))


def _frontier(db, context, decision_index, policy):
    return build_frontier_with_business_gates(_CORE_BUILD_FRONTIER, db, context, decision_index, policy)


def _persist_creative_content_with_assets(run_id, item):
    """Guarantee the canonical-content handoff contains all three durable asset URLs.

    The Night Brain creative path normally renders/uploads assets before persistence.
    Re-check at the persistence boundary because canonical content has a stricter
    contract than ranking persistence. If a row lost its asset annotations during a
    preceding save/normalization step, deterministically render/upload the same pack
    again to the same run/hash/variant storage paths before calling persist_content.
    """
    pack = item.get('creative_pack') or {}
    variants = pack.get('variants') if isinstance(pack, dict) else []
    complete = (
        isinstance(variants, list)
        and len(variants) == 3
        and all(str((variant or {}).get('asset_url') or '').startswith('https://') for variant in variants)
    )
    if not complete:
        night.v32._render_upload_one(item)
        pack = item.get('creative_pack') or {}
        variants = pack.get('variants') if isinstance(pack, dict) else []
    if not isinstance(variants, list) or len(variants) != 3 or any(
        not str((variant or {}).get('asset_url') or '').startswith('https://') for variant in variants
    ):
        raise RuntimeError(f'creative asset persistence preflight failed for {item.get("source_record_hash")}')
    return _CORE_PERSIST_CREATIVE_CONTENT(run_id, item)


def _safe_rank_with_agent(items):
    """Keep local AI additive, bounded and non-gating.

    The deterministic five-signal engine ranks the full shortlist. Local AI enriches
    only the strongest bounded slice; all remaining candidates use the deterministic
    fallback already implemented in build_rows(). This avoids a free CPU model
    becoming the throughput bottleneck while preserving AI judgement where it has
    the highest expected business value.
    """
    outputs = {}
    telemetry = []
    enrich_items = list(items[:AI_ENRICH_LIMIT])
    try:
        router = night.local_ai._router(max(420, night.local_ai.LOCAL_RANK_OUTPUT_TOKENS))
    except Exception as exc:
        return {}, {
            'agent_candidates': len(items),
            'agent_enrichment_limit': len(enrich_items),
            'agent_ranked': 0,
            'agent_errors': len(enrich_items),
            'local_model_calls': 0,
            'local_cache_hits': 0,
            'local_model': night.local_ai.LOCAL_MODEL,
            'paid_inference_cost_usd': 0.0,
            'ai_is_gate': False,
            'deterministic_fallback_candidates': len(items),
            'fallback_reason': f'router_unavailable:{str(exc)[:300]}',
        }

    def run_one(item):
        h = str((item.get('product') or {}).get('source_record_hash') or (item.get('_raw') or {}).get('source_record_hash') or '')
        data, stats = night.local_ai._run_task(router, night._agent_task(item))
        if not data or str(data.get('source_record_hash') or '') != h:
            return h, None, stats
        for key in (
            'product_market_fit_score', 'creative_potential_score', 'value_score',
            'confidence_score', 'conversion_potential_score', 'opportunity_score',
            'must_buy_score',
        ):
            data[key] = night.clamp(night.num(data.get(key)))
        seg = str(data.get('strategy_segment') or '').upper()
        data['strategy_segment'] = seg if seg in ('WINNER', 'CORE', 'OPPORTUNITY', 'MUST_BUY') else (item.get('_affiliate') or {}).get('strategy_segment', 'CORE')
        data['recommended_channels'] = night.local_ai._normalize_channels(data.get('recommended_channels'))
        return h, data, stats

    workers = max(1, min(2, night.local_ai.LOCAL_AI_WORKERS))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(run_one, item): item for item in enrich_items}
        for future in as_completed(futures):
            item = futures[future]
            try:
                h, data, stats = future.result()
                telemetry.append(stats or {'status': 'invalid', 'from_cache': False, 'cost_usd': 0})
                if data is not None:
                    outputs[h] = data
            except Exception as exc:
                h = str((item.get('product') or {}).get('source_record_hash') or (item.get('_raw') or {}).get('source_record_hash') or '')
                telemetry.append({
                    'status': 'error',
                    'from_cache': False,
                    'cost_usd': 0,
                    'source_record_hash': h,
                    'error': str(exc)[:500],
                })

    calls = sum(1 for x in telemetry if x.get('status') == 'ok' and not x.get('from_cache'))
    cache_hits = sum(1 for x in telemetry if x.get('from_cache'))
    errors = sum(1 for x in telemetry if x.get('status') == 'error')
    return outputs, {
        'agent_candidates': len(items),
        'agent_enrichment_limit': len(enrich_items),
        'agent_ranked': len(outputs),
        'agent_errors': errors,
        'local_model_calls': calls,
        'local_cache_hits': cache_hits,
        'local_model': night.local_ai.LOCAL_MODEL,
        'paid_inference_cost_usd': round(sum(night.num(x.get('cost_usd')) for x in telemetry), 6),
        'ai_is_gate': False,
        'deterministic_fallback_candidates': max(0, len(items) - len(outputs)),
    }


# Production refinements. Runtime configuration still patches scoring/context helpers
# before execution; these hooks are intentionally narrow and auditable.
v1.stage_feed = stage_feed
night.build_frontier = _frontier
night.rank_with_agent = _safe_rank_with_agent
night.v32._persist_creative_content = _persist_creative_content_with_assets


if __name__ == '__main__':
    night.main(sys.argv[1] if len(sys.argv) > 1 else v1.SOURCE_FEED)
