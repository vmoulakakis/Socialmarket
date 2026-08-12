import os, json, math, re, time, hashlib, statistics, datetime, unicodedata
from pathlib import Path
from urllib.parse import urlparse
from collections import defaultdict
import requests
from bs4 import BeautifulSoup
from rapidfuzz.fuzz import token_set_ratio

SEARXNG = os.getenv('SEARXNG_BASE_URL', 'http://127.0.0.1:8080').rstrip('/')
AUDIT_LIMIT = int(os.getenv('BTS_AUDIT_LIMIT', '220'))
FINAL_RESEARCH_LIMIT = int(os.getenv('BTS_RESEARCH_SHORTLIST', '60'))
TIMEOUT = 15
UA = {'User-Agent': 'Mozilla/5.0 SocialMarket-BTS-Research/1.0'}

MAJOR_DOMAINS = ('jumbo.', 'public.gr', 'plaisio.gr', 'kotsovolos.gr', 'e-shop.gr', 'eshop.gr', 'ikea.', 'jysk.')
MARKETPLACE_DOMAINS = ('skroutz.gr', 'bestprice.gr')
PICKUP_TERMS = ('παραλαβή από κατάστημα', 'παραλαβη απο καταστημα', 'store pickup', 'click & collect', 'click and collect')
NEG_QUALITY = ('έσπασε', 'εσπασε', 'χαλασε', 'χάλασε', 'κακη ποιοτητα', 'κακή ποιότητα', 'defect', 'broke', 'poor quality', 'επιστροφη', 'επιστροφή')

CLUSTER_QUERIES = {
    'grow_with_child_ergonomics': 'παιδική εργονομική καρέκλα ρυθμιζόμενο βάθος καθίσματος υποπόδιο αξιολογήσεις',
    'compact_space_study': 'πτυσσόμενο γραφείο τοίχου μικρός χώρος αξιολογήσεις Ελλάδα',
    'premium_safe_audio': 'παιδικά ακουστικά 85dB ANC noise cancelling αξιολογήσεις Ελλάδα',
    'teen_carry_ergonomics': 'εργονομικό σακίδιο laptop έφηβος πλάτη αξιολογήσεις Ελλάδα',
    'focus_and_organization': 'οργάνωση μικρό γραφείο μαθητή αποθήκευση ακουστικό panel αξιολογήσεις Ελλάδα',
    'stem_creator_tools': 'STEM robotics microscope drawing tablet μαθητές αξιολογήσεις Ελλάδα',
}


def fold(v):
    s = str(v or '').lower()
    return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))


def norm(v):
    return re.sub(r'[^a-z0-9α-ω]+', ' ', fold(v)).strip()


def clamp(v, lo=0, hi=100):
    return max(lo, min(hi, float(v)))


def host(url):
    try:
        return urlparse(url).netloc.lower().removeprefix('www.')
    except Exception:
        return ''


def search(query, limit=10):
    try:
        r = requests.get(f'{SEARXNG}/search', params={'q': query, 'format': 'json', 'language': 'el-GR', 'safesearch': 1}, headers=UA, timeout=20)
        r.raise_for_status()
        return (r.json().get('results') or [])[:limit]
    except Exception as exc:
        print(json.dumps({'warning': 'search_failed', 'query': query[:100], 'error': str(exc)[:180]}), flush=True)
        return []


def fetch_page(url):
    try:
        r = requests.get(url, headers=UA, timeout=TIMEOUT, allow_redirects=True)
        if not r.ok or 'text/html' not in (r.headers.get('content-type') or ''):
            return None
        text = BeautifulSoup(r.text[:2_500_000], 'html.parser').get_text(' ', strip=True)
        text = re.sub(r'\s+', ' ', text)[:180000]
        return {
            'url': r.url,
            'domain': host(r.url),
            'fetched_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'content_hash': hashlib.sha256(text.encode('utf-8', errors='ignore')).hexdigest(),
            'text': text,
        }
    except Exception:
        return None


