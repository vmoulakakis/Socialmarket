from __future__ import annotations

import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import category_pain_local_audit as audit


def _row(domain: str, idx: int, score: int = 8, body_size: int = 1400, family: str = 'community_forum'):
    return {
        'source_kind': 'pain_candidate',
        'source_url': f'https://{domain}/topic/{idx}',
        'title': f'Consumer topic {idx}',
        'body': ('πρόβλημα με φουσκωτό στρώμα που χάνει αέρα και θέλει ξανά φούσκωμα. ' * 30)[:body_size],
        'confidence': 0.8,
        'metadata': {
            'consumer_text': True,
            'eligible_for_pain_audit': True,
            'source_family': family,
            'consumer_language_score': score,
            'pain_language': ['πρόβλημα', 'χάνει αέρα'],
        },
    }


def _decision(indices, verdict='validated'):
    return {
        'canonical_text': 'Τα φουσκωτά camping στρώματα χάνουν αέρα και απαιτούν επαναλαμβανόμενο φούσκωμα.',
        'cluster_type': 'pain',
        'evidence_indices': indices,
        'pain_severity': 75,
        'commercial_intent': 60,
        'audit_score': 85,
        'confidence': 0.88,
        'verdict': verdict,
    }


class ExplodingRouter:
    def execute(self, task):
        raise AssertionError(f'router must not be called for impossible topology: {task.task_type}')


