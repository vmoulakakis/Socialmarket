from __future__ import annotations

import concurrent.futures
import json
import os
import re
import threading
import time
from urllib.parse import quote, urlparse

import requests

from evidence_collectors import searx_search

GATEWAY = os.environ["GENERIC_EVIDENCE_GATEWAY"]
SEARXNG = os.getenv("SEARXNG_BASE_URL", "http://127.0.0.1:8080").rstrip("/")
MAX = int(os.getenv("GENERIC_EVIDENCE_LIMIT", "300"))
WORKERS = max(1, min(int(os.getenv("GENERIC_EVIDENCE_WORKERS", "5")), 8))
AUD = "socialmarket-supabase-worker"
SOCIAL = {
    "reddit": "reddit.com",
    "youtube": "youtube.com",
    "facebook": "facebook.com",
    "instagram": "instagram.com",
    "tiktok": "tiktok.com",
}
PAIN_TERMS = (
    "πρόβλημα", "παράπονο", "ακριβ", "δεν βρίσκ", "δεν υπάρχει", "δεν μπορ",
    "καθυστερ", "επιστροφ", "εναλλακτ", "alternative", "too expensive", "problem",
    "refund", "can't find", "missing", "better than", "recommend", "προτείν",
)
BUY_TERMS = ("αγορά", "τιμή", "φθην", "cheap", "price", "buy", "recommend", "alternative", "εναλλακτ")

_token = None
_token_at = 0.0
_lock = threading.Lock()


def clamp(v: float, a: float = 0, b: float = 100) -> float:
    return max(a, min(b, float(v)))


def host(url: str | None) -> str:
    try:
        return urlparse(url or "").netloc.lower().removeprefix("www.")
    except Exception:
        return ""


def oidc() -> str:
    global _token, _token_at
    with _lock:
        if _token and time.time() - _token_at < 180:
            return _token
        u = os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"]
        rt = os.environ["ACTIONS_ID_TOKEN_REQUEST_TOKEN"]
        sep = "&" if "?" in u else "?"
        r = requests.get(f"{u}{sep}audience={quote(AUD)}", headers={"Authorization": f"Bearer {rt}"}, timeout=30)
        r.raise_for_status()
        _token = r.json()["value"]
        _token_at = time.time()
        return _token


def gateway(action: str, **kwargs):
    global _token
    r = requests.post(
        GATEWAY,
        headers={"Authorization": f"Bearer {oidc()}", "Content-Type": "application/json"},
        json={"action": action, **kwargs},
        timeout=180,
    )
    if r.status_code == 401:
        _token = None
        r = requests.post(
            GATEWAY,
            headers={"Authorization": f"Bearer {oidc()}", "Content-Type": "application/json"},
            json={"action": action, **kwargs},
            timeout=180,
        )
    r.raise_for_status()
    body = r.json()
    if not body.get("ok"):
        raise RuntimeError(body)
    return body


def significant_tokens(label: str) -> list[str]:
    stop = {"and", "the", "other", "services", "service"}
    return [x for x in re.findall(r"[\wΑ-Ωα-ωάέήίόύώϊϋΐΰ]+", label.lower()) if len(x) >= 3 and x not in stop]


def relevant(label: str, row: dict) -> bool:
    text = " ".join([row.get("title", ""), row.get("snippet", "")]).lower()
    tokens = significant_tokens(label)
    if not tokens:
        return False
    return any(t in text for t in tokens)


def as_evidence(row: dict, kind: str, platform: str | None = None, confidence: float = 0.6, query: str | None = None) -> dict:
    return {
        "source_kind": kind,
        "platform": platform,
        "source_url": row.get("url"),
        "title": row.get("title"),
        "body": row.get("snippet"),
        "collector": "searxng_generic",
        "confidence": confidence,
        "metadata": {"query": query} if query else {},
    }


