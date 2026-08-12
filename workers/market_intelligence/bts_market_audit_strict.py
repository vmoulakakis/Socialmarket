import os, re, math
import bts_market_audit as audit

MIN_TIMES_BOUGHT = float(os.getenv('BTS_MIN_TIMES_BOUGHT', '3'))
MAX_GREEK_SELLERS = int(os.getenv('BTS_MAX_GREEK_SELLERS', '4'))
MIN_OFFLINE_SCARCITY = float(os.getenv('BTS_MIN_OFFLINE_SCARCITY', '70'))
MIN_PRODUCT_REVIEW_SIGNAL = int(os.getenv('BTS_MIN_PRODUCT_REVIEW_SIGNAL', '10'))

# Generic return-policy text is not negative quality evidence. Keep only defect/failure language.
audit.NEG_QUALITY = (
    'έσπασε', 'εσπασε', 'χάλασε', 'χαλασε', 'ελαττωματικό', 'ελαττωματικο',
    'κακή ποιότητα', 'κακη ποιοτητα', 'δεν λειτουργεί', 'δεν λειτουργει',
    'defective', 'broke', 'broken', 'poor quality', 'stopped working', 'failed after'
)


def strict_review_count(text):
    """Prefer labelled product-review sections over seller/reputation counts."""
    t = audit.fold(text)
    preferred = []
    for pat in (
        r'αξιολογησεις\s*\(?\s*(\d{1,6})\s*\)?',
        r'κριτικες\s*\(?\s*(\d{1,6})\s*\)?',
        r'product\s+reviews?\s*\(?\s*(\d{1,6})\s*\)?',
        r'reviews?\s*\(?\s*(\d{1,6})\s*\)?',
        r'avis\s*\(?\s*(\d{1,6})\s*\)?',
    ):
        preferred.extend(int(x) for x in re.findall(pat, t) if int(x) < 500000)
    if preferred:
        return max(preferred)

    fallback = []
    for pat in (
        r'(\d{1,5})\s+αξιολογησεις', r'(\d{1,5})\s+κριτικες',
        r'(\d{1,5})\s+reviews?', r'(\d{1,5})\s+avis'
    ):
        fallback.extend(int(x) for x in re.findall(pat, t) if int(x) < 5000)
    return min(max(fallback), 100) if fallback else 0


def strict_percentile_map(rows, cluster):
    """Optional first-party signal. Zero/missing purchases never become high percentile through ties."""
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


def verified_discount_from_prices(p):
    """Never assume the feed discount field is a percentage; some merchants provide an absolute EUR delta."""
    try:
        price = float(p.get('price') or 0)
        full = float(p.get('full_price') or 0)
    except Exception:
        return None
    if price > 0 and full > price:
        return max(0.0, min(100.0, (full - price) / full * 100.0))
    return None


def external_product_demand(p):
    """Find product-level review evidence outside the stale Linkwise purchase counter.

    Results are still evidence candidates, not truth: pages must strongly match the exact product/model.
    """
    key = audit.product_key(p)
    if not key:
        return {'max_review_count': 0, 'review_domains': [], 'evidence': [], 'score': 0.0}

    results = []
    seen_urls = set()
    for query in (f'"{key}" reviews avis', f'"{key}" αξιολογήσεις κριτικές'):
        for item in audit.search(query, 8):
            url = item.get('url') or ''
            if url and url not in seen_urls:
                seen_urls.add(url)
                results.append(item)
        if len(results) >= 10:
            break

    evidence = []
    domains = set()
    max_reviews = 0
    for item in results[:10]:
        page = audit.fetch_page(item.get('url') or '')
        if not page:
            continue
        strength = audit.match_strength(p, page['text'], page['url'])
        if strength < 72:
            continue
        reviews = strict_review_count(page['text'])
        if reviews <= 0:
            continue
        max_reviews = max(max_reviews, reviews)
        domains.add(page['domain'])
        evidence.append({
            'url': page['url'],
            'domain': page['domain'],
            'fetched_at': page['fetched_at'],
            'content_hash': page['content_hash'],
            'match_strength': strength,
            'review_count_signal': reviews,
        })
        if len(evidence) >= 5:
            break

    score = audit.clamp(22 * math.log1p(max_reviews) + min(20, len(domains) * 8))
    return {
        'max_review_count': max_reviews,
        'review_domains': sorted(domains),
        'evidence': evidence,
        'score': round(score, 2),
    }


