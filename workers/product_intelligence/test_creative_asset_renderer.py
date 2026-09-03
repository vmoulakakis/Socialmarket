import io
import unittest
from unittest.mock import patch

from PIL import Image

from creative_asset_renderer import SIZES, render_pack, render_variant


class CreativeAssetRendererTests(unittest.TestCase):
    @staticmethod
    def _pack_row():
        return {
            'affiliate_short_url': 'https://rpfadpdnnxequgvdcfoq.supabase.co/functions/v1/socialscheduler-go/r-test',
            'image_url': 'https://cdn.example/expired.jpg',
            'product_name': 'Test Product',
            'merchant_name': 'Test Merchant',
            'effective_price': 19.90,
            'product_attributes': {
                'extra_images': ['https://cdn.example/working.jpg'],
                'target_url': 'https://shop.example/product',
                'target_domain': 'shop.example',
            },
            'creative_pack': {'variants': [{'id': x} for x in SIZES]},
        }

    def test_render_pack_falls_back_to_feed_extra_image(self):
        row = self._pack_row()
        image = Image.new('RGB', (800, 800), (240, 240, 240))
        with (
            patch('creative_asset_renderer._download_image', side_effect=[ValueError('text/html'), image]) as download,
            patch('creative_asset_renderer.render_variant', return_value=b'png'),
        ):
            rendered = render_pack(row)
        self.assertEqual(len(rendered), 3)
        self.assertEqual(download.call_count, 2)
        self.assertEqual(row['image_url'], 'https://cdn.example/working.jpg')

    def test_render_pack_recovers_from_validated_landing(self):
        row = self._pack_row()
        row['product_attributes']['extra_images'] = []
        image = Image.new('RGB', (800, 800), (240, 240, 240))
        with (
            patch('creative_asset_renderer._download_image', side_effect=[ValueError('text/html'), image]),
            patch('night_brain_gate_tools.recover_image', return_value=(
                'https://shop.example/recovered.jpg',
                {'status': 'recovered', 'source': 'merchant_landing_meta'},
            )),
            patch('creative_asset_renderer.render_variant', return_value=b'png'),
        ):
            rendered = render_pack(row)
        self.assertEqual(len(rendered), 3)
        self.assertEqual(row['image_url'], 'https://shop.example/recovered.jpg')
        self.assertEqual(row['creative_image_recovery']['status'], 'recovered')

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

    def test_visual_contract_json_drives_problem_solver_layout(self):
        source = Image.new('RGB', (900, 900), (230, 230, 230))
        variant = {
            'id': 'square_1x1',
            'visual_contract': {
                'layout': 'problem_solver_large_qr_v1',
                'eyebrow': 'DEALORA AI · SECURITY',
                'pain_headline': 'Θες να βλέπεις τον χώρο σου όπου κι αν είσαι;',
                'solution_line': 'Πρακτική λύση για σπίτι, εξοχικό ή μικρό επαγγελματικό χώρο.',
                'benefits': [
                    'Live εικόνα από κινητό',
                    'Καταγραφή & έλεγχος',
                    'Πιο ήσυχο κεφάλι όταν λείπεις',
                ],
                'cta': 'Σκάναρε για λεπτομέρειες',
                'qr_label': 'ΣΚΑΝΑΡΕ',
                'qr_size_ratio': 0.24,
            },
        }
        raw = render_variant(
            source_image=source,
            variant=variant,
            product_name='CCTV 8 καμερών',
            merchant_name='MagicStore',
            tracking_url='https://example.com/affiliate/exact',
            effective_price=321.30,
        )
        image = Image.open(io.BytesIO(raw))
        self.assertEqual(image.size, SIZES['square_1x1'])
        self.assertGreater(len(raw), 20_000)


if __name__ == '__main__':
    unittest.main()
