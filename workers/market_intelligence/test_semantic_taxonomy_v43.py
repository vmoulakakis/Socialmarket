import unittest

from semantic_taxonomy import resolve_merchant_taxonomy


class MerchantTaxonomyV43Tests(unittest.TestCase):
    def check(self, name, title, description, category, subcategory=None):
        r = resolve_merchant_taxonomy(name, title, description, ())
        self.assertEqual(r.category, category, r.as_dict())
        if subcategory is not None:
            self.assertEqual(r.subcategory, subcategory, r.as_dict())
        self.assertIn('v4.3', r.source)

    def test_croatia_airlines_not_car_rental(self):
        self.check('Croatia Airlines','Croatia Airlines - Book a flight','Explore destinations, book flights and manage your airline booking','Travel','Flights')

    def test_samsonite_not_coffee(self):
        self.check('Samsonite','Samsonite luggage, suitcases & backpacks','Travel bags, luggage, suitcases and backpacks','Fashion & Accessories','Bags & Luggage')

    def test_surfshark_has_real_digital_class(self):
        self.check('Surfshark','Surfshark VPN','VPN, online privacy, cybersecurity, antivirus and identity protection','Services & Digital','Cybersecurity & VPN')

    def test_ferries_have_real_subcategory(self):
        self.check('Ferries-Booking.com','Ferry tickets online','Book ferry tickets and sea travel','Travel','Ferries & Sea Travel')

    def test_jewellery_merchant_name_is_identity_signal(self):
        r=resolve_merchant_taxonomy('Kostis Jewellery','Kostis Jewellery','Jewellery, rings and watches',())
        self.assertEqual(r.category,'Fashion & Accessories')
        self.assertEqual(r.subcategory,'Jewelry & Watches')

    def test_ancillary_anchor_cannot_override_airline_identity(self):
        r=resolve_merchant_taxonomy('Croatia Airlines','Croatia Airlines - Book a flight','Book flights online',['Rent a Car','Hotels','Coffee','Coffee'])
        self.assertEqual((r.category,r.subcategory),('Travel','Flights'),r.as_dict())

    def test_ambiguous_brand_fails_closed(self):
        r=resolve_merchant_taxonomy('Example Brand','','',['Coffee','Shoes'])
        self.assertEqual(r.category,'Other',r.as_dict())


if __name__=='__main__':
    unittest.main()
