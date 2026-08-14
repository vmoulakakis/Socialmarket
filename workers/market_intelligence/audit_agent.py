from __future__ import annotations

import re
from collections import Counter
from urllib.parse import urlparse


def _domain(url: str | None) -> str:
    if not url:
        return ""
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        return ""


def _clamp(v: float, low: float = 0, high: float = 100) -> float:
    return max(low, min(high, float(v)))


def _tokens(text: str | None) -> list[str]:
    stop = {"shop", "store", "official", "the", "and", "gr", "com", "online", "greece"}
    return [x for x in re.findall(r"[\wΑ-Ωα-ωάέήίόύώϊϋΐΰ]+", (text or "").lower()) if len(x) >= 3 and x not in stop]


def _entity_relevant(e: dict, entity_name: str | None, authoritative_url: str | None) -> bool:
    """Conservative evidence-to-entity binding.

    An exact authoritative domain is always relevant. Multi-token names require all
    significant tokens in the result. Single-token brands are accepted from social
    sources when the token is explicitly present; this prevents generic web pages
    containing an ambiguous word from becoming merchant pain evidence.
    """
    src_domain = _domain(e.get("source_url"))
    auth_domain = _domain(authoritative_url)
    if auth_domain and src_domain == auth_domain:
        return True

    text = " ".join(filter(None, [e.get("title"), e.get("body")])).lower()
    toks = _tokens(entity_name)
    if not toks:
        return False
    if len(toks) >= 2:
        return all(t in text for t in toks)

    token = toks[0]
    platform = str(e.get("platform") or "").lower()
    source_kind = str(e.get("source_kind") or "").lower()
    social = platform in {"instagram", "facebook", "tiktok", "youtube", "reddit"} or source_kind.startswith("social")
    return social and token in text


