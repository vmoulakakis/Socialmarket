import sqlite3
import unittest
from unittest.mock import patch

import night_brain_gate_tools as gates


class NightBrainGateToolsTests(unittest.TestCase):
    def test_tracking_requires_decoded_matching_merchant_domain(self):
        product={
            'tracking_url':'https://go.linkwi.se/z/1-0/ABC/?lnkurl=https%3A%2F%2Fshop.example.gr%2Fp%2F1',
            'target_url':'https://shop.example.gr/p/1',
            'target_domain':'shop.example.gr',
        }
        ok,info=gates.validate_tracking_contract(product,{'official_domain':'example.gr'})
        self.assertTrue(ok)
        self.assertEqual(info['status'],'validated_structural')

        ok,info=gates.validate_tracking_contract(product,{'official_domain':'other.gr'})
        self.assertFalse(ok)
        self.assertEqual(info['reason'],'tracking_destination_merchant_mismatch')

    def test_tracking_missing_destination_is_invalid(self):
        ok,info=gates.validate_tracking_contract(
            {'tracking_url':'https://go.linkwi.se/z/1-0/ABC/'},
            {'official_domain':'example.gr'},
        )
        self.assertFalse(ok)
        self.assertEqual(info['reason'],'tracking_destination_not_decodable')

    def test_agent_floor_can_never_drop_below_ten(self):
        db=sqlite3.connect(':memory:')
        db.execute('create table candidates(expected_commission real)')
        db.executemany('insert into candidates values(?)',[(10.0,),(12.0,),(20.0,)])
        with patch.object(gates.v1,'RUNTIME_CONFIG',{'night_brain':{'commission_gate':{'minimum_pool_after_raise':2}}},create=True):
            result=gates.apply_agent_commission_floor(db,{'effective_floor_eur':3})
        self.assertEqual(result['effective_floor_eur'],10.0)
        self.assertEqual(result['candidate_pool_after_floor'],3)

    def test_high_agent_floor_relaxes_when_candidate_pool_too_small(self):
        db=sqlite3.connect(':memory:')
        db.execute('create table candidates(expected_commission real)')
        db.executemany('insert into candidates values(?)',[(10.0,)]*250+[(30.0,)]*10)
        with patch.object(gates.v1,'RUNTIME_CONFIG',{'night_brain':{'commission_gate':{'minimum_pool_after_raise':200}}},create=True):
            result=gates.apply_agent_commission_floor(db,{'effective_floor_eur':30})
        self.assertEqual(result['effective_floor_eur'],10.0)
        self.assertTrue(result['safety_relaxed_to_eur10'])

    def test_extra_feed_image_recovered_without_network(self):
        with patch('night_brain_gate_tools.urllib.request.urlopen') as urlopen:
            image,info=gates.recover_image({
                'extra_images':['https://cdn.example.gr/p.jpg'],
                'tracking_validation':{'status':'validated_structural'},
                'target_url':'https://example.gr/p/1',
            })
        self.assertEqual(image,'https://cdn.example.gr/p.jpg')
        self.assertEqual(info['source'],'feed_extra_image')
        urlopen.assert_not_called()


if __name__=='__main__':
    unittest.main()
