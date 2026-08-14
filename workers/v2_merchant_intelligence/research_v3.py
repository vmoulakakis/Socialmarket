from __future__ import annotations

from urllib.parse import parse_qs, unquote, urlparse

import research as core


def _decode_ddg_url(url: str) -> str:
    if url.startswith("//"):
        url = "https:" + url
    try:
        parsed = urlparse(url)
        if "duckduckgo.com" in (parsed.hostname or ""):
            target = parse_qs(parsed.query).get("uddg", [None])[0]
            if target:
                return unquote(target)
    except Exception:
        pass
    return url


def _duckduckgo_html(query: str, limit: int) -> list[dict]:
    response = core.SESSION.get(
        "https://html.duckduckgo.com/html/",
        params={"q": query, "kl": "gr-el", "kp": "1"},
        timeout=30,
    )
    response.raise_for_status()
    soup = core.BeautifulSoup(response.text, "html.parser")
    rows: list[dict] = []
    for block in soup.select(".result"):
        anchor = block.select_one("a.result__a")
        if not anchor:
            continue
        url = _decode_ddg_url(str(anchor.get("href") or "").strip())
        if not url.startswith(("http://", "https://")):
            continue
        snippet_node = block.select_one(".result__snippet")
        rows.append({
            "rank": len(rows) + 1,
            "url": url,
            "domain": core.host(url),
            "title": anchor.get_text(" ", strip=True),
            "snippet": snippet_node.get_text(" ", strip=True) if snippet_node else "",
            "engine": "duckduckgo_html",
            "query": query,
        })
        if len(rows) >= limit:
            break
    return rows


def evidence_search(query: str, limit: int = 8) -> list[dict]:
    errors: list[str] = []

    # Primary: private ephemeral SearXNG. Try Greek locale, then language-neutral.
    for language in ("el-GR", "all"):
        try:
            response = core.SESSION.get(
                f"{core.SEARXNG}/search",
                params={"q": query, "format": "json", "language": language, "safesearch": 1},
                timeout=25,
            )
            response.raise_for_status()
            rows: list[dict] = []
            for idx, item in enumerate((response.json().get("results") or [])[:limit], 1):
                url = str(item.get("url") or "").strip()
                if not url:
                    continue
                rows.append({
                    "rank": idx,
                    "url": url,
                    "domain": core.host(url),
                    "title": str(item.get("title") or "").strip(),
                    "snippet": str(item.get("content") or "").strip(),
                    "engine": str(item.get("engine") or "searxng"),
                    "query": query,
                })
            if rows:
                return rows
            errors.append(f"searxng_{language}:0_results")
        except Exception as exc:
            errors.append(f"searxng_{language}:{type(exc).__name__}:{exc}")

    # Free independent fallback. Empty SERP is treated as unavailable research,
    # never as evidence of poor merchant standing.
    try:
        rows = _duckduckgo_html(query, limit)
        if rows:
            return rows
        errors.append("duckduckgo_html:0_results")
    except Exception as exc:
        errors.append(f"duckduckgo_html:{type(exc).__name__}:{exc}")

    raise RuntimeError("research_search_unavailable:" + " | ".join(errors)[-1400:])


# research_one resolves `search` from the module global at call time.
core.search = evidence_search

if __name__ == "__main__":
    raise SystemExit(core.main())