def audit_research(result: dict, evidence: list[dict], authoritative_url: str | None = None) -> dict:
    reasons: list[str] = []
    contradictions: list[str] = []

    result_domain = _domain(result.get("official_url"))
    auth_domain = _domain(authoritative_url)
    identity_score = 70.0 if result_domain else 25.0
    if auth_domain:
        if result_domain == auth_domain:
            identity_score = 100.0
        elif result_domain:
            identity_score = 5.0
            contradictions.append(f"official_domain_mismatch:{result_domain}!={auth_domain}")
        else:
            identity_score = 40.0
            reasons.append("authoritative_url_exists_but_research_url_missing")

    all_evidence = [e for e in evidence if e.get("source_url") or e.get("body")]
    entity_name = result.get("merchant_name") or result.get("entity_name")
    valid_evidence = [e for e in all_evidence if _entity_relevant(e, entity_name, authoritative_url)]
    relevance_ratio = len(valid_evidence) / max(1, len(all_evidence))

    collectors = {e.get("collector") for e in valid_evidence if e.get("collector")}
    source_kinds = {e.get("source_kind") for e in valid_evidence if e.get("source_kind")}
    platforms = {e.get("platform") for e in valid_evidence if e.get("platform")}
    domains = {_domain(e.get("source_url")) for e in valid_evidence if _domain(e.get("source_url"))}

    quality = _clamp(sum(float(e.get("confidence") or 0) for e in valid_evidence) / max(1, len(valid_evidence)) * 100)
    diversity = _clamp(len(domains) * 7 + len(source_kinds) * 8 + len(collectors) * 7)
    social_score = _clamp(len(platforms) * 18 + sum(1 for e in valid_evidence if str(e.get("source_kind", "")).startswith("social")) * 2)
    relevance_score = _clamp(relevance_ratio * 100)

    category = (result.get("category") or "").strip().lower()
    subcategory = (result.get("subcategory") or "").strip().lower()
    bad_nav = {"home", "about", "contact", "help", "blog", "login", "register", "cart", "βοήθεια", "επικοινωνία", "αρχική"}
    promo_pattern = re.compile(r"(%|κουπ[όο]ν|έκπτωση|εκπτωση|sale|offer|προσφορ|δωρεάν|δωρεαν)", re.I)
    taxonomy_score = 80.0 if category and category != "other" else 35.0
    if subcategory and (subcategory in bad_nav or promo_pattern.search(subcategory)):
        taxonomy_score = 10.0
        contradictions.append(f"non_taxonomy_label_used_as_subcategory:{subcategory[:80]}")
    elif subcategory:
        taxonomy_score = min(100.0, taxonomy_score + 15)

    demand = float(result.get("demand_score") or 0)
    competition = float(result.get("competition_score") or 0)
    pain = float(result.get("pain_gap_score") or 0)

    demand_support = sum(1 for e in valid_evidence if e.get("source_kind") in {"demand", "alternatives", "social_public_observation", "social_comment"})
    comp_support = len({_domain(e.get("source_url")) for e in valid_evidence if e.get("source_kind") in {"demand", "alternatives"} and _domain(e.get("source_url"))})
    pain_support = sum(1 for e in valid_evidence if e.get("source_kind") in {"complaints", "alternatives", "social_comment", "social_public_observation"})

    demand_validation = _clamp(demand_support * 8 + (30 if demand < 80 or demand_support >= 4 else 0))
    competition_validation = _clamp(comp_support * 10)
    if competition == 0 and comp_support > 0:
        contradictions.append("competition_zero_despite_competitor_evidence")
        competition_validation = min(competition_validation, 25)
    pain_validation = _clamp(pain_support * 7 + (20 if pain < 80 or pain_support >= 5 else 0))

    if relevance_score < 35 and len(all_evidence) >= 5:
        contradictions.append("low_entity_relevance_in_evidence_set")

    contradiction_score = _clamp(100 - len(contradictions) * 35)
    overall = _clamp(
        identity_score * 0.20
        + relevance_score * 0.15
        + quality * 0.11
        + diversity * 0.10
        + taxonomy_score * 0.11
        + demand_validation * 0.11
        + competition_validation * 0.10
        + pain_validation * 0.08
        + social_score * 0.04
    )

    if contradictions or identity_score < 50 or overall < 55:
        verdict = "rejected" if identity_score < 20 or overall < 40 else "needs_review"
    elif overall >= 72 and diversity >= 40 and relevance_score >= 60:
        verdict = "validated"
    else:
        verdict = "needs_review"

    if len(valid_evidence) < 5:
        reasons.append("insufficient_relevant_evidence")
    if len(domains) < 3:
        reasons.append("low_source_diversity")
    if not platforms:
        reasons.append("no_social_evidence")

    return {
        "verdict": verdict,
        "overall_score": round(overall, 2),
        "identity_score": round(identity_score, 2),
        "entity_relevance_score": round(relevance_score, 2),
        "relevant_evidence_count": len(valid_evidence),
        "total_evidence_count": len(all_evidence),
        "source_quality_score": round(quality, 2),
        "source_diversity_score": round(diversity, 2),
        "contradiction_score": round(contradiction_score, 2),
        "taxonomy_score": round(taxonomy_score, 2),
        "demand_validation_score": round(demand_validation, 2),
        "competition_validation_score": round(competition_validation, 2),
        "pain_validation_score": round(pain_validation, 2),
        "social_validation_score": round(social_score, 2),
        "reasons": reasons,
        "contradictions": contradictions,
        "source_domains": sorted(domains),
        "platforms": sorted(platforms),
    }


def pain_language(
    evidence: list[dict],
    entity_name: str | None = None,
    authoritative_url: str | None = None,
    limit: int = 30,
) -> list[str]:
    """Extract only entity-bound pain/desire phrases.

    Official-site marketing/policy text is intentionally excluded. Pain candidates
    must come from complaints, alternatives, reviews or public social observations
    and pass the conservative entity relevance gate above.
    """
    allowed = {"complaints", "alternatives", "reviews", "social_comment", "social_public_observation"}
    terms = (
        "πρόβλημα", "παράπονο", "ακριβ", "δεν βρίσκ", "δεν μπορ", "καθυστερ",
        "επιστροφ", "alternative", "too expensive", "problem", "refund", "wish",
        "looking for", "can't find", "doesn't", "missing", "better than",
    )
    rows = []
    for e in evidence:
        if str(e.get("source_kind") or "") not in allowed:
            continue
        if not _entity_relevant(e, entity_name, authoritative_url):
            continue
        text = " ".join(filter(None, [e.get("title"), e.get("body")])).strip()
        if not text:
            continue
        low = text.lower()
        if any(t in low for t in terms):
            rows.append(text[:700])
    counts = Counter(rows)
    return [x for x, _ in counts.most_common(limit)]
