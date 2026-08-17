from __future__ import annotations

"""Shallow public-forum seed crawler for Category Pain V4.8.

This channel is intentionally independent of search-engine site operators. It
starts from verified public forum/index surfaces, follows only same-domain links,
and still requires actual fetched page text to pass the unchanged V4 consumer
pain scorer. It never bypasses login, robots, 403/CAPTCHA or anti-bot controls.
"""

import concurrent.futures
from html.parser import HTMLParser
from urllib.parse import parse_qs, urljoin, urlparse

import consumer_evidence_v4 as consumer
import consumer_searx_forum_v47 as v47

_ORIGINAL_COLLECT = None
_APPLIED = False

SEEDS = {
    ('Sports & Outdoors', 'Camping & Hiking'): (
        'https://www.e-camping.gr/forum',
    ),
    ('Home & Garden', 'Garden & Outdoor Living'): (
        'https://www.bonsaiforum.gr/viewforum.php?f=44',
        'https://2019.kalliergo.gr/forum',
    ),
    ('Sports & Outdoors', 'Fitness'): (
        'https://www.howtofixit.gr/forum/forumdisplay.php?f=353',
        'https://bodybuilding.gr/forum/',
    ),
    ('Sports & Outdoors', 'Cycling'): (
        'https://www.podilates.gr/forum',
        'https://greekwatchforum.gr/',
    ),
}

TOPIC_PATH_MARKERS = (
    'viewtopic.php', 'showthread.php', '/topic/', '/forums/topic/',
)
DISCUSSION_TERMS = (
    'προβλημα','πρόβλημα','εμπειρ','αγορα','αγορά','χρησ','δοκιμ','δεν','σπα','χαλα','δυσκολ',
    'problem','issue','review','buy','use','broken','fail','equipment','εξοπλισ',
)


class _Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self._href = None
        self._text = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == 'a':
            self._href = dict(attrs).get('href')
            self._text = []

    def handle_data(self, data):
        if self._href:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == 'a' and self._href:
            self.links.append((self._href, ' '.join(self._text).strip()))
            self._href = None
            self._text = []


def _host(url: str) -> str:
    return (urlparse(url).hostname or '').lower().removeprefix('www.')


def _same_domain(url: str, seed: str) -> bool:
    a, b = _host(url), _host(seed)
    return bool(a and b and (a == b or a.endswith('.' + b) or b.endswith('.' + a)))


def _topic_url(url: str) -> bool:
    """Classify real topic URLs without substring collisions such as catid=id.

    Forum URL contracts differ, so use exact query semantics where available
    and well-known topic path forms otherwise. Generic `id=` / `t=` substring
    matching is intentionally forbidden because category/index URLs can contain
    those character sequences (for example `catid=`).
    """
    parsed = urlparse(str(url or ''))
    path = parsed.path.lower()
    query = parse_qs(parsed.query, keep_blank_values=True)
    view = str((query.get('view') or [''])[0]).lower()
    if view == 'topic':
        return True
    return any(marker in path for marker in TOPIC_PATH_MARKERS)


def _fetch_html(url: str):
    try:
        response = consumer.SESSION.get(url, timeout=18, allow_redirects=True)
        if response.status_code in (401, 403, 429):
            return None, f'http_{response.status_code}'
        response.raise_for_status()
        if 'html' not in (response.headers.get('content-type') or '').lower():
            return None, 'non_html'
        return response.text[:2_000_000], None
    except Exception as exc:
        return None, type(exc).__name__


def _anchor_tokens(category: str, subcategory: str | None, aliases: list[str]):
    values = [subcategory, *aliases[:4], category]
    out = []
    for value in values:
        for token in v47._tokens(str(value or '')):
            if token not in out:
                out.append(token)
    return out[:18]


def _link_score(url: str, text: str, tokens: list[str]) -> int:
    hay = consumer.fold(f'{text} {url}')
    score = sum(4 for token in tokens if token in hay)
    score += sum(1 for term in DISCUSSION_TERMS if consumer.fold(term) in hay)
    if _topic_url(url):
        score += 2
    return score


def _extract_links(html: str, base_url: str, tokens: list[str], limit: int = 40):
    parser = _Links()
    parser.feed(html)
    rows = []
    seen = set()
    for href, text in parser.links:
        url = urljoin(base_url, href)
        if url in seen or not _same_domain(url, base_url):
            continue
        seen.add(url)
        score = _link_score(url, text, tokens)
        if score <= 0:
            continue
        rows.append({'url': url, 'title': text, 'snippet': '', 'crawl_score': score})
    rows.sort(key=lambda x: (x['crawl_score'], len(x['title'])), reverse=True)
    return rows[:limit]


