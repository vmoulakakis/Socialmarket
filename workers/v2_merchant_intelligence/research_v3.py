from __future__ import annotations

from urllib.parse import parse_qs, unquote, urlparse

import research as core


# Category classification must reflect what the merchant sells, not incidental footer/navigation words.
# Strong product/service intent terms dominate; generic words such as "delivery" or "accessories"
# can support a category but cannot win on their own against a specific product signal.
WEIGHTED_CATEGORY_RULES = [
    ("travel_transport", "Travel / Transport", "travel_service",
     ("airline", "airlines", "ferry", "ferries", "flight", "flights", "hotel booking", "travel agency", "tour operator", "αεροπορ", "ακτοπλο", "ταξιδιωτικ"),
     ("travel", "booking", "tour", "ταξίδ")),
    ("delivery_logistics", "Delivery / Logistics", "logistics_service",
     ("courier service", "parcel locker", "parcel delivery", "shipping company", "logistics company", "ταχυμεταφορ", "courier", "locker"),
     ("delivery", "shipping", "parcel", "μεταφορ")),
    ("insurance_finance", "Insurance / Finance", "financial_service",
     ("insurance company", "insurance broker", "ασφαλιστικ", "banking", "loan comparison", "financial services"),
     ("insurance", "finance", "loan", "bank", "ασφάλ")),
    ("energy_utilities", "Energy / Utilities", "utility_service",
     ("energy provider", "electricity provider", "natural gas provider", "πάροχος ρεύματος", "πάροχος ενέργειας"),
     ("energy", "electricity", "power", "gas", "ρεύμα", "ενέργ")),
    ("software_digital", "Software / Digital Services", "digital_service",
     ("vpn service", "software platform", "web hosting", "cloud service", "saas", "domain registrar"),
     ("vpn", "software", "hosting", "digital", "cloud", "app")),
    ("books_education", "Books / Education", "retailer",
     ("bookstore", "book shop", "bookseller", "publisher", "school supplies", "βιβλιοπωλ", "εκδόσεις", "σχολικά"),
     ("book", "books", "βιβλ", "education", "school")),
    ("beauty_health", "Beauty / Health", "retailer",
     ("nail products", "nail art", "gel polish", "semi permanent", "manicure", "pedicure", "cosmetics", "makeup", "skin care", "skincare", "pharmacy", "medical supplies", "beauty products", "προϊόντα νυχιών", "ημιμόνιμο", "μανικιούρ", "καλλυντικά", "φαρμακ"),
     ("beauty", "cosmetic", "skin", "health", "medical", "nail", "gel", "makeup")),
    ("fashion_footwear", "Fashion / Footwear", "retailer",
     ("shoe store", "shoes", "footwear", "sneakers", "boots", "sandals", "clothing", "fashion store", "apparel", "παπούτσια", "υποδήματα", "ένδυση", "ρούχα"),
     ("shoe", "fashion", "wear", "dress", "ρούχ", "παπού")),
    ("jewelry_accessories", "Jewelry / Accessories", "retailer",
     ("jewelry", "jewellery", "gold jewelry", "silver jewelry", "necklace", "bracelet", "earrings", "watches", "eyewear", "sunglasses", "κόσμημα", "κοσμήματα", "ρολόγια", "γυαλιά ηλίου"),
     ("jewel", "gold", "silver", "watch", "eyewear", "accessories", "accessoir")),
    ("home_garden", "Home / Garden", "retailer",
     ("furniture", "home furniture", "mattress", "carpet", "home decor", "garden furniture", "kitchenware", "έπιπλα", "στρώματα", "χαλιά", "είδη σπιτιού"),
     ("home", "garden", "decor", "kitchen", "σπίτι", "έπιπ", "χαλί")),
    ("electronics_tech", "Electronics / Technology", "retailer",
     ("electronics store", "consumer electronics", "computer store", "smartphones", "laptops", "mobile phones", "batteries", "ηλεκτρονικά", "υπολογιστές", "κινητά"),
     ("electro", "battery", "tech", "computer", "mobile", "gadget", "device", "ηλεκτρ")),
    ("sports_outdoor", "Sports / Outdoor", "retailer",
     ("sporting goods", "sports equipment", "fitness equipment", "scooters", "bicycles", "outdoor gear", "tennis equipment", "αθλητικά είδη", "ποδήλατα"),
     ("sport", "scooter", "fitness", "outdoor", "surf", "tennis", "athl", "αθλη")),
    ("toys_kids", "Toys / Kids", "retailer",
     ("toy store", "toys", "baby products", "kids products", "children toys", "παιχνίδια", "βρεφικά", "παιδικά είδη"),
     ("toy", "baby", "kid", "child", "παιχν", "βρεφ", "παιδ")),
    ("food_beverage", "Food / Beverage", "retailer",
     ("food store", "grocery", "coffee shop", "coffee beans", "wine shop", "beverages", "restaurant", "pizza", "τρόφιμα", "καφέ", "κρασί"),
     ("food", "coffee", "beverage", "wine", "taste", "τροφ", "ποτό")),
    ("pets", "Pet Supplies", "retailer",
     ("pet shop", "pet supplies", "dog food", "cat food", "είδη κατοικιδίων", "ζωοτροφές"),
     ("pet", "pets", "animal", "σκύλ", "γάτ")),
    ("tickets_entertainment", "Tickets / Entertainment", "ticket_service",
     ("ticket sales", "event tickets", "football tickets", "concert tickets", "εισιτήρια"),
     ("ticket", "tickets", "event", "football", "εισιτήρ")),
    ("marketplace_general", "Marketplace / General Retail", "marketplace",
     ("online marketplace", "department store", "general marketplace", "aliexpress"),
     ("marketplace", "department store", "mall", "general retail", "e-shop", "eshop")),
]


