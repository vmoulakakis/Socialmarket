"""SocialMarket Affiliate Night Brain v1.

One nightly autonomous affiliate pipeline:
  live catalog -> hard commercial gates -> 5-signal opportunity scoring ->
  bounded local AI opportunity reasoning -> diversified exploit/explore portfolio ->
  durable Top 100 -> mandatory mixed Top 20 creatives -> SocialScheduler handoff.

Business invariant: expected commission >= EUR 10 is a hard economic floor, not the
ranking objective. Ranking optimizes profitable conversion opportunity using
conversion/money potential, demand/supply gap, freshness/opportunity, product +
merchant quality and must-buy pain fit.

Safety invariant: the Top 100 is persisted and completed BEFORE creative work.
Creative/asset/publishing failure must never erase a valid ranking.
"""
from __future__ import annotations

import collections
import heapq
import html
import json
import math
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import product_intelligence_v1 as v1
import product_ranking_v3 as v3
import product_ranking_v32 as v32
import product_local_autopilot as local_ai
from creative_contract_v10 import excluded_vertical
from product_agents import clamp
from runtime_config import apply_runtime_config, load_runtime_config

ENGINE_VERSION = 'affiliate_night_brain_v1'
PROFILE = Path(os.getenv('PRODUCT_RANK_PROFILE_PATH', 'product-ranking-v3-profile.json'))
AI_CANDIDATE_DEFAULT = 120
FINAL_N = 100


def num(v: Any, default: float = 0.0) -> float:
    try:
        return float(default if v in (None, '') else v)
    except Exception:
        return float(default)


def pct(v: Any) -> float:
    x = num(v)
    if 0 <= x <= 1:
        x *= 100
    return clamp(x)


def _cfg(cfg: Mapping[str, Any]) -> dict[str, Any]:
    night = cfg.get('night_brain') if isinstance(cfg.get('night_brain'), dict) else {}
    weights = night.get('weights') if isinstance(night.get('weights'), dict) else {}
    portfolio = night.get('portfolio') if isinstance(night.get('portfolio'), dict) else {}
    ai = night.get('ai') if isinstance(night.get('ai'), dict) else {}
    creatives = night.get('creatives') if isinstance(night.get('creatives'), dict) else {}
    return {
        'weights': {
            'conversion_money': num(weights.get('conversion_money'), 35),
            'demand_supply_gap': num(weights.get('demand_supply_gap'), 25),
            'opportunity_freshness': num(weights.get('opportunity_freshness'), 20),
            'product_merchant_quality': num(weights.get('product_merchant_quality'), 10),
            'must_buy_pain': num(weights.get('must_buy_pain'), 10),
        },
        'top_n': max(100, int(portfolio.get('top_n') or FINAL_N)),
        'winner_target': max(0, int(portfolio.get('winner_target') or 55)),
        'opportunity_target': max(0, int(portfolio.get('opportunity_target') or 30)),
        'must_buy_target': max(0, int(portfolio.get('must_buy_target') or 15)),
        'renewal_min': max(0, min(100, int(portfolio.get('renewal_min_pct') or 25))),
        'renewal_target': max(0, min(100, int(portfolio.get('renewal_target_pct') or 40))),
        'renewal_max': max(0, min(100, int(portfolio.get('renewal_max_pct') or 50))),
        'max_per_merchant': max(2, int(portfolio.get('max_per_merchant') or 8)),
        'max_per_category': max(4, int(portfolio.get('max_per_top_category') or 15)),
        'ai_candidates': max(100, min(180, int(ai.get('candidate_limit') or AI_CANDIDATE_DEFAULT))),
        'creative_top_n': max(0, min(30, int(creatives.get('top_n') or 20))),
        'creative_winners': max(0, int(creatives.get('winner_target') or 8)),
        'creative_opportunities': max(0, int(creatives.get('opportunity_target') or 8)),
        'creative_must_buy': max(0, int(creatives.get('must_buy_target') or 4)),
    }


def top_category(raw: Any) -> str:
    text = html.unescape(str(raw or 'unknown')).strip().lower()
    parts = [p.strip() for p in re.split(r'\s*(?:->|>|/|\\)\s*', text) if p.strip()]
    return (parts[0] if parts else text or 'unknown')[:120]


