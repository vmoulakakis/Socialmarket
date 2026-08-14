from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from gateway import call

SEARXNG = os.getenv("SEARXNG_BASE_URL", "http://127.0.0.1:8080").rstrip("/")
USER_AGENT = "SocialMarketMerchantResearch/2.0 (+evidence-first)"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "el-GR,el;q=0.9,en;q=0.8"})

EXCLUDED_OFFICIAL_DOMAINS = {
    "facebook.com", "instagram.com", "linkedin.com", "youtube.com", "tiktok.com",
    "trustpilot.com", "skroutz.gr", "bestprice.gr", "tripadvisor.com", "wikipedia.org",
    "x.com", "twitter.com", "reddit.com", "pinterest.com", "linktr.ee",
}
REVIEW_DOMAINS = {
    "trustpilot.com", "skroutz.gr", "bestprice.gr", "tripadvisor.com", "google.com",
    "play.google.com", "apps.apple.com", "facebook.com",
}
HIGH_CREDIBILITY_HINTS = ("gov.gr", "businessregistry.gr", "eett.gr", "europa.eu", "grhotels.gr")
NEGATIVE_TERMS = (
    "scam", "fraud", "complaint", "complaints", "ripoff", "fake", "not delivered",
    "απάτη", "απατη", "καταγγελία", "καταγγελι", "παράπονα", "παραπονα", "δεν παρέλαβα",
)
GREEK_MARKERS = ("ελλάδα", "αθήνα", "θεσσαλονίκη", "πειραι", "κύπρο", "τηλέφων", "αφμ", "γεμη")

CATEGORY_RULES = [
    ("travel_transport", "Travel / Transport", "travel_service", ("airline", "airlines", "ferry", "ferries", "flight", "hotel", "booking", "travel", "tour", "αεροπορ", "πλοί", "ταξίδ")),
    ("delivery_logistics", "Delivery / Logistics", "logistics_service", ("courier", "delivery", "locker", "parcel", "shipping", "logistics", "μεταφορ", "ταχυμεταφορ")),
    ("insurance_finance", "Insurance / Finance", "financial_service", ("insurance", "ασφάλ", "finance", "loan", "bank", "broker")),
    ("energy_utilities", "Energy / Utilities", "utility_service", ("energy", "ρεύμα", "revma", "electric", "power", "gas", "ενέργ")),
    ("software_digital", "Software / Digital Services", "digital_service", ("vpn", "software", "hosting", "domain", "autodoc", "digital", "app", "cloud")),
    ("books_education", "Books / Education", "retailer", ("book", "books", "βιβλ", "school", "education", "daskaloi", "εκδό")),
    ("beauty_health", "Beauty / Health", "retailer", ("beauty", "cosmetic", "makeup", "skin", "pharm", "medical", "health", "vitamin", "supplement", "φαρμακ", "καλλυν")),
    ("fashion_footwear", "Fashion / Footwear", "retailer", ("fashion", "shoe", "shoes", "dress", "clothing", "lingerie", "wear", "apparel", "ρούχ", "παπού", "footwear")),
    ("jewelry_accessories", "Jewelry / Accessories", "retailer", ("jewel", "gold", "silver", "gem", "watch", "eyewear", "accessoir", "κόσμη", "ρολόι", "γυαλ")),
    ("home_garden", "Home / Garden", "retailer", ("home", "furniture", "carpet", "design", "decor", "garden", "kitchen", "filter", "water", "σπίτι", "έπιπ", "χαλί")),
    ("electronics_tech", "Electronics / Technology", "retailer", ("electro", "battery", "tech", "computer", "mobile", "gadget", "electronics", "device", "ηλεκτρ", "μπαταρ")),
    ("sports_outdoor", "Sports / Outdoor", "retailer", ("sport", "scooter", "fitness", "outdoor", "surf", "tennis", "athl", "ποδήλα", "αθλη")),
    ("toys_kids", "Toys / Kids", "retailer", ("toy", "toys", "baby", "kid", "kids", "child", "παιχν", "βρεφ", "παιδ")),
    ("food_beverage", "Food / Beverage", "retailer", ("food", "coffee", "pizza", "beverage", "wine", "taste", "grocery", "τροφ", "καφέ", "ποτό")),
    ("pets", "Pet Supplies", "retailer", ("pet", "pets", "animal", "σκύλ", "γάτ")),
    ("tickets_entertainment", "Tickets / Entertainment", "ticket_service", ("ticket", "tickets", "event", "football", "fc official store", "εισιτήρ")),
    ("marketplace_general", "Marketplace / General Retail", "marketplace", ("aliexpress", "marketplace", "department store", "eshop", "e-shop", "mall", "general retail")),
]


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def host(url: str | None) -> str | None:
    if not url:
        return None
    try:
        value = urlparse(url).hostname or ""
    except ValueError:
        return None
    value = value.lower().strip(".")
    return value[4:] if value.startswith("www.") else value or None


