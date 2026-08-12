import os, json, math, heapq, collections, datetime, re, unicodedata
from pathlib import Path
from stream_feed import iter_records, normalize

MIN_PRICE = float(os.getenv('BTS_MIN_PRICE_EUR', '50'))
MIN_VALIDITY_DAYS = int(os.getenv('BTS_MIN_VALIDITY_DAYS', '20'))
MIN_RAW_DISCOUNT = float(os.getenv('BTS_MIN_RAW_DISCOUNT_PCT', '12'))
GLOBAL_POOL = int(os.getenv('BTS_GLOBAL_POOL', '14000'))
PER_CLUSTER = int(os.getenv('BTS_PER_CLUSTER_POOL', '2500'))
MAX_OUTPUT = int(os.getenv('BTS_MAX_PREFILTER', '10000'))

MAJOR_MERCHANT_PATTERNS = (
    'jumbo', 'public', 'plaisio', 'πλαισιο', 'kotsovolos', 'κωτσοβολος',
    'e-shop.gr', 'eshop.gr', 'skroutz', 'bestprice', 'ikea', 'jysk'
)

# Broad first-pass discovery only. The semantic stage performs the actual pain matching.
PAIN_CLUSTERS = {
    'grow_with_child_ergonomics': {
        'strong': ('ergonomic', 'ergonomic chair', 'adjustable seat depth', 'adjustable back', 'footrest', 'kids chair', 'child chair', 'study chair', 'εργονομ', 'παιδικη καρεκλα', 'παιδική καρέκλα', 'υποποδιο', 'υποπόδιο', 'ρυθμιζομενο βαθος', 'ρυθμιζόμενο βάθος'),
        'weak': ('chair', 'seat', 'desk chair', 'back support', 'lumbar', 'καρεκλα', 'κάθισμα', 'γραφειου'),
    },
    'compact_space_study': {
        'strong': ('wall mounted desk', 'wall desk', 'folding desk', 'foldable desk', 'floating desk', 'compact desk', 'space saving desk', 'secretary desk', 'πτυσσομενο γραφειο', 'πτυσσόμενο γραφείο', 'γραφειο τοιχου', 'γραφείο τοίχου', 'αναδιπλουμενο γραφειο'),
        'weak': ('desk', 'table', 'shelf desk', 'small space', 'storage desk', 'γραφειο', 'γραφείο', 'ραφι', 'ράφι'),
    },
    'premium_safe_audio': {
        'strong': ('volume limit', '85db', '86db', 'safe listening', 'kids anc', 'child anc', 'noise cancelling kids', 'active noise cancellation', 'hearing protection', 'περιορισμο εντασης', 'περιορισμό έντασης', 'παιδικα ακουστικα', 'παιδικά ακουστικά'),
        'weak': ('headphones', 'headset', 'bluetooth headphones', 'microphone', 'anc', 'ακουστικα', 'ακουστικά'),
    },
    'teen_carry_ergonomics': {
        'strong': ('ergonomic backpack', 'laptop school backpack', 'orthopedic backpack', 'padded back', 'chest strap', 'load distribution', 'water resistant backpack', 'εργονομικη τσαντα', 'εργονομική τσάντα', 'σακιδιο laptop', 'σακίδιο laptop'),
        'weak': ('backpack', 'rucksack', 'school bag', 'laptop bag', 'σακιδιο', 'σακίδιο', 'τσάντα πλάτης'),
    },
    'focus_and_organization': {
        'strong': ('acoustic panel', 'desk privacy', 'study carrel', 'noise reduction panel', 'modular organizer', 'vertical organizer', 'under desk storage', 'sensory', 'focus booth', 'ηχοαπορροφη', 'οργανωση γραφειου', 'οργάνωση γραφείου'),
        'weak': ('organizer', 'storage', 'shelf', 'drawer', 'desk accessory', 'οργανω', 'αποθηκευση', 'αποθήκευση'),
    },
    'stem_creator_tools': {
        'strong': ('microscope', 'telescope', '3d pen', 'electronics kit', 'robotics kit', 'coding kit', 'drawing tablet', 'pen display', 'document camera', 'stem kit', 'μικροσκοπ', 'ρομποτικ', 'γραφιδα', 'γραφίδα'),
        'weak': ('science', 'maker', 'creative', 'tablet', 'camera', 'kit', 'εργαστηρ', 'δημιουργ'),
    },
}

