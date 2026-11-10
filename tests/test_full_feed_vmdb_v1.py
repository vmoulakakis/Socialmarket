import unittest
from workers.product_intelligence.full_feed_vmdb_v1 import (
    program_from_tracking,parse_price,stock_value,transform
)

class FullFeedContractTest(unittest.TestCase):
    def setUp(self):
        self.row={
            'product_id':'350336771_2437', 'product_name':'Γωνιακός καναπές',
            'price':'199.99','currency':'EUR','in_stock':'true',
            'tracking_url':'https://go.linkwi.se/z/23-0/CD104/?lnkurl=https%3A%2F%2Fexample.com'
        }
    def test_route_identity(self):
        self.assertEqual(program_from_tracking(self.row['tracking_url']),'23')
        self.assertIsNone(program_from_tracking('https://other.example/z/23-0/CD104/'))
        self.assertIsNone(program_from_tracking('https://go.linkwi.se/z/23-0/OTHER/'))
    def test_price_and_boolean_are_not_invented(self):
        self.assertEqual(parse_price('1.234,56'),'1234.5600')
        self.assertIsNone(parse_price(None))
        self.assertIsNone(parse_price('-2'))
        self.assertIsNone(stock_value('unknown'))
        self.assertFalse(stock_value('false'))
    def test_identity_stable_when_price_changes(self):
        a=transform(self.row)
        b=transform({**self.row,'price':'149.50'})
        self.assertEqual(a['record_key'],b['record_key'])
        self.assertNotEqual(a['content_sha256'],b['content_sha256'])
        self.assertEqual(a['program_id'],'23')
        self.assertEqual(a['quarantine_reason'],None)
    def test_unknown_terms_and_missing_tracking_quarantined(self):
        b=transform({**self.row,'tracking_url':'','price':'0'})
        self.assertIsNotNone(b['quarantine_reason'])
        self.assertIsNone(b['program_id'])
    def test_full_raw_json_keeps_extra_fields(self):
        b=transform({**self.row,'custom':{'colors':['red','blue']}})
        self.assertEqual(b['raw_json']['custom']['colors'],['red','blue'])

if __name__=='__main__':
    unittest.main()
