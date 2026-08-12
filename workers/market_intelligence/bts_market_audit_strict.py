import os
import bts_market_audit as audit

MIN_TIMES_BOUGHT = float(os.getenv('BTS_MIN_TIMES_BOUGHT', '3'))


def strict_percentile_map(rows, cluster):
    """Zero/missing or trivially low purchases are never allowed to become top percentile through ties."""
    qualified = sorted(
        float(p.get('times_bought') or 0)
        for p in rows
        if p.get('semantic_pain_cluster') == cluster
        and float(p.get('times_bought') or 0) >= MIN_TIMES_BOUGHT
    )
    out = {}
    for p in rows:
        if p.get('semantic_pain_cluster') != cluster:
            continue
        v = float(p.get('times_bought') or 0)
        if v < MIN_TIMES_BOUGHT or not qualified:
            out[p['external_product_id']] = 0.0
            continue
        lo, hi = 0, len(qualified)
        while lo < hi:
            mid = (lo + hi) // 2
            if qualified[mid] <= v:
                lo = mid + 1
            else:
                hi = mid
        out[p['external_product_id']] = lo / len(qualified)
    return out


_original_audit_candidate = audit.audit_candidate


def strict_audit_candidate(p, demand_pct, cluster_market):
    result = _original_audit_candidate(p, demand_pct, cluster_market)
    purchases = float(p.get('times_bought') or 0)
    cluster_engagement = float(cluster_market.get('engagement_score') or 0)

    first_party_signal = purchases >= MIN_TIMES_BOUGHT and demand_pct >= 0.65
    greek_market_signal = cluster_engagement >= 45
    signal_count = int(first_party_signal) + int(greek_market_signal)
    high_demand = signal_count >= 2 and float(result.get('demand_score') or 0) >= 60

    failures = [x for x in result.get('hard_fail_reasons', []) if x != 'high_demand_not_verified']
    if not high_demand:
        failures.append('high_demand_not_verified')

    result['times_bought_absolute'] = purchases
    result['minimum_times_bought_gate'] = MIN_TIMES_BOUGHT
    result['first_party_demand_signal'] = first_party_signal
    result['greek_market_demand_signal'] = greek_market_signal
    result['independent_demand_signal_count'] = signal_count
    result['high_demand_gate'] = high_demand
    result['hard_fail_reasons'] = failures
    result['research_survivor'] = not failures
    return result


audit.percentile_map = strict_percentile_map
audit.audit_candidate = strict_audit_candidate

if __name__ == '__main__':
    audit.main()