NEGATIVE_TERMS = (
    'replacement part', 'spare part', 'refill only', 'case only', 'cover only', 'sticker',
    'travel', 'luggage', 'suitcase', 'tourism', 'βαλιτ', 'αποσκευ', 'ταξιδ'
)


def fold(v):
    s = str(v or '').lower()
    return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))


def clamp(v, lo=0, hi=100):
    return max(lo, min(hi, float(v)))


def text_of(p):
    return fold(' '.join(str(p.get(k) or '') for k in (
        'product_name', 'model_name', 'description', 'brand_name', 'category_raw', 'merchant_name'
    )))


def major_merchant(p):
    m = fold(p.get('merchant_name') or p.get('program_name'))
    return any(fold(x) in m for x in MAJOR_MERCHANT_PATTERNS)


def cluster_relevance(text, spec):
    strong = sum(1 for x in spec['strong'] if fold(x) in text)
    weak = sum(1 for x in spec['weak'] if fold(x) in text)
    if not strong and not weak:
        return 0.0
    return clamp(28 + strong * 24 + weak * 9)


def demand_proxy(p):
    # First-party feed signal only; semantic/web demand evidence is added later.
    times = max(0.0, float(p.get('times_bought') or 0))
    return clamp(22 * math.log1p(times))


def raw_deal_proxy(p):
    d = max(0.0, float(p.get('discount_pct') or 0))
    return clamp(d * 2.15)


def data_quality_proxy(p):
    score = 15
    score += 18 if p.get('brand_name') else 0
    score += 12 if p.get('model_name') else 0
    score += 20 if len(str(p.get('description') or '')) >= 160 else 8 if p.get('description') else 0
    score += 15 if p.get('image_url') else 0
    score += 8 if p.get('extra_images') else 0
    score += 12 if p.get('category_raw') else 0
    return clamp(score)


def push(heap, score, seq, row, limit):
    item = (score, seq, row)
    if len(heap) < limit:
        heapq.heappush(heap, item)
    elif score > heap[0][0]:
        heapq.heapreplace(heap, item)