def review_count(text):
    t = fold(text)
    vals = []
    for pat in (
        r'(\d{1,6})\s*(?:αξιολογησεις|κριτικες|reviews|review)',
        r'(?:αξιολογησεις|κριτικες|reviews)\s*\(?\s*(\d{1,6})',
    ):
        vals.extend(int(x) for x in re.findall(pat, t) if int(x) < 500000)
    return max(vals) if vals else 0


def marketplace_seller_count(text):
    t = fold(text)
    vals = []
    for pat in (r'σε\s+(\d{1,4})\s+καταστημ', r'(\d{1,4})\s+καταστημ'):
        vals.extend(int(x) for x in re.findall(pat, t) if int(x) < 1000)
    return max(vals) if vals else 0


def euro_prices(text):
    vals = []
    for a, b in re.findall(r'(?<!\d)(\d{1,5})(?:[\.,](\d{1,2}))?\s*€', text or ''):
        try:
            vals.append(float(a) + (float(b) / (100 if len(b) == 2 else 10) if b else 0))
        except Exception:
            pass
    return vals


def product_key(p):
    model = str(p.get('model_name') or '').strip()
    if len(model) >= 4:
        return model
    name = str(p.get('product_name') or '').strip()
    return ' '.join(name.split()[:10])


def match_strength(p, page_text, page_url=''):
    model = norm(p.get('model_name'))
    text = norm(page_text)
    if model and len(model) >= 4 and model in text:
        return 100
    name = norm(p.get('product_name'))
    if not name:
        return 0
    sample = norm(page_text[:5000])
    return token_set_ratio(name, sample)


def percentile_map(rows, cluster):
    vals = sorted(max(0.0, float(p.get('times_bought') or 0)) for p in rows if p.get('semantic_pain_cluster') == cluster)
    if not vals:
        return {}
    out = {}
    for p in rows:
        if p.get('semantic_pain_cluster') != cluster:
            continue
        v = max(0.0, float(p.get('times_bought') or 0))
        # deterministic empirical percentile
        lo, hi = 0, len(vals)
        while lo < hi:
            mid = (lo + hi) // 2
            if vals[mid] <= v:
                lo = mid + 1
            else:
                hi = mid
        out[p['external_product_id']] = lo / len(vals)
    return out


def build_cluster_market_evidence(cluster):
    q = CLUSTER_QUERIES.get(cluster, cluster + ' Ελλάδα')
    results = search(q, 12)
    evidence = []
    independent_review_pages = 0
    max_reviews = 0
    major_presence = set()
    for x in results:
        u = x.get('url') or ''
        page = fetch_page(u)
        if not page:
            continue
        rc = review_count(page['text'])
        max_reviews = max(max_reviews, rc)
        if rc >= 3:
            independent_review_pages += 1
        d = page['domain']
        if any(m in d for m in MAJOR_DOMAINS + MARKETPLACE_DOMAINS):
            major_presence.add(d)
        evidence.append({
            'url': page['url'], 'domain': d, 'fetched_at': page['fetched_at'],
            'content_hash': page['content_hash'], 'review_count_signal': rc,
        })
        if len(evidence) >= 8:
            break
    engagement = clamp(25 * math.log1p(max_reviews) + 10 * independent_review_pages)
    return {
        'query': q,
        'engagement_score': round(engagement, 2),
        'max_review_count_signal': max_reviews,
        'independent_review_pages': independent_review_pages,
        'major_market_domains_observed': sorted(major_presence),
        'evidence': evidence,
    }


