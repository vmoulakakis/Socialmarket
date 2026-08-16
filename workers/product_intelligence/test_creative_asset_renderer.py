import io
import unittest

from PIL import Image

from creative_asset_renderer import SIZES, render_variant


class CreativeAssetRendererTests(unittest.TestCase):
    def test_all_three_variants_render_as_png_at_exact_dimensions(self):
        source = Image.new('RGB', (800, 800), (240, 240, 240))
        for variant_id, expected in SIZES.items():
            variant = {
                'id': variant_id,
                'headline': 'Πραγματικό προϊόν, καθαρό μήνυμα',
                'subheadline': 'Χωρίς εφευρεμένα χαρακτηριστικά',
                'cta': 'Δες το προϊόν',
            }
            raw = render_variant(
                source_image=source,
                variant=variant,
                product_name='Test Product',
                merchant_name='Test Merchant',
                tracking_url='https://example.com/affiliate/exact',
                effective_price=19.90,
            )
            image = Image.open(io.BytesIO(raw))
            self.assertEqual(image.format, 'PNG')
            self.assertEqual(image.size, expected)
            self.assertGreater(len(raw), 10_000)


if __name__ == '__main__':
    unittest.main()
