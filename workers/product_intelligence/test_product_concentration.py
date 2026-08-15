import json
import sqlite3
import unittest

from product_safety import candidate_concentration_profile, prune_dynamic_candidate_saturation


class ProductConcentrationPolicyTests(unittest.TestCase):
    def test_high_candidate_share_is_flagged_but_not_deleted(self):
        db = sqlite3.connect(':memory:')
        db.execute('''create table candidates(
          source_hash text primary key, canonical_key text, merchant_id text,
          merchant_name text, competition_score real, payload text,
          expected_commission real, preliminary_score real
        )''')
        for i in range(90):
            db.execute('insert into candidates values(?,?,?,?,?,?,?,?)',(
                f'a{i}',f'ca{i}','merchant-a','Merchant A',50,json.dumps({'i':i}),20,80
            ))
        for i in range(10):
            db.execute('insert into candidates values(?,?,?,?,?,?,?,?)',(
                f'b{i}',f'cb{i}','merchant-b','Merchant B',50,json.dumps({'i':i}),20,70
            ))
        db.commit()

        flags = candidate_concentration_profile(db)
        self.assertTrue(any(x['merchant_id']=='merchant-a' for x in flags))
        removed, compat_flags = prune_dynamic_candidate_saturation(db, {})
        self.assertEqual(removed, 0)
        self.assertEqual(db.execute('select count(*) from candidates').fetchone()[0], 100)
        self.assertTrue(any(x['action']=='diversify_shortlist_not_delete' for x in compat_flags))

    def test_feed_share_is_not_labeled_market_share(self):
        db = sqlite3.connect(':memory:')
        db.execute('''create table candidates(
          source_hash text primary key, canonical_key text, merchant_id text,
          merchant_name text, competition_score real, payload text,
          expected_commission real, preliminary_score real
        )''')
        db.execute('insert into candidates values(?,?,?,?,?,?,?,?)',(
            'x','cx','merchant-x','Merchant X',50,'{}',20,80
        ))
        db.commit()
        flags = candidate_concentration_profile(db)
        self.assertEqual(flags[0]['action'], 'diversify_shortlist_not_delete')


if __name__ == '__main__':
    unittest.main()