def _topicish(row: dict) -> bool:
    return _topic_url(str(row.get('url') or '')) and int(row.get('crawl_score') or 0) >= 3


def _crawl_seed(seed: str, tokens: list[str]):
    first_html, first_error = _fetch_html(seed)
    diag = {
        'source_kind': 'consumer_discovery',
        'source_url': seed,
        'title': f'Public forum seed crawl: {_host(seed)}',
        'body': '',
        'collector': 'forum_seed_crawl_v48',
        'confidence': .68 if first_html else .40,
        'metadata': {
            'geography': 'GR',
            'source_family': 'community_forum',
            'evidence_mode': 'discovery_only',
            'eligible_for_pain_audit': False,
            'fetch_error': first_error,
            'seed_url': seed,
            'depth': 0,
            'retrieval_version': 'forum_seed_crawl_v4.8',
        },
    }
    if not first_html:
        return [], [diag]

    first = _extract_links(first_html, seed, tokens, 28)
    topic_rows = [row for row in first if _topicish(row)]
    branch_rows = [row for row in first if not _topicish(row)][:8]
    diag['metadata']['first_level_links'] = len(first)
    diag['metadata']['first_level_topics'] = len(topic_rows)

    branch_diags = []
    for branch in branch_rows:
        html, error = _fetch_html(branch['url'])
        links = _extract_links(html, branch['url'], tokens, 24) if html else []
        topic_rows.extend(row for row in links if _topicish(row))
        branch_diags.append({
            'source_kind': 'consumer_discovery',
            'source_url': branch['url'],
            'title': str(branch.get('title') or '')[:500],
            'body': '',
            'collector': 'forum_seed_crawl_v48',
            'confidence': .64 if html else .40,
            'metadata': {
                'geography': 'GR',
                'source_family': 'community_forum',
                'evidence_mode': 'discovery_only',
                'eligible_for_pain_audit': False,
                'fetch_error': error,
                'seed_url': seed,
                'depth': 1,
                'links_found': len(links),
                'retrieval_version': 'forum_seed_crawl_v4.8',
            },
        })

    deduped = []
    seen = set()
    for row in sorted(topic_rows, key=lambda x: x.get('crawl_score', 0), reverse=True):
        url = row['url']
        if url in seen:
            continue
        seen.add(url)
        deduped.append({
            **row,
            'query': f'forum-seed:{seed}',
            'query_term': ' '.join(tokens[:6]),
            'expected_domain': _host(seed),
        })
        if len(deduped) >= 16:
            break
    diag['metadata']['topic_urls_selected'] = len(deduped)
    return deduped, [diag, *branch_diags]


def collect_consumer_evidence(category: str, subcategory: str | None, aliases: list[str], keywords: list[str], max_rows: int = 100):
    base_rows = _ORIGINAL_COLLECT(category, subcategory, aliases, keywords, max_rows=max_rows)
    seed_urls = SEEDS.get((str(category or ''), str(subcategory or '')), ())
    if not seed_urls:
        return base_rows

    tokens = _anchor_tokens(category, subcategory, aliases)
    candidates = []
    diagnostics = []
    for seed in seed_urls:
        rows, diag = _crawl_seed(seed, tokens)
        candidates.extend(rows)
        diagnostics.extend(diag)

    direct = []
    fetch_diags = []
    if candidates:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(6, len(candidates))) as pool:
            futures = [pool.submit(v47._extract_one, row, keywords) for row in candidates]
            for future in concurrent.futures.as_completed(futures):
                evidence, diagnostic = future.result()
                direct.extend(evidence)
                fetch_diags.append(diagnostic)

    pains = [x for x in base_rows if x.get('source_kind') == 'pain_candidate']
    other = [x for x in base_rows if x.get('source_kind') != 'pain_candidate']
    seen = {(consumer.host(x.get('source_url')), x.get('content_hash')) for x in pains}
    for item in sorted(direct, key=lambda x: ((x.get('metadata') or {}).get('consumer_language_score', 0), x.get('confidence', 0)), reverse=True):
        key = (consumer.host(item.get('source_url')), item.get('content_hash'))
        if key in seen:
            continue
        seen.add(key)
        pains.append(item)
        if len(pains) >= max_rows:
            break

    diagnostics = other + diagnostics + fetch_diags
    remaining = max(0, max_rows - len(pains))
    return pains[:max_rows] + diagnostics[:remaining]


def apply():
    global _APPLIED, _ORIGINAL_COLLECT
    if _APPLIED:
        return
    _ORIGINAL_COLLECT = consumer.collect_consumer_evidence
    consumer.collect_consumer_evidence = collect_consumer_evidence
    _APPLIED = True
