import json
import tempfile
import unittest
from pathlib import Path

import linkwise_direct_feed as lf


class LinkwiseShardMergeTests(unittest.TestCase):
    def test_merges_complete_arrays_in_numeric_category_order(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            a=root/'cat-67.json';a.write_text('[{"product_id":"b"}]',encoding='utf-8')
            b=root/'cat-3.json';b.write_text('  [ {"product_id":"a"} ]\n',encoding='utf-8')
            c=root/'cat-25.json';c.write_text('[]',encoding='utf-8')
            out=root/'merged.json'
            total,nonempty=lf._merge_shards([('67',a,a.stat().st_size),('3',b,b.stat().st_size),('25',c,c.stat().st_size)],out)
            self.assertGreater(total,0)
            self.assertEqual(nonempty,2)
            self.assertEqual(json.loads(out.read_text(encoding='utf-8')),[{'product_id':'a'},{'product_id':'b'}])

    def test_rejects_incomplete_shard(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'bad.json';p.write_text('[{"product_id":"x"}',encoding='utf-8')
            with self.assertRaises(RuntimeError):lf._array_body_bounds(p)

    def test_rejects_non_array_root(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'bad.json';p.write_text('{"products":[]}',encoding='utf-8')
            with self.assertRaises(RuntimeError):lf._array_body_bounds(p)


if __name__=='__main__':unittest.main()