def root_domain(h: str | None) -> str | None:
    if not h:
        return None
    parts = h.split(".")
    if len(parts) <= 2:
        return h
    if parts[-2:] in (["co", "uk"], ["com", "cy"]):
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def same_domain(a: str | None, b: str | None) -> bool:
    return bool(a and b and root_domain(a) == root_domain(b))


def clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def safe_float(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def search(query: str, limit: int = 8) -> list[dict]:
    last_error = None
    for attempt in range(3):
        try:
            r = SESSION.get(
                f"{SEARXNG}/search",
                params={"q": query, "format": "json", "language": "el-GR", "safesearch": 1},
                timeout=25,
            )
            r.raise_for_status()
            rows = []
            for idx, item in enumerate((r.json().get("results") or [])[:limit], 1):
                url = str(item.get("url") or "").strip()
                if not url:
                    continue
                rows.append({
                    "rank": idx,
                    "url": url,
                    "domain": host(url),
                    "title": str(item.get("title") or "").strip(),
                    "snippet": str(item.get("content") or "").strip(),
                    "engine": str(item.get("engine") or "searxng"),
                    "query": query,
                })
            return rows
        except Exception as exc:
            last_error = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"search_failed:{query}:{last_error}")


def credibility(domain: str | None, official: str | None = None) -> int:
    d = root_domain(domain)
    if official and same_domain(d, official):
        return 1
    if d and any(d.endswith(x) for x in HIGH_CREDIBILITY_HINTS):
        return 1
    if d in REVIEW_DOMAINS:
        return 2
    if d and (d.endswith(".gr") or d.endswith(".eu")):
        return 3
    return 4


def evidence_from_results(results: list[dict], evidence_type: str, official: str | None = None) -> list[dict]:
    now = utcnow()
    out = []
    for item in results:
        out.append({
            "evidence_type": evidence_type,
            "source_name": item.get("engine") or "search",
            "source_url": item["url"],
            "source_domain": item.get("domain"),
            "title": item.get("title"),
            "snippet": item.get("snippet"),
            "credibility_tier": credibility(item.get("domain"), official),
            "confidence": 0.72 if item.get("rank", 99) <= 3 else 0.55,
            "observed_at": now,
            "metadata": {"query": item.get("query"), "serp_rank": item.get("rank")},
        })
    return out


