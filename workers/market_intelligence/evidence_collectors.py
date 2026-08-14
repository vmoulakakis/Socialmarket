from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass, asdict
from typing import Any
from urllib.parse import urlparse

import requests

try:
    import trafilatura
except Exception:  # optional at import time
    trafilatura = None


UA = {"User-Agent": "Mozilla/5.0 SocialMarketEvidenceBot/1.0"}
SOCIAL_DOMAINS = {
    "instagram": "instagram.com",
    "facebook": "facebook.com",
    "tiktok": "tiktok.com",
    "youtube": "youtube.com",
    "reddit": "reddit.com",
}


@dataclass
class EvidenceRecord:
    source_kind: str
    source_url: str | None
    title: str | None = None
    body: str | None = None
    platform: str | None = None
    metrics: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None
    confidence: float = 0.5
    collector: str = "unknown"

    @property
    def content_hash(self) -> str:
        raw = json.dumps(asdict(self), sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["content_hash"] = self.content_hash
        return out


def _host(url: str | None) -> str:
    if not url:
        return ""
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        return ""


def searx_search(base_url: str, query: str, limit: int = 10) -> list[dict[str, str]]:
    try:
        r = requests.get(
            base_url.rstrip("/") + "/search",
            params={"q": query, "format": "json", "language": "el-GR", "safesearch": 1},
            headers=UA,
            timeout=25,
        )
        r.raise_for_status()
        rows = []
        for x in (r.json().get("results") or [])[:limit]:
            rows.append({
                "url": x.get("url", ""),
                "title": x.get("title", ""),
                "snippet": x.get("content") or x.get("snippet") or "",
            })
        return rows
    except Exception:
        return []


def collect_site(url: str | None) -> list[EvidenceRecord]:
    if not url:
        return []
    try:
        r = requests.get(url, headers=UA, timeout=20, allow_redirects=True)
        if not r.ok:
            return []
        text = ""
        if trafilatura is not None:
            text = trafilatura.extract(
                r.text,
                include_comments=True,
                include_links=True,
                include_tables=True,
                favor_precision=True,
            ) or ""
        if not text:
            text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", r.text))
        title = None
        m = re.search(r"<title[^>]*>(.*?)</title>", r.text, re.I | re.S)
        if m:
            title = re.sub(r"\s+", " ", m.group(1)).strip()[:500]
        return [EvidenceRecord(
            source_kind="official_site",
            source_url=r.url,
            title=title,
            body=text[:120000],
            metadata={"domain": _host(r.url), "status": r.status_code},
            confidence=0.95,
            collector="trafilatura" if trafilatura is not None else "requests_html_fallback",
        )]
    except Exception:
        return []


def collect_search_evidence(name: str, searx_url: str) -> list[EvidenceRecord]:
    queries = [
        ("reviews", f'"{name}" αξιολογήσεις κριτικές'),
        ("complaints", f'"{name}" παράπονα καταγγελίες πρόβλημα'),
        ("alternatives", f'"{name}" εναλλακτική alternative'),
        ("demand", f'"{name}" αγορά Ελλάδα'),
    ]
    out: list[EvidenceRecord] = []
    for kind, q in queries:
        for row in searx_search(searx_url, q, 10):
            out.append(EvidenceRecord(
                source_kind=kind,
                source_url=row["url"],
                title=row["title"],
                body=row["snippet"],
                confidence=0.65,
                collector="searxng",
            ))
    return out


def collect_social_evidence(name: str, searx_url: str) -> list[EvidenceRecord]:
    out: list[EvidenceRecord] = []
    pain_terms = "παράπονα πρόβλημα review experience alternative αξίζει"
    for platform, domain in SOCIAL_DOMAINS.items():
        for row in searx_search(searx_url, f'site:{domain} "{name}" {pain_terms}', 12):
            out.append(EvidenceRecord(
                source_kind="social_public_observation",
                platform=platform,
                source_url=row["url"],
                title=row["title"],
                body=row["snippet"],
                confidence=0.55 if platform in {"instagram", "facebook", "tiktok"} else 0.65,
                collector="searxng_social",
            ))
    return out


def collect_youtube_public(url: str) -> list[EvidenceRecord]:
    """Best-effort no-key YouTube metadata/comments via yt-dlp. Never fails the pipeline."""
    try:
        cmd = [
            "yt-dlp", "--skip-download", "--dump-single-json", "--no-warnings",
            "--extractor-args", "youtube:max_comments=50,all,all,50", url,
        ]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=90, check=False)
        if p.returncode != 0 or not p.stdout.strip():
            return []
        data = json.loads(p.stdout)
        rows = [EvidenceRecord(
            source_kind="social_video",
            platform="youtube",
            source_url=data.get("webpage_url") or url,
            title=data.get("title"),
            body=data.get("description"),
            metrics={
                "view_count": data.get("view_count"),
                "like_count": data.get("like_count"),
                "comment_count": data.get("comment_count"),
            },
            confidence=0.8,
            collector="yt-dlp",
        )]
        for c in (data.get("comments") or [])[:50]:
            rows.append(EvidenceRecord(
                source_kind="social_comment",
                platform="youtube",
                source_url=data.get("webpage_url") or url,
                body=c.get("text"),
                metrics={"like_count": c.get("like_count")},
                metadata={"author": c.get("author")},
                confidence=0.75,
                collector="yt-dlp",
            ))
        return rows
    except Exception:
        return []


def render_public_page(url: str) -> str | None:
    """Playwright fallback for JS-rendered public pages. No login/cookie bypass."""
    try:
        code = (
            "from playwright.sync_api import sync_playwright;"
            "import sys;"
            "p=sync_playwright().start();"
            "b=p.chromium.launch(headless=True);"
            "page=b.new_page();page.goto(sys.argv[1],wait_until='domcontentloaded',timeout=30000);"
            "print(page.locator('body').inner_text()[:120000]);b.close();p.stop()"
        )
        p = subprocess.run(["python", "-c", code, url], capture_output=True, text=True, timeout=45)
        return p.stdout[:120000] if p.returncode == 0 and p.stdout else None
    except Exception:
        return None


def collect_entity_evidence(name: str, official_url: str | None, searx_url: str) -> list[dict[str, Any]]:
    records: list[EvidenceRecord] = []
    records.extend(collect_site(official_url))
    records.extend(collect_search_evidence(name, searx_url))
    records.extend(collect_social_evidence(name, searx_url))
    # Enrich discovered YouTube URLs without API keys.
    youtube_urls = []
    for r in records:
        if r.platform == "youtube" and r.source_url and ("watch?v=" in r.source_url or "youtu.be/" in r.source_url):
            youtube_urls.append(r.source_url)
    for url in list(dict.fromkeys(youtube_urls))[:3]:
        records.extend(collect_youtube_public(url))
    return [r.to_dict() for r in records]
