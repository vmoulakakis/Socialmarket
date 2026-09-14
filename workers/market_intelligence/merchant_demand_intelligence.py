from __future__ import annotations

import datetime as dt
import json
import math
import os
import time
from urllib.parse import quote

import requests

# Reuse the mature deterministic/SearXNG research primitives without its legacy gateway.
os.environ.setdefault("MERCHANT_RESEARCH_GATEWAY", "http://127.0.0.1/unused")
import merchant_intelligence_v3 as legacy  # noqa: E402

GATEWAY = os.getenv("VMDB_WORKER_GATEWAY", "https://gqpbskssrvpfjtujwezc.supabase.co/functions/v1/github-worker-gateway")
AUDIENCE = "socialmarket-supabase-worker"
MODEL_ENDPOINT = "https://models.github.ai/inference/chat/completions"
MODEL = os.getenv("MERCHANT_AI_MODEL", "openai/gpt-4.1")
LIMIT = max(1, min(int(os.getenv("MERCHANT_360_LIMIT", "24")), 60))
AI_MAX_TOKENS = max(80, min(int(os.getenv("MERCHANT_AI_MAX_TOKENS", "220")), 400))

_token = None
_token_at = 0.0


def clamp(v, lo=0.0, hi=100.0):
    return max(lo, min(hi, float(v)))


def oidc_token():
    global _token, _token_at
    if _token and time.time() - _token_at < 180:
        return _token
    url = os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"]
    rt = os.environ["ACTIONS_ID_TOKEN_REQUEST_TOKEN"]
    sep = "&" if "?" in url else "?"
    r = requests.get(f"{url}{sep}audience={quote(AUDIENCE)}", headers={"Authorization": f"Bearer {rt}"}, timeout=30)
    r.raise_for_status()
    _token = r.json()["value"]
    _token_at = time.time()
    return _token


def db(method: str, resource: str, *, params=None, data=None, prefer=None):
    r = requests.post(
        GATEWAY,
        headers={"Authorization": f"Bearer {oidc_token()}", "Content-Type": "application/json"},
        json={"method": method, "resource": resource, "params": params or {}, "data": data, "prefer": prefer},
        timeout=180,
    )
    r.raise_for_status()
    body = r.json()
    if not body.get("ok"):
        raise RuntimeError(body)
    return body.get("result")


def github_model_judge(payload: dict) -> dict:
    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        return {"verdict": "needs_review", "confidence_delta": 0.0, "why_selected": None, "why_rejected": "github_model_token_missing"}
    system = (
        "Greek affiliate-commerce verifier. Use ONLY supplied evidence. Never invent facts. "
        "Return compact JSON only: verdict selected|needs_review|rejected, confidence_delta -0.10..0.05, why_selected, why_rejected."
    )
    r = requests.post(
        MODEL_ENDPOINT,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"model": MODEL, "temperature": 0, "max_tokens": AI_MAX_TOKENS, "response_format": {"type": "json_object"}, "messages": [{"role": "system", "content": system}, {"role": "user", "content": json.dumps(payload, ensure_ascii=False, separators=(",", ":"))}]},
        timeout=45,
    )
    if not r.ok:
        return {"verdict": "needs_review", "confidence_delta": -0.05, "why_selected": None, "why_rejected": f"model_http_{r.status_code}"}
    try:
        out = json.loads(r.json()["choices"][0]["message"]["content"])
    except Exception:
        return {"verdict": "needs_review", "confidence_delta": -0.05, "why_selected": None, "why_rejected": "invalid_model_json"}
    out["confidence_delta"] = max(-0.10, min(0.05, float(out.get("confidence_delta") or 0)))
    return out


def get_policy():
    rows = db("GET", "merchant_selection_policies", params={"select": "*", "policy_key": "eq.greece_problem_solver_v1", "limit": "1"}) or []
    if not rows:
        raise RuntimeError("merchant_selection_policy_missing")
    return rows[0]


def get_candidates():
    return db(
        "GET",
        "merchant_profiles",
        params={
            "select": "id,merchant_name,canonical_domain,primary_category,primary_subcategory,median_conversion_rate,median_epc_eur,median_approval_pct,median_approval_days,expected_commission_eur,metadata",
            "active": "eq.true",
            "expected_commission_eur": "gte.15",
            "order": "expected_commission_eur.desc",
            "limit": str(LIMIT),
        },
    ) or []


