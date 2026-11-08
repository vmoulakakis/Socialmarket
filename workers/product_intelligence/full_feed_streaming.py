"""Single-pass EUR15 research ingestion with SQLite write-ahead checkpoints.

Reuses the existing fullfeed OIDC gateway and discovery ranking. No LLM calls,
publishing, bulk JSON load, stock/price/merchant quality admission filters.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import os
import re
import sqlite3
import time
import uuid
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlparse

import ijson
import requests

from all_feed_opportunity_discovery import amount, gateway, normalize_signals, score_product
from linkwise_commission15_discovery import parse_record

FLOOR = 15.0
BATCH = 20


class CountingReader:
    def __init__(self, raw):
        self.raw, self.bytes_read = raw, 0

    def read(self, size=-1):
        data = self.raw.read(size)
        self.bytes_read += len(data)
        return data


@contextmanager
def source(args):
    if args.feed_url:
        u = urlparse(args.feed_url)
        if (u.scheme != 'https' or u.hostname != 'affiliate.linkwi.se' or
                u.username or u.password or u.query or u.fragment or
                not u.path.startswith('/feeds/1.2/CD104/programs-') or
                not u.path.endswith('/feed.json')):
            raise ValueError('expected official CD104 HTTPS feed without credentials/query')
        with requests.get(args.feed_url, stream=True, allow_redirects=False,
                          timeout=(30, 180), headers={'Accept-Encoding': 'gzip, deflate',
                          'User-Agent': 'SocialMarket-Streaming-EUR15/3'}) as res:
            if res.status_code != 200:
                raise RuntimeError(f'feed_http_{res.status_code}')
            if 'json' not in res.headers.get('content-type', '').lower():
                raise ValueError('source_content_type_not_json')
            res.raw.decode_content = True
            etag = res.headers.get('etag')
            signature = etag if etag and not etag.startswith('W/') else None
            reader = CountingReader(res.raw)
            yield reader, {'source_uri_hash': hashlib.sha256(args.feed_url.encode()).hexdigest(),
                           'source_etag': etag, 'source_last_modified': res.headers.get('last-modified'),
                           'source_signature': signature, 'source_kind': 'http_stream'}
    else:
        path = Path(args.feed).resolve()
        stat = path.stat()
        with path.open('rb') as raw:
            yield CountingReader(raw), {
                'source_uri_hash': hashlib.sha256(str(path).encode()).hexdigest(),
                'source_signature': f'local:{stat.st_size}:{stat.st_mtime_ns}',
                'source_kind': 'local_stream'}


def array_records(reader):
    events = ijson.parse(reader)
    first = next(events, None)
    if first is None or first[:2] != ('', 'start_array'):
        raise ValueError('source_root_must_be_array')
    yield from ijson.items(itertools.chain([first], events), 'item')


class Journal:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.execute('pragma journal_mode=WAL')
        self.db.execute('create table if not exists state (id integer primary key, value text not null)')
        self.db.execute('''create table if not exists inventory (
            run_key text, program_id text, product_id text, payload text not null,
            score real not null, uploaded integer not null default 0,
            primary key(run_key,program_id,product_id))''')
        self.db.execute('create index if not exists inventory_identity on inventory(run_key,product_id)')
        self.db.execute('create index if not exists inventory_pending on inventory(run_key,uploaded)')
        self.db.execute('create table if not exists inventory_totals (run_key text primary key,total integer,uploaded integer)')
        self.db.execute('''create trigger if not exists inventory_insert_stats after insert on inventory begin
            insert into inventory_totals values(new.run_key,1,new.uploaded)
            on conflict(run_key) do update set total=total+1,uploaded=uploaded+new.uploaded;
            end''')
        self.db.execute('''create trigger if not exists inventory_update_stats after update of uploaded on inventory begin
            update inventory_totals set uploaded=uploaded+new.uploaded-old.uploaded where run_key=new.run_key;
            end''')
        self.db.execute('''insert or ignore into inventory_totals
            select run_key,count(*),sum(uploaded) from inventory group by run_key''')
        self.db.commit()

    def load(self):
        row = self.db.execute('select value from state where id=1').fetchone()
        return json.loads(row[0]) if row else None

    def save(self, state):
        self.db.execute('insert or replace into state values(1,?)', (json.dumps(state),))
        self.db.commit()

    def add(self, run, record):
        # Existing remote uniqueness omits program_id. Stop on collisions rather
        # than silently merging two merchants' distinct products.
        collision = self.db.execute('select 1 from inventory where run_key=? and product_id=? and program_id<>? limit 1',
                                    (run, record['source_product_id'], record['program_id'])).fetchone()
        if collision:
            raise ValueError('cross_program_product_identity_collision')
        payload = json.dumps(record, ensure_ascii=False)
        prior = self.db.execute('select payload from inventory where run_key=? and program_id=? and product_id=?',
                               (run, record['program_id'], record['source_product_id'])).fetchone()
        self.db.execute('''insert into inventory values(?,?,?,?,?,0)
            on conflict(run_key,program_id,product_id) do update set
            payload=excluded.payload,score=excluded.score,uploaded=0''',
            (run, record['program_id'], record['source_product_id'], payload, record['opportunity_score']))
        return prior is not None

    def upload(self, run, send):
        while True:
            batch = self.db.execute('select program_id,product_id,payload from inventory where run_key=? and uploaded=0 limit ?',
                                    (run, BATCH)).fetchall()
            if not batch:
                return
            while batch and len(json.dumps({'action': 'store_research', 'run_key': run,
                    'rows': [json.loads(x[2]) for x in batch]}).encode('utf-8')) > 135000:
                if len(batch) == 1:
                    raise ValueError('source_record_exceeds_gateway_payload_budget')
                batch.pop()
            response = send('store_research', {'run_key': run, 'rows': [json.loads(x[2]) for x in batch]})
            if int(response.get('accepted', -1)) != len(batch):
                raise RuntimeError('batch_ack_count_mismatch')
            self.db.executemany('update inventory set uploaded=1 where run_key=? and program_id=? and product_id=?',
                                [(run, x[0], x[1]) for x in batch])
            self.db.commit()

    def totals(self, run):
        row = self.db.execute('select total,uploaded from inventory_totals where run_key=?', (run,)).fetchone() or (0, 0)
        return {'unique_eligible_inventory': row[0], 'acknowledged_inventory': row[1]}

    def shortlist(self, run, top):
        return [json.loads(row[0]) for row in self.db.execute(
            'select payload from inventory where run_key=? order by score desc,program_id,product_id limit ?', (run, top))]


def domain_terms(programs):
    """Index source-provided merchant domains; never infer rates from names."""
    result = {}
    for row in programs:
        website = str(row.get('actual_http_site') or '')
        host = urlparse(website if '://' in website else 'https://' + website).hostname
        if host:
            result.setdefault(host.lower().removeprefix('www.'), []).append(row)
    return result


def make_record(raw, rules, signals, counts, by_domain=None):
    if isinstance(raw, dict) and raw.get('program_id') is not None:
        raw = {**raw, 'program_id': str(raw['program_id'])}
    product = parse_record(raw)
    if product is None:
        counts['invalid_or_non_eur'] += 1
        return None
    rule = rules.get(product['program_id'])
    identity_match = 'network_program_id'
    if rule is None and by_domain:
        matches = [row for row in by_domain.get(product['merchant_domain'], [])
                   if not row.get('linkwise_program_id') or str(row['linkwise_program_id']) == product['program_id']]
        if len(matches) == 1:
            rule, identity_match = matches[0], 'exact_source_merchant_domain'
        elif len(matches) > 1:
            counts['ambiguous_domain_terms'] += 1
    commission, basis = amount(product['price'], rule)
    if commission is None:
        counts['commission_unknown'] += 1
        return None
    if commission < FLOOR:  # No pre-gate rounding or epsilon admission.
        counts['below_15'] += 1
        return None
    counts['commission_eligible'] += 1
    if len(product['tracking_url']) > 4000 or len(product['source_product_id']) > 150:
        raise ValueError('source_identity_exceeds_remote_contract')
    record = {
        'source_key': 'linkwise', 'source_product_id': product['source_product_id'],
        'program_id': product['program_id'], 'merchant_domain': product['merchant_domain'],
        'product_title': product['product_name'], 'category_text': product['category'],
        'price_eur': product['price'], 'calculated_commission_eur': commission,
        'commission_basis': basis, 'commission_provenance': {
            'network_program_id': product['program_id'], 'rule_source': rule.get('source'),
            'identity_match': identity_match,
            'imported_at': rule.get('imported_at'), 'estimate_only': True,
            'currency_basis': 'source_eur' if raw.get('currency') else 'linkwise_default_eur'},
        'original_tracking_url': product['tracking_url'], 'image_url': product['image_url'],
        'stock_state': 'unknown' if product['in_stock'] is None else 'in_stock' if product['in_stock'] else 'out_of_stock',
        'valid_to': product['valid_to'], 'feed_observed_at': None,
    }
    rank = score_product({**product, 'category_raw': product['category']}, signals)
    record.update(rank)
    return record


def retry_gateway(action, payload):
    for attempt in range(3):
        try:
            return gateway(action, payload)
        except requests.RequestException as exc:
            response = getattr(exc, 'response', None)
            if response is not None and response.status_code not in (429, 500, 502, 503, 504):
                raise
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def run(args, send=retry_gateway):
    by_domain = {}
    if args.commission_rules == 'vmdb':
        response = send('commission_rules', {})
        rules = response.get('rules', {})
        by_domain = domain_terms(response.get('programs', []))
    else:
        rules = json.loads(Path(args.commission_rules).read_text(encoding='utf-8'))
    if not isinstance(rules, dict) or not rules:
        raise ValueError('no_mapped_commission_rules')
    signals = normalize_signals(json.loads(Path(args.signals).read_text(encoding='utf-8'))) if args.signals else {}
    journal = Journal(args.checkpoint)
    previous = journal.load()
    state = {'run_key': str(uuid.uuid4()), 'counts': {}, 'source_metadata': {}, 'status': 'partial'}
    counts = Counter()
    began, error, result, accepted_source = False, None, None, False
    try:
        if args.persist_research and not args.resume:
            state['source_metadata'] = {'source_kind': 'http_stream' if args.feed_url else 'local_stream',
                                        'expected_records': args.expected_records}
            send('begin_research', {'run_key': state['run_key'], 'source_metadata': state['source_metadata']})
            began = True
        with source(args) as (reader, metadata):
            metadata['expected_records'] = args.expected_records
            rule_hash = hashlib.sha256(json.dumps([rules, by_domain], sort_keys=True).encode()).hexdigest()
            signal_hash = hashlib.sha256(json.dumps(signals, sort_keys=True).encode()).hexdigest()
            metadata.update({'rule_revision_hash': rule_hash, 'signal_revision_hash': signal_hash})
            if args.resume and previous:
                old = previous['source_metadata']
                for key in ('source_uri_hash', 'source_signature', 'rule_revision_hash', 'signal_revision_hash'):
                    if not metadata.get(key) or old.get(key) != metadata[key]:
                        raise ValueError('resume_requires_unchanged_versioned_source_rules_and_signals')
                if old.get('expected_records') != metadata['expected_records']:
                    raise ValueError('resume_requires_unchanged_expected_records')
                if previous.get('status') == 'completed':
                    raise ValueError('resume_of_completed_run_not_allowed')
                state = previous
                counts.update(state['counts'])
                counts.pop('source_integrity', None)
            state['source_metadata'] = metadata
            accepted_source = True
            run_key = state['run_key']
            if args.persist_research:
                if not began:
                    send('begin_research', {'run_key': run_key, 'source_metadata': metadata})
                began = True
                journal.upload(run_key, send)
            skip = int(counts.get('scanned', 0))

            def checkpoint():
                counts['bytes_read'] = reader.bytes_read
                state.update({'counts': dict(counts), 'status': 'partial'})
                journal.save(state)  # Commit inventory and input cursor before remote acknowledgement.
                if args.persist_research:
                    journal.upload(run_key, send)
                    send('checkpoint_research', {'run_key': run_key, 'counts': dict(counts), 'source_metadata': metadata})
                print(json.dumps({'run_key': run_key, 'counts': dict(counts), **journal.totals(run_key)}), flush=True)

            for ordinal, raw in enumerate(array_records(reader), 1):
                if ordinal <= skip:
                    continue  # Replay only a verified immutable source; no unsafe HTTP byte ranges.
                prior_counts = counts.copy()
                counts['scanned'] += 1
                try:
                    record = make_record(raw, rules, signals, counts, by_domain)
                    if record:
                        if journal.add(run_key, record):
                            counts['duplicate_encounter'] += 1
                        counts['since_flush'] += 1
                except Exception:
                    counts.clear()
                    counts.update(prior_counts)  # Failed identity is not a committed input cursor.
                    raise
                if counts['scanned'] % args.progress_every == 0 or counts['since_flush'] >= BATCH:
                    counts['since_flush'] = 0
                    checkpoint()
            counts['source_integrity'] = 'complete_json'
            checkpoint()
            enough = counts['scanned'] >= args.expected_records
            counts['coverage_threshold_met'] = int(enough)
            state['status'] = 'completed' if enough else 'partial'
            if not enough:
                error = 'source_smaller_than_requested_universe'
            metadata['scope_verified_by_publisher'] = False
    except Exception as exc:
        # Error class is sufficient telemetry; exception URLs may contain tokens.
        error = type(exc).__name__
        if isinstance(exc, ValueError) and re.fullmatch(r'[A-Za-z0-9_]{1,120}', str(exc)):
            error += '_' + str(exc)
        counts.setdefault('source_integrity', 'incomplete_or_failed')
        state['status'] = 'partial'
    finally:
        counts.pop('since_flush', None)
        state['counts'] = dict(counts)
        if error:
            state['source_metadata']['error_class'] = error[:180]
        if accepted_source or (began and not args.resume):
            journal.save(state)
        totals = journal.totals(state['run_key'])
        if args.persist_research and began:
            try:
                journal.upload(state['run_key'], send)
                totals = journal.totals(state['run_key'])
                finished = send('finish_research', {'run_key': state['run_key'], 'counts': dict(counts),
                     'status': state['status'], 'source_metadata': state['source_metadata']})
                if finished.get('status') != state['status']:
                    raise RuntimeError('remote_finalization_status_mismatch')
            except Exception as exc:
                state['status'] = 'partial'
                error = 'persistence_failed:' + type(exc).__name__
                journal.save(state)
        result = {**state, **totals, 'hard_filter': {'calculated_commission_eur_gte': FLOOR},
                  'only_research_candidates': True, 'market_demand_verified': False,
                  'affiliate_conversions_verified': False, 'program_rule_count': len(rules),
                  'products': journal.shortlist(state['run_key'], args.top), 'error': error}
        Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        journal.db.close()
    print(json.dumps({k: v for k, v in result.items() if k != 'products'}, ensure_ascii=False), flush=True)
    return 0 if result['status'] == 'completed' and not error else 2
