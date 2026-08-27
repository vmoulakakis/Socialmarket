import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse
from urllib import robotparser

import requests
from bs4 import BeautifulSoup
from rapidfuzz.fuzz import token_set_ratio

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "workers" / "market_intelligence"))
from gateway import db_call  # noqa: E402

from agent_runtime import FreeAgentRuntime  # noqa: E402
from model_router import FreeModelRouter  # noqa: E402
from greek_source_policy import annotate_evidence, beacon_policy  # noqa: E402

UA = "SocialMarketOpportunityResearch/2.0 (+evidence-first; respects robots)"
SEARXNG_URL = os.getenv("SEARXNG_URL", "http://127.0.0.1:8080").rstrip("/")
BLOCKED_DOMAINS = {
    "facebook.com", "instagram.com", "linkedin.com", "tiktok.com", "x.com", "twitter.com",
    "pinterest.com", "youtube.com", "youtu.be",
}
DISCOVERY_ONLY_DOMAINS = {"google.com", "bing.com", "duckduckgo.com"}
PAIN_RE = re.compile(
    r"\b(problem|problems|issue|issues|difficult|difficulty|frustrat\w*|annoy\w*|missing|lack\w*|wish\w*|"
    r"too expensive|overpriced|poor quality|doesn.?t work|does not work|cannot|can.?t|hard to|complain\w*|"
    r"πρόβλημ\w*|δυσκολ\w*|ενοχλ\w*|λείπ\w*|ακριβ\w*|κακή ποιότητα|δεν λειτουργ\w*|δεν μπορ\w*|"
    r"θα ήθελ\w*|μακάρι|παράπον\w*)\b",
    re.I,
)
SOLUTION_RE = re.compile(
    r"\b(solution|solves?|fix(?:es|ed)?|designed to|feature|supports?|includes?|alternative|"
    r"λύση|λύν\w*|διορθ\w*|διαθέτ\w*|περιλαμβάν\w*|χαρακτηριστικ\w*)\b",
    re.I,
)
COMMERCIAL_RE = re.compile(r"\b(price|cost|buy|purchase|worth|value|cheap|expensive|τιμή|κόστος|αγορά|αξίζει|φθην|ακριβ)\w*\b", re.I)


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def clamp(v, lo=0.0, hi=100.0):
    return max(lo, min(hi, float(v)))


def h(text: str):
    return hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()


def norm(text: str):
    text = re.sub(r"https?://\S+", " ", str(text or "").lower())
    text = re.sub(r"[^\w\sα-ωάέήίόύώϊϋΐΰ-]", " ", text, flags=re.I)
    return re.sub(r"\s+", " ", text).strip()[:700]


def domain(url: str):
    try:
        host = (urlparse(url).hostname or "").lower().removeprefix("www.")
        return host
    except Exception:
        return ""


def post_one(table: str, data: dict):
    out = db_call("POST", table, data=data, prefer="return=representation") or []
    return out[0] if isinstance(out, list) and out else out


def patch(table: str, filters: dict[str, str], data: dict):
    return db_call("PATCH", table, params=filters, data=data, prefer="return=minimal")


def get(table: str, params: dict[str, str]):
    return db_call("GET", table, params=params) or []


def audit(run_id, event_type, payload, *, actor="supervisor", entity_type=None, entity_id=None, severity="info", evidence_refs=None):
    post_one("audit_events", {
        "intelligence_run_id": run_id,
        "event_type": event_type,
        "actor_type": "agent",
        "actor_key": actor,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "severity": severity,
        "payload": payload,
        "evidence_refs": evidence_refs or [],
    })


def start_stage(run_id, name, agent, mode="deterministic"):
    return post_one("intelligence_stage_runs", {
        "run_id": run_id, "stage_name": name, "agent_name": agent,
        "status": "running", "execution_mode": mode, "started_at": now(),
    })


def finish_stage(stage, *, output_count=0, confidence=None, metrics=None, status="completed", error=None):
    patch("intelligence_stage_runs", {"id": f"eq.{stage['id']}"}, {
        "status": status, "output_count": int(output_count), "confidence": confidence,
        "metrics": metrics or {}, "error": error, "finished_at": now(),
    })


