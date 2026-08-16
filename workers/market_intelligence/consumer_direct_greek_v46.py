from __future__ import annotations

"""Direct Greece-first forum discovery for Category Pain V4.6.

Search engines are used ONLY to discover public Greek forum/review URLs. Search
snippets are never persisted as pain proof. Every candidate URL must be fetched
publicly and its actual page text must pass the existing V4 consumer scorer and
the downstream DeepSeek skeptic/cross-source validation gates.

No likes, views, follower counts or engagement metrics are collected or used.
No login, anti-bot bypass, CAPTCHA bypass or restricted API is used.
"""

import concurrent.futures
import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from urllib.parse import parse_qs, unquote, urlparse

import requests
import consumer_evidence_v4 as consumer

UA={'User-Agent':'Mozilla/5.0 (compatible; SocialMarketGreekPain/4.6; public research discovery)'}
DDG='https://html.duckduckgo.com/html/'
BING='https://www.bing.com/search'
DISCOVERY_WORKERS=6
FETCH_WORKERS=6

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

STOPWORDS={
    'για','που','δεν','και','την','τον','στο','στη','στην','απο','χωρις','με','σε','του','της','ένα','ενα',
    'for','the','and','with','without','that','this','home','school','σπιτι','σχολειο','ταξιδι',
}
_ORIGINAL_COLLECT=None
_APPLIED=False


class _Results(HTMLParser):
    def __init__(self):
        super().__init__();self.urls=[]
    def handle_starttag(self,tag,attrs):
        if tag!='a':return
        href=str(dict(attrs).get('href') or '')
        # Collect all anchors; _unwrap/_allowed performs the strict domain filter.
        if href:self.urls.append(href)


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
    if href.startswith('/'):href='https://duckduckgo.com'+href
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


def _unique(urls,limit):
    out=[];seen=set()
    for url in urls:
        if not url or url in seen or not _allowed(url):continue
        seen.add(url);out.append(url)
        if len(out)>=limit:break
    return out


def _ddg(query:str,limit:int=8):
    try:
        r=requests.get(DDG,params={'q':query,'kl':'gr-el'},headers=UA,timeout=12)
        if not r.ok:return [],f'http_{r.status_code}'
        p=_Results();p.feed(r.text[:1_500_000])
        return _unique([_unwrap(h) for h in p.urls],limit),None
    except Exception as exc:return [],type(exc).__name__


def _bing(query:str,limit:int=8):
    """Bing RSS is a discovery-only, no-key fallback when DDG under-returns."""
    try:
        r=requests.get(BING,params={'q':query,'format':'rss','setlang':'el'},headers=UA,timeout=12)
        if not r.ok:return [],f'http_{r.status_code}'
        root=ET.fromstring(r.content[:2_000_000])
        urls=[]
        for item in root.findall('.//item'):
            link=(item.findtext('link') or '').strip()
            if link:urls.append(link)
        return _unique(urls,limit),None
    except Exception as exc:return [],type(exc).__name__


def _search_anchor(term:str)->str:
    # Long exact pain phrases destroy search recall. Keep concrete product tokens
    # and let actual fetched page text + skeptic gates decide whether pain exists.
    tokens=re.findall(r"[A-Za-z0-9Α-Ωα-ωΆΈΉΊΌΎΏάέήίόύώϊϋΐΰ-]+",str(term or ''))
    kept=[]
    for token in tokens:
        f=consumer.fold(token)
        if len(f)<3 or f in STOPWORDS:continue
        kept.append(token)
    return ' '.join(kept[:5]) or str(term or '').strip()


def _queries(category:str,aliases:list[str]):
    domains=CATEGORY_DOMAINS.get(str(category or ''),DEFAULT_DOMAINS)
    terms=[x for x in aliases[:2] if str(x or '').strip()]
    out=[]
    for term in terms:
        anchor=_search_anchor(str(term))
        for d in domains[:4]:
            # No exact full-phrase quotes: product anchor maximizes recall; pain is
            # validated only after fetching the actual public page.
            out.append((str(term),anchor,d,f'site:{d} {anchor}'))
    return out


def _discover_one(spec):
    term,anchor,domain,query=spec
    ddg_urls,ddg_error=_ddg(query,6)
    bing_urls=[];bing_error=None
    if len(ddg_urls)<2:
        bing_urls,bing_error=_bing(query,6)
    urls=_unique([*ddg_urls,*bing_urls],6)
    errors=[x for x in (ddg_error,bing_error) if x]
    diagnostic={
        'source_kind':'consumer_discovery','source_url':f'https://html.duckduckgo.com/html/?q={query}',
        'title':f'Direct Greek forum discovery: {domain} / {anchor}','body':'',
        'collector':'greek_forum_search_discovery_v46','confidence':.40 if errors and not urls else .60,
        'metadata':{
            'query':query,'query_term':term,'search_anchor':anchor,'geography':'GR','source_family':'discovery_engine',
            'evidence_mode':'discovery_only','eligible_for_pain_audit':False,
            'fetch_error':';'.join(errors) if errors else None,'result_count':len(urls),
            'ddg_results':len(ddg_urls),'bing_results':len(bing_urls),
            'retrieval_version':'greece_direct_forum_v4.6',
            'metric_semantics':'URL discovery diagnostic only; search snippets/engagement are never pain or demand evidence'
        }
    }
    return spec,urls,diagnostic


def _discover(category:str,aliases:list[str],max_urls:int=24):
    specs=_queries(category,aliases);found=[];seen=set();diagnostics=[]
    if not specs:return found,diagnostics
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(DISCOVERY_WORKERS,len(specs))) as pool:
        futures=[pool.submit(_discover_one,s) for s in specs]
        for future in concurrent.futures.as_completed(futures):
            spec,urls,diagnostic=future.result();term,_anchor,_domain_name,query=spec
            diagnostics.append(diagnostic)
            for url in urls:
                if url in seen:continue
                seen.add(url);found.append({'url':url,'title':'','snippet':'','query':query,'query_term':term})
                if len(found)>=max_urls:break
    return found[:max_urls],diagnostics


def _fetch_one(row,keywords):
    fetched,text,error=consumer._fetch_text(row)
    diagnostic={
        'source_kind':'consumer_discovery','source_url':row['url'],'title':'','body':'',
        'collector':'direct_greek_forum_fetch_v46','confidence':.44 if error else .64,
        'metadata':{
            'query':row.get('query'),'query_term':row.get('query_term'),'geography':'GR',
            'source_family':consumer.source_family(row['url'])[0],
            'evidence_mode':'discovery_only','eligible_for_pain_audit':False,
            'fetch_error':error,'retrieval_version':'greece_direct_forum_v4.6'
        }
    }
    evidence=[]
    if text:
        for item in consumer._evidence_from_page(fetched,text,keywords):
            meta=dict(item.get('metadata') or {})
            meta.update({
                'retrieval_version':'greece_direct_forum_v4.6','source_role':'pain_only',
                'social_metrics_eligible_for_demand':False,
                'metric_semantics':'actual fetched public consumer/forum text; no likes/views/search snippets used'
            })
            evidence.append({**item,'collector':'direct_greek_forum_extract_v46','metadata':meta})
    return evidence,diagnostic


def _extract(found:list[dict],keywords:list[str]):
    out=[];diagnostics=[]
    if not found:return out,diagnostics
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(FETCH_WORKERS,len(found))) as pool:
        futures=[pool.submit(_fetch_one,row,keywords) for row in found]
        for future in concurrent.futures.as_completed(futures):
            evidence,diagnostic=future.result();out.extend(evidence);diagnostics.append(diagnostic)
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
