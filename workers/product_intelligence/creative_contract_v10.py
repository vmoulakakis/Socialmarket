"""Deterministic v10 publication contract for SocialMarket affiliate creatives."""
from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any, Mapping

SHORT_BASE = "https://rpfadpdnnxequgvdcfoq.supabase.co/functions/v1/socialscheduler-go"
_LINKWISE = re.compile(r"^https://go\.linkwi\.se/", re.I)
_URL = re.compile(r"https?://\S+", re.I)
_HOTEL_TERMS = (
    "hotel", "hotels", "resort", "accommodation", "lodging", "hostel",
    "travel package", "holiday package", "flight", "ferry ticket",
    "ξενοδοχ", "διαμον", "κατάλυμ", "θερετρ", "τουριστικο πακετ",
    "ταξιδιωτικο πακετ", "πτηση", "ακτοπλοϊκ",
)

def _fold(value: Any) -> str:
    raw = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(ch for ch in raw if not unicodedata.combining(ch)).lower()

def excluded_vertical(row: Mapping[str, Any]) -> bool:
    haystack = " ".join(_fold(row.get(k)) for k in (
        "product_name", "category", "subcategory", "program_name", "merchant_name",
    ))
    return any(term in haystack for term in _HOTEL_TERMS)

def affiliate_short_url(row: Mapping[str, Any]) -> str:
    destination = str(row.get("tracking_url") or "").strip()
    if not _LINKWISE.match(destination):
        raise ValueError("real Linkwise tracking URL required")
    identity = f"{row.get('source_record_hash') or ''}|{destination}"
    code = "r-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]
    return f"{SHORT_BASE}/{code}"

def _slug(value: Any, limit: int = 22) -> str:
    value = _fold(value)
    value = re.sub(r"[^0-9a-zα-ω]+", "", value)
    return value[:limit]

def _tags(row: Mapping[str, Any], variant_id: str, existing: Any) -> list[str]:
    clean: list[str] = []
    for value in existing if isinstance(existing, list) else []:
        tag = "#" + _slug(str(value).lstrip("#"), 28)
        if len(tag) > 2 and tag not in clean:
            clean.append(tag)
    unique = hashlib.sha256(
        f"{row.get('source_record_hash')}|{variant_id}".encode("utf-8")
    ).hexdigest()[:8]
    product = _slug(row.get("brand_name") or row.get("product_name")) or "product"
    seasonal = _fold(row.get("promotion_angle"))
    season_tag = (
        "#backtoschool" if any(x in seasonal for x in ("school", "σχολ", "φοιτητ"))
        else "#επιλογηεποχης"
    )
    required = ["#διαφημιση", "#affiliate", f"#{product}", season_tag, f"#sm{unique}"]
    for tag in required:
        if tag not in clean:
            clean.append(tag)
    return clean[:10]

def finalize_creative_rows(rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    seen_hooks: set[str] = set()
    seen_captions: set[str] = set()
    seen_tag_sets: set[tuple[str, ...]] = set()
    for row in rows[:limit]:
        if excluded_vertical(row):
            raise ValueError("excluded_hotel_accommodation_travel_package")
        short = affiliate_short_url(row)
        row["affiliate_short_url"] = short
        pack = row.get("creative_pack") or {}
        variants = pack.get("variants") or []
        if len(variants) != 3:
            raise ValueError("creative pack must have exactly 3 variants")
        for variant in variants:
            variant_id = str(variant.get("id") or "")
            suffix = hashlib.sha256(
                f"{row.get('source_record_hash')}|{variant_id}".encode("utf-8")
            ).hexdigest()[:6]
            hook = str(variant.get("hook") or variant.get("headline") or row.get("product_name") or "").strip()
            if not hook:
                raise ValueError("creative hook required")
            if _fold(hook) in seen_hooks:
                hook = f"{hook} · επιλογή {suffix}"
            seen_hooks.add(_fold(hook))
            caption = _URL.sub("", str(variant.get("caption") or "")).strip()
            caption = re.sub(r"\n{3,}", "\n\n", caption)
            caption = f"{caption}\n\nΔες το προϊόν: {short}\n#διαφήμιση".strip()
            if _fold(caption) in seen_captions:
                caption = f"{caption}\nΚωδικός επιλογής: {suffix}"
            seen_captions.add(_fold(caption))
            tags = _tags(row, variant_id, variant.get("hashtags"))
            tag_key = tuple(sorted(_fold(x) for x in tags))
            if tag_key in seen_tag_sets:
                tags = [x for x in tags if not x.startswith("#sm")] + [f"#sm{suffix}"]
                tag_key = tuple(sorted(_fold(x) for x in tags))
            if tag_key in seen_tag_sets:
                raise ValueError("hashtag_set_collision")
            seen_tag_sets.add(tag_key)
            variant["hook"] = hook
            variant["caption"] = caption
            variant["hashtags"] = tags
            variant["qr_spec"] = {
                "payload_rule": "exact_tracking_url",
                "payload_url": short,
                "placement": "bottom-right",
                "contrast_rule": "high contrast",
                "min_relative_size": "10%",
            }
        pack["affiliate_short_url"] = short
        pack["public_tracking_rule"] = "short_url_redirects_to_exact_linkwise_url"
        row["creative_pack"] = pack
    if len(seen_hooks) != limit * 3 or len(seen_captions) != limit * 3 or len(seen_tag_sets) != limit * 3:
        raise ValueError("batch_wide_creative_uniqueness_failed")
    return rows
