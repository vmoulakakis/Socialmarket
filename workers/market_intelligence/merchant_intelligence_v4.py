from __future__ import annotations

import concurrent.futures
import datetime
import json
import os

from audit_agent import audit_research, pain_language
from evidence_collectors import collect_entity_evidence
from merchant_intelligence_v3 import gateway, analyze

SEARXNG = os.getenv("SEARXNG_BASE_URL", "http://127.0.0.1:8080").rstrip("/")
MAX = int(os.getenv("MERCHANT_RESEARCH_LIMIT", "350"))
WORKERS = max(1, min(int(os.getenv("MERCHANT_RESEARCH_WORKERS", "5")), 8))


def process(job: dict) -> dict:
    try:
        base = analyze(job)
        authoritative_url = job.get("official_url") or base.get("official_url")
        evidence = collect_entity_evidence(job["canonical_name"], authoritative_url, SEARXNG)
        audit = audit_research(base, evidence, authoritative_url=job.get("official_url"))
        pains = pain_language(
            evidence,
            entity_name=job.get("canonical_name"),
            authoritative_url=job.get("official_url"),
        )

        base["evidence"] = (base.get("evidence") or []) + evidence[:120]
        base["evidence_count"] = len(base["evidence"])
        base.setdefault("metadata", {})
        base["metadata"].update({
            "worker": "merchant_intelligence_v4",
            "audit": audit,
            "pain_language": pains,
            "collector_stack": ["searxng", "trafilatura", "scrapy-ready", "yt-dlp", "gallery-dl", "playwright-fallback"],
            "authoritative_url_used": bool(job.get("official_url")),
            "pain_relevance_gate": "entity_bound_v2",
        })
        if pains:
            base["semantic_text"] = (base.get("semantic_text") or "") + " | validated pain candidates: " + " | ".join(pains[:12])

        if audit["verdict"] == "rejected":
            base["confidence"] = min(float(base.get("confidence") or 0), 0.35)
            base["risk_flag"] = True
            base["risk_reason"] = "audit_rejected"
        elif audit["verdict"] == "needs_review":
            base["confidence"] = min(float(base.get("confidence") or 0), 0.65)

        gateway("save", result=base)
        return {
            "ok": True,
            "merchant": job["canonical_name"],
            "audit": audit["verdict"],
            "audit_score": audit["overall_score"],
            "entity_relevance": audit.get("entity_relevance_score"),
            "evidence": len(evidence),
            "pain_candidates": len(pains),
            "url": authoritative_url,
        }
    except Exception as exc:
        try:
            gateway("fail", job_id=job["job_id"], error=str(exc)[:1200])
        except Exception:
            pass
        return {"ok": False, "merchant": job.get("canonical_name"), "error": str(exc)[:400]}


def main() -> None:
    done = 0
    summary = {"validated": 0, "needs_review": 0, "rejected": 0, "failed": 0}
    while done < MAX:
        batch = min(30, MAX - done)
        jobs = gateway("claim", limit=batch, worker="github-evidence-audit-v4.1").get("jobs") or []
        if not jobs:
            break
        with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
            for result in pool.map(process, jobs):
                print(json.dumps(result, ensure_ascii=False), flush=True)
                done += 1
                if result.get("ok"):
                    summary[result.get("audit", "needs_review")] = summary.get(result.get("audit", "needs_review"), 0) + 1
                else:
                    summary["failed"] += 1
    print(json.dumps({
        "status": "completed",
        "processed": done,
        "summary": summary,
        "workers": WORKERS,
        "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
