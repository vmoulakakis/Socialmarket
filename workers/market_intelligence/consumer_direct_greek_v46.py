from __future__ import annotations

"""Direct Greece-first forum discovery for Category Pain V4.6.

SearXNG remains the general market discovery layer, but niche consumer pain must
not disappear when a metasearch engine under-returns site-scoped forum results.
This module uses DuckDuckGo's public HTML search only to discover URLs on a
small allowlist of Greek consumer communities. Search snippets are NEVER pain
proof: every URL must be fetched publicly and its actual page text must pass the
existing V4 consumer scorer and the downstream DeepSeek skeptic/cross-source
validation gates.

No likes, views, follower counts or engagement metrics are collected or used.
No login, anti-bot bypass, CAPTCHA bypass or restricted API is used.
"""

import hashlib
import re
from html.parser import HTMLParser
from urllib.parse import parse_qs, unquote, urlparse

import requests
import consumer_evidence_v4 as consumer

UA={
    'User-Agent':'Mozilla/5.0 (compatible; SocialMarketGreekPain/4.6; public research discovery)'
}
DDG='https://html.duckduckgo.com/html/'

# Domain selection is intentionally small and category-aware. This makes the
# collector useful for cross-source validation instead of spraying the web.
DEFAULT_DOMAINS=('insomnia.gr','myphone.gr','thelab.gr','reviewit.gr')
CATEGORY_DOMAINS={
    'Electronics & Technology':('insomnia.gr','adslgr.com','thelab.gr','myphone.gr'),
    'Automotive':('forum.4troxoi.gr','insomnia.gr','myphone.gr'),
    'Sports & Outdoors':('gorun.gr','insomnia.gr','thelab.gr'),
    'Beauty & Personal Care':('reviewit.gr','beautyblog.gr','insomnia.gr'),
    'Home & Garden':('insomnia.gr','thelab.gr','reviewit.gr'),
    'Fashion & Accessories':('insomnia.gr','reviewit.gr','gorun.gr'),
    'Kids & Baby':('insomnia.gr','reviewit.gr','myphone.gr'),
    'Books & Education':('insomnia.gr','reviewit.gr'),
    'Pets':('insomnia.gr','reviewit.gr'),
}
ALLOWED=set(DEFAULT_DOMAINS)
for values in CATEGORY_DOMAINS.values():ALLOWED.update(values)

_ORIGINAL_COLLECT=None
_APPLIED=False


class _Results(HTMLParser):
    def __init__(self):
        super().__init__();self.urls=[]
    def handle_starttag(self,tag,attrs):
        if tag!='a':return
        a=dict(attrs);cls=str(a.get('class') or '')
        href=str(a.get('href') or '')
        if href and ('result__a' in cls or 'result-link' in cls):self.urls.append(href)


def _host(url:str)->str:
    try:return (urlparse(url).hostname or '').lower().removeprefix('www.')
    except Exception:return ''


def _allowed(url:str)->bool:
    d=_host(url)
    return any(d==x or d.endswith('.'+x) for x in ALLOWED)


def _unwrap(href:str)->str|None:
    href=str(href or '').strip()
    if not href:return None
    if href.startswith('//'):href='https:'+href
    if href.startswith('/'):
        href='https://duckduckgo.com'+href
    try:
        u=urlparse(href)
        if 'duckduckgo.com' in (u.hostname or ''):
            q=parse_qs(u.query)
            target=(q.get('uddg') or q.get('u') or [None])[0]
            if target:href=unquote(target)
        u=urlparse(href)
        if u.scheme not in ('http','https') or not u.hostname:return None
        return href if _allowed(href) else None
    except Exception:return None


def _ddg(query:str,limit:int=8):
    try:
        r=requests.get(DDG,params={'q':query,'kl':'gr-el'},headers=UA,timeout=25)
        if not r.ok:return [],f'http_{r.status_code}'
        p=_Results();p.feed(r.text[:1_500_000])
        out=[];seen=set()
        for href in p.urls:
            url=_unwrap(href)
            if not url or url in seen:continue
            seen.add(url);out.append(url)
            if len(out)>=limit:break
        return out,None
    except Exception as exc:
        return [],type(exc).__name__


