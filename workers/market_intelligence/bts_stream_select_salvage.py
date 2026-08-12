import json
from pathlib import Path
import ijson
import bts_stream_select as selector
from stream_feed import iter_records as base_iter_records


def salvage_iter_records(path):
    """Yield every complete product object and tolerate only a terminal incomplete-JSON EOF.

    Any non-EOF parser or data error still fails the run. This makes the source defect explicit
    without discarding millions of complete records that precede the malformed tail.
    """
    try:
        yield from base_iter_records(path)
    except ijson.common.IncompleteJSONError as exc:
        warning = {
            'feed_integrity': 'incomplete_json_salvaged',
            'source_path': str(path),
            'error_type': type(exc).__name__,
            'error': str(exc)[:500],
            'policy': 'Only complete product objects emitted before terminal premature EOF are retained; downstream output is research-only and must not be described as a clean full-feed scan.'
        }
        Path('bts-feed-integrity-warning.json').write_text(
            json.dumps(warning, ensure_ascii=False, indent=2), encoding='utf-8'
        )
        print(json.dumps({'warning': warning}, ensure_ascii=False), flush=True)


def main(path):
    selector.iter_records = salvage_iter_records
    selector.main(path)
    profile_path = Path('bts-feed-profile.json')
    profile = json.loads(profile_path.read_text(encoding='utf-8'))
    warning_path = Path('bts-feed-integrity-warning.json')
    if warning_path.exists():
        warning = json.loads(warning_path.read_text(encoding='utf-8'))
        profile['feed_integrity'] = warning['feed_integrity']
        profile['scan_complete_clean_json'] = False
        profile['integrity_note'] = warning['policy']
    else:
        profile['feed_integrity'] = 'clean_json'
        profile['scan_complete_clean_json'] = True
    profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'final_profile': profile}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else 'linkwise-products.json')