def log_model_usage(run_id, telemetry, task_type):
    if not telemetry:
        return
    post_one("model_usage_events", {
        "route": telemetry.get("route", "github_models_free"),
        "provider": "github",
        "model_name": telemetry.get("model"),
        "input_tokens": int(telemetry.get("input_tokens") or 0),
        "output_tokens": int(telemetry.get("output_tokens") or 0),
        "cost_usd": 0,
    })
    audit(run_id, "free_model_call", {"task_type": task_type, **telemetry}, actor="model-router")


def searx(query: str, limit=8):
    try:
        r = requests.get(f"{SEARXNG_URL}/search", params={"q": query, "format": "json", "language": "all", "safesearch": 1}, timeout=25)
        r.raise_for_status()
        rows = r.json().get("results") or []
        out = []
        for x in rows[:limit]:
            u = str(x.get("url") or "")
            d = domain(u)
            if not u.startswith(("http://", "https://")) or not d:
                continue
            out.append({"url": u, "domain": d, "title": str(x.get("title") or "")[:500], "snippet": str(x.get("content") or "")[:1200]})
        return out
    except Exception:
        return []


def robots_allowed(url: str):
    d = domain(url)
    if not d:
        return False
    if any(d == b or d.endswith("." + b) for b in BLOCKED_DOMAINS):
        return False
    try:
        parsed = urlparse(url)
        rp = robotparser.RobotFileParser()
        rp.set_url(f"{parsed.scheme}://{parsed.netloc}/robots.txt")
        rp.read()
        return rp.can_fetch(UA, url)
    except Exception:
        # A failed robots fetch is not treated as a permission grant for known
        # restricted social platforms (already blocked above). For ordinary
        # sites we make one low-rate GET and still respect server errors.
        return True


def fetch_page(url: str):
    if not robots_allowed(url):
        return None
    try:
        r = requests.get(url, headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml"}, timeout=18, allow_redirects=True)
        if r.status_code != 200:
            return None
        ctype = (r.headers.get("content-type") or "").lower()
        if "html" not in ctype:
            return None
        soup = BeautifulSoup(r.text[:2_000_000], "html.parser")
        for tag in soup(["script", "style", "noscript", "svg", "nav", "footer"]):
            tag.decompose()
        title = soup.title.get_text(" ", strip=True)[:500] if soup.title else ""
        text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))
        return {"url": str(r.url), "domain": domain(str(r.url)), "title": title, "text": text[:40_000]}
    except Exception:
        return None


def sentences(text: str):
    parts = re.split(r"(?<=[.!?;·])\s+|\n+", text or "")
    return [re.sub(r"\s+", " ", p).strip() for p in parts if 35 <= len(p.strip()) <= 650]


def pain_severity(statement: str):
    s = statement.lower()
    score = 45
    for word, add in [("cannot", 18), ("can't", 18), ("doesn't work", 20), ("problem", 10), ("frustr", 13), ("too expensive", 10), ("δεν μπορ", 18), ("δεν λειτουργ", 20), ("πρόβλημ", 10), ("δυσκολ", 12)]:
        if word in s:
            score += add
    return clamp(score)


def create_doc(run_id, page, metadata=None):
    clean = page["text"][:20_000]
    source_metadata = dict(metadata or {})
    if policy := beacon_policy(page["domain"]):
        source_metadata.update(policy)
        source_metadata["role_semantics"] = "Demand beacon only; excluded from competitor classification."
    return post_one("research_documents", {
        "intelligence_run_id": run_id,
        "canonical_url": page["url"],
        "source_domain": page["domain"],
        "document_type": "web_page",
        "title": page["title"],
        "raw_text": clean,
        "clean_text": clean,
        "content_hash": h(clean),
        "credibility_tier": 3,
        "extraction_method": "deterministic_html",
        "status": "parsed",
        "metadata": source_metadata,
    })


def create_evidence(run_id, doc, statement, relation="support", evidence_type="voice_of_customer"):
    doc_metadata = dict((doc or {}).get("metadata") or {})
    row = annotate_evidence({"source_url": (doc or {}).get("canonical_url"), "source_kind": "pain_candidate", "metadata": {"consumer_text": evidence_type == "voice_of_customer", "source_family": doc_metadata.get("source_family") or "public_web"}})
    return post_one("evidence_items", {
        "intelligence_run_id": run_id,
        "document_id": doc["id"] if doc else None,
        "evidence_type": evidence_type,
        "statement": statement[:1800],
        "normalized_statement": norm(statement),
        "relation": relation,
        "severity_score": pain_severity(statement) if relation == "support" else 50,
        "relevance_score": 75,
        "credibility_score": 65,
        "confidence": 0.68,
        "source_independence_key": doc.get("source_domain") if doc else None,
        "extraction_mode": "deterministic",
        "quote_hash": h(statement),
        "metadata": {"untrusted_external_content": True, **row["metadata"]},
    })