def discover_official(name: str, existing: str | None, brand_results: list[dict]) -> tuple[str | None, float]:
    if existing:
        return root_domain(existing), 0.98
    name_tokens = [t for t in re.findall(r"[a-z0-9α-ω]+", name.lower()) if len(t) >= 3]
    best: tuple[float, str] | None = None
    for item in brand_results[:8]:
        d = root_domain(item.get("domain"))
        if not d or d in EXCLUDED_OFFICIAL_DOMAINS or any(d.endswith("." + x) for x in EXCLUDED_OFFICIAL_DOMAINS):
            continue
        hay = f"{d} {item.get('title','')} {item.get('snippet','')}".lower()
        token_hits = sum(1 for token in name_tokens if token in hay)
        score = 0.32 + min(0.36, token_hits * 0.12)
        if d.endswith(".gr"):
            score += 0.12
        if item.get("rank") == 1:
            score += 0.12
        elif item.get("rank") <= 3:
            score += 0.06
        if "official" in hay or "επίση" in hay:
            score += 0.08
        score = min(score, 0.96)
        if best is None or score > best[0]:
            best = (score, d)
    return (best[1], best[0]) if best else (None, 0.0)


@dataclass
class SiteFacts:
    ok: bool = False
    status: int | None = None
    final_url: str | None = None
    title: str = ""
    description: str = ""
    text: str = ""
    has_canonical: bool = False
    has_schema: bool = False
    has_og: bool = False
    has_h1: bool = False
    robots: bool = False
    sitemap: bool = False


def fetch_site(domain: str | None) -> SiteFacts:
    if not domain:
        return SiteFacts()
    facts = SiteFacts()
    for scheme in ("https", "http"):
        try:
            r = SESSION.get(f"{scheme}://{domain}/", timeout=18, allow_redirects=True)
            facts.status = r.status_code
            facts.final_url = r.url
            if r.status_code >= 400:
                continue
            soup = BeautifulSoup(r.text[:1_500_000], "html.parser")
            facts.ok = True
            facts.title = (soup.title.get_text(" ", strip=True) if soup.title else "")[:500]
            desc = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
            facts.description = str(desc.get("content") or "")[:1000] if desc else ""
            facts.has_canonical = bool(soup.find("link", attrs={"rel": re.compile("canonical", re.I)}))
            facts.has_schema = bool(soup.find("script", attrs={"type": "application/ld+json"}))
            facts.has_og = bool(soup.find("meta", attrs={"property": re.compile("^og:", re.I)}))
            facts.has_h1 = bool(soup.find("h1"))
            facts.text = soup.get_text(" ", strip=True)[:60_000]
            break
        except Exception:
            continue
    if facts.ok:
        for path, attr in (("/robots.txt", "robots"), ("/sitemap.xml", "sitemap")):
            try:
                rr = SESSION.get(f"https://{domain}{path}", timeout=10)
                setattr(facts, attr, rr.status_code < 400 and len(rr.text) > 20)
            except Exception:
                pass
    return facts


def rdap_age_years(domain: str | None) -> float | None:
    if not domain:
        return None
    try:
        r = SESSION.get(f"https://rdap.org/domain/{domain}", timeout=15)
        if r.status_code >= 400:
            return None
        dates = []
        for ev in r.json().get("events") or []:
            if str(ev.get("eventAction") or "").lower() in {"registration", "registered", "creation"}:
                raw = str(ev.get("eventDate") or "")
                try:
                    dates.append(datetime.fromisoformat(raw.replace("Z", "+00:00")))
                except ValueError:
                    pass
        if not dates:
            return None
        years = (datetime.now(timezone.utc) - min(dates)).days / 365.2425
        return round(max(0.0, years), 2)
    except Exception:
        return None


def infer_category(name: str, text: str) -> tuple[str, str, str, float, list[str]]:
    hay = f"{name} {text}".lower()
    scored = []
    for peer, category, merchant_type, words in CATEGORY_RULES:
        hits = sorted({w for w in words if w in hay})
        if hits:
            scored.append((len(hits), peer, category, merchant_type, hits))
    if not scored:
        return "unclassified", "Unclassified", "unknown", 0.30, []
    scored.sort(key=lambda x: (x[0], len(x[4])), reverse=True)
    hits, peer, category, merchant_type, matched = scored[0]
    confidence = min(0.92, 0.52 + hits * 0.10)
    return peer, category, merchant_type, confidence, matched


