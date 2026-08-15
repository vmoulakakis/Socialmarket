from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable


def fold(text: str | None) -> str:
    s = unicodedata.normalize("NFKD", str(text or ""))
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).lower()
    return re.sub(r"\s+", " ", s).strip()


# Closed commercial taxonomy. Raw page labels never become taxonomy names directly.
TAXONOMY: dict[str, dict[str, tuple[str, ...]]] = {
    "Fashion & Accessories": {
        "Apparel": ("clothing", "clothes", "apparel", "fashion", "ρουχα", "ενδυ", "μπλουζ", "πουκαμισ", "παντελον", "φορεμ", "ζακετ", "μπουφαν"),
        "Footwear": ("shoe", "shoes", "footwear", "sneaker", "boot", "sandals", "παπουτ", "μποτ", "σανδαλ"),
        "Bags & Luggage": ("bag", "bags", "handbag", "backpack", "luggage", "τσαντ", "βαλιτσ"),
        "Jewelry & Watches": ("jewelry", "jewellery", "watch", "watches", "κοσμη", "ρολογ"),
        "Eyewear & Accessories": ("eyewear", "sunglass", "glasses", "belt", "wallet", "γυαλ", "ζων", "πορτοφολ"),
    },
    "Beauty & Personal Care": {
        "Skincare": ("skincare", "skin care", "serum", "cream", "moistur", "περιποιηση προσωπου", "κρεμα", "ορος"),
        "Sun Care": ("sunscreen", "sun care", "spf", "αντηλια", "ηλιοπροστα"),
        "Makeup": ("makeup", "make-up", "cosmetic", "foundation", "mascara", "lipstick", "μακιγιαζ", "καλλυν"),
        "Hair Care": ("hair care", "shampoo", "conditioner", "hair color", "μαλλι", "σαμπουαν"),
        "Fragrance": ("perfume", "fragrance", "cologne", "αρωμα"),
        "Personal Care": ("personal care", "body care", "deodorant", "oral care", "περιποιηση σωματος", "στοματικ"),
    },
    "Health & Wellness": {
        "Supplements": ("supplement", "vitamin", "protein", "creatine", "συμπληρω", "βιταμιν", "πρωτειν"),
        "Pharmacy & OTC": ("pharmacy", "otc", "medical", "φαρμακ", "παραφαρμακ"),
        "Wellness & Recovery": ("wellness", "massage", "recovery", "orthopedic", "ορθοπεδ", "μασαζ", "αποκατασταση"),
    },
    "Electronics & Technology": {
        "Computers & Laptops": ("computer", "laptop", "notebook", "desktop", "pc", "υπολογισ", "λαπτοπ"),
        "Phones & Accessories": ("smartphone", "mobile phone", "phone case", "charger", "κινητ", "τηλεφων", "φορτιστ"),
        "TV & Audio": ("television", "smart tv", "speaker", "headphone", "audio", "τηλεορα", "ηχει", "ακουστικ"),
        "Gaming": ("gaming", "console", "playstation", "xbox", "nintendo", "gamepad"),
        "Smart Home & Gadgets": ("smart home", "gadget", "wearable", "smartwatch", "camera", "καμερα", "gadget"),
    },
    "Home & Garden": {
        "Furniture": ("furniture", "sofa", "chair", "table", "bed", "επιπλ", "καναπ", "καρεκλ", "κρεβατ"),
        "Home Decor": ("home decor", "decoration", "canvas", "wall art", "διακοσμ", "πινακ", "καμβα"),
        "Kitchen & Dining": ("kitchen", "cookware", "dining", "kitchenware", "κουζιν", "μαγειρ"),
        "Bathroom": ("bathroom", "bath", "towel", "μπανιο", "πετσετ"),
        "Garden & Outdoor Living": ("garden", "outdoor furniture", "patio", "bbq", "κηπ", "βεραντ", "ψησταρ"),
        "Home Appliances": ("appliance", "vacuum", "coffee machine", "air fryer", "συσκευ", "σκουπα", "καφετιερ"),
        "Bedding & Textiles": ("bedding", "mattress", "pillow", "linen", "στρωμα", "μαξιλαρ", "σεντον"),
    },
    "Sports & Outdoors": {
        "Fitness": ("fitness", "gym", "training", "weights", "yoga", "γυμνασ", "βαρη"),
        "Running": ("running", "runner", "trail running", "τρεξιμ"),
        "Cycling": ("cycling", "bicycle", "bike", "ποδηλα"),
        "Camping & Hiking": ("camping", "hiking", "tent", "outdoor", "καμπιν", "πεζοπορ"),
        "Sports Equipment": ("sports equipment", "football", "basketball", "tennis", "αθλητικ", "μπαλα", "τενις"),
    },
    "Kids & Baby": {
        "Baby Care": ("baby care", "diaper", "feeding", "stroller", "βρεφ", "πανα", "καροτσ"),
        "Kids Clothing": ("kids clothing", "children clothing", "παιδικα ρουχα", "παιδικη ενδυση"),
        "Toys & Games": ("toy", "toys", "game", "lego", "παιχνιδ"),
        "School Supplies": ("school supplies", "stationery", "school bag", "pencil", "τετραδι", "σχολικα", "γραφικη υλη", "κασετιν"),
    },
    "Books & Education": {
        "Books": ("book", "books", "βιβλι"),
        "Educational Materials": ("educational", "learning", "study", "school book", "εκπαιδευ", "μαθησιακ", "βοηθημα"),
        "Courses & Training": ("course", "training course", "seminar", "μαθημα", "σεμιναρ", "καταρτιση"),
    },
    "Food & Drink": {
        "Grocery": ("grocery", "food", "supermarket", "τροφ", "παντοπωλ"),
        "Coffee & Tea": ("coffee", "tea", "espresso", "καφε", "τσα"),
        "Wine & Beverages": ("wine", "beer", "beverage", "drink", "κρασι", "ποτο", "ροφημ"),
        "Specialty Food": ("organic food", "delicatessen", "gourmet", "βιολογικ", "delicatessen"),
    },
    "Travel": {
        "Flights": ("flight", "airline", "air ticket", "πτηση", "αεροπορ"),
        "Hotels & Accommodation": ("hotel", "accommodation", "resort", "ξενοδοχ", "διαμον"),
        "Travel Packages & Activities": ("travel package", "tour", "activity", "excursion", "πακετο διακοπων", "εκδρομ"),
        "Car Rental": ("car rental", "rent a car", "ενοικιαση αυτοκινητου"),
    },
    "Automotive": {
        "Car Parts & Accessories": ("car part", "auto part", "accessories", "ανταλλακτικ", "αξεσουαρ αυτοκινητου"),
        "Tyres & Wheels": ("tyre", "tire", "wheel", "ελαστικ", "ζαντ"),
        "Motorcycle": ("motorcycle", "moto", "scooter", "μοτοσυκ", "μηχαν"),
        "Car Care": ("car care", "detailing", "motor oil", "λιπαντικ", "περιποιηση αυτοκινητου"),
    },
    "Pets": {
        "Pet Food": ("pet food", "dog food", "cat food", "τροφη σκυλου", "τροφη γατας", "ζωοτροφ"),
        "Pet Supplies": ("pet supplies", "pet accessories", "litter", "λουρι", "αξεσουαρ κατοικιδ"),
        "Pet Health": ("pet health", "veterinary", "flea", "κτηνιατρ", "αντιπαρασιτ"),
    },
    "Services & Digital": {
        "Software & SaaS": ("software", "saas", "app subscription", "λογισμικ"),
        "Hosting & Domains": ("hosting", "domain", "server", "φιλοξενια ιστοσελιδ"),
        "Finance & Insurance": ("insurance", "finance", "banking", "loan", "ασφαλ", "τραπεζ", "δανει"),
        "Telecom & Utilities": ("telecom", "internet provider", "energy provider", "τηλεπικοινων", "ενεργεια"),
    },
}

