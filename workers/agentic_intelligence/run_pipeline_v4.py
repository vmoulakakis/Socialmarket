import requests
from urllib.parse import urlparse
from urllib import robotparser

import run_pipeline as core
from research_v2 import discover_market_queries, relevant_searx

_original_searx = core.searx
core.discover_market_queries = discover_market_queries
core.searx = lambda query, limit=8: relevant_searx(_original_searx, query, limit)


def fast_robots_allowed(url: str):
    d = core.domain(url)
    if not d:
        return False
    if any(d == b or d.endswith('.' + b) for b in core.BLOCKED_DOMAINS):
        return False
    try:
        p = urlparse(url)
        rr = requests.get(
            f"{p.scheme}://{p.netloc}/robots.txt",
            headers={'User-Agent': core.UA},
            timeout=3,
            allow_redirects=True,
        )
        if rr.status_code == 200 and rr.text:
            rp = robotparser.RobotFileParser()
            rp.set_url(str(rr.url))
            rp.parse(rr.text.splitlines())
            return rp.can_fetch(core.UA, url)
        if rr.status_code in (401, 403):
            return False
        return True
    except Exception:
        return True


core.robots_allowed = fast_robots_allowed

if __name__ == '__main__':
    core.main()
