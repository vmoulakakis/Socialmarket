from workers.product_intelligence.creative_contract_v10 import (
    affiliate_short_url,
    excluded_vertical,
    finalize_creative_rows,
)


def _row(i: int):
    return {
        "source_record_hash": f"{i:064x}",
        "tracking_url": f"https://go.linkwi.se/z/1-1/CD{i}?lnk_source=SocialMarket",
        "product_name": f"Προϊόν {i}",
        "merchant_name": "Κατάστημα",
        "category": "Σχολικά",
        "promotion_angle": "Back to school",
        "creative_pack": {
            "variants": [
                {"id": "feed_4x5", "hook": "Δες την επιλογή", "headline": "Επιλογή", "caption": "Χρήσιμη επιλογή", "hashtags": ["#test tag", "##"]},
                {"id": "reel_9x16", "hook": "Δες την επιλογή", "headline": "Επιλογή", "caption": "Χρήσιμη επιλογή", "hashtags": ["#test tag", "##"]},
                {"id": "square_1x1", "hook": "Δες την επιλογή", "headline": "Επιλογή", "caption": "Χρήσιμη επιλογή", "hashtags": ["#test tag", "##"]},
            ]
        },
    }


def test_excludes_lodging_but_not_physical_travel_goods():
    assert excluded_vertical({"product_name": "Ξενοδοχείο Αθήνα 2 νύχτες"})
    assert excluded_vertical({"category": "Accommodation"})
    assert excluded_vertical({"product_name": "Mountain House Αράχωβα — διανυκτερεύσεις"})
    assert excluded_vertical({"merchant_name": "Ekdromi.gr", "category": "Travel package"})
    assert not excluded_vertical({"product_name": "Travel adapter USB-C", "category": "Ηλεκτρονικά"})
    assert not excluded_vertical({"product_name": "Βαλίτσα καμπίνας", "category": "Αποσκευές"})


def test_short_link_is_stable_and_linkwise_only():
    row = _row(1)
    assert affiliate_short_url(row) == affiliate_short_url(row)
    assert "/socialscheduler-go/r-" in affiliate_short_url(row)


def test_sixty_variants_have_unique_copy_tags_and_exact_short_url():
    rows = finalize_creative_rows([_row(i) for i in range(20)], 20)
    variants = [v for row in rows for v in row["creative_pack"]["variants"]]
    assert len(variants) == 60
    assert len({v["hook"].casefold() for v in variants}) == 60
    assert len({v["caption"].casefold() for v in variants}) == 60
    assert len({tuple(sorted(v["hashtags"])) for v in variants}) == 60
    for row in rows:
        short = row["affiliate_short_url"]
        for variant in row["creative_pack"]["variants"]:
            assert variant["caption"].count(short) == 1
            assert "go.linkwi.se" not in variant["caption"]
            assert variant["qr_spec"]["payload_url"] == short
            assert all(tag.startswith("#") and " " not in tag for tag in variant["hashtags"])
