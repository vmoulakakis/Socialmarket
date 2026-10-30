import unittest
from workers.product_intelligence.linkwise_delta_only_v2 import (
    check_feed_url,product_to_row,fingerprint,stream_records,DEFAULT_BATCH,MAX_RECORD_BYTES
)
from workers.product_intelligence.full_feed_vmdb_v1 import program_from_tracking
import io,json

BASE="https://affiliate.linkwi.se/feeds/1.2/CD104/programs-all/columns-product_id,price,tracking_url/incomplete/catinc-1,3/catex-0/proginc-0/progex-0/feed.json"
TRACK="https://go.linkwi.se/z/11532-0/CD104/?lnkurl=https%3A%2F%2Fmerchant.example%2F"
class NewOnlyStreamingTest(unittest.TestCase):
    def test_exact_feed_scope(self):
        self.assertEqual(check_feed_url(BASE),BASE)
        for bad in [
            "https://evil.example/feeds/1.2/CD104/programs-all/columns-x/catinc-1/catex-0/proginc-0/progex-0/feed.json",
            "http://affiliate.linkwi.se/feeds/1.2/CD104/programs-all/columns-x/catinc-1/catex-0/proginc-0/progex-0/feed.json",
            "https://affiliate.linkwi.se/feeds/1.2/NOT-CD104/programs-all/columns-x/catinc-1/catex-0/proginc-0/progex-0/feed.json",
        ]:
            with self.assertRaises(ValueError): check_feed_url(bad)
    def test_record_key_matches_historical_identity(self):
        x={"product_id":"A508","product_name":"Καρέκλα","currency":"EUR",
            "price":"250.00","tracking_url":TRACK,"in_stock":"false",
            "valid_to":"2027-01-02T00:00:00Z","longitude":23.71,"custom":{"k":"v"}}
        a,large=product_to_row(x)
        self.assertFalse(large)
        self.assertEqual(a["record_key"],"11532|A508")
        self.assertEqual(a["program_id"],"11532")
        self.assertEqual(a["raw_json"]["custom"],{"k":"v"})
        self.assertFalse(a["stock_available"])
        self.assertEqual(a["quarantine_reason"],None)
        y,_=product_to_row({**x,"price":"101.00"})
        self.assertEqual(a["record_key"],y["record_key"])
        self.assertNotEqual(a["content_sha256"],y["content_sha256"])
    def test_unknown_deeplinks_unsafe(self):
        self.assertEqual(program_from_tracking(
            "https://go.linkwi.se/z/12858-0/CD104/?lnkurl=https%3A%2F%2F24home.gr"),"12858")
        # A route can be parsed; it does NOT prove it belongs to this merchant.
        bad,_=product_to_row({"product_id":"abc","price":"200","currency":"EUR",
           "tracking_url":"https://merchant.example/"})
        self.assertTrue(bad["quarantine_reason"])
        self.assertEqual(bad["record_key"],"unknown|abc")
    def test_oversize_never_admitted(self):
        x={"product_id":"A","price":"250","currency":"EUR","tracking_url":TRACK,
             "description":"a"*6000}
        a,large=product_to_row(x,max_bytes=4096)
        self.assertTrue(large)
        self.assertEqual(a["raw_json"],{"oversize_omitted":True})
        self.assertIn("oversize_omitted",a["quarantine_reason"])
    def test_snapshot_resume_only_strong_etag(self):
        fp,strong=fingerprint({"ETag":'"abc"',"Content-Length":"500"},BASE)
        self.assertTrue(strong)
        self.assertEqual(len(fp),64)
        weak,ok=fingerprint({"ETag":'W/"abc"'},BASE)
        self.assertFalse(ok)
        self.assertNotEqual(fp,weak)
    def test_streaming_item_json(self):
        raw=json.dumps([{"product_id":"a"},{"product_id":"b"}]).encode()
        records=list(stream_records(io.BytesIO(raw),"item"))
        self.assertEqual(len(records),2)
        self.assertEqual(records[0]["product_id"],"a")
    def test_hard_batch_limit(self):
        self.assertLessEqual(DEFAULT_BATCH,250)
        self.assertLessEqual(MAX_RECORD_BYTES,128*1024)
if __name__=="__main__":
    unittest.main()
