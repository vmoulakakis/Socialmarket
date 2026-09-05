"""Bounded Greece scarcity evidence for the autonomous Top-100 agent.

Fail closed: an LLM guess or failed search is never proof that a product is absent
from Greece. Greek retail destinations are rejected immediately. International
candidates are searched against indexed results from two major Greek shopping
surfaces (Skroutz and BestPrice). A product is scarcity-eligible only when both
surface-specific searches succeed and neither returns a sufficiently specific
product/model match.

The wording is intentionally conservative: the resulting state means "rare or not
found on the sampled major Greek shopping surfaces", not "provably nonexistent in
all of Greece".
"""
from __future__ import annotations

import html
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Mapping

MARKETS = ("skroutz.gr", "bestprice.gr")
UA = "Mozilla/5.0 (compatible; SocialMarket-GreeceScarcity/2.1; evidence-only)"
STOP = {"και","with","for","the","from","black","white","blue","red","green","small","large","new","professional","portable","electric","machine","tool","home","μαυρο","μαύρο","λευκο","λευκό","ανδρικο","ανδρικό","γυναικειο","γυναικείο","σετ"}


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
        host = urllib.parse.urlparse(target).hostname or urllib.parse.urlparse(tracking).hostname or ""
        return host.lower().removeprefix("www.")
    except Exception:
        return ""


def _signature(name: str, brand: str = "", model: str = "") -> dict[str, Any]:
    tokens = [t for t in _fold(f"{brand} {model} {name}").split() if len(t) >= 4 and t not in STOP]
    modelish = [t for t in tokens if any(ch.isdigit() for ch in t)]
    distinctive: list[str] = []
    for token in modelish + tokens:
        if token not in distinctive:
            distinctive.append(token)
    return {"tokens": distinctive[:10], "modelish": modelish[:5]}


def _match_result(text: str, signature: Mapping[str, Any]) -> bool:
    hay = _fold(text)
    modelish = list(signature.get("modelish") or [])
    tokens = list(signature.get("tokens") or [])
    if modelish:
        return any(t in hay for t in modelish) and sum(1 for t in tokens[:7] if t in hay) >= 2
    # Generic products need a much stronger lexical match so "vacuum machine" or
    # "cutting board" alone does not falsely prove that the exact product exists.
    return len(tokens) >= 5 and sum(1 for t in tokens[:8] if t in hay) >= 5


def _query_text(signature: Mapping[str, Any]) -> str:
    modelish = list(signature.get("modelish") or [])
    tokens = list(signature.get("tokens") or [])
    chosen: list[str] = []
    for token in modelish + tokens:
        if token not in chosen:
            chosen.append(token)
    return " ".join(chosen[:6])


def _bing_rss_probe(market: str, query: str, signature: Mapping[str, Any], timeout: float) -> dict[str, Any]:
    q = f"site:{market} {query}".strip()
    url = "https://www.bing.com/search?format=rss&q=" + urllib.parse.quote_plus(q)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "el-GR,el;q=0.9,en;q=0.6"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read(1_200_000)
            status = int(response.status)
        root = ET.fromstring(raw)
        results=[]
        for item in root.findall('.//item'):
            title=item.findtext('title') or ''
            link=item.findtext('link') or ''
            description=item.findtext('description') or ''
            host=(urllib.parse.urlparse(link).hostname or '').lower().removeprefix('www.')
            if host==market or host.endswith('.'+market):
                results.append({'title':title[:300],'link':link[:900],'description':re.sub('<[^>]+>',' ',description)[:700]})
        matches=[r for r in results if _match_result(f"{r['title']} {r['link']} {r['description']}",signature)]
        return {"source":"bing_rss","market":market,"ok":200<=status<400,"status":status,"result_count":len(results),"match":bool(matches),"matches":matches[:3]}
    except Exception as exc:
        return {"source":"bing_rss","market":market,"ok":False,"status":None,"result_count":0,"match":False,"matches":[],"error":str(exc)[:220]}


def probe_product(row: Mapping[str, Any], timeout: float = 8.0) -> dict[str, Any]:
    name = str(row.get("product_name") or row.get("title") or "").strip()
    brand = str(row.get("brand_name") or "").strip()
    model = str(row.get("model_name") or "").strip()
    domain = _target_domain(row)
    if domain.endswith(".gr") or domain in MARKETS:
        return {"status":"available_greece","eligible":False,"confidence":100,"reason":"affiliate_destination_is_greek_retail_domain","target_domain":domain,"sources_ok":0,"matches":[domain]}
    signature = _signature(name, brand, model)
    if len(signature["tokens"]) < 2:
        return {"status":"unknown","eligible":False,"confidence":0,"reason":"product_identity_too_weak","target_domain":domain,"evidence":[]}
    query=_query_text(signature)
    evidence=[_bing_rss_probe(market,query,signature,timeout) for market in MARKETS]
    ok=[x for x in evidence if x.get('ok')]
    hits=[x['market'] for x in ok if x.get('match')]
    if hits:
        return {"status":"found_major_greek_search","eligible":False,"confidence":92,"reason":"specific_match_found_on_major_greek_shopping_surface","target_domain":domain,"sources_ok":len(ok),"matches":hits,"evidence":evidence}
    covered={str(x.get('market')) for x in ok}
    if covered==set(MARKETS):
        return {"status":"rare_or_not_found_major_greek_search","eligible":True,"confidence":80,"reason":"skroutz_and_bestprice_index_searches_succeeded_without_specific_match","target_domain":domain,"sources_ok":len(ok),"matches":[],"evidence":evidence}
    return {"status":"unknown","eligible":False,"confidence":20,"reason":"insufficient_live_greece_search_evidence","target_domain":domain,"sources_ok":len(ok),"matches":[],"evidence":evidence}


def qualify_rows(rows: list[dict[str, Any]], limit: int = 180, workers: int = 8) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    # Candidate pool is already hard-gated on commission. Preserve its economics
    # ordering if no rank_score exists instead of accidentally randomizing it.
    ordered = sorted(rows, key=lambda r: (float(r.get("rank_score") or 0), float(r.get("expected_commission_eur") or 0)), reverse=True)
    bounded = ordered[:max(1, limit)]
    qualified: list[dict[str, Any]] = []
    stats: dict[str, Any] = {"probed":0,"eligible":0,"available_greece":0,"found_major_greek_search":0,"unknown":0}
    with ThreadPoolExecutor(max_workers=max(1, min(12, workers))) as pool:
        futures = {pool.submit(probe_product, row): row for row in bounded}
        for future in as_completed(futures):
            row = futures[future]
            try:
                scarcity = future.result()
            except Exception as exc:
                scarcity={"status":"unknown","eligible":False,"confidence":0,"reason":"probe_exception","error":str(exc)[:220]}
            stats["probed"] += 1
            status = str(scarcity.get("status") or "unknown")
            stats[status] = stats.get(status, 0) + 1
            updated = dict(row)
            evidence = dict(updated.get("evidence_summary") or {})
            evidence["greece_scarcity"] = scarcity
            updated["evidence_summary"] = evidence
            updated["greece_scarcity_status"] = status
            updated["greece_scarcity_confidence"] = scarcity.get("confidence")
            updated["greece_scarcity_evidence"] = scarcity
            if scarcity.get("eligible"):
                qualified.append(updated)
                stats["eligible"] += 1
    qualified.sort(key=lambda r: float(r.get("expected_commission_eur") or 0), reverse=True)
    return qualified, stats
