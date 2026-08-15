import collections

from product_agents import clamp, commission_score, fold


def _num(v, default=0.0):
    try:
        return float(v)
    except Exception:
        return float(default)


def _category_key(item):
    raw = item.get('_raw') or {}
    value = raw.get('category_raw') or item.get('product', {}).get('category_raw') or 'UNKNOWN'
    return fold(value) or 'unknown'


def _merchant_key(item):
    merchant = item.get('merchant') or {}
    raw = item.get('_raw') or {}
    return str(merchant.get('merchant_id') or raw.get('merchant_name') or 'UNKNOWN')


def pain_first_score(item):
    """Deterministic shortlist score used only to decide which candidates deserve AI review.

    This is not the final opportunity score and cannot validate a product. Missing
    competition contributes zero upside instead of being converted to favorable
    inverse competition.
    """
    pains = list(item.get('_pains') or [])
    if not pains:
        return None

    top_retrieval = max((_num(x.get('retrieval_score')) for x in pains), default=0.0)
    severity = max((_num(x.get('pain_severity')) for x in pains), default=0.0)
    intent = max((_num(x.get('commercial_intent')) for x in pains), default=0.0)
    demand = max((_num(x.get('demand_score')) for x in pains), default=0.0)
    observed_comp = [_num(x.get('competition_score')) for x in pains if x.get('competition_score') is not None]
    inverse_comp = 100.0 - (sum(observed_comp) / len(observed_comp)) if observed_comp else 0.0
    evidence = max((min(100.0, _num(x.get('source_diversity')) * 10.0 + _num(x.get('evidence_count')) * 2.0) for x in pains), default=0.0)

    merchant = item.get('merchant') or {}
    whitespace = _num(merchant.get('solution_whitespace_score'))
    trust = _num(merchant.get('trust_score'))
    commission = commission_score((item.get('_raw') or {}).get('expected_commission_eur'))

    score = (
        clamp(top_retrieval) * 0.35
        + clamp(severity) * 0.15
        + clamp(intent) * 0.10
        + clamp(demand) * 0.10
        + clamp(inverse_comp) * 0.08
        + clamp(evidence) * 0.08
        + clamp(whitespace) * 0.07
        + clamp(trust) * 0.04
        + clamp(commission) * 0.03
    )
    return round(clamp(score), 3)


def _take_with_caps(scored, limit, merchant_cap, category_cap):
    selected = []
    deferred = []
    merchant_counts = collections.Counter()
    category_counts = collections.Counter()

    for score, item in scored:
        merchant = _merchant_key(item)
        category = _category_key(item)
        if merchant_counts[merchant] >= merchant_cap or category_counts[category] >= category_cap:
            deferred.append((score, item))
            continue
        item['_shortlist_score'] = score
        selected.append(item)
        merchant_counts[merchant] += 1
        category_counts[category] += 1
        if len(selected) >= limit:
            break

    if len(selected) < limit:
        # Second pass relaxes diversity limits but never relaxes evidence/pain gates.
        for score, item in deferred:
            if len(selected) >= limit:
                break
            merchant = _merchant_key(item)
            category = _category_key(item)
            if merchant_counts[merchant] >= merchant_cap * 2 or category_counts[category] >= category_cap * 2:
                continue
            item['_shortlist_score'] = score
            selected.append(item)
            merchant_counts[merchant] += 1
            category_counts[category] += 1

    if len(selected) < limit:
        # Final fill is still restricted to pain-matched candidates. Diversity is a
        # sampling preference, never a reason to fabricate or lower validation quality.
        chosen = {str(x.get('product', {}).get('source_record_hash')) for x in selected}
        for score, item in scored:
            if len(selected) >= limit:
                break
            h = str(item.get('product', {}).get('source_record_hash'))
            if h in chosen:
                continue
            item['_shortlist_score'] = score
            selected.append(item)
            chosen.add(h)

    return selected[:limit]


def select_ai_shortlist(products, context, build_ai_item, limit, max_per_merchant=20, max_per_category=40):
    """Build a pain-first, diversified shortlist from all deterministic candidates.

    Every candidate is evaluated against validated pain RAG before it can consume an
    AI call. Candidates without validated pain matches are counted and skipped.
    The AI auditor remains fully authoritative for validation.
    """
    stats = collections.Counter()
    scored = []

    for product in products:
        stats['pre_ai_candidates_considered'] += 1
        item = build_ai_item(product, context)
        score = pain_first_score(item)
        if score is None:
            stats['pre_ai_no_validated_pain_match'] += 1
            continue
        stats['pain_matched_candidates'] += 1
        scored.append((score, item))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    merchant_cap = max(1, int(max_per_merchant))
    category_cap = max(1, int(max_per_category))
    selected = _take_with_caps(scored, max(1, int(limit)), merchant_cap, category_cap)

    stats['shortlist_candidates'] = len(selected)
    stats['shortlist_unique_merchants'] = len({_merchant_key(x) for x in selected})
    stats['shortlist_unique_categories'] = len({_category_key(x) for x in selected})
    stats['shortlist_capacity'] = max(1, int(limit))
    stats['shortlist_cap_reached'] = int(len(selected) >= max(1, int(limit)))
    return selected, dict(stats)
