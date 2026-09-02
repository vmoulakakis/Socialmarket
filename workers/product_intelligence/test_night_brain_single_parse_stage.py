import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import quote

import night_brain_gate_tools as legacy
import night_brain_single_parse_stage as single
import product_intelligence_v1 as v1
import product_safety as safety
from stream_feed import iter_records as real_iter_records


class NightBrainSingleParseStageTests(unittest.TestCase):
    def _context(self):
        return {
            'programs': [{
                'merchant_id': 'm1',
                'merchant_program_id': 'm1',
                'canonical_name': 'Example Store',
                'official_domain': 'example.gr',
                'program_name': 'Example Store',
                'aliases': [],
                'trust_score': 90,
                'raw_commission_pct': '20%',
                'raw_flat_commission': None,
                'solution_whitespace_score': 60,
                'demand_beacon_score': 50,
                'demand_score': 70,
                'competition_score': 30,
                'confidence': 90,
                'promotion_mode': 'eligible',
                'dominant_market': False,
            }]
        }

    def _tracking(self, product_id, host='example.gr'):
        target = f'https://{host}/p/{product_id}'
        return f'https://go.linkwi.se/z/1-0/ABC/?lnkurl={quote(target, safe="")}'

    def _row(self, product_id, price=100, **overrides):
        row = {
            'product_id': str(product_id),
            'product_name': f'Useful product {product_id}',
            'description': 'Verified product description',
            'category': 'Home',
            'image_url': f'https://cdn.example.gr/{product_id}.jpg',
            'in_stock': True,
            'currency': 'EUR',
            'price': price,
            'full_price': price,
            'tracking_url': self._tracking(product_id),
        }
        row.update(overrides)
        return row

    def _feed(self, path):
        rows = [self._row(i) for i in range(20)]
        # Enough normal observations establish a ~EUR100 merchant baseline. This row
        # passes the EUR10 commission floor but must be quarantined as an extreme
        # price outlier by both the legacy and single-parse implementations.
        rows.append(self._row('outlier', price=5000))
        # These fail independent hard gates and must never reach the final candidate set.
        rows.append(self._row('low-commission', price=20))
        rows.append(self._row('out-of-stock', in_stock=False))
        # program_name resolves the merchant even though the decoded tracking target is
        # deliberately wrong, exercising the tracking-domain mismatch gate itself.
        rows.append(self._row(
            'wrong-domain',
            program_name='Example Store',
            tracking_url=self._tracking('wrong-domain', 'other.gr'),
        ))
        path.write_text(json.dumps(rows, ensure_ascii=False), encoding='utf-8')

    @staticmethod
    def _payloads(db):
        return [json.loads(payload) for (payload,) in db.execute('select payload from candidates order by source_hash')]

    def test_single_parse_matches_legacy_final_candidates_and_reads_raw_feed_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            feed = root / 'feed.json'
            self._feed(feed)
            context = self._context()

            legacy_db_path = root / 'legacy.sqlite3'
            legacy_profile = root / 'legacy-safety.json'
            with patch.object(v1, 'STAGE_DB', str(legacy_db_path)), patch.object(safety, 'SAFETY_PROFILE_PATH', legacy_profile):
                legacy_db, legacy_stats = legacy.stage_feed(str(feed), context)
                legacy_payloads = self._payloads(legacy_db)
                legacy_db.close()

            single_db_path = root / 'single.sqlite3'
            single_profile = root / 'single-safety.json'
            with (
                patch.object(v1, 'STAGE_DB', str(single_db_path)),
                patch.object(safety, 'SAFETY_PROFILE_PATH', single_profile),
                patch.object(single, 'SINGLE_PARSE_ENABLED', True),
                patch.object(single, 'iter_records', wraps=real_iter_records) as parse_spy,
            ):
                single_db, single_stats = single.stage_feed(str(feed), context)
                single_payloads = self._payloads(single_db)
                single_db.close()

            self.assertEqual(parse_spy.call_count, 1)
            self.assertEqual(single_stats['feed_parse_passes'], 1)
            self.assertFalse(single_stats['raw_feed_reparsed'])
            self.assertEqual(single_stats['stage_engine'], 'single_parse_materialized_v1')
            self.assertEqual(single_stats['price_revalidation_rows_removed'], 1)
            self.assertEqual(single_stats['commission_eligible_records'], 20)
            self.assertEqual(legacy_stats['commission_eligible_records'], 20)
            self.assertEqual(len(single_payloads), 20)

            # The optimized stage must preserve the authoritative final candidate
            # contract, not merely produce the same count.
            self.assertEqual(single_payloads, legacy_payloads)
            self.assertTrue(all('price_integrity_pending' not in row for row in single_payloads))
            self.assertTrue(all((row.get('price_integrity') or {}).get('status') == 'price_major_unit_probable' for row in single_payloads))

            excluded = dict(single_stats['excluded_reasons'])
            self.assertEqual(excluded.get('price_extreme_outlier_unverified'), 1)
            self.assertEqual(excluded.get('commission_below_immutable_10_eur_floor'), 1)
            self.assertEqual(excluded.get('out_of_stock'), 1)
            self.assertEqual(excluded.get('tracking_destination_merchant_mismatch'), 1)

    def test_feature_flag_uses_legacy_stage(self):
        with patch.object(single, 'SINGLE_PARSE_ENABLED', False), patch.object(single.legacy, 'stage_feed', return_value=('db', {'legacy': True})) as fallback:
            result = single.stage_feed('feed.json', {'programs': []})
        self.assertEqual(result, ('db', {'legacy': True}))
        fallback.assert_called_once_with('feed.json', {'programs': []})


if __name__ == '__main__':
    unittest.main()
