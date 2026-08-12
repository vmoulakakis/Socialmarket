import json, re, sys, math, urllib.parse, collections
from pathlib import Path
import ijson
from stream_feed import iter_records, fold_text

MIN_PRICE = 50.0
MIN_TIMES = 3
MAX_OUTPUT = 3000

CLUSTERS = {
    'grow_with_child_ergonomics': [
        r'παιδικ\w*\s+καρεκλ', r'καρεκλ\w*\s+γραφει', r'εργονομ\w*\s+καρεκλ',
        r'kids?\s+(?:desk\s+)?chair', r'child\w*\s+(?:desk\s+)?chair', r'ergonomic\s+chair', r'study\s+chair',
    ],
    'compact_space_study': [
        r'πτυσσ\w*\s+γραφει', r'αναδιπλ\w*\s+γραφει', r'γραφει\w*\s+τοιχ', r'παιδικ\w*\s+γραφει',
        r'wall[- ]mounted\s+desk', r'fold\w*\s+desk', r'floating\s+desk', r'kids?\s+desk', r'child\w*\s+desk', r'study\s+desk',
    ],
    'premium_safe_audio': [
        r'παιδικ\w*\s+ακουστικ', r'kids?\s+headphones?', r'child\w*\s+headphones?', r'volume\s+limit', r'\b85\s*db\b',
        r'noise\s+cancell\w*', r'active\s+noise\s+cancell\w*', r'\banc\b',
    ],
    'teen_carry_ergonomics': [
        r'εργονομ\w*\s+(?:σχολικ\w*\s+)?(?:τσαντ|σακιδ)', r'σχολικ\w*\s+(?:τσαντ|σακιδ)', r'σακιδ\w*\s+laptop',
        r'ergonomic\s+backpack', r'school\s+(?:bag|backpack)', r'laptop\s+backpack', r'chest\s+strap', r'padded\s+back',
    ],
    'focus_and_organization': [
        r'οργανω\w*\s+γραφει', r'αποθηκευ\w*\s+γραφει', r'desk\s+organizer', r'desk\s+storage', r'under[- ]desk\s+storage',
        r'acoustic\s+panel', r'privacy\s+panel', r'study\s+carrel',
    ],
    'stem_creator_tools': [
        r'μικροσκοπ', r'τηλεσκοπ', r'ρομποτικ', r'γραφιδ\w*\s+tablet', r'microscope', r'telescope', r'robotics?\s+kit',
        r'coding\s+kit', r'3d\s+pen', r'drawing\s+tablet', r'pen\s+display', r'document\s+camera', r'stem\s+kit',
    ],
}
COMPILED = {k: [re.compile(p, re.I) for p in ps] for k, ps in CLUSTERS.items()}
TRAVEL = re.compile(r'\b(?:travel|luggage|suitcase|touris\w*|βαλιτσ\w*|αποσκευ\w*|ταξιδ\w*)\b', re.I)


def as_float(v):
    if v in (None, ''): return None
    try: return float(str(v).replace('€','').replace('%','').replace(' ','').replace(',','.'))
    except: return None


def as_int(v):
    x = as_float(v)
    return int(x) if x is not None else None


def text(raw):
    vals=[]
    for k in ('product_name','model_name','description','category','brand_name'):
        v=raw.get(k)
        if v: vals.append(str(v))
    return fold_text(' '.join(vals))


def target_domain(tracking):
    try:
        u=urllib.parse.urlparse(str(tracking or ''))
        q=urllib.parse.parse_qs(u.query)
        target=(q.get('lnkurl') or q.get('url') or [None])[0]
        if target:
            return urllib.parse.urlparse(target).netloc.lower().removeprefix('www.')
    except: pass
    return None


def main(path):
    seen=0; price_pass=0; demand_pass=0; bts_pass=0
    rows=[]; by_cluster=collections.Counter(); by_domain=collections.Counter()
    truncated=False; parse_error=None
    try:
        for raw in iter_records(path):
            seen += 1
            price=as_float(raw.get('price'))
            if price is None or price <= MIN_PRICE: continue
            price_pass += 1
            times=as_int(raw.get('times_bought')) or 0
            if times < MIN_TIMES: continue
            demand_pass += 1
            t=text(raw)
            if TRAVEL.search(t): continue
            clusters=[]
            for c, pats in COMPILED.items():
                hits=[p.pattern for p in pats if p.search(t)]
                if hits: clusters.append({'cluster':c,'matched_patterns':hits[:5]})
            if not clusters: continue
            tracking=raw.get('tracking_url'); image=raw.get('image_url') or raw.get('thumb_url')
            if not tracking or not image: continue
            bts_pass += 1
            full=as_float(raw.get('full_price'))
            true_disc=None
            if full and full>0 and price<=full:
                true_disc=round(max(0.0,(1-price/full)*100),2)
            domain=target_domain(tracking)
            row={
                'product_id':str(raw.get('product_id') or raw.get('id') or ''),
                'product_name':raw.get('product_name'), 'model_name':raw.get('model_name'),
                'brand_name':raw.get('brand_name'), 'category':raw.get('category'),
                'program_name':raw.get('program_name'), 'target_domain':domain,
                'price':price, 'full_price':full, 'true_discount_pct':true_disc,
                'raw_discount_field':raw.get('discount'), 'times_bought':times,
                'availability':raw.get('availability'), 'in_stock':raw.get('in_stock'),
                'valid_from':raw.get('valid_from'), 'valid_to':raw.get('valid_to'),
                'tracking_url':tracking, 'image_url':image,
                'clusters':clusters,
            }
            rows.append(row)
            for c in clusters: by_cluster[c['cluster']]+=1
            if domain: by_domain[domain]+=1
            if len(rows)%50==0:
                print(json.dumps({'seen':seen,'demand_bts_candidates':len(rows)}),flush=True)
    except ijson.common.IncompleteJSONError as exc:
        truncated=True; parse_error=str(exc)[:500]

    # Demand dominates; deal is only a secondary tie-breaker. No candidate is promoted here.
    rows.sort(key=lambda r:(r['times_bought'], r.get('true_discount_pct') or 0, r['price']), reverse=True)
    rows=rows[:MAX_OUTPUT]
    Path('bts-demand-first-candidates.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    summary={
        'records_seen_before_eof':seen,'price_over_50':price_pass,'times_bought_gte_3':demand_pass,
        'demand_first_bts_candidates':bts_pass,'output':len(rows),'feed_truncated':truncated,'parse_error':parse_error,
        'cluster_counts':by_cluster.most_common(),'top_target_domains':by_domain.most_common(30),
        'discount_policy':'true_discount_pct is always recomputed from price/full_price; raw discount is retained only for audit',
        'selection_policy':'price > 50 AND times_bought >= 3 AND boundary-aware BTS relevance AND tracking/image. Current stock, competition, physical availability, quality and deal must be verified live before promotion.'
    }
    Path('bts-demand-first-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False),flush=True)

if __name__=='__main__': main(sys.argv[1] if len(sys.argv)>1 else 'linkwise-products.json')