def audit_candidate(p, demand_pct, cluster_market):
    key = product_key(p)
    q = f'"{key}" Ελλάδα τιμή' if key else f'"{p.get("product_name")}" Ελλάδα τιμή'
    results = search(q, 9)
    exact_pages = []
    domains = set()
    major = set()
    marketplace_sellers = 0
    pickup = False
    peer_prices = []
    negative_quality_hits = 0

    current_price = float(p.get('price') or 0)
    merchant_name = norm(p.get('merchant_name'))
    for x in results:
        page = fetch_page(x.get('url') or '')
        if not page:
            continue
        strength = match_strength(p, page['text'], page['url'])
        if strength < 72:
            continue
        d = page['domain']
        exact_pages.append({
            'url': page['url'], 'domain': d, 'fetched_at': page['fetched_at'],
            'content_hash': page['content_hash'], 'match_strength': strength,
            'review_count_signal': review_count(page['text']),
            'seller_count_signal': marketplace_seller_count(page['text']),
        })
        if not merchant_name or merchant_name not in norm(d):
            domains.add(d)
        if any(m in d for m in MAJOR_DOMAINS):
            major.add(d)
        if any(m in d for m in MARKETPLACE_DOMAINS):
            marketplace_sellers = max(marketplace_sellers, marketplace_seller_count(page['text']))
        low = fold(page['text'])
        pickup = pickup or any(fold(t) in low for t in PICKUP_TERMS)
        negative_quality_hits += sum(1 for t in NEG_QUALITY if fold(t) in low)
        for price in euro_prices(page['text'][:25000]):
            if current_price > 0 and current_price * .45 <= price <= current_price * 2.2:
                peer_prices.append(price)
        if len(exact_pages) >= 6:
            break

    # Count exact Greek supply conservatively: marketplace count dominates simple domain count.
    seller_breadth = max(max(0, len(domains) - 1), marketplace_sellers)
    competition = clamp(len(major) * 24 + min(55, seller_breadth * 6.5) + (10 if pickup else 0))
    offline_scarcity = clamp(100 - competition)

    raw_discount = max(0.0, float(p.get('discount_pct') or 0))
    peer_median = statistics.median(peer_prices) if peer_prices else None
    peer_adv = 0.0
    if peer_median and peer_median > 0:
        peer_adv = (peer_median - current_price) / peer_median
    raw_deal = clamp(raw_discount * 2.35)
    if peer_median:
        true_deal = clamp(raw_deal * .62 + clamp(50 + peer_adv * 180) * .38)
        deal_conf = .82
    else:
        true_deal = clamp(raw_deal * .74)
        deal_conf = .48

    cluster_engagement = float(cluster_market.get('engagement_score') or 0)
    demand_score = clamp(demand_pct * 72 + cluster_engagement * .28)
    independent_demand_signals = int(demand_pct >= .65) + int(cluster_engagement >= 45)
    high_demand = independent_demand_signals >= 2 and demand_score >= 60
    low_competition = competition <= 45

    # This is only an automated quality evidence proxy. Final shortlist still requires product-level audit.
    data_q = float(p.get('data_quality_proxy') or 0)
    review_signal = max([x['review_count_signal'] for x in exact_pages] or [0])
    quality_evidence = clamp(data_q * .72 + clamp(20 * math.log1p(review_signal)) * .28 - min(25, negative_quality_hits * 5))

    semantic = clamp((float(p.get('semantic_pain_similarity') or 0) - .30) / .50 * 100)
    merchant_component = 50  # filled by the final merchant audit; neutral here
    affiliate_component = 50
    hidden_score = clamp(
        quality_evidence * .25 + semantic * .20 + offline_scarcity * .20 + true_deal * .15 +
        demand_score * .10 + merchant_component * .07 + affiliate_component * .03
    )

    hard_fail = []
    if current_price <= 50:
        hard_fail.append('price_not_over_50')
    if not high_demand:
        hard_fail.append('high_demand_not_verified')
    if not low_competition:
        hard_fail.append('competition_too_high')
    if len(major) >= 2 or seller_breadth >= 8:
        hard_fail.append('widely_available_in_greece')
    if raw_discount < 20 and peer_adv < .10:
        hard_fail.append('deal_not_strong_enough')
    if quality_evidence < 62:
        hard_fail.append('quality_evidence_too_weak')

    return {
        **p,
        'demand_times_bought_percentile_within_pain': round(demand_pct, 4),
        'cluster_market_demand': cluster_market,
        'exact_product_market_evidence': exact_pages,
        'major_retail_domains_exact': sorted(major),
        'greek_seller_breadth_proxy': seller_breadth,
        'physical_pickup_evidence': pickup,
        'competition_score': round(competition, 2),
        'offline_scarcity_proxy': round(offline_scarcity, 2),
        'peer_price_median_signal': round(peer_median, 2) if peer_median else None,
        'peer_price_advantage': round(peer_adv, 4),
        'true_deal_score': round(true_deal, 2),
        'true_deal_confidence': deal_conf,
        'demand_score': round(demand_score, 2),
        'independent_demand_signal_count': independent_demand_signals,
        'high_demand_gate': high_demand,
        'low_competition_gate': low_competition,
        'quality_evidence_proxy': round(quality_evidence, 2),
        'negative_quality_hits': negative_quality_hits,
        'bts_hidden_product_score_premerchant': round(hidden_score, 2),
        'hard_fail_reasons': hard_fail,
        'research_survivor': not hard_fail,
    }