CATEGORY_ALIASES = {
    "fashion": "Fashion & Accessories",
    "fashion / footwear": "Fashion & Accessories",
    "beauty": "Beauty & Personal Care",
    "health": "Health & Wellness",
    "electronics": "Electronics & Technology",
    "electronics / technology": "Electronics & Technology",
    "home & garden": "Home & Garden",
    "sports & outdoors": "Sports & Outdoors",
    "sports / outdoor": "Sports & Outdoors",
    "kids & baby": "Kids & Baby",
    "food & drink": "Food & Drink",
    "travel": "Travel",
    "automotive": "Automotive",
    "pets": "Pets",
    "services": "Services & Digital",
}

NAVIGATION_PATTERNS = (
    r"\bskip to\b", r"\bjump to\b", r"\bgo to (main )?content\b", r"\bsign[ -]?up\b", r"\blog[ -]?in\b",
    r"\bregister\b", r"\bmy account\b", r"\blost password\b", r"\bcart\b", r"\bcheckout\b", r"\bcookies?\b",
    r"\bprivacy\b", r"\bterms( of use)?\b", r"\bcompany\b", r"\babout us\b", r"\bcontact\b", r"\bhelp\b",
    r"μεταβαση στο", r"παραλειψη", r"συνδεση", r"εγγραφ", r"λογαριασ", r"καλαθι", r"κωδικ.*προωθητικ",
    r"πολιτικη απορρητου", r"οροι χρησης", r"ποιοι ειμαστε", r"η εταιρεια", r"βοηθεια", r"πληροφορι",
    r"παρακολουθηση παραγγελιας", r"εξελιξη παραγγελιας", r"καταστηματα?", r"κατηγοριες?", r"προιοντα?$",
)
PROMO_PATTERNS = (
    r"\bsale\b", r"\boffers?\b", r"\bdiscount\b", r"\bcoupon\b", r"\bpromo\b", r"%", r"hot\d+",
    r"εκπτω", r"προσφορ", r"κουπον", r"δωρεαν αποστολ", r"δωροεπιταγ",
)
THEME_PATTERNS = (
    r"back[ -]?to[ -]?school", r"black friday", r"cyber monday", r"christmas", r"xmas", r"valentine",
    r"mother.?s day", r"father.?s day", r"summer( favourites?| sales?)?", r"winter sale", r"school season",
    r"χριστουγεν", r"παναγια", r"αγιου βαλεντιν", r"καλοκαιρ", r"επιστροφη στο σχολειο",
)
SERVICE_PATTERNS = (
    r"payment", r"shipping", r"delivery", r"returns?", r"refund", r"warranty", r"track(ing)? order",
    r"πληρωμ", r"αποστολ", r"παραδοση", r"επιστροφ", r"εγγυησ", r"παραγγελι",
)
LANGUAGE_LABELS = {"english", "german", "greek", "francais", "french", "deutsch", "ελληνικα", "αγγλικα", "γερμανικα"}
GREEK_LOCATIONS = {"αθηνα", "θεσσαλονικη", "πατρα", "ηρακλειο", "λαρισα", "βολος", "ιωαννινα", "χαλκιδα", "πειραιας", "ροδος", "κρητη", "κυπρος", "greece", "athens", "thessaloniki"}