def collect(label: str) -> dict:
    demand_queries = [
        f'"{label}" αγορά Ελλάδα',
        f'"{label}" καλύτερο τι να αγοράσω',
        f'"{label}" τιμή σύγκριση',
    ]
    pain_queries = [
        f'"{label}" πρόβλημα παράπονα',
        f'"{label}" πολύ ακριβό φθηνότερη λύση',
        f'"{label}" δεν βρίσκω εναλλακτική',
        f'"{label}" απογοήτευση επιστροφή',
    ]

    demand_rows = []
    pain_rows = []
    evidence = []
    for q in demand_queries:
        for row in searx_search(SEARXNG, q, 12):
            if relevant(label, row):
                demand_rows.append(row)
                evidence.append(as_evidence(row, "category_demand", confidence=0.62, query=q))
    for q in pain_queries:
        for row in searx_search(SEARXNG, q, 12):
            if relevant(label, row):
                text = (row.get("title", "") + " " + row.get("snippet", "")).lower()
                if any(t in text for t in PAIN_TERMS):
                    pain_rows.append(row)
                    evidence.append(as_evidence(row, "category_pain", confidence=0.65, query=q))

    social_rows = []
    for platform, domain in SOCIAL.items():
        queries = [
            f'site:{domain} "{label}"',
            f'site:{domain} "{label}" πρόβλημα OR ακριβό OR alternative OR recommend',
        ]
        for q in queries:
            for row in searx_search(SEARXNG, q, 10):
                if relevant(label, row):
                    social_rows.append((platform, row))
                    evidence.append(as_evidence(row, "social_category_observation", platform=platform, confidence=0.55 if platform in {"facebook","instagram","tiktok"} else 0.65, query=q))

    # Dedupe normalized evidence before scoring.
    uniq = {}
    for e in evidence:
        key = (e.get("source_kind"), e.get("platform"), e.get("source_url"), (e.get("body") or "")[:160])
        uniq[key] = e
    evidence = list(uniq.values())

    domains = {host(e.get("source_url")) for e in evidence if host(e.get("source_url"))}
    competition_domains = {host(x.get("url")) for x in demand_rows if host(x.get("url"))}
    social_platforms = {p for p, _ in social_rows}

    demand = clamp(20 + min(45, len(demand_rows) * 4) + min(20, len(social_rows) * 2))
    competition = clamp(len(competition_domains) * 8)
    pain_severity = clamp(15 + len(pain_rows) * 7 + min(20, len(social_rows) * 2))
    source_diversity = len(domains)
    audit = clamp(source_diversity * 7 + len(social_platforms) * 10 + min(30, len(pain_rows) * 5) + min(20, len(demand_rows) * 2))
    confidence = clamp((audit / 100) * 0.8 + (0.15 if source_diversity >= 3 else 0), 0, 1)

    clusters = []
    seen_text = set()
    for row in pain_rows + [r for _, r in social_rows]:
        text = " ".join(filter(None, [row.get("title"), row.get("snippet")])).strip()
        low = text.lower()
        if len(text) < 25 or not any(t in low for t in PAIN_TERMS):
            continue
        normalized = re.sub(r"\s+", " ", low)[:500]
        if normalized in seen_text:
            continue
        seen_text.add(normalized)
        commercial = clamp(35 + sum(12 for t in BUY_TERMS if t in low))
        cluster_type = "alternative_request" if any(t in low for t in ("alternative", "εναλλακτ", "φθηνότερ", "better than")) else "pain"
        validation = "validated" if audit >= 70 and source_diversity >= 4 and len(pain_rows) >= 2 else "pending"
        clusters.append({
            "cluster_type": cluster_type,
            "canonical_text": text[:900],
            "evidence_count": len(evidence),
            "source_diversity": source_diversity,
            "demand_score": demand,
            "competition_score": competition,
            "pain_severity": pain_severity,
            "commercial_intent": commercial,
            "audit_score": audit,
            "confidence": confidence,
            "validation_status": validation,
            "metadata": {
                "methodology": "generic_category_pain_v1",
                "social_platforms": sorted(social_platforms),
                "competition_domains": sorted(competition_domains)[:30],
            },
        })
        if len(clusters) >= 25:
            break

    return {
        "evidence": evidence[:180],
        "clusters": clusters,
        "scores": {
            "demand": demand,
            "competition": competition,
            "pain_severity": pain_severity,
            "audit": audit,
            "confidence": confidence,
            "source_diversity": source_diversity,
            "social_platforms": sorted(social_platforms),
        },
    }


def process(job: dict) -> dict:
    try:
        payload = job.get("payload") or {}
        name = str(payload.get("name") or "").strip()
        if not name:
            raise ValueError("job_payload_name_missing")
        analysis = collect(name)
        result = {
            "job_id": job["id"],
            "entity_type": job["entity_type"],
            "entity_id": job["entity_id"],
            "evidence": analysis["evidence"],
            "clusters": [
                {**c, "category": name if payload.get("node_type") == "category" else None,
                 "subcategory": name if payload.get("node_type") == "subcategory" else None}
                for c in analysis["clusters"]
            ],
        }
        saved = gateway("save", result=result)
        return {"ok": True, "name": name, **analysis["scores"], "clusters": len(analysis["clusters"]), "saved": saved.get("result")}
    except Exception as exc:
        try:
            gateway("fail", job_id=job.get("id"), error=str(exc)[:1200])
        except Exception:
            pass
        return {"ok": False, "name": (job.get("payload") or {}).get("name"), "error": str(exc)[:400]}


def main() -> None:
    done = 0
    while done < MAX:
        jobs = gateway("claim", limit=min(30, MAX-done), worker="github-generic-evidence-v1", collection_type="pain_discovery").get("jobs") or []
        if not jobs:
            break
        with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
            for result in pool.map(process, jobs):
                print(json.dumps(result, ensure_ascii=False), flush=True)
                done += 1
    print(json.dumps({"status": "completed", "processed": done}, ensure_ascii=False))


if __name__ == "__main__":
    main()
