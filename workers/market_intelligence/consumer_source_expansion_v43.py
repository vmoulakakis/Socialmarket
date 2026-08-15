from __future__ import annotations

"""V4.3 source expansion for Greek consumer pain evidence.

This module expands discovery only. It does NOT relax the V4.2 evidence or
validation gates. Every candidate URL must still be publicly fetchable and yield
extracted product-bound consumer text before it can enter the skeptic audit.
"""

import consumer_evidence_v4 as consumer

_EXTRA_SOURCE_RULES=(
    ('gorun.gr','community_forum',.86),
    ('reviewit.gr','consumer_review',.78),
)
_EXTRA_COMMUNITY_DOMAINS=(
    'gorun.gr',
)

_ORIGINAL_DISCOVER_QUERIES=consumer._discover_queries
_ORIGINAL_CONSUMER_SCORE=consumer._consumer_score
_APPLIED=False


def _expanded_queries(term:str):
    """Prepend broad discovery fallbacks before the existing site-scoped queries.

    Some SearXNG engines under-return on site: filters. These broad queries name
    the target Greek communities but actual source family is determined from the
    returned URL, and the page still has to pass full extraction/scoring.
    """
    broad=(
        (f'{term} πρόβλημα εμπειρία myphone','community_forum'),
        (f'{term} πρόβλημα εμπειρία insomnia','community_forum'),
        (f'{term} γνώμη εμπειρία avsite','community_forum'),
        (f'{term} πρόβλημα εμπειρία thelab','community_forum'),
        (f'{term} γνώμη εμπειρία adslgr','community_forum'),
        (f'{term} εμπειρία reviewit','consumer_review'),
        (f'{term} πρόβλημα reviewit','consumer_review'),
        (f'{term} γνώμη forum gorun','community_forum'),
        (f'{term} πρόβλημα forum gorun','community_forum'),
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
        # ReviewIt contains many merchant/service complaints. A review may support
        # product pain only when the segment also contains concrete purchase/use
        # or first-person product experience. Taxonomy/pain binding is already
        # enforced by the base scorer before reaching this branch.
        if not first and not purchase:return 0,pain,purchase,first
        score+=5
    return score,pain,purchase,first


def apply():
    global _APPLIED
    if _APPLIED:return
    existing={x[0] for x in consumer.SOURCE_RULES}
    consumer.SOURCE_RULES=tuple([x for x in _EXTRA_SOURCE_RULES if x[0] not in existing])+tuple(consumer.SOURCE_RULES)
    domains=list(consumer.COMMUNITY_DISCOVERY_DOMAINS)
    for d in _EXTRA_COMMUNITY_DOMAINS:
        if d not in domains:domains.append(d)
    consumer.COMMUNITY_DISCOVERY_DOMAINS=tuple(domains)
    consumer._discover_queries=_expanded_queries
    consumer._consumer_score=_strict_consumer_score
    consumer.UA={'User-Agent':'Mozilla/5.0 SocialMarketConsumerEvidence/4.3 (+public evidence research)'}
    _APPLIED=True