def evidence_urls(rows, n=12):
    out = []
    for x in rows[:n]:
        u = x.get("url")
        if u and u not in out:
            out.append(u)
    return out


def analyze(m: dict, policy: dict) -> dict:
    name = m["merchant_name"]
    label = m.get("primary_subcategory") or m.get("primary_category") or name
    demand, competition, gap, suggestions, need, buy, pain, competitor_domains = legacy.market(label)

    official = None
    if m.get("canonical_domain"):
        official = str(m["canonical_domain"])
        if not official.startswith("http"):
            official = "https://" + official
    official = legacy.discover(name, official)
    crawl = legacy.crawl(official) if official else legacy.crawl("")
    corpus = " ".join([str(crawl.get("title") or ""), str(crawl.get("description") or ""), str(crawl.get("text") or "")]).lower()

    reviews = legacy.search(f'"{name}" αξιολογήσεις κριτικές', 10)
    complaints = legacy.search(f'"{name}" παράπονα καταγγελίες', 10)
    _, neg, satisfaction = legacy.sentiment(reviews + complaints)
    identity = clamp(30 + (25 if crawl.get("ok") else 0) + (15 if crawl.get("title") else 0) + (15 if any(k in corpus for k in ("επικοινων", "contact", "όροι", "terms")) else 0) + (15 if any(k in corpus for k in ("επιστροφ", "return", "εγγύ", "warranty")) else 0))
    trust = clamp(identity * 0.45 + satisfaction * 0.55 - min(20, neg * 4))

    fulfilment_hits = sum(1 for k in ("ελλάδα", "greece", "αποστολ", "delivery", "παράδοση", "επιστροφ", "return", "εγγύ", "warranty") if k in corpus)
    fulfilment = clamp(25 + (20 if crawl.get("ok") else 0) + min(50, fulfilment_hits * 7))
    price_hits = sum(1 for k in ("προσφορ", "sale", "discount", "best price", "χαμηλότερ", "τιμή", "price") if k in corpus)
    price_value = clamp(45 + min(25, price_hits * 5) + (10 if gap >= 60 else 0) + (10 if competition <= 45 else 0))

    conv = float(m.get("median_conversion_rate") or 0)
    epc = float(m.get("median_epc_eur") or 0)
    approval = float(m.get("median_approval_pct") or 0)
    affiliate_perf = clamp(min(100, epc / 25 * 100) * 0.40 + min(100, conv / 5 * 100) * 0.25 + approval * 0.35)
    expected_comm = float(m.get("expected_commission_eur") or 0)
    commission_score = clamp(30 + max(0, expected_comm - 15) * 2.2)
    problem_solving = clamp(gap * 0.58 + demand * 0.27 + (100 - competition) * 0.15)
    scarcity = clamp((100 - competition) * 0.65 + gap * 0.35)
    conversion_potential = clamp(affiliate_perf * 0.30 + demand * 0.25 + trust * 0.20 + (100 - competition) * 0.15 + problem_solving * 0.10)
    expected_revenue = clamp(commission_score * 0.55 + conversion_potential * 0.45)
    confidence = clamp(0.30 + (0.15 if crawl.get("ok") else 0) + (0.12 if reviews else 0) + (0.12 if buy else 0) + (0.10 if suggestions else 0) + (0.08 if m.get("median_epc_eur") is not None else 0) + (0.08 if m.get("median_approval_pct") is not None else 0), 0, 1)

    judge_payload = {
        "merchant": name,
        "category": m.get("primary_category"),
        "subcategory": m.get("primary_subcategory"),
        "expected_commission_eur": expected_comm,
        "demand_score": demand,
        "competition_score": competition,
        "supply_gap_score": gap,
        "problem_solving_score": problem_solving,
        "trust_score": trust,
        "price_value_score": price_value,
        "greek_fulfilment_score": fulfilment,
        "affiliate_performance_score": affiliate_perf,
        "official_url": official,
        "market_evidence_urls": evidence_urls(buy),
        "pain_evidence_urls": evidence_urls(pain),
        "review_urls": evidence_urls(reviews + complaints),
    }
    judge = github_model_judge(judge_payload)
    confidence = clamp(confidence + float(judge.get("confidence_delta") or 0), 0, 1)

    demand_supply_gap = clamp(demand * 0.40 + gap * 0.35 + (100 - competition) * 0.25)
    operational = clamp(approval * 0.75 + max(0, 100 - float(m.get("median_approval_days") or 45) * 1.5) * 0.25)
    raw = clamp(
        affiliate_perf * 0.15 + commission_score * 0.15 + problem_solving * 0.14 + demand_supply_gap * 0.14 +
        trust * 0.12 + price_value * 0.10 + fulfilment * 0.08 + scarcity * 0.05 + conversion_potential * 0.04 + operational * 0.03
    )
    adjusted = clamp(raw * (0.65 + 0.35 * confidence))

    checks = {
        "expected_commission": expected_comm >= float(policy["min_expected_commission_eur"]),
        "demand": demand >= float(policy["min_demand_score"]),
        "competition": competition <= float(policy["max_competition_score"]),
        "supply_gap": gap >= float(policy["min_supply_gap_score"]),
        "problem_solving": problem_solving >= float(policy["min_problem_solving_score"]),
        "trust": trust >= float(policy["min_trust_score"]),
        "price_value": price_value >= float(policy["min_price_value_score"]),
        "greek_fulfilment": fulfilment >= float(policy["min_greek_fulfilment_score"]),
        "confidence": confidence >= float(policy["min_confidence"]),
        "score": adjusted >= float(policy["min_confidence_adjusted_score"]),
        "ai_not_rejected": judge.get("verdict") != "rejected",
    }
    hard_gate = all(checks.values())
    failed = [k for k, ok in checks.items() if not ok]
    grade = "S" if adjusted >= 90 else "A" if adjusted >= 80 else "B" if adjusted >= 70 else "C" if adjusted >= 60 else "D"

    return {
        "official_url": official,
        "demand_score": round(demand, 3),
        "commercial_intent_score": round(clamp(demand * 0.70 + len(need) * 3), 3),
        "competition_score": round(competition, 3),
        "supply_gap_score": round(gap, 3),
        "greek_scarcity_score": round(scarcity, 3),
        "problem_solving_score": round(problem_solving, 3),
        "price_value_score": round(price_value, 3),
        "trust_score": round(trust, 3),
        "warranty_returns_score": round(fulfilment, 3),
        "greek_fulfilment_score": round(fulfilment, 3),
        "affiliate_performance_score": round(affiliate_perf, 3),
        "conversion_potential_score": round(conversion_potential, 3),
        "expected_revenue_score": round(expected_revenue, 3),
        "confidence": round(confidence, 4),
        "raw_360_score": round(raw, 3),
        "confidence_adjusted_score": round(adjusted, 3),
        "grade": grade,
        "hard_gate_pass": hard_gate,
        "hard_gate_reasons": failed,
        "ai_verdict": judge.get("verdict") or "needs_review",
        "why_selected": judge.get("why_selected"),
        "why_rejected": judge.get("why_rejected"),
        "evidence": {
            "query_label": label,
            "suggestions": suggestions[:10],
            "problem_suggestions": need[:10],
            "competitor_domains": competitor_domains[:20],
            "market_urls": evidence_urls(buy),
            "pain_urls": evidence_urls(pain),
            "review_urls": evidence_urls(reviews + complaints),
            "official_url": official,
        },
    }


