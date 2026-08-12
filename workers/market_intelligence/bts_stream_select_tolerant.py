import json, sys
from pathlib import Path
import ijson
import bts_stream_select as selector
from stream_feed import iter_records as strict_iter_records

INTEGRITY = {
    'feed_truncated': False,
    'parse_error': None,
    'integrity_policy': 'salvage_complete_records_before_premature_eof',
}


def tolerant_iter_records(path):
    """Yield every complete record and stop cleanly if the stored giant JSON ends mid-record.

    This does not pretend the feed is complete: downstream profile is explicitly marked truncated.
    """
    it = strict_iter_records(path)
    while True:
        try:
            yield next(it)
        except StopIteration:
            return
        except ijson.common.IncompleteJSONError as exc:
            INTEGRITY['feed_truncated'] = True
            INTEGRITY['parse_error'] = str(exc)[:500]
            print(json.dumps({'warning': 'truncated_feed_recovered', **INTEGRITY}, ensure_ascii=False), flush=True)
            return


def main(path):
    selector.iter_records = tolerant_iter_records
    selector.main(path)
    profile_path = Path('bts-feed-profile.json')
    profile = json.loads(profile_path.read_text(encoding='utf-8'))
    profile['feed_integrity'] = INTEGRITY
    profile['coverage_warning'] = (
        'Stored Linkwise JSON ended prematurely; all complete records before EOF were analyzed. '
        'Results are valid for recovered records but are not claimed as complete coverage of the Linkwise universe.'
        if INTEGRITY['feed_truncated'] else
        'JSON parsed to normal end-of-document.'
    )
    profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'bts_feed_profile_final': profile}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'linkwise-products.json')