def load_products(max_products):
    rows = get("products", {
        "select": "id,product_name,description,category_raw,brand_name,merchant_name,price,full_price,times_bought,tracking_url,availability,in_stock,merchant_trust_score",
        "market_eligible": "eq.true", "is_active": "eq.true",
        "order": "times_bought.desc.nullslast,price.desc.nullslast", "limit": str(max_products),
    })
    if not rows:
        rows = get("products", {
            "select": "id,product_name,description,category_raw,brand_name,merchant_name,price,full_price,times_bought,tracking_url,availability,in_stock,merchant_trust_score",
            "is_active": "eq.true", "order": "times_bought.desc.nullslast", "limit": str(max_products),
        })
    return rows


def discover_market_queries(products, cap):
    queries = []
    seen = set()
    for p in products:
        name = re.sub(r"\s+", " ", str(p.get("product_name") or "")).strip()[:120]
        brand = str(p.get("brand_name") or "").strip()[:70]
        if not name:
            continue
        for q in [
            f'"{name}" problems review',
            f'"{name}" complaints issues',
            f'"{name}" alternatives competitors',
            f'"{name}" προβλήματα κριτικές',
            f'{brand} {name} drawbacks' if brand else "",
        ]:
            if q and q not in seen:
                seen.add(q); queries.append(q)
            if len(queries) >= cap:
                return queries
    return queries


def competitor_candidates(results, products, agent_runtime, run_id):
    domains = Counter(r["domain"] for r in results if r.get("domain") and r["domain"] not in DISCOVERY_ONLY_DOMAINS)
    candidates = [{"domain": d, "frequency": c} for d, c in domains.most_common(20)]
    if not candidates:
        return []
    payload = {
        "market_products": [{"name": p.get("product_name"), "brand": p.get("brand_name")} for p in products[:8]],
        "candidate_domains": candidates,
        "task": "Identify only domains that are plausibly product/service competitors or substitute sellers. Exclude search engines, news, forums, review sites, social networks and generic publishers. Return competitors:[{domain,name,confidence}].",
    }
    parsed, telemetry = agent_runtime.run_json("Competitor Intelligence Agent", "Classify candidate domains conservatively using only the supplied metadata.", payload)
    log_model_usage(run_id, telemetry, "competitor_classification")
    if parsed and isinstance(parsed.get("competitors"), list):
        valid = []
        allowed_domains = {x["domain"] for x in candidates}
        for x in parsed["competitors"][:10]:
            d = str(x.get("domain") or "").lower().removeprefix("www.")
            if d in allowed_domains and float(x.get("confidence") or 0) >= 0.55:
                valid.append({"domain": d, "name": str(x.get("name") or d)[:200], "confidence": float(x.get("confidence") or 0)})
        if valid:
            return valid
    # Conservative deterministic fallback: only domains occurring in multiple
    # independent alternative/competitor searches; do not call them validated.
    return [{"domain": d, "name": d, "confidence": 0.45} for d, c in domains.most_common(8) if c >= 2]


def get_or_create_competitor(c):
    key = re.sub(r"[^a-z0-9.-]", "", c["domain"].lower())
    found = get("competitors", {"competitor_key": f"eq.{key}", "select": "id,competitor_key,name,official_domain", "limit": "1"})
    if found:
        return found[0]
    try:
        return post_one("competitors", {
            "competitor_key": key, "name": c.get("name") or key, "official_domain": c["domain"],
            "competitor_type": "indirect", "market_scope": "GR", "metadata": {"discovery_confidence": c.get("confidence")},
        })
    except Exception:
        found = get("competitors", {"competitor_key": f"eq.{key}", "select": "id,competitor_key,name,official_domain", "limit": "1"})
        return found[0] if found else None