def main(path):
    global_heap = []
    cluster_heaps = collections.defaultdict(list)
    cluster_stats = collections.defaultdict(lambda: {
        'eligible': 0, 'times_bought': 0.0, 'merchants': collections.Counter(),
        'brands': collections.Counter(), 'categories': collections.Counter()
    })
    merchant_stats = collections.defaultdict(lambda: {'eligible': 0, 'times_bought': 0.0, 'clusters': collections.Counter()})
    reasons = collections.Counter()
    seen = broad = 0
    seq = 0

    for raw in iter_records(path):
        seen += 1
        seq += 1
        p = normalize(raw)

        price = float(p.get('price') or 0)
        days = p.get('validity_days_remaining')
        if price <= MIN_PRICE:
            reasons['price_not_over_50'] += 1
            continue
        if days is None or days <= MIN_VALIDITY_DAYS:
            reasons['insufficient_validity'] += 1
            continue
        if p.get('travel_related'):
            reasons['travel'] += 1
            continue
        if p.get('in_stock') is False:
            reasons['out_of_stock'] += 1
            continue
        if not p.get('tracking_url') or not (p.get('image_url') or p.get('thumb_url')):
            reasons['missing_tracking_or_image'] += 1
            continue

        text = text_of(p)
        if any(fold(x) in text for x in NEGATIVE_TERMS):
            reasons['negative_scope_term'] += 1
            continue

        matches = []
        for cluster, spec in PAIN_CLUSTERS.items():
            rel = cluster_relevance(text, spec)
            if rel >= 28:
                matches.append((cluster, rel))
        if not matches:
            reasons['not_bts_solution_candidate'] += 1
            continue

        discount = max(0.0, float(p.get('discount_pct') or 0))
        demand = demand_proxy(p)
        # Keep strong first-party demand even with weak/no crossed-out discount; true-deal audit happens later.
        if discount < MIN_RAW_DISCOUNT and demand < 58:
            reasons['weak_initial_deal_and_demand'] += 1
            continue

        broad += 1
        q = {k: p.get(k) for k in (
            'external_product_id','product_name','model_name','description','brand_name','program_name',
            'merchant_name','category_raw','price','full_price','discount_pct','currency','in_stock','availability',
            'valid_from','valid_to','validity_days_remaining','times_bought','tracking_url','image_url','thumb_url',
            'extra_images','colour','size'
        )}
        q['major_merchant_source'] = major_merchant(p)
        q['demand_proxy'] = round(demand, 2)
        q['raw_deal_proxy'] = round(raw_deal_proxy(p), 2)
        q['data_quality_proxy'] = round(data_quality_proxy(p), 2)
        q['pain_cluster_matches'] = [{'cluster': c, 'lexical_relevance': round(r, 2)} for c, r in sorted(matches, key=lambda x: x[1], reverse=True)]
        best_rel = max(r for _, r in matches)
        q['_prefilter_score'] = round(clamp(demand * .42 + q['raw_deal_proxy'] * .23 + best_rel * .23 + q['data_quality_proxy'] * .12), 3)

        m = p.get('merchant_name') or p.get('program_name') or 'Unknown'
        for c, _ in matches:
            st = cluster_stats[c]
            st['eligible'] += 1
            st['times_bought'] += float(p.get('times_bought') or 0)
            st['merchants'][m] += 1
            st['categories'][p.get('category_raw') or 'Uncategorized'] += 1
            if p.get('brand_name'):
                st['brands'][p['brand_name']] += 1
            merchant_stats[m]['clusters'][c] += 1
            push(cluster_heaps[c], q['_prefilter_score'], seq, q, PER_CLUSTER)
        merchant_stats[m]['eligible'] += 1
        merchant_stats[m]['times_bought'] += float(p.get('times_bought') or 0)
        push(global_heap, q['_prefilter_score'], seq, q, GLOBAL_POOL)

        if seen % 250000 == 0:
            print(json.dumps({'seen': seen, 'bts_candidates': broad, 'global_pool': len(global_heap)}), flush=True)

    union = {}
    for _, _, p in global_heap:
        union[p['external_product_id']] = p
    for h in cluster_heaps.values():
        for _, _, p in h:
            union[p['external_product_id']] = p

    # Feed-side saturation is only a weak prior; Greek retail competition is audited later.
    cluster_out = {}
    for c, st in cluster_stats.items():
        merchant_count = len(st['merchants'])
        brand_count = len(st['brands'])
        offers = st['eligible']
        saturation = clamp(16 * math.log1p(merchant_count) + 7 * math.log1p(max(1, offers / 20)) + 5 * math.log1p(brand_count))
        cluster_out[c] = {
            'eligible': offers,
            'total_times_bought': round(st['times_bought'], 2),
            'merchant_count': merchant_count,
            'brand_count': brand_count,
            'feed_saturation_prior': round(saturation, 2),
            'top_merchants': st['merchants'].most_common(15),
            'top_categories': st['categories'].most_common(15),
        }

    rows = list(union.values())
    for p in rows:
        cs = [cluster_out[x['cluster']]['feed_saturation_prior'] for x in p['pain_cluster_matches'] if x['cluster'] in cluster_out]
        p['feed_competition_prior'] = round(min(cs) if cs else 50, 2)
        p['_rank'] = round(clamp(p['_prefilter_score'] * .90 + (100 - p['feed_competition_prior']) * .10), 3)
    rows.sort(key=lambda x: x['_rank'], reverse=True)
    rows = rows[:MAX_OUTPUT]

    with open('bts-pre-candidates.jsonl', 'w', encoding='utf-8') as f:
        for p in rows:
            q = {k: v for k, v in p.items() if not k.startswith('_')}
            q['bts_prefilter_score'] = p['_rank']
            f.write(json.dumps(q, ensure_ascii=False, default=str) + '\n')

    merchant_out = {}
    for m, st in merchant_stats.items():
        merchant_out[m] = {
            'eligible_bts_candidates': st['eligible'],
            'total_times_bought': round(st['times_bought'], 2),
            'top_clusters': st['clusters'].most_common(8),
        }
    Path('bts-cluster-stats.json').write_text(json.dumps(cluster_out, ensure_ascii=False, indent=2), encoding='utf-8')
    Path('bts-merchant-stats.json').write_text(json.dumps(merchant_out, ensure_ascii=False, indent=2), encoding='utf-8')
    profile = {
        'generated_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'records_seen': seen,
        'broad_bts_candidates': broad,
        'prefilter_output': len(rows),
        'min_price_eur_strictly_greater_than': MIN_PRICE,
        'min_validity_days': MIN_VALIDITY_DAYS,
        'min_raw_discount_pct_unless_strong_demand': MIN_RAW_DISCOUNT,
        'excluded_reasons': reasons.most_common(),
        'method': 'BTS pain-seeded full-stream prefilter; demand/discount are discovery proxies; semantic + Greek market audit required before promotion'
    }
    Path('bts-feed-profile.json').write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(profile, ensure_ascii=False))


if __name__ == '__main__':
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else 'linkwise-products.json')
