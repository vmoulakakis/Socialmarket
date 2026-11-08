"""Offline regression coverage for durable streaming research ingestion."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import full_feed_streaming as worker


class StreamingIngestionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.feed = self.root / 'feed.json'
        self.rules = self.root / 'rules.json'
        self.rules.write_text(json.dumps({
            '23': {'flat_commission_min_eur': 20},
            '24': {'flat_commission_min_eur': 20},
        }), encoding='utf-8')

    def row(self, product_id, program='23', **fields):
        return {
            'product_id': str(product_id), 'product_name': 'Example product',
            'price': 200, 'currency': 'EUR', 'in_stock': False,
            'tracking_url': f'https://go.linkwi.se/z/{program}-0/CD104/?lnkurl=https%3A%2F%2Fshop.example%2Fp',
            **fields,
        }

    def args(self, **changes):
        values = dict(
            feed_url=None, feed=str(self.feed), commission_rules=str(self.rules),
            signals='', checkpoint=str(self.root / 'journal.sqlite'), resume=False,
            expected_records=0, persist_research=True, progress_every=100,
            output=str(self.root / 'result.json'), top=2,
        )
        values.update(changes)
        return SimpleNamespace(**values)

    def execute(self, args=None, sender=None):
        args = args or self.args()
        calls = []

        def send(action, payload):
            calls.append((action, json.loads(json.dumps(payload))))
            if sender:
                return sender(action, payload)
            return {'ok': True, 'accepted': len(payload.get('rows', [])),
                    'status': payload.get('status', 'partial')}

        with contextlib.redirect_stdout(io.StringIO()):
            status = worker.run(args, send)
        return status, json.loads(Path(args.output).read_text(encoding='utf-8')), calls

    def saved_state(self):
        journal = worker.Journal(self.args().checkpoint)
        try:
            return journal.load()
        finally:
            journal.db.close()

    def test_all_eligible_inventory_persists_beyond_top_and_stock_is_weighted(self):
        self.feed.write_text(json.dumps([self.row(i) for i in range(43)]))
        status, result, calls = self.execute()
        self.assertEqual(status, 0)
        self.assertEqual(result['unique_eligible_inventory'], 43)
        self.assertEqual(result['acknowledged_inventory'], 43)
        self.assertEqual(len(result['products']), 2)
        uploads = [payload['rows'] for action, payload in calls if action == 'store_research']
        self.assertEqual(sum(map(len, uploads)), 43)
        self.assertTrue(all(len(rows) <= 20 for rows in uploads))
        self.assertTrue(all(row['stock_state'] == 'out_of_stock' for rows in uploads for row in rows))
        self.assertEqual(calls[0][0], 'begin_research')

    def test_truncated_input_retains_only_complete_records_and_is_partial(self):
        self.feed.write_text('[' + json.dumps(self.row(1)) + ',' + json.dumps(self.row(2))[:-3])
        status, result, calls = self.execute()
        self.assertEqual(status, 2)
        self.assertEqual(result['counts']['scanned'], 1)
        self.assertEqual(result['unique_eligible_inventory'], 1)
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(calls[-1][0], 'finish_research')
        self.assertEqual(calls[-1][1]['status'], 'partial')

    def test_non_array_root_is_refused(self):
        self.feed.write_text(json.dumps({'products': [self.row(1)]}))
        status, result, _ = self.execute()
        self.assertEqual(status, 2)
        self.assertEqual(result['unique_eligible_inventory'], 0)
        self.assertIn('source_root_must_be_array', result['error'])

    def test_complete_source_below_expected_count_is_partial(self):
        self.feed.write_text(json.dumps([self.row(1)]))
        status, result, calls = self.execute(self.args(expected_records=100))
        self.assertEqual(status, 2)
        self.assertEqual(result['counts']['source_integrity'], 'complete_json')
        self.assertEqual(result['counts']['coverage_threshold_met'], 0)
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(calls[-1][1]['status'], 'partial')

    def test_identity_failure_does_not_advance_durable_cursor(self):
        self.feed.write_text(json.dumps([self.row(1), self.row(1, '24')]))
        status, result, _ = self.execute()
        self.assertEqual(status, 2)
        self.assertEqual(result['counts']['scanned'], 1)
        self.assertEqual(result['counts']['commission_eligible'], 1)
        self.assertEqual(self.saved_state()['counts']['scanned'], 1)
        status, resumed, _ = self.execute(self.args(resume=True))
        self.assertEqual(status, 2)
        self.assertEqual(resumed['counts']['scanned'], 1)
        self.assertEqual(resumed['run_key'], result['run_key'])

    def test_upload_failure_resumes_without_inventory_loss(self):
        self.feed.write_text(json.dumps([self.row(i) for i in range(21)]))

        def fail_upload(action, payload):
            if action == 'store_research':
                raise RuntimeError('offline')
            return {'ok': True, 'status': payload.get('status', 'partial')}

        status, result, _ = self.execute(sender=fail_upload)
        self.assertEqual(status, 2)
        self.assertEqual(result['counts']['scanned'], 20)
        self.assertEqual(result['acknowledged_inventory'], 0)
        self.assertEqual(self.saved_state()['counts']['scanned'], 20)
        status, resumed, _ = self.execute(self.args(resume=True))
        self.assertEqual(status, 0)
        self.assertEqual(resumed['run_key'], result['run_key'])
        self.assertEqual(resumed['unique_eligible_inventory'], 21)
        self.assertEqual(resumed['acknowledged_inventory'], 21)
        self.assertEqual(resumed['counts']['scanned'], 21)

    def test_changed_source_does_not_overwrite_resume_state(self):
        self.feed.write_text(json.dumps([self.row(1)]))
        self.execute(self.args(expected_records=2))
        before = self.saved_state()
        self.feed.write_text(json.dumps([self.row(2), self.row(3)]))
        status, _, calls = self.execute(self.args(resume=True, expected_records=2))
        self.assertEqual(status, 2)
        self.assertEqual(self.saved_state(), before)
        self.assertEqual(calls, [])

    def test_changed_terms_do_not_overwrite_resume_state(self):
        self.feed.write_text(json.dumps([self.row(1)]))
        self.execute(self.args(expected_records=2))
        before = self.saved_state()
        self.rules.write_text(json.dumps({'23': {'flat_commission_min_eur': 30}}))
        status, _, calls = self.execute(self.args(resume=True, expected_records=2))
        self.assertEqual(status, 2)
        self.assertEqual(self.saved_state(), before)
        self.assertEqual(calls, [])

    def test_changed_coverage_target_does_not_overwrite_resume_state(self):
        self.feed.write_text(json.dumps([self.row(1)]))
        self.execute(self.args(expected_records=100))
        before = self.saved_state()
        status, _, calls = self.execute(self.args(resume=True, expected_records=0))
        self.assertEqual(status, 2)
        self.assertEqual(self.saved_state(), before)
        self.assertEqual(calls, [])

    def test_remote_partial_finalization_cannot_report_completion(self):
        self.feed.write_text(json.dumps([self.row(1)]))

        def partial_finish(action, payload):
            return {'ok': True, 'accepted': len(payload.get('rows', [])), 'status': 'partial'}

        status, result, _ = self.execute(sender=partial_finish)
        self.assertEqual(status, 2)
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(result['acknowledged_inventory'], 1)
        self.assertEqual(self.saved_state()['status'], 'partial')

    def test_incorrect_acknowledgement_keeps_pending_inventory(self):
        self.feed.write_text(json.dumps([self.row(1)]))
        status, result, _ = self.execute(sender=lambda action, payload: {'ok': True, 'accepted': 0})
        self.assertEqual(status, 2)
        self.assertEqual(result['acknowledged_inventory'], 0)
        self.assertEqual(result['unique_eligible_inventory'], 1)

    def test_http_redirect_creates_and_finishes_partial_run(self):
        response = SimpleNamespace(status_code=302)
        with patch.object(worker.requests, 'get', return_value=contextlib.nullcontext(response)) as get:
            status, result, calls = self.execute(self.args(
                feed_url='https://affiliate.linkwi.se/feeds/1.2/CD104/programs-all/columns-product_id/catinc-0/catex-0/proginc-0/progex-0/feed.json'))
        self.assertEqual(status, 2)
        self.assertEqual(result['status'], 'partial')
        self.assertFalse(get.call_args.kwargs['allow_redirects'])
        self.assertEqual([action for action, _ in calls], ['begin_research', 'finish_research'])
        self.assertEqual(calls[-1][1]['status'], 'partial')

    def test_http_missing_version_headers_is_scannable_but_not_resumable(self):
        url = 'https://affiliate.linkwi.se/feeds/1.2/CD104/programs-all/columns-product_id/catinc-0/catex-0/proginc-0/progex-0/feed.json'

        def response(*args, **kwargs):
            value = SimpleNamespace(status_code=200, headers={'content-type': 'application/json'},
                                    raw=io.BytesIO(json.dumps([self.row(1)]).encode()))
            return contextlib.nullcontext(value)

        with patch.object(worker.requests, 'get', side_effect=response):
            status, result, _ = self.execute(self.args(feed_url=url, expected_records=100))
            self.assertEqual(status, 2)
            self.assertEqual(result['counts']['scanned'], 1)
            self.assertIsNone(result['source_metadata']['source_signature'])
            before = self.saved_state()
            status, _, calls = self.execute(self.args(feed_url=url, expected_records=100, resume=True))
        self.assertEqual(status, 2)
        self.assertEqual(self.saved_state(), before)
        self.assertEqual(calls, [])

    def test_http_non_json_response_is_partial_before_parsing(self):
        response = SimpleNamespace(status_code=200, headers={'content-type': 'text/html'})
        with patch.object(worker.requests, 'get', return_value=contextlib.nullcontext(response)):
            status, result, calls = self.execute(self.args(
                feed_url='https://affiliate.linkwi.se/feeds/1.2/CD104/programs-all/foo/feed.json'))
        self.assertEqual(status, 2)
        self.assertEqual(result['unique_eligible_inventory'], 0)
        self.assertEqual(calls[-1][1]['status'], 'partial')

    def test_exact_commission_floor_has_no_rounding_admission(self):
        counts = worker.Counter()
        rules = {'23': {'percent_commission_min': 10}}
        self.assertIsNone(worker.make_record(self.row(1, price=149.99999), rules, {}, counts))
        self.assertEqual(counts['below_15'], 1)
        record = worker.make_record(self.row(2, price=150), rules, {}, counts)
        self.assertEqual(record['calculated_commission_eur'], 15)

    def test_non_eur_cannot_pass_commission_floor(self):
        counts = worker.Counter()
        self.assertIsNone(worker.make_record(self.row(1, currency='USD'), {'23': {'flat_commission_min_eur': 20}}, {}, counts))
        self.assertEqual(counts['invalid_or_non_eur'], 1)

    def test_missing_currency_is_explicitly_labelled_default(self):
        raw = self.row(1)
        del raw['currency']
        record = worker.make_record(raw, {'23': {'flat_commission_min_eur': 20}}, {}, worker.Counter())
        self.assertEqual(record['commission_provenance']['currency_basis'], 'linkwise_default_eur')

    def test_zero_eligible_run_is_created_and_finalized(self):
        self.feed.write_text(json.dumps([self.row(1, '99')]))
        status, result, calls = self.execute()
        self.assertEqual(status, 0)
        self.assertEqual(result['unique_eligible_inventory'], 0)
        self.assertEqual(result['counts']['commission_unknown'], 1)
        self.assertEqual(calls[0][0], 'begin_research')
        self.assertEqual(calls[-1][0], 'finish_research')
        self.assertFalse(any(action == 'store_research' for action, _ in calls))

    def test_ambiguous_domain_terms_remain_unknown(self):
        counts = worker.Counter()
        by_domain = {'shop.example': [{'flat_commission_min_eur': 20}, {'flat_commission_min_eur': 25}]}
        self.assertIsNone(worker.make_record(self.row(1), {}, {}, counts, by_domain))
        self.assertEqual(counts['commission_unknown'], 1)
        self.assertEqual(counts['ambiguous_domain_terms'], 1)

    def test_exact_domain_terms_preserve_match_provenance(self):
        row = {'actual_http_site': 'https://shop.example', 'flat_commission_min_eur': 20}
        record = worker.make_record(self.row(1), {}, {}, worker.Counter(), worker.domain_terms([row]))
        self.assertEqual(record['commission_provenance']['identity_match'], 'exact_source_merchant_domain')
        self.assertEqual(record['program_id'], '23')

    def test_conflicting_program_domain_terms_do_not_supply_rates(self):
        row = {'actual_http_site': 'https://shop.example', 'linkwise_program_id': '24', 'flat_commission_min_eur': 20}
        self.assertIsNone(worker.make_record(self.row(1), {}, {}, worker.Counter(), worker.domain_terms([row])))

    def test_checkpoint_metadata_uses_safe_identity_hashes(self):
        self.feed.write_text(json.dumps([self.row(1)]))
        _, result, calls = self.execute()
        metadata = result['source_metadata']
        for key in ('source_uri_hash', 'rule_revision_hash', 'signal_revision_hash'):
            self.assertRegex(metadata[key], r'^[0-9a-f]{64}$')
        self.assertRegex(metadata['source_signature'], r'^local:[0-9]+:[0-9]+$')
        self.assertIs(metadata['scope_verified_by_publisher'], False)
        self.assertNotIn(str(self.feed), json.dumps(calls))
        self.assertNotIn('feed_url', metadata)


if __name__ == '__main__':
    unittest.main()
