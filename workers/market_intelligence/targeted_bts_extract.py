import json
import sys
from pathlib import Path
import ijson
from stream_feed import iter_records, normalize, fold_text

TARGETS = [
    'vipack comfortline 201', 'comfortline 201', '5420070224147',
    'vidaxl 243054', '243054', '8718475977339',
    'acc-8483', 'acc-8493', 'acc-8491', 'acc-8486', 'acc-8516', 'acc-8479',
    'acc-8492', 'acc-8513', 'acc-8502', 'acc-8501', 'acc-8490', 'acc-8485',
    'acc-8507', 'acc-8497', 'acc-8498', 'acc-8484', 'acc-8511', 'acc-8512',
    'bf-2101', 'bf-2120', 'bf-2130', 'eo-201',
]

FIELDS = (
    'product_id','model_name','product_name','description','category','brand_name','program_name',
    'price','full_price','discount','times_bought','in_stock','availability','valid_from','valid_to',
    'tracking_url','image_url','thumb_url','custom'
)


def raw_text(raw):
    parts = []
    for key in ('product_id','model_name','product_name','description','category','brand_name','program_name','custom'):
        value = raw.get(key)
        if value is not None:
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False, default=str)
            parts.append(str(value))
    return fold_text(' '.join(parts))


def main(path):
    targets = [(t, fold_text(t)) for t in TARGETS]
    seen = 0
    matches = []
    feed_truncated = False
    parse_error = None
    try:
        for raw in iter_records(path):
            seen += 1
            hay = raw_text(raw)
            hit = sorted({label for label, needle in targets if needle in hay})
            if not hit:
                continue
            try:
                norm = normalize(raw)
            except Exception as exc:
                norm = {'normalization_error': f'{type(exc).__name__}: {str(exc)[:300]}'}
            matches.append({
                'matched_targets': hit,
                'raw': {k: raw.get(k) for k in FIELDS if raw.get(k) is not None},
                'normalized': norm,
            })
            print(json.dumps({'seen': seen, 'match_count': len(matches), 'targets': hit, 'product': raw.get('product_name')}, ensure_ascii=False), flush=True)
    except ijson.common.IncompleteJSONError as exc:
        feed_truncated = True
        parse_error = str(exc)[:500]

    Path('targeted-bts-linkwise-matches.json').write_text(
        json.dumps(matches, ensure_ascii=False, indent=2, default=str), encoding='utf-8'
    )
    summary = {
        'records_seen_before_eof': seen,
        'matches': len(matches),
        'feed_truncated': feed_truncated,
        'parse_error': parse_error,
        'targets': TARGETS,
        'policy': 'Exact/near-exact targeted evidence extraction only. No validity, demand, competition or quality gate is applied here.'
    }
    Path('targeted-bts-linkwise-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'linkwise-products.json')
