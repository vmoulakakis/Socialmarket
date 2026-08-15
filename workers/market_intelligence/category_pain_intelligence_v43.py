from __future__ import annotations

import collections
import re
import threading

import consumer_evidence_v4 as consumer

# Keep the V4.2 native-parser safety invariant: HTTP remains concurrent while
# Trafilatura/libxml parsing is serialized in one process-wide critical section.
_EXTRACT_LOCK=threading.Lock()
_ORIGINAL_EXTRACT=consumer.trafilatura.extract


def _serial_extract(*args,**kwargs):
    with _EXTRACT_LOCK:
        return _ORIGINAL_EXTRACT(*args,**kwargs)


consumer.trafilatura.extract=_serial_extract

PER_DOMAIN_CAP=5
GENERIC_DOMAIN_CAP=2
GENERIC_TOTAL_CAP=12
MAX_TOTAL=max(24,int(getattr(consumer,'MAX_DISCOVERY_URLS',60)))
HIGH_VALUE_DOMAINS=tuple(dict.fromkeys((
    *consumer.COMMUNITY_DISCOVERY_DOMAINS,
    *consumer.COMMUNITY_BLOG_DOMAINS,
    'skroutz.gr','bestprice.gr','insomnia.gr','reddit.com','youtube.com',
)))


def _term_tokens(term:str):
    f=consumer.fold(term)
    return {x for x in re.split(r'\s+',f) if len(x)>=4}


def _relevant(row,term:str):
    title=consumer.fold(row.get('title') or '')
    snippet=consumer.fold(row.get('snippet') or '')
    url=consumer.fold(row.get('url') or '')
    exact=consumer.fold(term)
    toks=_term_tokens(term)
    # Exact phrase anywhere is strong enough. Otherwise require a meaningful
    # taxonomy token in the title OR two meaningful tokens across title/snippet.
    if exact and exact in f'{title} {snippet} {url}':return True
    title_hits=sum(1 for t in toks if t in title)
    all_hits=sum(1 for t in toks if t in f'{title} {snippet}')
    return title_hits>=1 or (len(toks)>=2 and all_hits>=2)


def _query_specs(term:str):
    specs=[]
    for domain_name in consumer.COMMUNITY_DISCOVERY_DOMAINS:
        specs.extend((
            (domain_name,f'site:{domain_name} "{term}"','community_forum'),
            (domain_name,f'site:{domain_name} "{term}" πρόβλημα','community_forum'),
            (domain_name,f'site:{domain_name} "{term}" γνώμη εμπειρία','community_forum'),
        ))
    for domain_name in consumer.COMMUNITY_BLOG_DOMAINS:
        specs.extend((
            (domain_name,f'site:{domain_name} "{term}" σχόλια','community_blog'),
            (domain_name,f'site:{domain_name} "{term}" εμπειρία','community_blog'),
        ))
    specs.extend((
        ('skroutz.gr',f'site:skroutz.gr/s/ "{term}"','marketplace_review'),
        ('bestprice.gr',f'site:bestprice.gr "{term}" αξιολογήσεις','marketplace_review'),
        ('insomnia.gr',f'site:insomnia.gr "{term}"','community_forum'),
        ('reddit.com',f'site:reddit.com/r/greece "{term}"','social_forum'),
        ('youtube.com',f'site:youtube.com "{term}" review ελληνικά','social_video'),
    ))
    return specs


def _add_rows(out,seen,domain_counts,rows,term,query,expected_family,per_query=2):
    added=0
    for row in rows:
        url=str(row.get('url') or '')
        d=consumer.host(url)
        if not d or url in seen or not _relevant(row,term):continue
        cap=PER_DOMAIN_CAP if any(d==x or d.endswith('.'+x) for x in HIGH_VALUE_DOMAINS) else GENERIC_DOMAIN_CAP
        if domain_counts[d]>=cap:continue
        family,confidence=consumer.source_family(url)
        seen.add(url);domain_counts[d]+=1;added+=1
        out.append({
            **row,'query':query,'query_term':term,'source_family':family,
            'expected_family':expected_family,'base_confidence':confidence,
            'discovery_version':'domain_balanced_exact_phrase_v43',
        })
        if added>=per_query:return


def discover_urls_v43(aliases:list[str]):
    """Domain-balanced discovery so one forum can never consume the evidence budget.

    Round 1 gives each high-value Greek/community source a chance using exact-phrase
    taxonomy queries. Round 2 adds generic public-web fallback with strict caps.
    Search snippets remain discovery-only; validation still requires fetched and
    extracted consumer text plus the unchanged Skeptic cross-source gates.
    """
    out=[];seen=set();domain_counts=collections.Counter()
    terms=[str(x).strip() for x in aliases[:4] if str(x).strip()]

    # Round-robin by query position rather than exhausting one domain first.
    specs_by_term={term:_query_specs(term) for term in terms}
    max_specs=max((len(v) for v in specs_by_term.values()),default=0)
    for i in range(max_specs):
        for term in terms:
            specs=specs_by_term[term]
            if i>=len(specs):continue
            _,query,expected=specs[i]
            _add_rows(out,seen,domain_counts,consumer.search(query,4),term,query,expected,per_query=2)
            if len(out)>=MAX_TOTAL-GENERIC_TOTAL_CAP:return out[:MAX_TOTAL]

    # Generic web fallback is intentionally small and diverse.
    generic_added=0
    for term in terms:
        for query in (
            f'"{term}" πρόβλημα κριτική Ελλάδα',
            f'"{term}" μειονεκτήματα εμπειρία αγοράς',
            f'"{term}" δεν αξίζει εναλλακτική',
        ):
            before=len(out)
            _add_rows(out,seen,domain_counts,consumer.search(query,6),term,query,'public_web',per_query=4)
            generic_added+=len(out)-before
            if generic_added>=GENERIC_TOTAL_CAP or len(out)>=MAX_TOTAL:return out[:MAX_TOTAL]
    return out[:MAX_TOTAL]


consumer.discover_urls=discover_urls_v43

import category_pain_intelligence_v4 as v4  # noqa: E402


if __name__=='__main__':
    v4.main()