_original_audit_candidate = audit.audit_candidate


def strict_audit_candidate(p, demand_pct, cluster_market):
    # Correct deal semantics before the base audit sees the discount.
    candidate = dict(p)
    raw_feed_discount = candidate.get('discount_pct')
    verified_discount = verified_discount_from_prices(candidate)
    if verified_discount is not None:
        candidate['discount_pct'] = verified_discount

    result = _original_audit_candidate(candidate, demand_pct, cluster_market)
    purchases = float(candidate.get('times_bought') or 0)
    cluster_engagement = float(cluster_market.get('engagement_score') or 0)
    cluster_review_pages = int(cluster_market.get('independent_review_pages') or 0)
    product_demand = external_product_demand(candidate)

    # Linkwise times_bought is optional supporting evidence only. The July 2026 snapshot contains
    # almost no usable BTS purchase counters, so absence must not be interpreted as absence of demand.
    first_party_signal = purchases >= MIN_TIMES_BOUGHT and demand_pct >= 0.65
    greek_pain_signal = cluster_engagement >= 45 and cluster_review_pages >= 1
    product_review_signal = (
        int(product_demand.get('max_review_count') or 0) >= MIN_PRODUCT_REVIEW_SIGNAL
        and len(product_demand.get('review_domains') or []) >= 1
    )
    signal_count = int(first_party_signal) + int(greek_pain_signal) + int(product_review_signal)

    external_score = float(product_demand.get('score') or 0)
    if first_party_signal:
        demand_score = audit.clamp(cluster_engagement * .42 + external_score * .43 + demand_pct * 100 * .15)
    else:
        demand_score = audit.clamp(cluster_engagement * .50 + external_score * .50)
    high_demand = signal_count >= 2 and demand_score >= 60

    failures = [x for x in result.get('hard_fail_reasons', []) if x != 'high_demand_not_verified']
    if not high_demand:
        failures.append('high_demand_not_verified')

    # Normal winners must be hard to find offline and outside major retail.
    # Any major-retailer exception is reviewed manually later and is not auto-selected here.
    if result.get('physical_pickup_evidence'):
        failures.append('physical_store_pickup_detected')
    if result.get('major_retail_domains_exact'):
        failures.append('major_retail_presence_requires_manual_exception')
    seller_breadth = int(result.get('greek_seller_breadth_proxy') or 0)
    if seller_breadth > MAX_GREEK_SELLERS:
        failures.append('too_many_greek_sellers')
    if float(result.get('offline_scarcity_proxy') or 0) < MIN_OFFLINE_SCARCITY:
        failures.append('offline_scarcity_too_low')

    failures = list(dict.fromkeys(failures))

    result['raw_feed_discount_field_interpreted_by_normalizer'] = raw_feed_discount
    result['verified_discount_pct_from_price_full_price'] = round(verified_discount, 2) if verified_discount is not None else None
    result['times_bought_absolute'] = purchases
    result['times_bought_is_optional_supporting_signal'] = True
    result['first_party_demand_signal'] = first_party_signal
    result['greek_pain_demand_signal'] = greek_pain_signal
    result['external_product_review_signal'] = product_review_signal
    result['external_product_demand_evidence'] = product_demand
    result['independent_demand_signal_count'] = signal_count
    result['demand_score'] = round(demand_score, 2)
    result['high_demand_gate'] = high_demand
    result['max_greek_sellers_gate'] = MAX_GREEK_SELLERS
    result['minimum_offline_scarcity_gate'] = MIN_OFFLINE_SCARCITY
    result['hard_fail_reasons'] = failures
    result['research_survivor'] = not failures
    return result


audit.review_count = strict_review_count
audit.percentile_map = strict_percentile_map
audit.audit_candidate = strict_audit_candidate

if __name__ == '__main__':
    audit.main()
