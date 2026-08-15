import unittest

from candidate_shortlist import pain_first_score, select_ai_shortlist


def product(hash_, merchant_id, merchant_name, category, commission, whitespace=60, trust=80):
    raw = {
        'source_record_hash': hash_,
        'merchant_name': merchant_name,
        'category_raw': category,
        'expected_commission_eur': commission,
        'merchant_context': {
            'merchant_id': merchant_id,
            'canonical_name': merchant_name,
            'solution_whitespace_score': whitespace,
            'trust_score': trust,
        },
    }
    return raw


def pain(id_, retrieval, severity=80, intent=80, demand=80, competition=35, evidence=12, sources=4):
    return {
        'id': id_,
        'canonical_text': f'pain {id_}',
        'retrieval_score': retrieval,
        'pain_severity': severity,
        'commercial_intent': intent,
        'demand_score': demand,
        'competition_score': competition,
        'evidence_count': evidence,
        'source_diversity': sources,
    }


def build_factory(pain_map):
    def build(raw, context):
        pains = pain_map.get(raw['source_record_hash'], [])
        return {
            'product': {
                'source_record_hash': raw['source_record_hash'],
                'category_raw': raw['category_raw'],
            },
            'merchant': raw['merchant_context'],
            'pain_rag': pains,
            'theme_rag': [],
            '_pains': pains,
            '_themes': [],
            '_raw': raw,
        }
    return build


class CandidateShortlistTests(unittest.TestCase):
    def test_candidate_without_validated_pain_never_consumes_ai_capacity(self):
        rows = [product('no-pain', 'm1', 'M1', 'Pool Robots', 500)]
        selected, stats = select_ai_shortlist(rows, {}, build_factory({}), limit=100)
        self.assertEqual(selected, [])
        self.assertEqual(stats['pre_ai_no_validated_pain_match'], 1)
        self.assertEqual(stats['shortlist_candidates'], 0)

    def test_strong_pain_fit_outranks_huge_commission_only_candidate(self):
        rows = [
            product('high-commission', 'm1', 'M1', 'Pool Robots', 500, whitespace=90),
            product('pain-solver', 'm2', 'M2', 'Travel Bags', 16, whitespace=60),
        ]
        pains = {'pain-solver': [pain('p1', retrieval=95, severity=92, intent=88, demand=84, competition=28)]}
        selected, stats = select_ai_shortlist(rows, {}, build_factory(pains), limit=1)
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]['product']['source_record_hash'], 'pain-solver')
        self.assertEqual(stats['pre_ai_no_validated_pain_match'], 1)

    def test_missing_competition_does_not_create_inverse_competition_upside(self):
        base = product('x', 'm1', 'M1', 'Travel Bags', 20)
        missing = build_factory({'x': [pain('p', retrieval=75, competition=None)]})(base, {})
        observed = build_factory({'x': [pain('p', retrieval=75, competition=20)]})(base, {})
        self.assertGreater(pain_first_score(observed), pain_first_score(missing))

    def test_initial_shortlist_is_diversified_by_merchant_and_category(self):
        rows = []
        pains = {}
        for i in range(8):
            h = f'a-{i}'
            rows.append(product(h, 'merchant-a', 'Merchant A', 'Rugs', 30))
            pains[h] = [pain(f'p-{i}', retrieval=95-i)]
        for i in range(4):
            h = f'b-{i}'
            rows.append(product(h, f'merchant-b-{i}', f'Merchant B{i}', f'Category {i}', 22))
            pains[h] = [pain(f'pb-{i}', retrieval=80-i)]

        selected, stats = select_ai_shortlist(
            rows, {}, build_factory(pains), limit=6, max_per_merchant=2, max_per_category=2
        )
        merchants = [x['merchant']['merchant_id'] for x in selected]
        categories = [x['_raw']['category_raw'] for x in selected]
        self.assertLessEqual(merchants.count('merchant-a'), 4)  # relaxed second pass may double cap
        self.assertGreaterEqual(len(set(merchants)), 3)
        self.assertGreaterEqual(len(set(categories)), 3)
        self.assertEqual(stats['shortlist_candidates'], 6)

    def test_shortlist_score_does_not_validate_or_relax_audit_thresholds(self):
        row = product('solver', 'm1', 'M1', 'Travel Bags', 20)
        item = build_factory({'solver': [pain('p', retrieval=100)]})(row, {})
        score = pain_first_score(item)
        self.assertIsInstance(score, float)
        self.assertNotIn('validation_status', item)
        self.assertNotIn('verdict', item)


if __name__ == '__main__':
    unittest.main()
