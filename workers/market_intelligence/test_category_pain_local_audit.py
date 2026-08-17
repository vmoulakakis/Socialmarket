from __future__ import annotations

import os
import unittest
from unittest.mock import patch

import category_pain_local_audit as audit


def _row(domain: str, idx: int, score: int = 8, body_size: int = 1400):
    return {
        'source_kind': 'pain_candidate',
        'source_url': f'https://{domain}/topic/{idx}',
        'title': f'Consumer topic {idx}',
        'body': ('πρόβλημα με αυτόματο πότισμα και άνιση ροή νερού. ' * 40)[:body_size],
        'confidence': 0.8,
        'metadata': {
            'consumer_text': True,
            'eligible_for_pain_audit': True,
            'source_family': 'community_forum',
            'consumer_language_score': score,
            'pain_language': ['πρόβλημα', 'άνιση'],
        },
    }


def _cluster(indices):
    return {
        'canonical_text': 'Οι σταλάκτες βουλώνουν και το πότισμα γίνεται αναξιόπιστο.',
        'cluster_type': 'pain',
        'evidence_indices': indices,
        'pain_severity': 75,
        'commercial_intent': 60,
        'audit_score': 85,
        'confidence': 0.88,
        'rationale': 'Τρεις ανεξάρτητες consumer πηγές περιγράφουν το ίδιο failure mode.',
        'verdict': 'validated',
    }


