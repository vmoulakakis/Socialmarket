"""Bounded Greece scarcity evidence for Affiliate Night Brain.

Fail closed: an LLM guess or failed HTTP request is never proof that a product is
absent from Greece. Greek retail destinations are rejected immediately. For an
international destination, a bounded shortlist is checked against two major Greek
shopping search surfaces and is eligible only when both respond and neither shows
a sufficiently specific product/model match.
"""
from __future__ import annotations

import html
import re
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Mapping

SOURCES = (
    ("skroutz", "https://www.skroutz.gr/search?keyphrase={q}"),
    ("bestprice", "https://www.bestprice.gr/search?q={q}"),
)
UA = "Mozilla/5.0 (compatible; SocialMarket-GreeceScarcity/2.0; evidence-only)"
STOP = {"και","with","for","the","from","black","white","blue","red","green","small","large","μαυρο","μαύρο","λευκο","λευκό","ανδρικο","ανδρικό","γυναικειο","γυναικείο","σετ"}


def _fold(value: Any) -> str:
    text = html.unescape(str(value or "")).casefold()
    text = re.sub(r"[^\w\-]+", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def _target_domain(row: Mapping[str, Any]) -> str:
    attrs = row.get("product_attributes") if isinstance(row.get("product_attributes"), Mapping) else {}
    domain = str((attrs or {}).get("target_domain") or "").strip().lower()
    if domain:
        return domain.removeprefix("www.")
    tracking = str(row.get("tracking_url") or "")
    try:
        parsed = urllib.parse.urlparse(tracking)
        qs = urllib.parse.parse_qs(parsed.query)
        target = (qs.get("lnkurl") or qs.get("url") or [""])[0]
        host = urllib.parse.urlparse(target).hostname or ""
        return host.lower().removeprefix("www.")
    except Exception:
        return ""


def _signature(name: str, brand: str = "", model: str = "") -> dict[str, Any]:
    tokens = [t for t in _fold(f"{brand} {model} {name}").split() if len(t) >= 4 and t not in STOP]
    modelish = [t for t in tokens if any(ch.isdigit() for ch in t)]
    distinctive = []
    for token in modelish + tokens:
        if token not in distinctive:
            distinctive.append(token)
    return {"tokens": distinctive[:10], "modelish": modelish[:5]}


def _match(body: str, signature: Mapping[str, Any]) -> bool:
    text = _fold(body)
    modelish = list(signature.get("modelish") or [])
    tokens = list(signature.get("tokens") or [])
    if modelish:
        return any(t in text for t in modelish) and sum(1 for t in tokens[:6] if t in text) >= 2
    return len(tokens) >= 4 and sum(1 for t in tokens[:7] if t in text) >= 4


def _probe_one(source: str, template: str, query: str, signature: Mapping[str, Any], timeout: float) -> dict[str, Any]:
    url = template.format(q=urllib.parse.quote_plus(query[:160]))
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "el-GR,el;q=0.9,en;q=0.6"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read(900_000).decode("utf-8", errors="ignore")
            ok = 200 <= int(response.status) < 400
            return {"source": source, "ok": ok, "status": int(response.status), "match": bool(ok and _match(body, signature))}
    except Exception as exc:
        return {"source": source, "ok": False, "status": None, "match": False, "error": str(exc)[:180]}


def probe_product(row: Mapping[str, Any], timeout: float = 7.0) -> dict[str, Any]:
    name = str(row.get("product_name") or row.get("title") or "").strip()
    brand = str(row.get("brand_name") or "").strip()
    model = str(row.get("model_name") or "").strip()
    domain = _target_domain(row)
    if domain.endswith(".gr") or domain in {"skroutz.gr", "bestprice.gr"}:
        return {"status":"available_greece","eligible":False,"confidence":100,"reason":"affiliate_destination_is_greek_retail_domain","target_domain":domain,"sources_ok":0,"matches":[domain]}
    signature = _signature(name, brand, model)
    if len(signature["tokens"]) < 2:
        return {"status":"unknown","eligible":False,"confidence":0,"reason":"product_identity_too_weak","target_domain":domain}
    query = " ".join(([brand] if brand else []) + ([model] if model else []) + [name])
    evidence = [_probe_one(source, template, query, signature, timeout) for source, template in SOURCES]
    ok = [x for x in evidence if x.get("ok")]
    hits = [x["source"] for x in ok if x.get("match")]
    if hits:
        return {"status":"found_major_greek_search","eligible":False,"confidence":90,"reason":"specific_match_found","target_domain":domain,"sources_ok":len(ok),"matches":hits,"evidence":evidence}
    if len(ok) >= 2:
        return {"status":"rare_or_not_found_major_greek_search","eligible":True,"confidence":82,"reason":"two_independent_greek_search_surfaces_no_specific_match","target_domain":domain,"sources_ok":len(ok),"matches":[],"evidence":evidence}
    return {"status":"unknown","eligible":False,"confidence":20,"reason":"insufficient_live_greece_search_evidence","target_domain":domain,"sources_ok":len(ok),"matches":[],"evidence":evidence}


def qualify_rows(rows: list[dict[str, Any]], limit: int = 180, workers: int = 8) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    ordered = sorted(rows, key=lambda r: float(r.get("rank_score") or 0), reverse=True)
    bounded = ordered[:max(1, limit)]
    qualified: list[dict[str, Any]] = []
    stats: dict[str, Any] = {"probed":0,"eligible":0,"available_greece":0,"found_major_greek_search":0,"unknown":0}
    with ThreadPoolExecutor(max_workers=max(1, min(12, workers))) as pool:
        futures = {pool.submit(probe_product, row): row for row in bounded}
        for future in as_completed(futures):
            row = futures[future]
            scarcity = future.result()
            stats["probed"] += 1
            status = str(scarcity.get("status") or "unknown")
            stats[status] = stats.get(status, 0) + 1
            updated = dict(row)
            evidence = dict(updated.get("evidence_summary") or {})
            evidence["greece_scarcity"] = scarcity
            updated["evidence_summary"] = evidence
            updated["greece_scarcity_status"] = status
            updated["greece_scarcity_confidence"] = scarcity.get("confidence")
            if scarcity.get("eligible"):
                qualified.append(updated)
                stats["eligible"] += 1
    qualified.sort(key=lambda r: float(r.get("rank_score") or 0), reverse=True)
    return qualified, stats