def group_pains(evidence_rows, agent_runtime, run_id):
    groups = []
    for ev in evidence_rows:
        text = ev.get("normalized_statement") or norm(ev.get("statement") or "")
        best = None; best_score = 0
        for g in groups:
            sc = token_set_ratio(text, g["representative"])
            if sc > best_score:
                best, best_score = g, sc
        if best is not None and best_score >= 72:
            best["items"].append(ev)
            if len(text) < len(best["representative"]):
                best["representative"] = text
        else:
            groups.append({"representative": text, "items": [ev]})

    groups.sort(key=lambda g: len(g["items"]), reverse=True)
    groups = groups[:12]
    payload = {
        "clusters": [{"index": i, "representative": g["representative"], "count": len(g["items"])} for i, g in enumerate(groups)],
        "task": "For each cluster, give a concise neutral customer pain label (max 14 words), pain_type, and target_segment only when inferable. Do not add facts. Return labels:[{index,label,pain_type,target_segment}].",
    }
    parsed, telemetry = agent_runtime.run_json("Pain Mining Agent", "Normalize already-clustered customer pain statements without changing their meaning.", payload)
    log_model_usage(run_id, telemetry, "pain_normalization")
    labels = {}
    if parsed and isinstance(parsed.get("labels"), list):
        for x in parsed["labels"]:
            try: labels[int(x["index"])] = x
            except Exception: pass
    for i, g in enumerate(groups):
        label = labels.get(i, {}).get("label") or g["representative"][:180]
        g["label"] = str(label)[:220]
        g["pain_type"] = str(labels.get(i, {}).get("pain_type") or "friction")[:80]
        g["target_segment"] = str(labels.get(i, {}).get("target_segment") or "")[:200] or None
    return groups


def create_pain(run_id, group):
    items = group["items"]
    sources = {x.get("source_independence_key") for x in items if x.get("source_independence_key")}
    count = len(items)
    avg_sev = sum(float(x.get("severity_score") or 0) for x in items) / max(1, count)
    commercial = sum(1 for x in items if COMMERCIAL_RE.search(str(x.get("statement") or "")))
    data = {
        "intelligence_run_id": run_id,
        "pain_key": h(group["label"] + "|" + str(group.get("target_segment")))[:32],
        "label": group["label"], "description": group["representative"][:1200],
        "target_segment": group.get("target_segment"), "pain_type": group.get("pain_type"),
        "frequency_score": clamp(count * 12), "severity_score": clamp(avg_sev),
        "recency_score": 80, "source_diversity_score": clamp(len(sources) * 30),
        "commercial_intent_score": clamp((commercial / max(1, count)) * 100),
        "competitor_weakness_score": 50, "evidence_quality_score": 65,
        "contradiction_penalty": 0, "evidence_count": count,
        "independent_source_count": len(sources), "contradiction_count": 0,
        "confidence": min(0.98, 0.25 + len(sources) * 0.15 + count * 0.03),
        "rationale": {"method": "rule_extract+rapidfuzz_cluster+optional_free_agent_label", "source_domains": sorted(sources)},
    }
    pain = post_one("pain_candidates", data)
    for ev in items:
        post_one("pain_evidence_links", {"pain_id": pain["id"], "evidence_id": ev["id"], "relation": "support", "weight": 1})
    db_call("POST", "rpc/refresh_pain_candidate_score", data={"p_pain_id": pain["id"]})
    fresh = get("pain_candidates", {"id": f"eq.{pain['id']}", "select": "*", "limit": "1"})
    return fresh[0] if fresh else pain


def contradiction_check(run_id, pain, max_pages=2):
    query = f'"{pain["label"][:120]}" solution alternative solved'
    rows = searx(query, limit=6)
    contradict = []
    for r in rows:
        if len(contradict) >= max_pages:
            break
        p = fetch_page(r["url"])
        if not p or not SOLUTION_RE.search(p["text"]):
            continue
        # Require at least one meaningful token from the pain label in page text.
        keys = [x for x in norm(pain["label"]).split() if len(x) >= 5][:8]
        if keys and not any(k in p["text"].lower() for k in keys):
            continue
        doc = create_doc(run_id, p, {"research_role": "contradiction_search", "pain_id": pain["id"]})
        st = next((s for s in sentences(p["text"]) if SOLUTION_RE.search(s) and any(k in s.lower() for k in keys)), None)
        if not st:
            continue
        ev = create_evidence(run_id, doc, st, relation="contradict", evidence_type="solution_counterevidence")
        post_one("pain_evidence_links", {"pain_id": pain["id"], "evidence_id": ev["id"], "relation": "contradict", "weight": 1})
        contradict.append(ev)
    if contradict:
        penalty = clamp(len(contradict) * 8, 0, 30)
        patch("pain_candidates", {"id": f"eq.{pain['id']}"}, {"contradiction_count": len(contradict), "contradiction_penalty": penalty})
        db_call("POST", "rpc/refresh_pain_candidate_score", data={"p_pain_id": pain["id"]})
    fresh = get("pain_candidates", {"id": f"eq.{pain['id']}", "select": "*", "limit": "1"})
    return fresh[0] if fresh else pain, contradict