def parse_review_signals(results: list[dict]) -> tuple[float, float, list[float], list[int]]:
    ratings: list[float] = []
    counts: list[int] = []
    for r in results:
        text = f"{r.get('title','')} {r.get('snippet','')}".replace(",", ".")
        for m in re.finditer(r"(?<!\d)([0-5](?:\.\d{1,2})?)\s*(?:/\s*5|stars?|αστέρ)", text, re.I):
            val = float(m.group(1))
            if 0 <= val <= 5:
                ratings.append(val)
        for m in re.finditer(r"([0-9][0-9., ]{1,10})\s*(?:reviews?|ratings?|κριτικ)", text, re.I):
            digits = re.sub(r"\D", "", m.group(1))
            if digits:
                counts.append(min(int(digits), 10_000_000))
    if ratings:
        reputation = clamp(sum(ratings) / len(ratings) * 20)
    else:
        reputation = 50.0
    footprint = clamp(18 * len({root_domain(r.get('domain')) for r in results if r.get('domain') in REVIEW_DOMAINS}) + 8 * len(ratings) + (math.log10(max(counts) + 1) * 12 if counts else 0))
    return round(reputation, 2), round(footprint, 2), ratings, counts


def complaint_risk(results: list[dict]) -> tuple[float, int]:
    independent = set()
    weighted = 0.0
    for r in results:
        text = f"{r.get('title','')} {r.get('snippet','')}".lower()
        hits = sum(1 for term in NEGATIVE_TERMS if term in text)
        if hits:
            independent.add(root_domain(r.get("domain")) or r.get("url"))
            weighted += min(3, hits) * (1.0 if r.get("rank", 99) <= 3 else 0.6)
    return round(clamp(weighted * 9), 2), len(independent)


def seo_technical(domain: str | None, site: SiteFacts) -> float:
    score = 0.0
    if site.ok:
        score += 15
    if (site.final_url or "").startswith("https://"):
        score += 15
    if site.title:
        score += 12
    if site.description:
        score += 10
    if site.has_canonical:
        score += 10
    if site.has_schema:
        score += 10
    if site.has_og:
        score += 8
    if site.has_h1:
        score += 5
    if site.robots:
        score += 7
    if site.sitemap:
        score += 8
    return round(clamp(score), 2)


def brand_serp_score(brand_results: list[dict], official: str | None) -> float:
    if not official:
        return 20.0
    owned = [r for r in brand_results[:10] if same_domain(r.get("domain"), official)]
    if not owned:
        return 20.0
    best_rank = min(r["rank"] for r in owned)
    rank_component = max(0.0, 100.0 - (best_rank - 1) * 11.0)
    share_component = min(100.0, len(owned) / 3 * 100)
    return round(0.75 * rank_component + 0.25 * share_component, 2)


def organic_visibility(brand_score: float, category_results: list[dict], official: str | None) -> float:
    category_rank = next((r["rank"] for r in category_results if same_domain(r.get("domain"), official)), None)
    category_component = 10.0 if category_rank is None else max(20.0, 100.0 - (category_rank - 1) * 10.0)
    return round(clamp(0.65 * brand_score + 0.35 * category_component), 2)


def competition_score(category_results: list[dict], official: str | None) -> tuple[float, list[dict]]:
    seen = []
    for r in category_results[:10]:
        d = root_domain(r.get("domain"))
        if not d or same_domain(d, official) or d in {"facebook.com", "instagram.com", "youtube.com"}:
            continue
        if d not in [x["domain"] for x in seen]:
            seen.append({"domain": d, "title": r.get("title"), "rank": r.get("rank"), "url": r.get("url")})
    score = clamp(25 + len(seen) * 7.5)
    return round(score, 2), seen[:8]


