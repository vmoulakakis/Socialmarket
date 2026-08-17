from __future__ import annotations

"""Domain-bound SearXNG public-forum acquisition for Category Pain V4.7.

Why this exists:
- production smoke V4.6 proved local AI works but direct DDG/Bing site discovery
  returned zero URLs or timed out;
- generic SearX discovery returned many irrelevant merchant/public-web URLs;
- public Greek forum pages with exact product pains are discoverable, but the
  collector must bind results to the requested domain before fetching.

Safety invariants:
- search snippets are discovery diagnostics only, never pain evidence;
- only successfully fetched public page text can become pain_candidate;
- no login, CAPTCHA, anti-bot or 403 bypass;
- existing deterministic consumer/pain/taxonomy scorer remains mandatory;
- no engagement metrics are used as demand or pain proof.
"""

import concurrent.futures
import hashlib
import re
from collections import Counter
from urllib.parse import urlparse

import consumer_evidence_v4 as consumer

_ORIGINAL_COLLECT = None
_APPLIED = False

# Public, crawlable Greek discussion surfaces verified for product/use problems.
# This is a discovery allowlist, not a truth whitelist: every fetched statement
# must still pass the exact consumer scorer and downstream independent skeptic.
CATEGORY_DOMAINS = {
    'Home & Garden': (
        'kalliergo.gr', '2019.kalliergo.gr', 'bonsaiforum.gr', 'insomnia.gr',
    ),
    'Sports & Outdoors': (
        'podilates.gr', 'greekwatchforum.gr', 'howtofixit.gr', 'bodybuilding.gr', 'insomnia.gr',
    ),
    'Kids & Baby': (
        'parents.org.gr', 'parentscafe.gr', 'insomnia.gr',
    ),
    'Food & Drink': (
        'insomnia.gr',
    ),
    'Electronics & Technology': (
        'insomnia.gr', 'myphone.gr', 'thelab.gr', 'adslgr.com',
    ),
    'Automotive': (
        'forum.4troxoi.gr', 'insomnia.gr',
    ),
    'Beauty & Personal Care': (
        'reviewit.gr', 'beautyblog.gr', 'insomnia.gr',
    ),
    'Fashion & Accessories': (
        'insomnia.gr', 'reviewit.gr',
    ),
}

STOPWORDS = {
    'για','που','δεν','και','την','τον','στο','στη','στην','απο','χωρις','με','σε','του','της','ένα','ενα',
    'for','the','and','with','without','that','this','home','school','σπιτι','σχολειο','ταξιδι',
    'εξοπλισμος','equipment','προιον','product',
}


def _host(url: str) -> str:
    try:
        return (urlparse(url).hostname or '').lower().removeprefix('www.')
    except Exception:
        return ''


def _domain_match(url: str, domain: str) -> bool:
    host = _host(url)
    base = domain.lower().removeprefix('www.')
    return host == base or host.endswith('.' + base)


def _tokens(text: str) -> list[str]:
    raw = re.findall(r"[A-Za-z0-9Α-Ωα-ωΆΈΉΊΌΎΏάέήίόύώϊϋΐΰ-]+", str(text or ''))
    out = []
    for token in raw:
        folded = consumer.fold(token)
        if len(folded) < 3 or folded in STOPWORDS:
            continue
        if folded not in out:
            out.append(folded)
    return out


def _anchors(category: str, subcategory: str | None, aliases: list[str]) -> list[str]:
    candidates = []
    for raw in [subcategory, *aliases[:4], category]:
        toks = _tokens(str(raw or ''))
        if not toks:
            continue
        anchor = ' '.join(toks[:5])
        if anchor and anchor not in candidates:
            candidates.append(anchor)
    return candidates[:4]


def _result_relevant(row: dict, anchor: str, domain: str) -> bool:
    if not _domain_match(str(row.get('url') or ''), domain):
        return False
    anchor_tokens = [x for x in _tokens(anchor) if len(x) >= 3]
    if not anchor_tokens:
        return True
    hay = consumer.fold(' '.join([
        str(row.get('title') or ''), str(row.get('snippet') or ''), str(row.get('url') or '')
    ]))
    hits = sum(1 for token in anchor_tokens if token in hay)
    # One concrete token is enough for a site-bound forum result; real page text
    # and taxonomy binding still determine evidence eligibility downstream.
    return hits >= 1