def _matches(patterns: Iterable[str], value: str) -> bool:
    return any(re.search(p, value, re.I) for p in patterns)


def _keyword_score(text: str, keywords: Iterable[str]) -> int:
    low = fold(text)
    score = 0
    for kw in keywords:
        k = fold(kw)
        if k and k in low:
            score += 3 if " " in k else 1
    return score


def classify_label(label: str | None) -> dict:
    raw = str(label or "").strip()
    low = fold(raw)
    if not raw or len(low) < 2:
        return {"label": raw, "role": "noise", "confidence": 1.0, "reason": "empty_or_too_short"}
    if low in LANGUAGE_LABELS:
        return {"label": raw, "role": "language", "confidence": 0.99, "reason": "language_switch"}
    if low in GREEK_LOCATIONS:
        return {"label": raw, "role": "location", "confidence": 0.99, "reason": "geo_label"}
    if _matches(NAVIGATION_PATTERNS, low):
        return {"label": raw, "role": "navigation", "confidence": 0.99, "reason": "navigation_or_account_ui"}
    if _matches(SERVICE_PATTERNS, low):
        return {"label": raw, "role": "service_policy", "confidence": 0.95, "reason": "service_or_policy"}
    if _matches(PROMO_PATTERNS, low):
        return {"label": raw, "role": "promotion", "confidence": 0.98, "reason": "campaign_or_offer_label"}
    if _matches(THEME_PATTERNS, low):
        return {"label": raw, "role": "theme", "confidence": 0.98, "reason": "seasonal_or_campaign_theme"}

    scored: list[tuple[int, str, str]] = []
    for category, subs in TAXONOMY.items():
        for subcategory, kws in subs.items():
            s = _keyword_score(low, (*kws, subcategory, category))
            if s:
                scored.append((s, category, subcategory))
    if scored:
        scored.sort(reverse=True)
        s, cat, sub = scored[0]
        return {"label": raw, "role": "product_taxonomy", "category": cat, "subcategory": sub, "confidence": min(0.98, 0.58 + s * 0.08), "reason": "canonical_keyword_match"}

    # Brand heuristic: short title-cased/all-caps multiword labels with no product semantics.
    words = re.findall(r"[A-Za-zΑ-ΩΆΈΉΊΌΎΏα-ωάέήίόύώϊϋΐΰ0-9]+", raw)
    alpha = [w for w in words if any(ch.isalpha() for ch in w)]
    if 1 <= len(alpha) <= 4 and len(raw) <= 45:
        upperish = sum(1 for w in alpha if len(w) > 1 and (w.isupper() or w[:1].isupper()))
        if upperish >= max(1, len(alpha) - 1):
            return {"label": raw, "role": "brand_or_collection", "confidence": 0.72, "reason": "brand_like_without_product_semantics"}

    if re.search(r"\d{1,2}:\d{2}:\d{2}|^\d{1,2}[ηης]?\b", low):
        return {"label": raw, "role": "noise", "confidence": 0.95, "reason": "timestamp_or_counter"}
    if "�" in raw or re.search(r"[ÎÃ]{1,2}[A-Za-zΑ-Ωα-ω]", raw):
        return {"label": raw, "role": "noise", "confidence": 0.9, "reason": "encoding_noise"}
    return {"label": raw, "role": "unknown", "confidence": 0.45, "reason": "no_commercial_taxonomy_evidence"}


