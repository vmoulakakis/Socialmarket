from __future__ import annotations

import json
import re
from typing import Any

import requests
from bs4 import BeautifulSoup

from .common import clean_text, stable_hash


UA = "Mozilla/5.0 (compatible; SocialMarketEvidenceBot/1.0; +affiliate-content-evidence)"


def _jsonld_objects(value: Any):
    if isinstance(value, dict):
        yield value
        for v in value.values():
            yield from _jsonld_objects(v)
    elif isinstance(value, list):
        for v in value:
            yield from _jsonld_objects(v)


def enrich_public_landing(url: str, fallback: dict[str, Any]) -> dict[str, Any]:
    facts = {
        "product_name": fallback.get("product_name"),
        "brand": fallback.get("brand_name"),
        "merchant": fallback.get("merchant_name"),
        "price": fallback.get("price"),
        "full_price": fallback.get("full_price"),
        "discount_pct": fallback.get("discount_pct"),
        "currency": fallback.get("currency") or "EUR",
        "availability": fallback.get("availability"),
        "image_url": fallback.get("image_url"),
        "tracking_url": url,
    }
    source_meta: dict[str, Any] = {"method": "product_db_fallback"}
    resolved_url = url
    http_status = None
    try:
        r = requests.get(url, headers={"user-agent": UA, "accept-language": "el,en;q=0.8"}, timeout=25, allow_redirects=True)
        http_status = r.status_code
        resolved_url = r.url
        source_meta["content_type"] = r.headers.get("content-type")
        if r.ok and "html" in (r.headers.get("content-type") or ""):
            soup = BeautifulSoup(r.text[:2_500_000], "html.parser")
            title = clean_text((soup.title.string if soup.title else ""), 300)
            desc = soup.find("meta", attrs={"name": re.compile("description", re.I)})
            og_image = soup.find("meta", attrs={"property": "og:image"})
            if title:
                source_meta["page_title"] = title
            if desc and desc.get("content"):
                source_meta["meta_description"] = clean_text(desc.get("content"), 500)
            if og_image and og_image.get("content"):
                facts["page_image_url"] = og_image.get("content")
            for script in soup.find_all("script", attrs={"type": "application/ld+json"})[:20]:
                try:
                    data = json.loads(script.string or script.get_text() or "null")
                except Exception:
                    continue
                for obj in _jsonld_objects(data):
                    typ = obj.get("@type")
                    types = {str(x).lower() for x in (typ if isinstance(typ, list) else [typ]) if x}
                    if "product" not in types:
                        continue
                    facts["structured_name"] = clean_text(obj.get("name"), 300) or facts.get("product_name")
                    brand = obj.get("brand")
                    if isinstance(brand, dict):
                        brand = brand.get("name")
                    if brand:
                        facts["structured_brand"] = clean_text(brand, 150)
                    offers = obj.get("offers")
                    if isinstance(offers, list):
                        offers = offers[0] if offers else None
                    if isinstance(offers, dict):
                        if offers.get("price") is not None:
                            facts["structured_price"] = offers.get("price")
                        if offers.get("priceCurrency"):
                            facts["structured_currency"] = offers.get("priceCurrency")
                        if offers.get("availability"):
                            facts["structured_availability"] = clean_text(offers.get("availability"), 250)
                    images = obj.get("image")
                    if images:
                        facts["structured_image"] = images[0] if isinstance(images, list) else images
                    source_meta["jsonld_product_found"] = True
                    break
        source_meta["method"] = "public_landing_metadata"
    except Exception as exc:
        source_meta["fetch_error"] = clean_text(exc, 300)

    snapshot = {
        "source_url": url,
        "resolved_url": resolved_url,
        "http_status": http_status,
        "facts": facts,
        "source_meta": source_meta,
    }
    snapshot["content_hash"] = stable_hash(snapshot)
    return snapshot