def _discover(category: str, subcategory: str | None, aliases: list[str], max_urls: int = 32):
    domains = CATEGORY_DOMAINS.get(str(category or ''), ('insomnia.gr',))
    anchors = _anchors(category, subcategory, aliases)
    found = []
    diagnostics = []
    seen = set()
    for domain in domains:
        for anchor in anchors[:3]:
            queries = (
                f'site:{domain} {anchor} πρόβλημα',
                f'site:{domain} {anchor} εμπειρία',
                f'site:{domain} {anchor} αγορά',
            )
            for query in queries:
                rows = consumer.search(query, 8)
                accepted = 0
                rejected_domain = 0
                rejected_binding = 0
                for row in rows:
                    url = str(row.get('url') or '')
                    if not _domain_match(url, domain):
                        rejected_domain += 1
                        continue
                    if not _result_relevant(row, anchor, domain):
                        rejected_binding += 1
                        continue
                    if url in seen:
                        continue
                    seen.add(url)
                    found.append({
                        **row,
                        'query': query,
                        'query_term': anchor,
                        'expected_domain': domain,
                    })
                    accepted += 1
                    if len(found) >= max_urls:
                        break
                diagnostics.append({
                    'source_kind': 'consumer_discovery',
                    'source_url': f'searxng://site/{domain}',
                    'title': f'Domain-bound forum discovery: {domain} / {anchor}',
                    'body': '',
                    'collector': 'searx_forum_discovery_v47',
                    'confidence': .62 if accepted else .42,
                    'metadata': {
                        'query': query,
                        'query_term': anchor,
                        'geography': 'GR',
                        'source_family': 'discovery_engine',
                        'evidence_mode': 'discovery_only',
                        'eligible_for_pain_audit': False,
                        'expected_domain': domain,
                        'search_results': len(rows),
                        'accepted_urls': accepted,
                        'rejected_wrong_domain': rejected_domain,
                        'rejected_weak_binding': rejected_binding,
                        'retrieval_version': 'searx_forum_v4.7',
                        'metric_semantics': 'URL discovery diagnostic only; snippets are never pain proof',
                    },
                })
                if len(found) >= max_urls:
                    return found[:max_urls], diagnostics
    return found[:max_urls], diagnostics


def _explain_reject(segment: str, title: str, keywords: list[str], family: str, url: str) -> str:
    folded = consumer.fold(segment)
    if any(x in folded for x in consumer.BOILERPLATE):
        return 'boilerplate'
    pain = [x for x in consumer.PAIN_STEMS if x in folded]
    if not pain:
        return 'no_pain_language'
    taxonomy = consumer._keyword_hits(segment, keywords, title)
    title_binding = bool(consumer._keyword_hits('', keywords, title))
    if not taxonomy and not title_binding:
        return 'no_taxonomy_binding'
    if consumer._looks_editorial(title, url, family):
        return 'editorial_surface'
    purchase = [x for x in consumer.PURCHASE_STEMS if x in folded]
    first = any(x in folded for x in consumer.FIRST_PERSON_STEMS)
    if family in ('community_forum', 'social_forum', 'marketplace_review', 'social_video') and not first and not purchase:
        return 'no_first_person_or_purchase'
    return 'score_below_threshold'