class CategoryPainLocalAuditCompactTests(unittest.TestCase):
    def test_filters_non_consumer_and_ineligible_rows(self):
        item = {'evidence': [
            _row('a.gr', 1),
            {**_row('b.gr', 2), 'source_kind': 'consumer_discovery'},
            {**_row('c.gr', 3), 'metadata': {**_row('c.gr', 3)['metadata'], 'consumer_text': False}},
            {**_row('d.gr', 4), 'metadata': {**_row('d.gr', 4)['metadata'], 'eligible_for_pain_audit': False}},
        ]}
        packed = audit._pain_evidence(item)
        self.assertEqual(len(packed), 1)
        self.assertEqual(packed[0]['source_domain'], 'a.gr')

    def test_source_diversity_is_selected_before_duplicate_domain_rows(self):
        evidence = [_row('dominant.gr', i, score=10) for i in range(12)]
        evidence += [_row('second.gr', 20, score=7), _row('third.gr', 30, score=6)]
        with patch.dict(os.environ, {'CATEGORY_PAIN_AUDIT_MAX_EVIDENCE': '6'}, clear=False):
            packed = audit._pain_evidence({'evidence': evidence})
        self.assertEqual(len(packed), 6)
        first_domains = {row['source_domain'] for row in packed[:3]}
        self.assertEqual(first_domains, {'dominant.gr', 'second.gr', 'third.gr'})

    def test_body_and_total_rows_are_bounded(self):
        evidence = [_row(f'd{i}.gr', i, body_size=3000) for i in range(20)]
        with patch.dict(os.environ, {
            'CATEGORY_PAIN_AUDIT_MAX_EVIDENCE': '10',
            'CATEGORY_PAIN_AUDIT_BODY_CHARS': '500',
        }, clear=False):
            packed = audit._pain_evidence({'evidence': evidence})
        self.assertEqual(len(packed), 10)
        self.assertTrue(all(len(row['body']) <= 500 for row in packed))

    def test_selection_is_deterministic(self):
        evidence = [_row('a.gr', 2), _row('b.gr', 1), _row('a.gr', 1)]
        first = audit._pain_evidence({'evidence': evidence})
        second = audit._pain_evidence({'evidence': list(reversed(evidence))})
        self.assertEqual(first, second)

    def test_task_payload_excludes_bulky_market_context_and_versions_cache(self):
        item = {
            'entity_id': 'entity-1',
            'category': 'Home & Garden',
            'subcategory': 'Garden & Outdoor Living',
            'market': {'evidence_quality': {'huge': 'x' * 50000}},
            'evidence': [_row('a.gr', 1), _row('b.gr', 2), _row('c.gr', 3)],
        }
        task = audit.build_task(item)
        self.assertNotIn('market_evidence_quality', task.payload)
        self.assertEqual(task.prompt_version, 'category-pain-local-v3-concise')
        self.assertEqual(task.metadata['source_domains'], 3)
        self.assertEqual(task.metadata['evidence_pack'], 'source_diverse_compact_v2')
        self.assertLessEqual(len(task.payload['evidence']), 10)

    def test_nested_contract_rejects_two_row_cluster_without_normalization(self):
        data = {
            'clusters': [_cluster([0, 1])],
            'audit_summary': 'Not enough independent support.',
            'rejected_patterns': [],
        }
        valid, reason = audit._validate_nested(data, 3)
        self.assertFalse(valid)
        self.assertEqual(reason, 'cluster_insufficient_evidence_indices')

    def test_normalization_drops_model_explanation_with_too_few_rows(self):
        candidate = _cluster([0])
        candidate['verdict'] = 'rejected'
        data = {
            'clusters': [candidate],
            'audit_summary': 'One row mentions the issue, so nothing qualifies.',
            'rejected_patterns': ['single-row candidate'],
        }
        normalized = audit._normalize_result(data)
        self.assertEqual(normalized['clusters'], [])
        valid, reason = audit._validate_nested(normalized, 3)
        self.assertTrue(valid)
        self.assertIsNone(reason)

    def test_normalization_cannot_promote_two_row_validated_claim(self):
        candidate = _cluster([0, 1])
        candidate['verdict'] = 'validated'
        normalized = audit._normalize_result({
            'clusters': [candidate],
            'audit_summary': 'Model overclaimed it.',
            'rejected_patterns': [],
        })
        self.assertEqual(normalized['clusters'], [])

    def test_normalization_keeps_three_row_cluster_for_full_validation(self):
        data = {
            'clusters': [_cluster([0, 1, 2])],
            'audit_summary': 'Three corroborating rows.',
            'rejected_patterns': [],
        }
        normalized = audit._normalize_result(data)
        self.assertEqual(len(normalized['clusters']), 1)
        valid, reason = audit._validate_nested(normalized, 3)
        self.assertTrue(valid)
        self.assertIsNone(reason)

    def test_nested_contract_accepts_concise_three_row_cluster(self):
        data = {
            'clusters': [_cluster([0, 1, 2])],
            'audit_summary': 'Three corroborating rows support the same irrigation failure.',
            'rejected_patterns': ['generic gardening difficulty'],
        }
        valid, reason = audit._validate_nested(data, 3)
        self.assertTrue(valid)
        self.assertIsNone(reason)

    def test_longer_summary_is_presentation_only_and_does_not_override_evidence_gate(self):
        data = {
            'clusters': [_cluster([0, 1, 2])],
            'audit_summary': 'A' * 600,
            'rejected_patterns': [],
        }
        valid, reason = audit._validate_nested(data, 3)
        self.assertTrue(valid)
        self.assertIsNone(reason)

    def test_summary_still_has_hard_bound(self):
        data = {
            'clusters': [_cluster([0, 1, 2])],
            'audit_summary': 'A' * 801,
            'rejected_patterns': [],
        }
        valid, reason = audit._validate_nested(data, 3)
        self.assertFalse(valid)
        self.assertEqual(reason, 'audit_summary_too_long')

    def test_nested_contract_rejects_unbounded_cluster_count(self):
        data = {
            'clusters': [_cluster([0, 1, 2]), _cluster([0, 1, 2]), _cluster([0, 1, 2])],
            'audit_summary': 'Too many.',
            'rejected_patterns': [],
        }
        valid, reason = audit._validate_nested(data, 3)
        self.assertFalse(valid)
        self.assertEqual(reason, 'too_many_clusters')


if __name__ == '__main__':
    unittest.main()