def persist(m: dict, result: dict):
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    run = db("POST", "merchant_research_runs", data={
        "merchant_id": m["id"], "run_scope": "merchant_360", "methodology_version": "merchant_360_v1",
        "market_code": "GR", "status": "running", "model_provider": "github_models", "model_name": MODEL,
        "prompt_version": "merchant_judge_v1", "confidence": result["confidence"], "started_at": now,
    }, prefer="return=representation")[0]

    ev_rows = []
    for typ, urls in (("market_demand", result["evidence"]["market_urls"]), ("pain_gap", result["evidence"]["pain_urls"]), ("merchant_reputation", result["evidence"]["review_urls"])):
        ev_rows.append({"merchant_id": m["id"], "research_run_id": run["id"], "evidence_type": typ, "source_name": "searxng_multi_source", "source_url": urls[0] if urls else None, "source_tier": 3, "confidence": result["confidence"], "evidence": {"urls": urls}})
    if result.get("official_url"):
        ev_rows.append({"merchant_id": m["id"], "research_run_id": run["id"], "evidence_type": "official_site", "source_name": "merchant_official_site", "source_url": result["official_url"], "source_tier": 1, "confidence": result["confidence"], "evidence": {}})
    if ev_rows:
        db("POST", "merchant_evidence", data=ev_rows, prefer="return=minimal")

    assessment = db("POST", "merchant_demand_assessments", data={
        "merchant_id": m["id"], "research_run_id": run["id"], "market_code": "GR",
        "category": m.get("primary_category"), "subcategory": m.get("primary_subcategory"),
        "problem_cluster": m.get("primary_subcategory") or m.get("primary_category"),
        "demand_score": result["demand_score"], "commercial_intent_score": result["commercial_intent_score"],
        "competition_score": result["competition_score"], "supply_gap_score": result["supply_gap_score"],
        "greek_scarcity_score": result["greek_scarcity_score"], "problem_solving_score": result["problem_solving_score"],
        "price_value_score": result["price_value_score"], "trust_score": result["trust_score"],
        "warranty_returns_score": result["warranty_returns_score"], "greek_fulfilment_score": result["greek_fulfilment_score"],
        "affiliate_performance_score": result["affiliate_performance_score"], "conversion_potential_score": result["conversion_potential_score"],
        "expected_revenue_score": result["expected_revenue_score"], "confidence": result["confidence"],
        "verdict": result["ai_verdict"], "why_selected": result["why_selected"], "why_rejected": result["why_rejected"],
        "evidence_summary": result["evidence"], "assessed_at": now,
    }, prefer="return=representation")[0]

    db("POST", "merchant_rankings", data={
        "merchant_id": m["id"], "demand_assessment_id": assessment["id"], "methodology_version": "merchant_360_v1",
        "category_snapshot": m.get("primary_category"), "subcategory_snapshot": m.get("primary_subcategory"),
        "raw_360_score": result["raw_360_score"], "confidence_adjusted_score": result["confidence_adjusted_score"],
        "confidence": result["confidence"], "hard_gate_pass": result["hard_gate_pass"],
        "hard_gate_reasons": result["hard_gate_reasons"], "grade": result["grade"],
        "eligible_for_product_discovery": result["hard_gate_pass"], "ai_verdict": result["ai_verdict"], "ranked_at": now,
    }, prefer="return=minimal")

    db("PATCH", "merchant_research_runs", params={"id": f"eq.{run['id']}"}, data={
        "status": "succeeded", "evidence_count": sum(len(result["evidence"].get(k) or []) for k in ("market_urls", "pain_urls", "review_urls")) + (1 if result.get("official_url") else 0),
        "confidence": result["confidence"], "completed_at": now,
        "summary": {"raw_360_score": result["raw_360_score"], "confidence_adjusted_score": result["confidence_adjusted_score"], "hard_gate_pass": result["hard_gate_pass"], "reasons": result["hard_gate_reasons"]},
    }, prefer="return=minimal")