def newness_signal(raw: Mapping[str, Any]) -> float:
    value = raw.get('valid_from') or raw.get('created_at') or raw.get('first_seen_at')
    if not value:
        return 0.0
    try:
        dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        days = max(0.0, (datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).total_seconds() / 86400)
        if days <= 2:
            return 100.0
        if days <= 7:
            return 85.0
        if days <= 14:
            return 70.0
        if days <= 30:
            return 50.0
        if days <= 60:
            return 25.0
    except Exception:
        return 0.0
    return 0.0


def first_party_signal(item: Mapping[str, Any]) -> tuple[float, dict[str, Any]]:
    fp = item.get('_first_party_kpi') or {}
    impressions = max(0.0, num(fp.get('impressions')))
    clicks = max(0.0, num(fp.get('outbound_clicks')))
    conversions = max(0.0, num(fp.get('conversions_approved')))
    revenue = max(0.0, num(fp.get('commission_approved_eur')))
    ctr = clicks / impressions * 100 if impressions else None
    cvr = conversions / clicks * 100 if clicks else None
    epc = revenue / clicks if clicks else None
    sample = min(1.0, math.log1p(clicks) / math.log1p(300)) if clicks else 0.0
    observed = (
        (clamp((cvr or 0) * 12) * .45)
        + (clamp((epc or 0) * 80) * .40)
        + (clamp((ctr or 0) * 10) * .15)
    )
    score = observed * sample
    return round(clamp(score), 3), {
        'impressions': int(impressions), 'clicks': int(clicks), 'approved_conversions': int(conversions),
        'approved_commission_eur': round(revenue, 4), 'ctr_pct': None if ctr is None else round(ctr, 3),
        'cvr_pct': None if cvr is None else round(cvr, 3), 'epc_eur': None if epc is None else round(epc, 4),
        'sample_confidence': round(sample, 3),
    }


def affiliate_signals(item: Mapping[str, Any], weights: Mapping[str, float]) -> dict[str, Any]:
    raw = item.get('_raw') or {}
    merchant = item.get('merchant') or {}
    m = item.get('_rank_metrics') or {}
    deep = item.get('_deep_demand') or {}
    program = item.get('_program_kpi') or {}

    fp_score, fp = first_party_signal(item)
    network = clamp(num(m.get('network_performance_score')))
    purchase = clamp(num(m.get('purchase_signal_score')))
    commission = clamp(num(m.get('commercial_score')))
    conversion = clamp(network * .40 + purchase * .20 + fp_score * .40)
    conversion_money = clamp(conversion * .80 + commission * .20)

    demand = clamp(num(m.get('merchant_demand_score')))
    whitespace = clamp(num(m.get('merchant_whitespace_score')))
    inverse = clamp(num(m.get('inverse_competition_score')))
    deep_score = clamp(num(m.get('deep_demand_score')))
    demand_gap = clamp(demand * .35 + whitespace * .30 + inverse * .15 + deep_score * .20)

    fresh = newness_signal(raw)
    seasonal = clamp(num(m.get('seasonal_score')))
    discount = clamp(num(m.get('discount_score')))
    opportunity = clamp(fresh * .35 + seasonal * .20 + discount * .15 + demand_gap * .30)

    trust = clamp(num(m.get('merchant_trust_score')))
    program_conf = pct(program.get('data_confidence'))
    quality = clamp(trust * .70 + program_conf * .30)

    pain = clamp(num(m.get('pain_signal_score')))
    must_buy = clamp(pain * .55 + demand_gap * .30 + purchase * .15)

    total_weight = max(1.0, sum(num(x) for x in weights.values()))
    score = clamp(sum({
        'conversion_money': conversion_money,
        'demand_supply_gap': demand_gap,
        'opportunity_freshness': opportunity,
        'product_merchant_quality': quality,
        'must_buy_pain': must_buy,
    }[k] * num(weights.get(k)) for k in weights) / total_weight)

    if must_buy >= 62 and pain >= 35:
        segment = 'MUST_BUY'
    elif opportunity >= 62 and (fresh >= 35 or demand_gap >= 70):
        segment = 'OPPORTUNITY'
    elif conversion_money >= 62 or fp_score >= 55:
        segment = 'WINNER'
    else:
        segment = 'CORE'

    return {
        'conversion_money_score': round(conversion_money, 3),
        'demand_supply_gap_score': round(demand_gap, 3),
        'opportunity_freshness_score': round(opportunity, 3),
        'product_merchant_quality_score': round(quality, 3),
        'must_buy_pain_score': round(must_buy, 3),
        'newness_score': round(fresh, 3),
        'first_party_signal_score': fp_score,
        'first_party': fp,
        'affiliate_score': round(score, 3),
        'strategy_segment': segment,
        'deep_demand_optional': bool(deep.get('matched')),
    }