def greek_market_fit(domain: str | None, site: SiteFacts, results: list[dict]) -> float:
    score = 0.0
    d = domain or ""
    combined = f"{site.title} {site.description} {site.text[:20000]}".lower()
    if d.endswith(".gr"):
        score += 30
    greek_chars = len(re.findall(r"[α-ωάέήίόύώϊϋΐΰ]", combined, re.I))
    if greek_chars > 100:
        score += 25
    elif greek_chars > 20:
        score += 15
    marker_hits = sum(1 for m in GREEK_MARKERS if m in combined)
    score += min(25, marker_hits * 5)
    greek_result_domains = sum(1 for r in results[:10] if str(r.get("domain") or "").endswith(".gr"))
    score += min(20, greek_result_domains * 4)
    return round(clamp(score), 2)


def business_identity(domain: str | None, site: SiteFacts, age: float | None) -> float:
    if not domain:
        return 10.0
    text = f"{site.title} {site.description} {site.text[:30000]}".lower()
    score = 25.0 if site.ok else 10.0
    if domain.endswith(".gr"):
        score += 8
    for marker in ("contact", "επικοινων", "about", "σχετικά", "τηλέφων", "phone", "address", "διεύθυν", "αφμ", "vat", "γεμη", "terms", "όροι"):
        if marker in text:
            score += 4
    if age is not None:
        score += min(15, age)
    return round(clamp(score), 2)


def make_summary(name: str, metrics: dict, category: str, competitors: list[dict]) -> tuple[str, list[str], list[str]]:
    strengths = []
    weaknesses = []
    if metrics["trust_score"] >= 75:
        strengths.append("Strong evidence-backed trust profile")
    elif metrics["trust_score"] < 45:
        weaknesses.append("Weak or insufficient trust signals")
    if metrics["seo_organic_visibility_score"] >= 70:
        strengths.append("Strong search visibility for current evidence set")
    elif metrics["seo_organic_visibility_score"] < 40:
        weaknesses.append("Low observed organic/brand search visibility")
    if metrics["greek_market_fit_score"] >= 70:
        strengths.append("Strong Greece-market relevance signals")
    elif metrics["greek_market_fit_score"] < 40:
        weaknesses.append("Limited Greece-market evidence")
    if metrics["complaint_risk_score"] >= 65:
        weaknesses.append("Material complaint/risk signals require human review")
    if metrics["competition_intensity_score"] <= 45:
        strengths.append("Relatively favorable observed competitive intensity")
    elif metrics["competition_intensity_score"] >= 80:
        weaknesses.append("High observed search competition")
    summary = (
        f"{name} is classified provisionally in {category}. Evidence-backed scores: "
        f"trust {metrics['trust_score']:.1f}/100, SEO visibility {metrics['seo_organic_visibility_score']:.1f}/100, "
        f"competition intensity {metrics['competition_intensity_score']:.1f}/100, Greece-market fit {metrics['greek_market_fit_score']:.1f}/100. "
        f"Commercial program score is {metrics['commercial_score']:.1f}/100. "
        f"The current competitor set contains {len(competitors)} independently observed domains."
    )
    return summary, strengths[:6], weaknesses[:6]


def optional_ai_audit(name: str, evidence: list[dict], metrics: dict, summary: str, strengths: list[str], weaknesses: list[str]) -> tuple[str, list[str], list[str], dict]:
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    enabled = os.getenv("ENABLE_DEEPSEEK_AUDIT", "0") == "1"
    if not api_key or not enabled:
        return summary, strengths, weaknesses, {"ai_auditor": "disabled_or_no_key"}
    compact = [
        {"type": e.get("evidence_type"), "domain": e.get("source_domain"), "title": e.get("title"), "snippet": e.get("snippet"), "tier": e.get("credibility_tier")}
        for e in evidence[:35]
    ]
    prompt = {
        "merchant": name,
        "deterministic_scores": metrics,
        "evidence": compact,
        "instructions": (
            "Act as a skeptical evidence auditor. Do not alter numeric scores and do not add facts absent from evidence. "
            "Return strict JSON with summary (max 110 words), strengths (max 5), weaknesses (max 5), contradictions (max 5). "
            "Explicitly mention uncertainty or contradictory sources."
        ),
    }
    try:
        response = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
                "messages": [{"role": "user", "content": json.dumps(prompt, ensure_ascii=False)}],
            },
            timeout=60,
        )
        response.raise_for_status()
        data = json.loads(response.json()["choices"][0]["message"]["content"])
        return (
            str(data.get("summary") or summary)[:5000],
            [str(x) for x in (data.get("strengths") or strengths)][:6],
            [str(x) for x in (data.get("weaknesses") or weaknesses)][:6],
            {"ai_auditor": "deepseek", "contradictions": data.get("contradictions") or []},
        )
    except Exception as exc:
        return summary, strengths, weaknesses, {"ai_auditor": "failed", "ai_error": str(exc)[:300]}