@dataclass(frozen=True)
class TaxonomyResolution:
    category: str
    subcategory: str | None
    confidence: float
    source: str
    label_audit: tuple[dict, ...]

    def as_dict(self) -> dict:
        return {
            "category": self.category,
            "subcategory": self.subcategory,
            "confidence": self.confidence,
            "source": self.source,
            "label_audit": list(self.label_audit),
        }


def resolve_taxonomy(
    merchant_name: str,
    corpus: str,
    anchors: Iterable[str],
    existing_category: str | None = None,
    existing_subcategory: str | None = None,
) -> TaxonomyResolution:
    corpus_folded = fold(corpus)
    audits = tuple(classify_label(x) for x in list(anchors)[:120])

    scores: dict[tuple[str, str], float] = {}
    for category, subs in TAXONOMY.items():
        for subcategory, kws in subs.items():
            s = float(_keyword_score(corpus_folded[:180000], (*kws, subcategory, category)))
            # Product-bearing navigation labels are useful evidence only after role classification.
            for a in audits:
                if a.get("role") == "product_taxonomy" and a.get("category") == category and a.get("subcategory") == subcategory:
                    s += 5.0 * float(a.get("confidence") or 0)
            if s > 0:
                scores[(category, subcategory)] = s

    # Existing category is only a prior if it maps to the closed taxonomy.
    prior = CATEGORY_ALIASES.get(fold(existing_category))
    if prior:
        for (cat, sub) in list(scores):
            if cat == prior:
                scores[(cat, sub)] += 2.5
        if not any(cat == prior for cat, _ in scores):
            # Keep category but no fabricated subcategory.
            return TaxonomyResolution(prior, None, 0.60, "existing_category_prior", audits)

    # Existing subcategory must itself classify as product taxonomy.
    old_sub = classify_label(existing_subcategory)
    if old_sub.get("role") == "product_taxonomy":
        key = (old_sub["category"], old_sub["subcategory"])
        scores[key] = scores.get(key, 0.0) + 4.0

    if not scores:
        return TaxonomyResolution("Other", None, 0.25, "no_valid_product_taxonomy_signal", audits)

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    (category, subcategory), best = ranked[0]
    second = ranked[1][1] if len(ranked) > 1 else 0.0
    margin = best - second
    confidence = min(0.97, 0.52 + min(best, 12) * 0.025 + min(max(margin, 0), 8) * 0.02)
    if best < 4:
        # Evidence is too weak for a subcategory; preserve only the category.
        return TaxonomyResolution(category, None, min(confidence, 0.60), "weak_semantic_category_only", audits)
    return TaxonomyResolution(category, subcategory, confidence, "closed_semantic_taxonomy", audits)


def is_valid_taxonomy_label(label: str | None) -> bool:
    return classify_label(label).get("role") == "product_taxonomy"