def _queries(category:str,aliases:list[str]):
    domains=CATEGORY_DOMAINS.get(str(category or ''),DEFAULT_DOMAINS)
    # Two concrete niche terms are enough to keep direct discovery bounded.
    terms=[x for x in aliases[:2] if str(x or '').strip()]
    out=[]
    for term in terms:
        for d in domains[:4]:
            out.append((str(term),d,f'site:{d} "{term}"'))
    return out


def _discover(category:str,aliases:list[str],max_urls:int=24):
    found=[];seen=set();diagnostics=[]
    for term,domain,query in _queries(category,aliases):
        urls,error=_ddg(query,6)
        diagnostics.append({
            'source_kind':'consumer_discovery','source_url':f'https://html.duckduckgo.com/html/?q={query}',
            'title':f'Direct Greek forum discovery: {domain} / {term}','body':'',
            'collector':'duckduckgo_greek_forum_discovery_v46','confidence':.40 if error else .58,
            'metadata':{
                'query':query,'query_term':term,'geography':'GR','source_family':'discovery_engine',
                'evidence_mode':'discovery_only','eligible_for_pain_audit':False,
                'fetch_error':error,'result_count':len(urls),'retrieval_version':'greece_direct_forum_v4.6',
                'metric_semantics':'URL discovery diagnostic only; search snippets/engagement are never pain or demand evidence'
            }
        })
        for url in urls:
            if url in seen:continue
            seen.add(url);found.append({'url':url,'title':'','snippet':'','query':query,'query_term':term})
            if len(found)>=max_urls:return found,diagnostics
    return found,diagnostics


def _extract(found:list[dict],keywords:list[str]):
    out=[];diagnostics=[]
    for row in found:
        fetched,text,error=consumer._fetch_text(row)
        diagnostics.append({
            'source_kind':'consumer_discovery','source_url':row['url'],'title':'','body':'',
            'collector':'direct_greek_forum_fetch_v46','confidence':.44 if error else .64,
            'metadata':{
                'query':row.get('query'),'query_term':row.get('query_term'),'geography':'GR',
                'source_family':consumer.source_family(row['url'])[0],
                'evidence_mode':'discovery_only','eligible_for_pain_audit':False,
                'fetch_error':error,'retrieval_version':'greece_direct_forum_v4.6'
            }
        })
        if not text:continue
        for evidence in consumer._evidence_from_page(fetched,text,keywords):
            meta=dict(evidence.get('metadata') or {})
            meta.update({
                'retrieval_version':'greece_direct_forum_v4.6','source_role':'pain_only',
                'social_metrics_eligible_for_demand':False,
                'metric_semantics':'actual fetched public consumer/forum text; no likes/views/search snippets used'
            })
            evidence={**evidence,'collector':'direct_greek_forum_extract_v46','metadata':meta}
            out.append(evidence)
    return out,diagnostics


def collect_consumer_evidence(category:str,subcategory:str|None,aliases:list[str],keywords:list[str],max_rows:int=100):
    base=_ORIGINAL_COLLECT(category,subcategory,aliases,keywords,max_rows=max_rows)
    found,discovery_diag=_discover(category,aliases,24)
    direct,fetch_diag=_extract(found,keywords)

    pains=[x for x in base if x.get('source_kind')=='pain_candidate']
    diagnostics=[x for x in base if x.get('source_kind')!='pain_candidate']
    seen={(consumer.host(x.get('source_url')),x.get('content_hash')) for x in pains}
    for e in sorted(direct,key=lambda x:(x.get('confidence',0),(x.get('metadata') or {}).get('consumer_language_score',0)),reverse=True):
        key=(consumer.host(e.get('source_url')),e.get('content_hash'))
        if key in seen:continue
        seen.add(key);pains.append(e)
        if len(pains)>=max_rows:break
    diagnostics.extend(discovery_diag);diagnostics.extend(fetch_diag)
    return pains+diagnostics[:min(60,max_rows)]


def apply():
    global _APPLIED,_ORIGINAL_COLLECT
    if _APPLIED:return
    _ORIGINAL_COLLECT=consumer.collect_consumer_evidence
    consumer.collect_consumer_evidence=collect_consumer_evidence
    _APPLIED=True
