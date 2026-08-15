from __future__ import annotations

"""V4.3 Greek-source expansion + domain-balanced discovery.

Discovery diversity is enforced before fetch. This never relaxes V4.2 extraction,
consumer-language, market-readiness or Skeptic validation gates.
"""

import collections
import re

import consumer_evidence_v4 as consumer

_EXTRA_SOURCE_RULES=(
    ('gorun.gr','community_forum',.86),
    ('reviewit.gr','consumer_review',.78),
)
_EXTRA_COMMUNITY_DOMAINS=('gorun.gr',)
PER_DOMAIN_CAP=5
GENERIC_DOMAIN_CAP=2
GENERIC_TOTAL_CAP=12

_ORIGINAL_DISCOVER_QUERIES=consumer._discover_queries
_ORIGINAL_CONSUMER_SCORE=consumer._consumer_score
_ORIGINAL_SOURCE_FAMILY=consumer.source_family
_APPLIED=False


def _expanded_queries(term:str):
    broad=(
        (f'"{term}" πρόβλημα εμπειρία myphone','community_forum'),
        (f'"{term}" πρόβλημα εμπειρία insomnia','community_forum'),
        (f'"{term}" γνώμη εμπειρία avsite','community_forum'),
        (f'"{term}" πρόβλημα εμπειρία thelab','community_forum'),
        (f'"{term}" γνώμη εμπειρία adslgr','community_forum'),
        (f'"{term}" εμπειρία reviewit','consumer_review'),
        (f'"{term}" πρόβλημα reviewit','consumer_review'),
        (f'"{term}" γνώμη forum gorun','community_forum'),
        (f'"{term}" πρόβλημα forum gorun','community_forum'),
    )
    seen=set();out=[]
    for q,family in (*broad,*_ORIGINAL_DISCOVER_QUERIES(term)):
        key=(q,family)
        if key in seen:continue
        seen.add(key);out.append(key)
    return tuple(out)


def _strict_consumer_score(text:str,title:str,keywords:list[str],family:str,url:str=''):
    score,pain,purchase,first=_ORIGINAL_CONSUMER_SCORE(text,title,keywords,family,url)
    if score<=0:return score,pain,purchase,first
    if family=='consumer_review':
        if not first and not purchase:return 0,pain,purchase,first
        score+=5
    return score,pain,purchase,first


def _source_family_v43(url:str):
    d=consumer.host(url)
    for suffix,family,confidence in _EXTRA_SOURCE_RULES:
        if d==suffix or d.endswith('.'+suffix):return family,confidence
    return _ORIGINAL_SOURCE_FAMILY(url)


def _tokens(term:str):
    return {x for x in re.split(r'\s+',consumer.fold(term)) if len(x)>=4}


def _relevant(row,term:str):
    title=consumer.fold(row.get('title') or '')
    snippet=consumer.fold(row.get('snippet') or '')
    url=consumer.fold(row.get('url') or '')
    exact=consumer.fold(term)
    if exact and exact in f'{title} {snippet} {url}':return True
    toks=_tokens(term)
    title_hits=sum(1 for t in toks if t in title)
    all_hits=sum(1 for t in toks if t in f'{title} {snippet}')
    return title_hits>=1 or (len(toks)>=2 and all_hits>=2)


def _high_value(domain:str):
    known=(
        *getattr(consumer,'COMMUNITY_DISCOVERY_DOMAINS',()),
        *getattr(consumer,'COMMUNITY_BLOG_DOMAINS',()),
        *_EXTRA_COMMUNITY_DOMAINS,
        'reviewit.gr','skroutz.gr','bestprice.gr','insomnia.gr','reddit.com','youtube.com',
    )
    return any(domain==x or domain.endswith('.'+x) for x in known)


def _discover_urls_balanced(aliases:list[str]):
    limit=max(24,int(getattr(consumer,'MAX_DISCOVERY_URLS',60)))
    terms=[str(x).strip() for x in aliases[:4] if str(x).strip()]
    query_sets={term:list(_expanded_queries(term)) for term in terms}
    max_queries=max((len(v) for v in query_sets.values()),default=0)
    found=[];seen=set();domain_counts=collections.Counter();generic_total=0

    # Round-robin across terms/query positions. One prolific source can never
    # consume the complete discovery budget before later sources are attempted.
    for query_idx in range(max_queries):
        for term in terms:
            specs=query_sets[term]
            if query_idx>=len(specs):continue
            query,expected_family=specs[query_idx]
            added=0
            for row in consumer.search(query,5):
                url=str(row.get('url') or '');d=consumer.host(url)
                if not d or url in seen or not _relevant(row,term):continue
                high=_high_value(d);cap=PER_DOMAIN_CAP if high else GENERIC_DOMAIN_CAP
                if domain_counts[d]>=cap:continue
                if not high and generic_total>=GENERIC_TOTAL_CAP:continue
                family,confidence=_source_family_v43(url)
                seen.add(url);domain_counts[d]+=1
                if not high:generic_total+=1
                found.append({
                    **row,'query':query,'query_term':term,'source_family':family,
                    'expected_family':expected_family,'base_confidence':confidence,
                    'discovery_version':'expanded_balanced_v43',
                })
                added+=1
                if added>=2 or len(found)>=limit:break
            if len(found)>=limit:return found[:limit]
    return found[:limit]


def apply():
    global _APPLIED
    if _APPLIED:return
    existing={x[0] for x in consumer.SOURCE_RULES}
    consumer.SOURCE_RULES=tuple([x for x in _EXTRA_SOURCE_RULES if x[0] not in existing])+tuple(consumer.SOURCE_RULES)
    domains=list(consumer.COMMUNITY_DISCOVERY_DOMAINS)
    for d in _EXTRA_COMMUNITY_DOMAINS:
        if d not in domains:domains.append(d)
    consumer.COMMUNITY_DISCOVERY_DOMAINS=tuple(domains)
    consumer.source_family=_source_family_v43
    consumer._discover_queries=_expanded_queries
    consumer.discover_urls=_discover_urls_balanced
    consumer._consumer_score=_strict_consumer_score
    consumer.UA={'User-Agent':'Mozilla/5.0 SocialMarketConsumerEvidence/4.3 (+public evidence research)'}
    _APPLIED=True