def research_one(job: dict) -> None:
    job_id = job["job_id"]
    name = job["merchant_name"]
    commercial = job.get("commercial_context") or {}
    commercial_score = safe_float(commercial.get("rank_score"), 50.0) or 50.0

    brand_results = search(f'"{name}" Ελλάδα', 10)
    official, identity_conf = discover_official(name, job.get("official_domain"), brand_results)
    site = fetch_site(official)
    age = rdap_age_years(official)

    context_text = " ".join([name, site.title, site.description, site.text[:25000], " ".join(x.get("title", "") + " " + x.get("snippet", "") for x in brand_results[:8])])
    peer, category, merchant_type, category_conf, category_hints = infer_category(name, context_text)

    review_results = search(f'"{name}" κριτικές reviews', 8)
    risk_results = search(f'"{name}" παράπονα καταγγελίες scam', 7)
    category_results = [] if peer == "unclassified" else search(f'"{category}" Ελλάδα online', 10)

    evidence = []
    evidence.extend(evidence_from_results(brand_results[:8], "brand_serp", official))
    evidence.extend(evidence_from_results(review_results[:7], "review_reputation", official))
    evidence.extend(evidence_from_results(risk_results[:6], "complaint_risk", official))
    evidence.extend(evidence_from_results(category_results[:8], "category_competition", official))
    if official:
        evidence.append({
            "evidence_type": "official_site",
            "source_name": "official_site_probe",
            "source_url": site.final_url or f"https://{official}/",
            "source_domain": official,
            "title": site.title,
            "snippet": site.description,
            "credibility_tier": 1,
            "confidence": identity_conf,
            "observed_at": utcnow(),
            "metadata": {"http_status": site.status, "technical_probe": True},
        })
    if age is not None:
        evidence.append({
            "evidence_type": "domain_registration",
            "source_name": "RDAP",
            "source_url": f"https://rdap.org/domain/{official}",
            "source_domain": "rdap.org",
            "title": f"Domain age: {age} years",
            "snippet": "Registration-age signal from RDAP; not a standalone trust guarantee.",
            "credibility_tier": 2,
            "confidence": 0.88,
            "observed_at": utcnow(),
            "metadata": {"domain_age_years": age},
        })

    review_reputation, review_footprint, ratings, review_counts = parse_review_signals(review_results)
    complaint, negative_sources = complaint_risk(risk_results)
    identity_score = business_identity(official, site, age)
    seo_tech = seo_technical(official, site)
    seo_brand = brand_serp_score(brand_results, official)
    seo_visibility = organic_visibility(seo_brand, category_results, official)
    competition, competitors = competition_score(category_results, official)
    greek_fit = greek_market_fit(official, site, brand_results)
    age_score = 35.0 if age is None else clamp(age / 12.0 * 100)
    trust = clamp(identity_score * 0.35 + review_reputation * 0.30 + review_footprint * 0.10 + (100 - complaint) * 0.15 + age_score * 0.10)
    deep = clamp(trust * 0.30 + seo_visibility * 0.15 + (100 - competition) * 0.15 + greek_fit * 0.20 + commercial_score * 0.20)

    independent_domains = {root_domain(e.get("source_domain")) for e in evidence if e.get("source_domain")}
    confidence = clamp(
        (0.18 if official else 0) +
        (0.12 if site.ok else 0) +
        (0.12 if age is not None else 0) +
        min(0.22, len(independent_domains) * 0.035) +
        (0.12 if review_results else 0) +
        (0.12 if category_results else 0) +
        (0.12 if commercial.get("data_confidence") else 0),
        0, 0.98,
    )

    metrics = {
        "commercial_score": round(commercial_score, 2),
        "business_identity_score": identity_score,
        "review_reputation_score": review_reputation,
        "review_footprint_score": review_footprint,
        "complaint_risk_score": complaint,
        "seo_technical_score": seo_tech,
        "seo_brand_serp_score": seo_brand,
        "seo_organic_visibility_score": seo_visibility,
        "competition_intensity_score": competition,
        "greek_market_fit_score": greek_fit,
        "trust_score": round(trust, 2),
        "deep_research_score": round(deep, 2),
    }
    summary, strengths, weaknesses = make_summary(name, metrics, category, competitors)
    summary, strengths, weaknesses, ai_meta = optional_ai_audit(name, evidence, metrics, summary, strengths, weaknesses)

    call("submit_evidence", p_job_id=job_id, p_items=evidence)
    risk_flag = complaint >= 70 and negative_sources >= 2
    snapshot = {
        "official_domain": official if identity_conf >= 0.65 else None,
        "domain_age_years": age,
        "merchant_type": merchant_type,
        "peer_group": peer,
        "primary_category": category,
        "identity_confidence": round(min(identity_conf, category_conf) if official else category_conf * 0.65, 3),
        **metrics,
        "confidence": round(confidence / 100 if confidence > 1 else confidence, 3),
        "risk_flag": risk_flag,
        "risk_reason": "Multiple independent complaint/risk signals" if risk_flag else None,
        "ai_summary": summary,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "competitors": competitors,
        "category_hints": category_hints,
        "evidence_count": len(evidence),
        "methodology_version": "merchant_research_v2",
        "metadata": {
            "review_ratings_observed": ratings[:10],
            "review_counts_observed": review_counts[:10],
            "negative_independent_sources": negative_sources,
            "category_confidence": category_conf,
            "official_domain_confidence": identity_conf,
            **ai_meta,
        },
    }
    call("complete_research", p_job_id=job_id, p_snapshot=snapshot)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-jobs", type=int, default=int(os.getenv("MERCHANT_RESEARCH_MAX_JOBS", "100")))
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--worker", default=os.getenv("GITHUB_RUN_ID", "local") + "-" + os.getenv("WORKER_SLOT", "0"))
    args = parser.parse_args()

    processed = failed = 0
    while processed + failed < args.max_jobs:
        jobs = call(
            "claim",
            p_worker=args.worker,
            p_job_types=["merchant_deep_research"],
            p_limit=min(args.batch_size, args.max_jobs - processed - failed),
            p_lease_minutes=45,
        ) or []
        if not jobs:
            break
        for job in jobs:
            try:
                research_one(job)
                processed += 1
                print(json.dumps({"merchant": job.get("merchant_name"), "status": "completed"}, ensure_ascii=False), flush=True)
            except Exception as exc:
                failed += 1
                try:
                    call("fail_job", p_job_id=job["job_id"], p_error=str(exc), p_retry_minutes=30)
                except Exception as fail_exc:
                    print(f"failed_to_record_failure:{job.get('merchant_name')}:{fail_exc}", flush=True)
                print(json.dumps({"merchant": job.get("merchant_name"), "status": "failed", "error": str(exc)[:500]}, ensure_ascii=False), flush=True)
        time.sleep(0.35)
    print(json.dumps({"processed": processed, "failed": failed, "worker": args.worker}))
    return 0 if processed or not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
