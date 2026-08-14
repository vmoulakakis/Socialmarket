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
except Exception:
    trafilatura = None

UA = {"User-Agent": "Mozilla/5.0 SocialMarketEvidenceBot/1.1"}
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
        return [{
            "url": x.get("url", ""),
            "title": x.get("title", ""),
            "snippet": x.get("content") or x.get("snippet") or "",
        } for x in (r.json().get("results") or [])[:limit]]
    except Exception:
        return []


def render_public_page(url: str) -> str | None:
    """JS-rendered public-page fallback. Never logs in or bypasses access controls."""
    try:
        code = (
            "from playwright.sync_api import sync_playwright;import sys;"
            "p=sync_playwright().start();b=p.chromium.launch(headless=True);"
            "page=b.new_page();page.goto(sys.argv[1],wait_until='domcontentloaded',timeout=30000);"
            "print(page.locator('body').inner_text()[:120000]);b.close();p.stop()"
        )
        p = subprocess.run(["python", "-c", code, url], capture_output=True, text=True, timeout=45)
        return p.stdout[:120000] if p.returncode == 0 and p.stdout else None
    except Exception:
        return None


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
                r.text, include_comments=True, include_links=True,
                include_tables=True, favor_precision=True,
            ) or ""
        collector = "trafilatura"
        if len(text.strip()) < 250:
            rendered = render_public_page(r.url)
            if rendered:
                text = rendered
                collector = "playwright"
        if not text:
            text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", r.text))
            collector = "requests_html_fallback"
        title = None
        m = re.search(r"<title[^>]*>(.*?)</title>", r.text, re.I | re.S)
        if m:
            title = re.sub(r"\s+", " ", m.group(1)).strip()[:500]
        return [EvidenceRecord(
            source_kind="official_site", source_url=r.url, title=title, body=text[:120000],
            metadata={"domain": _host(r.url), "status": r.status_code},
            confidence=0.95, collector=collector,
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
    seen = set()
    for kind, q in queries:
        for row in searx_search(searx_url, q, 12):
            key = (kind, row["url"], row["snippet"][:120])
            if key in seen:
                continue
            seen.add(key)
            out.append(EvidenceRecord(
                source_kind=kind, source_url=row["url"], title=row["title"], body=row["snippet"],
                confidence=0.65, collector="searxng",
            ))
    return out


def collect_social_evidence(name: str, searx_url: str) -> list[EvidenceRecord]:
    """No-key social discovery through search-visible public pages.

    Mention queries and pain queries are separate so a platform with sparse indexing
    does not disappear just because every pain term is not present in one result.
    """
    out: list[EvidenceRecord] = []
    seen = set()
    for platform, domain in SOCIAL_DOMAINS.items():
        queries = [
            f'site:{domain} "{name}"',
            f'site:{domain} "{name}" review OR reviews OR αξιολόγηση OR κριτική',
            f'site:{domain} "{name}" πρόβλημα OR παράπονο OR expensive OR alternative',
        ]
        for query_type, q in enumerate(queries):
            for row in searx_search(searx_url, q, 10):
                key = (platform, row["url"], row["snippet"][:120])
                if key in seen:
                    continue
                seen.add(key)
                out.append(EvidenceRecord(
                    source_kind="social_public_observation",
                    platform=platform,
                    source_url=row["url"],
                    title=row["title"],
                    body=row["snippet"],
                    metadata={"query_type": ["mention", "review", "pain"][query_type]},
                    confidence=0.5 if platform in {"instagram", "facebook", "tiktok"} else 0.65,
                    collector="searxng_social",
                ))
    return out


def collect_youtube_public(url: str) -> list[EvidenceRecord]:
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
            source_kind="social_video", platform="youtube",
            source_url=data.get("webpage_url") or url, title=data.get("title"), body=data.get("description"),
            metrics={"view_count": data.get("view_count"), "like_count": data.get("like_count"), "comment_count": data.get("comment_count")},
            confidence=0.8, collector="yt-dlp",
        )]
        for c in (data.get("comments") or [])[:50]:
            rows.append(EvidenceRecord(
                source_kind="social_comment", platform="youtube",
                source_url=data.get("webpage_url") or url, body=c.get("text"),
                metrics={"like_count": c.get("like_count")}, metadata={"author": c.get("author")},
                confidence=0.75, collector="yt-dlp",
            ))
        return rows
    except Exception:
        return []


def collect_gallery_public(url: str) -> list[EvidenceRecord]:
    """Optional public metadata fallback for supported social/media URLs."""
    try:
        p = subprocess.run(["gallery-dl", "--dump-json", url], capture_output=True, text=True, timeout=60, check=False)
        if p.returncode != 0 or not p.stdout.strip():
            return []
        return [EvidenceRecord(
            source_kind="social_media_metadata", source_url=url, body=p.stdout[:10000],
            confidence=0.45, collector="gallery-dl",
        )]
    except Exception:
        return []


def collect_entity_evidence(name: str, official_url: str | None, searx_url: str) -> list[dict[str, Any]]:
    records: list[EvidenceRecord] = []
    records.extend(collect_site(official_url))
    records.extend(collect_search_evidence(name, searx_url))
    records.extend(collect_social_evidence(name, searx_url))

    youtube_urls = []
    for r in records:
        if r.platform == "youtube" and r.source_url and ("watch?v=" in r.source_url or "youtu.be/" in r.source_url):
            youtube_urls.append(r.source_url)
    for url in list(dict.fromkeys(youtube_urls))[:2]:
        records.extend(collect_youtube_public(url))

    # Media collectors are intentionally capped: they are enrichment, not the source of truth.
    social_urls = [r.source_url for r in records if r.platform in {"instagram", "tiktok"} and r.source_url]
    for url in list(dict.fromkeys(social_urls))[:2]:
        records.extend(collect_gallery_public(url))

    return [r.to_dict() for r in records]