def _cheap_item(product: Mapping[str, Any], decision_index: Mapping[str, Any], weights: Mapping[str, float]) -> dict[str, Any]:
    item = {'product': {}, 'merchant': product.get('merchant_context') or {}, '_raw': product, '_pains': [], '_themes': []}
    v3.attach_commercial_context(item, decision_index)
    item['_deep_demand'] = v3.match_deep_demand(item, decision_index)
    item['_rank_metrics'] = v3.deterministic_metrics(item)
    item['_affiliate'] = affiliate_signals(item, weights)
    return item


def build_frontier(db: Any, context: Mapping[str, Any], decision_index: Mapping[str, Any], policy: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    heap: list[tuple[float, int, Mapping[str, Any]]] = []
    considered = 0
    frontier_size = max(800, min(2000, policy['ai_candidates'] * 10))
    for product in v1.iter_best_offers(db, 1):
        considered += 1
        item = _cheap_item(product, decision_index, policy['weights'])
        score = num(item['_affiliate']['affiliate_score'])
        entry = (score, considered, product)
        if len(heap) < frontier_size:
            heapq.heappush(heap, entry)
        elif score > heap[0][0]:
            heapq.heapreplace(heap, entry)

    full: list[dict[str, Any]] = []
    for _, _, product in sorted(heap, reverse=True):
        item = v1.build_ai_item(product, context)
        v3.attach_commercial_context(item, decision_index)
        item['_deep_demand'] = v3.match_deep_demand(item, decision_index)
        item['_rank_metrics'] = v3.deterministic_metrics(item)
        item['_affiliate'] = affiliate_signals(item, policy['weights'])
        full.append(item)
    full.sort(key=lambda x: num((x.get('_affiliate') or {}).get('affiliate_score')), reverse=True)

    selected: list[dict[str, Any]] = []
    merchant_counts = collections.Counter()
    category_counts = collections.Counter()
    for item in full:
        merchant = str((item.get('merchant') or {}).get('merchant_id') or 'unknown')
        category = top_category((item.get('_raw') or {}).get('category_raw'))
        if merchant_counts[merchant] >= policy['max_per_merchant']:
            continue
        if category_counts[category] >= policy['max_per_category']:
            continue
        selected.append(item)
        merchant_counts[merchant] += 1
        category_counts[category] += 1
        if len(selected) >= policy['ai_candidates']:
            break

    if len(selected) < 100:
        chosen = {str((x.get('_raw') or {}).get('source_record_hash')) for x in selected}
        for item in full:
            h = str((item.get('_raw') or {}).get('source_record_hash'))
            if h in chosen:
                continue
            selected.append(item); chosen.add(h)
            if len(selected) >= max(100, policy['ai_candidates']):
                break

    return selected, {
        'eligible_candidates_considered': considered,
        'deterministic_frontier': len(full),
        'ai_shortlist': len(selected),
        'unique_merchants': len({str((x.get('merchant') or {}).get('merchant_id')) for x in selected}),
        'unique_top_categories': len({top_category((x.get('_raw') or {}).get('category_raw')) for x in selected}),
        'policy': 'single-pass hard-gated feed -> five-signal deterministic frontier -> diversity caps -> local affiliate agent',
    }


def _agent_task(item: Mapping[str, Any]) -> Any:
    raw = item.get('_raw') or {}
    a = item.get('_affiliate') or {}
    compact = local_ai._compact_product(item)
    compact['affiliate_signals'] = {k: a.get(k) for k in (
        'conversion_money_score', 'demand_supply_gap_score', 'opportunity_freshness_score',
        'product_merchant_quality_score', 'must_buy_pain_score', 'newness_score', 'first_party_signal_score', 'strategy_segment')}
    compact['first_party'] = a.get('first_party') or {}
    compact['business_context'] = {
        'objective': 'maximize approved affiliate profit now, balancing proven winners with fresh opportunities and must-buy pain solvers',
        'commission_rule': 'EUR 10 minimum is a hard economic gate, never the main ranking objective',
        'exploit_explore': 'protect products with conversion evidence while actively challenging them with high-quality new demand/supply gaps',
        'deep_demand': 'optional modeled context; missing or stale context is never automatic rejection',
        'quality': 'freshness alone never beats a materially stronger conversion-quality candidate',
    }
    return local_ai.AITask(
        task_type='affiliate_night_brain_opportunity',
        role='Senior Greek Affiliate Opportunity Strategist',
        prompt_version='night-brain-v1', max_tier=2, cacheable=True, material_change_capable=True,
        required_keys=(
            'source_record_hash', 'product_market_fit_score', 'creative_potential_score', 'value_score', 'confidence_score',
            'conversion_potential_score', 'opportunity_score', 'must_buy_score', 'strategy_segment',
            'promotion_angle', 'promotion_reason', 'audience', 'recommended_channels', 'rationale'),
        instructions=(
            'Think like an opportunistic affiliate operator, not a commission leaderboard. Use only supplied evidence. '
            'The product already passed the EUR10 economic gate. Decide how likely it is to convert profitably NOW in Greece, whether demand exceeds effective supply/competition, whether it is a credible fresh opportunity, and whether it solves a must-buy pain. '
            'Protect proven conversion evidence but allow strong new challengers with clear demand-gap/value reasons. Freshness is a bonus only when quality and purchase reason are credible. '
            'Score 0-100: product_market_fit_score, creative_potential_score, value_score, confidence_score, conversion_potential_score, opportunity_score, must_buy_score. '
            'strategy_segment must be WINNER, CORE, OPPORTUNITY, or MUST_BUY. Missing Deep Demand or pain evidence is not rejection and gives no invented bonus. '
            'recommended_channels may contain only instagram, facebook, tiktok. Use natural concise Greek for promotion_angle, promotion_reason, audience and rationale. Return exact source_record_hash.'
        ), payload=compact, metadata={'bulk_feed_exposed': False, 'affiliate_night_brain': True},
    )


def rank_with_agent(items: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    router = local_ai._router(max(420, local_ai.LOCAL_RANK_OUTPUT_TOKENS))
    outputs: dict[str, dict[str, Any]] = {}
    telemetry: list[dict[str, Any]] = []

    def run_one(item: dict[str, Any]):
        h = str((item.get('product') or {}).get('source_record_hash') or (item.get('_raw') or {}).get('source_record_hash') or '')
        data, stats = local_ai._run_task(router, _agent_task(item))
        if not data or str(data.get('source_record_hash') or '') != h:
            return h, None, stats
        for key in ('product_market_fit_score','creative_potential_score','value_score','confidence_score','conversion_potential_score','opportunity_score','must_buy_score'):
            data[key] = clamp(num(data.get(key)))
        seg = str(data.get('strategy_segment') or '').upper()
        data['strategy_segment'] = seg if seg in ('WINNER','CORE','OPPORTUNITY','MUST_BUY') else (item.get('_affiliate') or {}).get('strategy_segment','CORE')
        data['recommended_channels'] = local_ai._normalize_channels(data.get('recommended_channels'))
        return h, data, stats

    workers = max(1, min(2, local_ai.LOCAL_AI_WORKERS))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(run_one, item): item for item in items}
        for future in as_completed(futures):
            h, data, stats = future.result(); telemetry.append(stats)
            if data is not None:
                outputs[h] = data

    calls = sum(1 for x in telemetry if x.get('status') == 'ok' and not x.get('from_cache'))
    cache_hits = sum(1 for x in telemetry if x.get('from_cache'))
    return outputs, {
        'agent_candidates': len(items), 'agent_ranked': len(outputs), 'local_model_calls': calls,
        'local_cache_hits': cache_hits, 'local_model': local_ai.LOCAL_MODEL,
        'paid_inference_cost_usd': round(sum(num(x.get('cost_usd')) for x in telemetry), 6),
        'ai_is_gate': False,
    }


def build_rows(items: list[dict[str, Any]], agent_outputs: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in items:
        h = str((item.get('product') or {}).get('source_record_hash') or (item.get('_raw') or {}).get('source_record_hash') or '')
        a = item.get('_affiliate') or {}
        agent = dict(agent_outputs.get(h) or {})
        if not agent:
            agent = {
                'product_market_fit_score': a.get('demand_supply_gap_score', 50),
                'creative_potential_score': a.get('opportunity_freshness_score', 50),
                'value_score': a.get('conversion_money_score', 50),
                'confidence_score': 45,
                'conversion_potential_score': a.get('conversion_money_score', 50),
                'opportunity_score': a.get('opportunity_freshness_score', 50),
                'must_buy_score': a.get('must_buy_pain_score', 50),
                'strategy_segment': a.get('strategy_segment','CORE'),
                'promotion_angle': 'Επιλογή βάσει εμπορικών σημάτων και ζήτησης',
                'promotion_reason': 'Deterministic affiliate fallback χωρίς εφεύρεση στοιχείων.',
                'audience': 'Ελληνικό κοινό με σχετική πρόθεση αγοράς',
                'recommended_channels': ['instagram','facebook'],
                'rationale': 'AI unavailable; deterministic five-signal ranking retained.',
            }
        row = v3.final_row(item, {'ranking': agent, 'audit': {'risk_score': 0, 'risk_flags': []}})
        ai_business = clamp(
            num(agent.get('conversion_potential_score')) * .40
            + num(agent.get('opportunity_score')) * .25
            + num(agent.get('must_buy_score')) * .15
            + num(agent.get('product_market_fit_score')) * .15
            + num(agent.get('confidence_score')) * .05
        )
        det = clamp(num(a.get('affiliate_score')))
        quality = clamp(num(a.get('product_merchant_quality_score')))
        penalty = max(0.0, (45.0 - quality) * .20)
        final = clamp(det * .65 + ai_business * .35 - penalty)
        seg = str(agent.get('strategy_segment') or a.get('strategy_segment') or 'CORE').upper()
        if seg == 'MUST_BUY' and max(num(agent.get('must_buy_score')), num(a.get('must_buy_pain_score'))) < 58:
            seg = 'OPPORTUNITY' if num(a.get('opportunity_freshness_score')) >= 62 else 'CORE'
        if seg == 'OPPORTUNITY' and num(a.get('newness_score')) < 20 and num(a.get('demand_supply_gap_score')) < 65:
            seg = 'WINNER' if num(a.get('conversion_money_score')) >= 62 else 'CORE'
        row['rank_score'] = round(final, 3)
        row['rank_band'] = 'PROMOTE_NOW' if final >= 82 else 'HIGH_POTENTIAL' if final >= 72 else 'TEST' if final >= 62 else 'WATCHLIST'
        row['evidence_summary'] = {
            **(row.get('evidence_summary') or {}),
            'night_brain': a,
            'strategy_segment': seg,
            'ai_business_score': round(ai_business, 3),
            'quality_penalty': round(penalty, 3),
            'engine': ENGINE_VERSION,
        }
        row['ai_summary'] = f"{seg}: {agent.get('rationale') or row.get('ai_summary') or ''}"[:4000]
        row['_strategy_segment'] = seg
        row['_top_category'] = top_category(row.get('category'))
        rows.append(row)
    rows.sort(key=lambda x: (num(x.get('rank_score')), num(x.get('ai_confidence')), num(x.get('expected_commission_eur'))), reverse=True)
    return rows


def portfolio_select(rows: list[dict[str, Any]], policy: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    chosen: set[str] = set()
    mc = collections.Counter(); cc = collections.Counter()

    def add(row: dict[str, Any]) -> bool:
        h = str(row.get('source_record_hash') or '')
        merchant = str(row.get('merchant_id') or row.get('merchant_name') or 'unknown')
        category = str(row.get('_top_category') or top_category(row.get('category')))
        if not h or h in chosen:
            return False
        if mc[merchant] >= policy['max_per_merchant'] or cc[category] >= policy['max_per_category']:
            return False
        selected.append(row); chosen.add(h); mc[merchant] += 1; cc[category] += 1
        return True

    buckets = {
        'MUST_BUY': [r for r in rows if r.get('_strategy_segment') == 'MUST_BUY'],
        'OPPORTUNITY': [r for r in rows if r.get('_strategy_segment') == 'OPPORTUNITY'],
        'WINNER_CORE': [r for r in rows if r.get('_strategy_segment') in ('WINNER','CORE')],
    }
    targets = [('MUST_BUY', policy['must_buy_target']), ('OPPORTUNITY', policy['opportunity_target']), ('WINNER_CORE', policy['winner_target'])]
    for name, target in targets:
        taken = 0
        for row in buckets[name]:
            if add(row):
                taken += 1
            if taken >= target:
                break

    for row in rows:
        if len(selected) >= policy['top_n']:
            break
        add(row)

    # If strict diversity caps leave us below 100, relax only the category cap first,
    # then merchant cap as a final completeness fallback. Never relax hard economic gates.
    if len(selected) < policy['top_n']:
        for row in rows:
            h = str(row.get('source_record_hash') or '')
            merchant = str(row.get('merchant_id') or row.get('merchant_name') or 'unknown')
            if h in chosen or mc[merchant] >= policy['max_per_merchant']:
                continue
            selected.append(row); chosen.add(h); mc[merchant] += 1
            if len(selected) >= policy['top_n']:
                break
    if len(selected) < policy['top_n']:
        for row in rows:
            h = str(row.get('source_record_hash') or '')
            if h in chosen:
                continue
            selected.append(row); chosen.add(h)
            if len(selected) >= policy['top_n']:
                break

    selected = selected[:policy['top_n']]
    selected.sort(key=lambda x: num(x.get('rank_score')), reverse=True)
    for idx, row in enumerate(selected, 1):
        row['evidence_summary'] = {**(row.get('evidence_summary') or {}), 'night_brain_global_rank': idx}

    counts = collections.Counter(str(r.get('_strategy_segment') or 'CORE') for r in selected)
    renewal = counts['OPPORTUNITY'] + counts['MUST_BUY']
    return selected, {
        'portfolio_counts': dict(counts), 'renewal_count': renewal,
        'renewal_pct': round(renewal / max(1, len(selected)) * 100, 2),
        'renewal_target_pct': policy['renewal_target'], 'renewal_bounds_pct': [policy['renewal_min'], policy['renewal_max']],
        'max_per_merchant': policy['max_per_merchant'], 'max_per_top_category': policy['max_per_category'],
        'portfolio_policy': 'soft 55 winner/core + 30 opportunity + 15 must-buy; quality-ranked fill; diversity caps relax only for Top100 completeness',
    }


def creative_mix(rows: list[dict[str, Any]], policy: Mapping[str, Any]) -> list[dict[str, Any]]:
    picked: list[dict[str, Any]] = []; chosen: set[str] = set()
    plans = [
        (('WINNER','CORE'), policy['creative_winners']),
        (('OPPORTUNITY',), policy['creative_opportunities']),
        (('MUST_BUY',), policy['creative_must_buy']),
    ]
    for segments, target in plans:
        n = 0
        for row in rows:
            h = str(row.get('source_record_hash') or '')
            if h in chosen or row.get('_strategy_segment') not in segments:
                continue
            picked.append(dict(row)); chosen.add(h); n += 1
            if n >= target:
                break
    for row in rows:
        if len(picked) >= policy['creative_top_n']:
            break
        h = str(row.get('source_record_hash') or '')
        if h not in chosen:
            picked.append(dict(row)); chosen.add(h)
    return picked[:policy['creative_top_n']]


def main(feed: str) -> dict[str, Any]:
    cfg = load_runtime_config(v1); apply_runtime_config(v1, cfg); policy = _cfg(cfg)
    if num(v1.MIN_COMMISSION) < 10:
        raise SystemExit(f'Night Brain requires economic floor >= EUR10; got {v1.MIN_COMMISSION}')

    run_key = f"{os.getenv('GITHUB_RUN_ID') or datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{os.getenv('GITHUB_RUN_ATTEMPT','1')}"
    run = v32.BASE_RANK_GATEWAY('ranking_start', run_key=run_key, engine_version=ENGINE_VERSION, metadata={
        'runtime_config_version': cfg.get('_version'), 'orchestrator': ENGINE_VERSION,
        'stage': 'starting', 'owner_min_expected_commission_eur': float(v1.MIN_COMMISSION),
        'objective': 'profitable conversion + demand/supply opportunity + freshness + quality + must-buy pain',
        'paid_llm_required': False, 'bulk_feed_to_llm': False, 'ai_is_gate': False,
    })
    run_id = str(run['run_id']); db = None; stage = 'context'
    try:
        context = v1.gateway('context')
        decision_payload = v32.BASE_RANK_GATEWAY('decision_context')
        decision_index = v3.prepare_decision_context(decision_payload)

        stage = 'single_pass_stage'
        db, stream_stats = v1.stage_feed(feed, context); stream_stats = dict(stream_stats)
        stage = 'five_signal_frontier'
        shortlist, shortlist_stats = build_frontier(db, context, decision_index, policy)
        # Defence in depth: the streaming gate is authoritative, but no excluded
        # vertical may enter agent ranking even if a future staging implementation
        # omits the canonical publication policy.
        excluded_from_frontier = sum(1 for row in shortlist if excluded_vertical(row))
        shortlist = [row for row in shortlist if not excluded_vertical(row)]
        shortlist_stats = {**shortlist_stats, 'excluded_verticals_from_frontier': excluded_from_frontier}
        if len(shortlist) < 100:
            raise RuntimeError(f'Night Brain frontier too small for Top100: {len(shortlist)}')

        stage = 'affiliate_agent'
        agent_outputs, agent_stats = rank_with_agent(shortlist)
        stage = 'portfolio'
        rows = build_rows(shortlist, agent_outputs)
        final_rows, portfolio_stats = portfolio_select(rows, policy)
        if len(final_rows) < 100:
            raise RuntimeError(f'Night Brain Top100 completeness failed: {len(final_rows)}')
        if any(num(x.get('expected_commission_eur')) + 1e-9 < 10 for x in final_rows):
            raise RuntimeError('EUR10 commission hard gate violation after portfolio selection')
        if any(excluded_vertical(x) for x in final_rows):
            raise RuntimeError('excluded vertical hard gate violation before Top100 persistence')

        # Deterministic SEO is safe and cheap. It is part of ranking persistence, but no
        # generative/creative dependency can block the Top100.
        final_rows, seo_stats = local_ai.enrich_seo_deterministic(final_rows)
        stage = 'persist_top100'
        saved = 0
        for i in range(0, len(final_rows), 40):
            saved += int(v32.BASE_RANK_GATEWAY('save_rankings', run_id=run_id, items=final_rows[i:i+40]).get('saved') or 0)
        if saved < 100:
            raise RuntimeError(f'Top100 persistence incomplete: {saved}/100')

        # The ranking is now authoritative. Creative failure below cannot roll it back.
        v32.BASE_RANK_GATEWAY('ranking_complete', run_id=run_id,
            records_seen=int(stream_stats.get('records_seen') or 0),
            eligible_candidates=int(stream_stats.get('commission_eligible_records') or 0),
            ai_ranked=int(agent_stats.get('agent_ranked') or 0), saved_count=saved,
            metadata={'shortlist': shortlist_stats, 'agent': agent_stats, 'portfolio': portfolio_stats,
                      'seo': seo_stats, 'orchestrator': ENGINE_VERSION, 'ranking_survives_creative_failure': True})

        stage = 'mandatory_v10_creatives'
        mix = creative_mix(final_rows, policy)
        # Put the selected exploit/explore mix first because the local creative engine
        # intentionally works on rows[:20].
        rest = [dict(x) for x in final_rows if x.get('source_record_hash') not in {m.get('source_record_hash') for m in mix}]
        creative_rows = mix + rest
        creative_rows, generated = local_ai.enrich_creatives_local(creative_rows)
        creative_items = creative_rows[:policy['creative_top_n']]
        persisted = 0
        for i in range(0, len(creative_items), 40):
            persisted += int(v32.rank_gateway_final('save_rankings', run_id=run_id, items=creative_items[i:i+40]).get('saved') or 0)
        if persisted < policy['creative_top_n']:
            raise RuntimeError(f'v10 creative persistence incomplete: {persisted}/{policy["creative_top_n"]}')
        stage = 'mandatory_v10_finalize'
        final_contract = v32.rank_gateway_final(
            'ranking_complete', run_id=run_id,
            records_seen=int(stream_stats.get('records_seen') or 0),
            eligible_candidates=int(stream_stats.get('commission_eligible_records') or 0),
            ai_ranked=int(agent_stats.get('agent_ranked') or 0), saved_count=saved,
            metadata={'shortlist': shortlist_stats, 'agent': agent_stats, 'portfolio': portfolio_stats,
                      'seo': seo_stats, 'orchestrator': ENGINE_VERSION, 'v10_handoff_required': True},
        )
        creative_stats = {**generated, 'creative_status': 'completed', 'creative_rankings_persisted': persisted,
                          'final_contract': final_contract,
                          'mix': dict(collections.Counter(x.get('_strategy_segment','CORE') for x in creative_items))}

        profile = {
            'engine_version': ENGINE_VERSION, 'run_key': run_key,
            'owner_min_expected_commission_eur': float(v1.MIN_COMMISSION),
            **stream_stats, **shortlist_stats, **agent_stats, **portfolio_stats, **seo_stats,
            'saved_rankings': saved, 'creative': creative_stats,
            'paid_llm_required': False, 'bulk_feed_to_llm': False,
            'deep_demand_role': 'optional additive context, never a hard gate',
            'top_20': [
                {k: x.get(k) for k in ('product_name','merchant_name','rank_score','rank_band','expected_commission_eur','promotion_angle')}
                | {'strategy_segment': x.get('_strategy_segment'), 'night_brain': (x.get('evidence_summary') or {}).get('night_brain')}
                for x in final_rows[:20]
            ],
        }
        PROFILE.write_text(json.dumps(profile, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
        print(json.dumps({'affiliate_night_brain': profile}, ensure_ascii=False, default=str), flush=True)
        return profile
    except BaseException as exc:
        if isinstance(exc, KeyboardInterrupt):
            raise
        # Keep a bounded diagnostic artifact even when the mandatory creative
        # contract fails. The GitHub workflow uploads it with `if: always()`.
        failure_profile = {
            'engine_version': ENGINE_VERSION, 'run_key': run_key, 'run_id': run_id,
            'status': 'failed', 'failed_stage': stage, 'error': str(exc)[:1600],
            'ranking_preserved': stage in {'mandatory_v10_creatives', 'mandatory_v10_finalize'},
            'paid_llm_required': False,
        }
        try:
            PROFILE.write_text(json.dumps(failure_profile, ensure_ascii=False, indent=2), encoding='utf-8')
        except Exception as profile_exc:
            print(json.dumps({'warning': 'night_brain_failure_profile_write_failed', 'error': str(profile_exc)[:800]}), flush=True)
        try:
            # Observability failure marking is best-effort; never hide the root error.
            import product_ranking_v363_production as old_prod
            old_prod.run_observability('ranking_fail', run_id=run_id, stage=stage, error=str(exc), metadata={
                'engine_version': ENGINE_VERSION, 'run_key': run_key, 'stage': stage,
                'owner_min_expected_commission_eur': float(v1.MIN_COMMISSION), 'paid_llm_required': False})
        except Exception as mark_exc:
            print(json.dumps({'warning':'night_brain_failure_observability_failed','error':str(mark_exc)[:800]}), flush=True)
        raise
    finally:
        if db is not None:
            try:
                db.close()
            except Exception:
                pass


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else v1.SOURCE_FEED)