def weighted_infer_category(name: str, text: str):
    hay = f" {name} {text} ".lower()
    scored = []
    for peer, category, merchant_type, strong_terms, weak_terms in WEIGHTED_CATEGORY_RULES:
        strong_hits = sorted({term for term in strong_terms if term in hay})
        weak_hits = sorted({term for term in weak_terms if term in hay})
        # One strong product signal is intentionally worth more than several generic operational words.
        score = len(strong_hits) * 4.0 + len(weak_hits) * 0.75
        if not strong_hits:
            # Generic-only evidence is deliberately capped so "delivery", "accessories", etc. cannot dominate.
            score = min(score, 2.0)
        if score > 0:
            scored.append((score, len(strong_hits), peer, category, merchant_type, strong_hits + weak_hits))
    if not scored:
        return "unclassified", "Unclassified", "unknown", 0.30, []
    scored.sort(key=lambda x: (x[0], x[1], len(x[5])), reverse=True)
    score, strong_count, peer, category, merchant_type, matched = scored[0]
    runner_up = scored[1][0] if len(scored) > 1 else 0.0
    margin = max(0.0, score - runner_up)
    confidence = min(0.96, 0.50 + min(0.28, strong_count * 0.10) + min(0.18, margin * 0.025))
    if strong_count == 0:
        confidence = min(confidence, 0.48)
    return peer, category, merchant_type, confidence, matched[:20]


def _decode_ddg_url(url: str) -> str:
    if url.startswith("//"):
        url = "https:" + url
    try:
        parsed = urlparse(url)
        if "duckduckgo.com" in (parsed.hostname or ""):
            target = parse_qs(parsed.query).get("uddg", [None])[0]
            if target:
                return unquote(target)
    except Exception:
        pass
    return url


def _duckduckgo_html(query: str, limit: int) -> list[dict]:
    response = core.SESSION.get(
        "https://html.duckduckgo.com/html/",
        params={"q": query, "kl": "gr-el", "kp": "1"},
        timeout=30,
    )
    response.raise_for_status()
    soup = core.BeautifulSoup(response.text, "html.parser")
    rows: list[dict] = []
    for block in soup.select(".result"):
        anchor = block.select_one("a.result__a")
        if not anchor:
            continue
        url = _decode_ddg_url(str(anchor.get("href") or "").strip())
        if not url.startswith(("http://", "https://")):
            continue
        snippet_node = block.select_one(".result__snippet")
        rows.append({
            "rank": len(rows) + 1,
            "url": url,
            "domain": core.host(url),
            "title": anchor.get_text(" ", strip=True),
            "snippet": snippet_node.get_text(" ", strip=True) if snippet_node else "",
            "engine": "duckduckgo_html",
            "query": query,
        })
        if len(rows) >= limit:
            break
    return rows


def evidence_search(query: str, limit: int = 8) -> list[dict]:
    errors: list[str] = []
    for language in ("el-GR", "all"):
        try:
            response = core.SESSION.get(
                f"{core.SEARXNG}/search",
                params={"q": query, "format": "json", "language": language, "safesearch": 1},
                timeout=25,
            )
            response.raise_for_status()
            rows: list[dict] = []
            for idx, item in enumerate((response.json().get("results") or [])[:limit], 1):
                url = str(item.get("url") or "").strip()
                if not url:
                    continue
                rows.append({
                    "rank": idx,
                    "url": url,
                    "domain": core.host(url),
                    "title": str(item.get("title") or "").strip(),
                    "snippet": str(item.get("content") or "").strip(),
                    "engine": str(item.get("engine") or "searxng"),
                    "query": query,
                })
            if rows:
                return rows
            errors.append(f"searxng_{language}:0_results")
        except Exception as exc:
            errors.append(f"searxng_{language}:{type(exc).__name__}:{exc}")

    try:
        rows = _duckduckgo_html(query, limit)
        if rows:
            return rows
        errors.append("duckduckgo_html:0_results")
    except Exception as exc:
        errors.append(f"duckduckgo_html:{type(exc).__name__}:{exc}")

    raise RuntimeError("research_search_unavailable:" + " | ".join(errors)[-1400:])


# research_one resolves these names from the module globals at call time.
core.search = evidence_search
core.infer_category = weighted_infer_category

if __name__ == "__main__":
    raise SystemExit(core.main())