def _extract_one(row: dict, keywords: list[str]):
    fetched, text, error = consumer._fetch_text(row)
    family = 'community_forum'
    evidence = []
    reasons = Counter()
    segment_count = 0
    if text:
        title = str(fetched.get('title') or '')
        for segment in consumer._split_segments(text):
            segment_count += 1
            score, pain, purchase, first = consumer._consumer_score(segment, title, keywords, family, row['url'])
            if score < 10:
                reasons[_explain_reject(segment, title, keywords, family, row['url'])] += 1
                continue
            digest = hashlib.sha256(segment.encode('utf-8', 'ignore')).hexdigest()
            evidence.append({
                'source_kind': 'pain_candidate',
                'source_url': row['url'],
                'title': title[:500],
                'body': segment[:1600],
                'collector': 'searx_forum_extract_v47',
                'confidence': round(min(.95, .80 + min(.10, score * .002)), 3),
                'content_hash': digest,
                'metadata': {
                    'query': row.get('query'),
                    'query_term': row.get('query_term'),
                    'expected_domain': row.get('expected_domain'),
                    'geography': 'GR',
                    'source_family': family,
                    'evidence_mode': 'fetched_public_forum_text',
                    'consumer_text': True,
                    'page_extracted': True,
                    'eligible_for_pain_audit': True,
                    'pain_language': pain[:12],
                    'purchase_language': purchase[:10],
                    'first_person_signal': first,
                    'consumer_language_score': score,
                    'ugc_surface': True,
                    'retrieval_version': 'searx_forum_v4.7',
                    'source_role': 'pain_only',
                    'social_metrics_eligible_for_demand': False,
                    'metric_semantics': 'actual fetched public forum text; search snippets/engagement excluded',
                },
            })
    diagnostic = {
        'source_kind': 'consumer_discovery',
        'source_url': row['url'],
        'title': str(row.get('title') or '')[:500],
        'body': str(row.get('snippet') or '')[:700],
        'collector': 'searx_forum_fetch_v47',
        'confidence': .45 if error else .66,
        'metadata': {
            'query': row.get('query'),
            'query_term': row.get('query_term'),
            'expected_domain': row.get('expected_domain'),
            'geography': 'GR',
            'source_family': family,
            'evidence_mode': 'discovery_only',
            'eligible_for_pain_audit': False,
            'fetch_error': error,
            'page_extracted': bool(text),
            'segments_examined': segment_count,
            'pain_candidates_emitted': len(evidence),
            'reject_reasons': dict(reasons),
            'retrieval_version': 'searx_forum_v4.7',
        },
    }
    evidence.sort(key=lambda x: (x['metadata']['consumer_language_score'], x['confidence']), reverse=True)
    return evidence[:16], diagnostic


def _extract(found: list[dict], keywords: list[str]):
    evidence = []
    diagnostics = []
    if not found:
        return evidence, diagnostics
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(6, len(found))) as pool:
        futures = [pool.submit(_extract_one, row, keywords) for row in found]
        for future in concurrent.futures.as_completed(futures):
            rows, diagnostic = future.result()
            evidence.extend(rows)
            diagnostics.append(diagnostic)
    return evidence, diagnostics


def collect_consumer_evidence(category: str, subcategory: str | None, aliases: list[str], keywords: list[str], max_rows: int = 100):
    base = _ORIGINAL_COLLECT(category, subcategory, aliases, keywords, max_rows=max_rows)
    found, discovery_diag = _discover(category, subcategory, aliases, max_urls=32)
    direct, fetch_diag = _extract(found, keywords)

    pains = [x for x in base if x.get('source_kind') == 'pain_candidate']
    diagnostics = [x for x in base if x.get('source_kind') != 'pain_candidate']
    seen = {(consumer.host(x.get('source_url')), x.get('content_hash')) for x in pains}
    for item in sorted(direct, key=lambda x: (x.get('confidence', 0), (x.get('metadata') or {}).get('consumer_language_score', 0)), reverse=True):
        key = (consumer.host(item.get('source_url')), item.get('content_hash'))
        if key in seen:
            continue
        seen.add(key)
        pains.append(item)
        if len(pains) >= max_rows:
            break

    diagnostics.extend(discovery_diag)
    diagnostics.extend(fetch_diag)
    # Keep enough diagnostics to make the funnel auditable without crowding out
    # real pain evidence.
    return pains + diagnostics[:min(90, max_rows)]


def apply():
    global _APPLIED, _ORIGINAL_COLLECT
    if _APPLIED:
        return
    _ORIGINAL_COLLECT = consumer.collect_consumer_evidence
    consumer.collect_consumer_evidence = collect_consumer_evidence
    _APPLIED = True