class StaticRouter:
    def __init__(self, data):
        self.data = data
        self.calls = 0

    def execute(self, task):
        self.calls += 1
        attempt = SimpleNamespace(as_dict=lambda: {'status': 'ok', 'executor': 'fake-local', 'task_type': task.task_type})
        return SimpleNamespace(ok=True, data=self.data, attempts=[attempt], reason=None, status='ok')


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
        self.assertEqual({row['source_domain'] for row in packed[:3]}, {'dominant.gr', 'second.gr', 'third.gr'})

    def test_body_and_total_rows_are_bounded(self):
        evidence = [_row(f'd{i}.gr', i, body_size=3000) for i in range(20)]
        with patch.dict(os.environ, {'CATEGORY_PAIN_AUDIT_MAX_EVIDENCE': '10', 'CATEGORY_PAIN_AUDIT_BODY_CHARS': '500'}, clear=False):
            packed = audit._pain_evidence({'evidence': evidence})
        self.assertEqual(len(packed), 10)
        self.assertTrue(all(len(row['body']) <= 500 for row in packed))

    def test_selection_is_deterministic(self):
        evidence = [_row('a.gr', 2), _row('b.gr', 1), _row('a.gr', 1)]
        self.assertEqual(
            audit._pain_evidence({'evidence': evidence}),
            audit._pain_evidence({'evidence': list(reversed(evidence))}),
        )

    def test_task_is_compact_decision_only(self):
        item = {
            'entity_id': 'entity-1',
            'category': 'Sports & Outdoors',
            'subcategory': 'Camping & Hiking',
            'evidence': [_row('a.gr', 1), _row('b.gr', 2, family='community_blog'), _row('a.gr', 3)],
        }
        task = audit.build_task(item)
        self.assertEqual(task.prompt_version, 'category-pain-local-v5-compact-decision')
        self.assertEqual(task.required_keys, ('clusters',))
        self.assertEqual(task.metadata['evidence_pack'], 'source_diverse_compact_v4')
        schema = task.metadata['response_schema']
        self.assertEqual(set(schema['properties']), {'clusters'})
        cluster_props = schema['properties']['clusters']['items']['properties']
        self.assertNotIn('rationale', cluster_props)
        self.assertNotIn('audit_summary', schema['properties'])
        self.assertNotIn('rejected_patterns', schema['properties'])

    def test_router_output_budget_is_reduced_not_increased(self):
        router = audit.make_router()
        self.assertGreaterEqual(len(router.executors), 1)
        self.assertEqual(router.executors[0].max_output_tokens, 240)
        self.assertEqual(router.executors[0].model, 'qwen3.5:4b')

    def test_topology_rejects_fewer_than_three_rows(self):
        ready, reason = audit._hard_topology_ready([
            {'source_domain': 'a.gr', 'source_family': 'community_forum'},
            {'source_domain': 'b.gr', 'source_family': 'community_blog'},
        ])
        self.assertFalse(ready)
        self.assertEqual(reason, 'fewer_than_3_consumer_rows')

    def test_topology_rejects_two_domains_one_family(self):
        ready, reason = audit._hard_topology_ready([
            {'source_domain': 'a.gr', 'source_family': 'community_forum'},
            {'source_domain': 'a.gr', 'source_family': 'community_forum'},
            {'source_domain': 'b.gr', 'source_family': 'community_forum'},
        ])
        self.assertFalse(ready)
        self.assertEqual(reason, 'source_diversity_gate_impossible')

    def test_topology_accepts_two_domains_two_families(self):
        ready, reason = audit._hard_topology_ready([
            {'source_domain': 'a.gr', 'source_family': 'community_forum'},
            {'source_domain': 'a.gr', 'source_family': 'community_forum'},
            {'source_domain': 'b.gr', 'source_family': 'community_blog'},
        ])
        self.assertTrue(ready)
        self.assertEqual(reason, 'ready')

    def test_topology_accepts_three_domains_same_family(self):
        ready, reason = audit._hard_topology_ready([
            {'source_domain': 'a.gr', 'source_family': 'community_forum'},
            {'source_domain': 'b.gr', 'source_family': 'community_forum'},
            {'source_domain': 'c.gr', 'source_family': 'community_forum'},
        ])
        self.assertTrue(ready)
        self.assertEqual(reason, 'ready')

    def test_audit_items_skips_llm_when_topology_impossible(self):
        result = audit.audit_items([{
            'entity_id': 'entity-1', 'category': 'X', 'subcategory': 'Y',
            'evidence': [_row('a.gr', 1), _row('a.gr', 2), _row('b.gr', 3)],
        }], router=ExplodingRouter())
        self.assertEqual(result['items'][0]['clusters'], [])
        self.assertEqual(result['telemetry'][0]['executor'], 'deterministic-preflight')
        self.assertEqual(result['telemetry'][0]['status'], 'safe_hold')

    def test_adapter_drops_two_row_validated_overclaim(self):
        adapted = audit._adapt_result({'clusters': [_decision([0, 1], verdict='validated')]})
        self.assertEqual(adapted['clusters'], [])
        self.assertEqual(adapted['audit_summary'], 'No qualifying cluster returned by local skeptic.')
        self.assertEqual(adapted['rejected_patterns'], [])

    def test_adapter_restores_downstream_metadata_deterministically(self):
        adapted = audit._adapt_result({'clusters': [_decision([0, 1, 2])]})
        self.assertEqual(len(adapted['clusters']), 1)
        self.assertEqual(
            adapted['clusters'][0]['rationale'],
            'Local skeptic decision over bounded supplied evidence indices.',
        )
        self.assertEqual(
            adapted['audit_summary'],
            'Local skeptic evaluated bounded source-diverse consumer evidence.',
        )
        self.assertEqual(adapted['rejected_patterns'], [])

    def test_valid_three_row_compact_decision_passes_full_validation(self):
        adapted = audit._adapt_result({'clusters': [_decision([0, 1, 2])]})
        self.assertEqual(audit._validate_nested(adapted, 3), (True, None))

    def test_invalid_index_still_fails_after_adapter(self):
        adapted = audit._adapt_result({'clusters': [_decision([0, 1, 9])]})
        self.assertEqual(audit._validate_nested(adapted, 3), (False, 'evidence_index_out_of_range'))

    def test_out_of_range_scores_still_fail(self):
        decision = _decision([0, 1, 2])
        decision['audit_score'] = 101
        adapted = audit._adapt_result({'clusters': [decision]})
        self.assertEqual(audit._validate_nested(adapted, 3), (False, 'cluster_score_out_of_range'))

    def test_audit_items_uses_compact_model_then_adapter(self):
        router = StaticRouter({'clusters': [_decision([0, 1, 2])]})
        result = audit.audit_items([{
            'entity_id': 'entity-1', 'category': 'Sports & Outdoors', 'subcategory': 'Camping & Hiking',
            'evidence': [
                _row('e-camping.gr', 1),
                _row('lightgear.gr', 2, family='community_blog'),
                _row('e-camping.gr', 3),
            ],
        }], router=router)
        self.assertEqual(router.calls, 1)
        self.assertEqual(len(result['items'][0]['clusters']), 1)
        self.assertIn('rationale', result['items'][0]['clusters'][0])
        self.assertEqual(result['items'][0]['rejected_patterns'], [])


if __name__ == '__main__':
    unittest.main()