def main():
    policy = get_policy()
    merchants = get_candidates()
    print(json.dumps({"phase": "start", "candidates": len(merchants), "policy": policy["policy_key"]}, ensure_ascii=False), flush=True)
    ok = failed = 0
    for m in merchants:
        try:
            result = analyze(m, policy)
            persist(m, result)
            ok += 1
            print(json.dumps({"merchant": m["merchant_name"], "score": result["confidence_adjusted_score"], "demand": result["demand_score"], "competition": result["competition_score"], "eligible_pre_diversity": result["hard_gate_pass"], "reasons": result["hard_gate_reasons"]}, ensure_ascii=False), flush=True)
        except Exception as exc:
            failed += 1
            print(json.dumps({"merchant": m.get("merchant_name"), "error": str(exc)[:800]}, ensure_ascii=False), flush=True)
    final = db("GET", "merchant_product_discovery_eligible", params={"select": "merchant_name,primary_category,primary_subcategory,expected_commission_eur,demand_score,competition_score,supply_gap_score,confidence_adjusted_score,subcategory_rank", "order": "confidence_adjusted_score.desc", "limit": "100"}) or []
    print(json.dumps({"status": "completed", "processed": ok, "failed": failed, "final_eligible": final, "at": dt.datetime.now(dt.timezone.utc).isoformat()}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