def main():
    rows = []
    with open('bts-semantic-candidates.jsonl', encoding='utf-8') as f:
        for line in f:
            rows.append(json.loads(line))
    rows.sort(key=lambda p: float(p.get('semantic_stage_score') or 0), reverse=True)

    percentiles = {}
    for cluster in CLUSTER_QUERIES:
        percentiles.update(percentile_map(rows, cluster))

    # Research category/pain demand once, then exact supply/deal for strongest first-party candidates.
    cluster_evidence = {c: build_cluster_market_evidence(c) for c in CLUSTER_QUERIES}
    Path('bts-cluster-market-evidence.json').write_text(json.dumps(cluster_evidence, ensure_ascii=False, indent=2), encoding='utf-8')

    eligible_for_audit = [
        p for p in rows
        if percentiles.get(p.get('external_product_id'), 0) >= .55
    ][:AUDIT_LIMIT]

    audited = []
    for i, p in enumerate(eligible_for_audit, 1):
        c = p.get('semantic_pain_cluster')
        audited.append(audit_candidate(p, percentiles.get(p.get('external_product_id'), 0), cluster_evidence.get(c, {})))
        if i % 20 == 0:
            print(json.dumps({'audited': i, 'limit': len(eligible_for_audit)}), flush=True)
        time.sleep(.08)

    with open('bts-market-audited.jsonl', 'w', encoding='utf-8') as f:
        for p in audited:
            f.write(json.dumps(p, ensure_ascii=False, default=str) + '\n')

    survivors = [p for p in audited if p.get('research_survivor')]
    survivors.sort(key=lambda p: p['bts_hidden_product_score_premerchant'], reverse=True)

    # Diversity: no major merchant by default; exceptions are left available but not preferred.
    final = []
    merchant_count = defaultdict(int)
    pain_count = defaultdict(int)
    major_count = 0
    for p in survivors:
        if len(final) >= FINAL_RESEARCH_LIMIT:
            break
        m = p.get('merchant_name') or 'Unknown'
        c = p.get('semantic_pain_cluster') or 'unknown'
        is_major = bool(p.get('major_merchant_source'))
        if merchant_count[m] >= 3 or pain_count[c] >= 14:
            continue
        if is_major and major_count >= max(1, math.floor(FINAL_RESEARCH_LIMIT * .10)):
            continue
        merchant_count[m] += 1
        pain_count[c] += 1
        major_count += int(is_major)
        final.append(p)

    Path('bts-research-shortlist.json').write_text(json.dumps(final, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    report = {
        'semantic_candidates': len(rows),
        'audited': len(audited),
        'research_survivors': len(survivors),
        'shortlist': len(final),
        'major_merchant_shortlist_count': major_count,
        'high_demand_definition': '>=2 independent signals: Linkwise times_bought percentile plus fetched Greek market engagement evidence',
        'low_competition_definition': 'SKU-level major-chain presence + seller breadth + marketplace seller signal + pickup evidence',
        'warning': 'offline_scarcity and quality are conservative proxies until final human/source audit; shortlist is research-ready, not auto-publish-ready'
    }
    Path('bts-market-audit-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