def create_gap(run_id, pain, competitors, products):
    product_scores = []
    for p in products:
        text = f"{p.get('product_name','')} {p.get('description','')}"
        product_scores.append(token_set_ratio(pain["label"], text))
    fit_count = sum(1 for s in product_scores if s >= 45)
    prices = [float(p["price"]) for p in products if p.get("price") not in (None, "")]
    median_price = sorted(prices)[len(prices)//2] if prices else 0
    contradiction_count = int(pain.get("contradiction_count") or 0)
    comp_count = len(competitors)
    gap = post_one("gap_candidates", {
        "intelligence_run_id": run_id, "pain_id": pain["id"],
        "gap_key": h("gap|" + pain["pain_key"])[:32],
        "title": f"Underserved: {pain['label']}"[:250], "description": pain.get("description"),
        "gap_type": "feature", "target_segment": pain.get("target_segment"),
        "demand_score": clamp(pain.get("pain_score") or 0),
        "pain_confidence_score": clamp(float(pain.get("confidence") or 0) * 100),
        "competitor_weakness_score": clamp(80 - contradiction_count * 15),
        "solution_scarcity_score": clamp(100 - contradiction_count * 25),
        "willingness_to_pay_score": 75 if median_price >= 150 else (60 if median_price >= 80 else 45),
        "feasibility_score": clamp(35 + fit_count * 12),
        "source_diversity_score": clamp(int(pain.get("independent_source_count") or 0) * 30),
        "evidence_quality_score": float(pain.get("evidence_quality_score") or 60),
        "contradiction_penalty": clamp(contradiction_count * 8, 0, 30),
        "competitor_count": comp_count, "evidence_count": int(pain.get("evidence_count") or 0),
        "contradiction_count": contradiction_count,
        "confidence": float(pain.get("confidence") or 0) * min(1, 0.55 + comp_count * 0.1),
        "solution_requirements": {"must_address_pain": pain["label"], "evidence_backed": True},
        "explanation": {"method": "deterministic_gap_formula", "internal_fit_candidates": fit_count, "median_internal_price": median_price},
    })
    support = get("pain_evidence_links", {"pain_id": f"eq.{pain['id']}", "select": "evidence_id,relation", "limit": "100"})
    for link in support:
        post_one("gap_evidence_links", {"gap_id": gap["id"], "evidence_id": link["evidence_id"], "relation": link["relation"] if link["relation"] in ("support","contradict") else "context", "weight": 1})
    for c in competitors:
        post_one("gap_competitor_coverage", {
            "gap_id": gap["id"], "competitor_id": c["id"],
            "coverage_score": clamp(20 + contradiction_count * 12),
            "weakness_score": clamp(80 - contradiction_count * 12),
            "evidence_count": contradiction_count,
            "rationale": {"method": "bounded_counterevidence_proxy", "requires_deeper_competitor_audit": True},
        })
    db_call("POST", "rpc/refresh_gap_candidate_score", data={"p_gap_id": gap["id"]})
    fresh = get("gap_candidates", {"id": f"eq.{gap['id']}", "select": "*", "limit": "1"})
    return fresh[0] if fresh else gap


def match_products(gap, pain, products):
    matches = []
    for p in products:
        corpus = f"{p.get('product_name','')} {p.get('description','')} {p.get('brand_name','')}"
        semantic = float(token_set_ratio(pain["label"], corpus))
        requirement = semantic
        price = float(p.get("price") or 0)
        price_fit = 75 if price > 0 else 40
        avail_fit = 90 if p.get("in_stock") is not False else 20
        trust = float(p.get("merchant_trust_score") or 50)
        differentiation = clamp(45 + semantic * 0.35)
        overall = clamp(requirement * .35 + semantic * .20 + price_fit * .10 + avail_fit * .10 + trust * .10 + differentiation * .15)
        if overall < 45:
            continue
        status = "recommended" if gap.get("status") in ("validated","strong_gap","exceptional") and overall >= 65 else "candidate"
        row = post_one("product_gap_matches", {
            "gap_id": gap["id"], "product_id": p["id"],
            "requirement_match_score": requirement, "semantic_fit_score": semantic,
            "evidence_fit_score": float(pain.get("pain_score") or 0), "price_fit_score": price_fit,
            "availability_fit_score": avail_fit, "merchant_trust_score": trust,
            "differentiation_score": differentiation, "contradiction_penalty": float(gap.get("contradiction_penalty") or 0),
            "overall_fit_score": overall, "confidence": min(0.95, float(gap.get("confidence") or 0) * (overall / 100)),
            "status": status,
            "why_fit": {"pain": pain["label"], "deterministic_lexical_fit": round(semantic, 2), "note": "candidate until vector/feature validation passes"},
            "blockers": [] if status == "recommended" else ["gap_not_fully_validated_or_fit_below_recommendation_gate"],
            "evidence_refs": [],
        })
        matches.append(row)
    matches.sort(key=lambda x: float(x.get("overall_fit_score") or 0), reverse=True)
    for rank, m in enumerate(matches, 1):
        patch("product_gap_matches", {"id": f"eq.{m['id']}"}, {"rank": rank})
    return matches


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", default="GR")
    ap.add_argument("--max-products", type=int, default=12)
    ap.add_argument("--max-searches", type=int, default=24)
    ap.add_argument("--free-model-calls", type=int, default=8)
    args = ap.parse_args()

    router = FreeModelRouter(max_calls=args.free_model_calls)
    agents = FreeAgentRuntime(router)
    run = post_one("intelligence_runs", {
        "run_type": "market_gap_discovery", "scope_type": "market", "scope_key": args.scope,
        "country_code": args.scope, "status": "running", "started_at": now(),
        "config": {"max_products": args.max_products, "max_searches": args.max_searches, "free_model_calls": args.free_model_calls,
                   "paid_remote": False, "evidence_first": True, "pipeline_version": "agentic-gap-v2"},
    })
    run_id = run["id"]
    audit(run_id, "pipeline_started", run["config"])
    totals = defaultdict(int)

    try:
        stage = start_stage(run_id, "product_context", "market-discovery")
        products = load_products(args.max_products)
        totals["products"] = len(products)
        finish_stage(stage, output_count=len(products), confidence=1.0, metrics={"paid_tokens": 0})
        if not products:
            raise RuntimeError("No active products available for bounded market context")

        stage = start_stage(run_id, "market_research", "source-research")
        queries = discover_market_queries(products, args.max_searches)
        all_results = []
        docs = []
        evidence = []
        seen_urls = set()
        for qi, q in enumerate(queries):
            rows = searx(q, limit=6)
            all_results.extend(rows)
            for r in rows[:3]:
                if r["url"] in seen_urls or r["domain"] in DISCOVERY_ONLY_DOMAINS:
                    continue
                seen_urls.add(r["url"])
                page = fetch_page(r["url"])
                if not page:
                    continue
                doc = create_doc(run_id, page, {"query": q, "search_rank_source": "searxng"})
                docs.append(doc)
                # Large Greek commerce sites are useful market-presence signals,
                # not pain proof in this generic crawler. The dedicated consumer
                # collector separately validates extracted first-person reviews.
                if beacon_policy(page["domain"]):
                    continue
                extracted = 0
                for s in sentences(page["text"]):
                    if PAIN_RE.search(s):
                        ev = create_evidence(run_id, doc, s)
                        evidence.append(ev); extracted += 1
                        if extracted >= 8:
                            break
                if len(docs) >= max(8, args.max_searches):
                    break
            if len(docs) >= max(8, args.max_searches):
                break
            time.sleep(0.15)
        totals["documents"] = len(docs); totals["evidence"] = len(evidence)
        finish_stage(stage, output_count=len(evidence), confidence=0.75 if docs else 0.2,
                     metrics={"queries": len(queries), "documents": len(docs), "evidence": len(evidence), "paid_tokens": 0})
        audit(run_id, "market_research_completed", {"queries": len(queries), "documents": len(docs), "pain_evidence": len(evidence)}, actor="source-research")

        stage = start_stage(run_id, "competitor_intelligence", "competitor-intelligence", "github_models_free" if router.available else "deterministic")
        cc = competitor_candidates(all_results, products, agents, run_id)
        competitors = [x for x in (get_or_create_competitor(c) for c in cc) if x]
        totals["competitors"] = len(competitors)
        finish_stage(stage, output_count=len(competitors), confidence=0.65 if competitors else 0.2,
                     metrics={"candidate_domains": len({r['domain'] for r in all_results}), "free_model_calls_used": router.calls})

        stage = start_stage(run_id, "pain_mining", "pain-miner", "github_models_free" if router.available else "deterministic")
        groups = group_pains(evidence, agents, run_id) if evidence else []
        pains = [create_pain(run_id, g) for g in groups]
        totals["pains"] = len(pains)
        finish_stage(stage, output_count=len(pains), confidence=max([float(p.get("confidence") or 0) for p in pains], default=0),
                     metrics={"free_model_calls_used": router.calls, "paid_remote_calls": 0})

        stage = start_stage(run_id, "contradiction_audit", "contradiction-skeptic")
        checked = []
        contradiction_total = 0
        for p in pains[:8]:
            if float(p.get("pain_score") or 0) < 45:
                checked.append(p); continue
            fresh, con = contradiction_check(run_id, p, max_pages=2)
            checked.append(fresh); contradiction_total += len(con)
        pains = checked + pains[len(checked):]
        totals["contradictions"] = contradiction_total
        finish_stage(stage, output_count=contradiction_total, confidence=0.8,
                     metrics={"pains_checked": len(checked), "paid_tokens": 0})

        stage = start_stage(run_id, "gap_validation", "gap-validator")
        gaps = []
        for p in pains:
            # Create a gap record for auditable candidates >=50, but validation
            # status is awarded only by hard database thresholds.
            if float(p.get("pain_score") or 0) < 50:
                continue
            gaps.append(create_gap(run_id, p, competitors, products))
        totals["gaps"] = len(gaps)
        validated_gaps = [g for g in gaps if g.get("status") in ("validated", "strong_gap", "exceptional")]
        totals["validated_gaps"] = len(validated_gaps)
        finish_stage(stage, output_count=len(gaps), confidence=max([float(g.get("confidence") or 0) for g in gaps], default=0),
                     metrics={"validated": len(validated_gaps), "competitors": len(competitors), "paid_tokens": 0})

        stage = start_stage(run_id, "product_gap_matching", "product-fit")
        matches = []
        pain_by_id = {p["id"]: p for p in pains}
        for g in gaps:
            p = pain_by_id.get(g["pain_id"])
            if p:
                matches.extend(match_products(g, p, products))
        totals["matches"] = len(matches)
        recommended = [m for m in matches if m.get("status") == "recommended"]
        totals["recommended"] = len(recommended)
        finish_stage(stage, output_count=len(matches), confidence=0.75 if matches else 0.3,
                     metrics={"recommended": len(recommended), "vector_validation_pending": True, "paid_tokens": 0})

        # Final governance gate: no candidate is promoted just because an LLM
        # said so. All statuses came from hard database scoring functions.
        stage = start_stage(run_id, "audit_governance", "audit-governance")
        budget = get("v_remote_budget_current_month", {"select": "*"})
        audit(run_id, "pipeline_finished", dict(totals), actor="audit-governance")
        finish_stage(stage, output_count=1, confidence=1.0,
                     metrics={"remote_budget": budget[0] if budget else {}, "free_model_calls_used": router.calls})

        summary = dict(totals)
        summary.update({
            "free_model_calls_used": router.calls,
            "paid_remote_calls_this_run": 0,
            "paid_llm_cost_usd": 0,
            "result_quality_note": "Only database-gated validated pains/gaps are eligible for recommendation; candidates remain auditable but unpromoted.",
        })
        patch("intelligence_runs", {"id": f"eq.{run_id}"}, {"status": "completed", "summary": summary, "finished_at": now()})
        print(json.dumps({"status": "completed", "run_id": run_id, "summary": summary}, ensure_ascii=False, indent=2))
    except Exception as exc:
        audit(run_id, "pipeline_failed", {"error": str(exc)[:1200]}, severity="error")
        patch("intelligence_runs", {"id": f"eq.{run_id}"}, {"status": "failed", "summary": {"error": str(exc)[:1200], **dict(totals)}, "finished_at": now()})
        raise


if __name__ == "__main__":
    main()
