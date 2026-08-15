from __future__ import annotations

import os
from urllib.parse import urlparse

import requests

SEARXNG=os.getenv('SEARXNG_BASE_URL','http://127.0.0.1:8080').rstrip('/')
UA={'User-Agent':'Mozilla/5.0 SocialMarketAuthoritativeContext/2.0'}
SOURCES=(
    {'domain':'statistics.gr','source_kind':'official_context','source_class':'official_statistics','authority_weight':1.0,'themes':('λιανικό εμπόριο Ελλάδα','Έρευνα Οικογενειακών Προϋπολογισμών','ηλεκτρονικό εμπόριο νοικοκυριά')},
    {'domain':'ec.europa.eu','source_kind':'official_context','source_class':'public_institution','authority_weight':1.0,'themes':('Eurostat Greece e-commerce','Eurostat Greece online shopping','Eurostat Greece retail trade')},
    {'domain':'greekecommerce.gr','source_kind':'industry_context','source_class':'industry_primary','authority_weight':.82,'themes':('έρευνα ηλεκτρονικού εμπορίου Ελλάδα','Greek e-commerce research')},
)


def _host(url:str)->str:
    try:return urlparse(url).netloc.lower().split(':')[0].removeprefix('www.')
    except:return ''


def _fold(x:str)->str:
    import unicodedata
    x=unicodedata.normalize('NFKD',str(x or '')).encode('ascii','ignore').decode().lower()
    return ' '.join(x.replace('&',' ').replace('/',' ').replace('-',' ').split())


def _search(q:str,limit:int=5):
    try:
        r=requests.get(f'{SEARXNG}/search',params={'q':q,'format':'json','language':'el-GR','safesearch':1},headers=UA,timeout=25)
        r.raise_for_status()
        return [{'url':x.get('url',''),'title':x.get('title',''),'snippet':x.get('content') or x.get('snippet') or ''} for x in (r.json().get('results') or [])[:limit*3]]
    except Exception:
        return []


def _row(source,row,query,scope,taxonomy_direct,confidence):
    return {
        'source_kind':source['source_kind'],
        'source_url':row['url'],
        'title':str(row.get('title') or '')[:500],
        'body':str(row.get('snippet') or '')[:1800],
        'collector':'searxng_authoritative_context_v2',
        'confidence':confidence,
        'metadata':{
            'query':query,
            'geography':'GR',
            'context_only':True,
            'context_scope':scope,
            'taxonomy_direct':taxonomy_direct,
            'source_class':source['source_class'],
            'authority_weight':source['authority_weight'],
            'does_not_feed_demand_score':True,
            'context_semantics':'official/industry exogenous context; never search volume, market size or category demand unless the source directly measures it',
            'retrieval_version':'greek_authoritative_context_v2'
        }
    }


def authoritative_context_rows(category,subcategory,aliases,keywords):
    """Return direct category context when available, otherwise a small Greece-macro fallback.

    Fallback observations are intentionally lower-confidence and taxonomy_direct=False.
    They are context-only and must never enter demand-score arithmetic.
    """
    out=[]
    normalized_keywords={_fold(x) for x in (keywords or []) if len(_fold(x))>=4}
    direct_terms=[]
    for x in [*(aliases or [])[:3],subcategory or '',category or '']:
        f=_fold(x)
        if f and f not in {_fold(v) for v in direct_terms}:direct_terms.append(str(x))

    for source in SOURCES:
        source_rows=[]
        # Pass 1: category/subcategory-aware authoritative evidence.
        for term in direct_terms[:4]:
            for theme in source['themes'][:2]:
                q=f"site:{source['domain']} {term} {theme}"
                for r in _search(q,4):
                    if source['domain'] not in _host(r['url']):continue
                    hay=_fold(f"{r.get('title','')} {r.get('snippet','')} {r.get('url','')}")
                    exact=_fold(term)
                    matches=(3 if exact and exact in hay else 0)+sum(1 for k in normalized_keywords if k in hay)
                    if matches<1:continue
                    conf=.93 if source['authority_weight']>=1 else .80
                    source_rows.append(_row(source,r,q,'category_or_subcategory',True,conf))

        # Pass 2: Greece-wide macro/digital-commerce context if no taxonomy-direct row exists.
        # This prevents a false impression that Greece has no official context merely because
        # ELSTAT/Eurostat do not publish the exact SocialMarket taxonomy label.
        if not source_rows:
            for theme in source['themes'][:2]:
                q=f"site:{source['domain']} {theme}"
                for r in _search(q,4):
                    if source['domain'] not in _host(r['url']):continue
                    conf=.76 if source['authority_weight']>=1 else .66
                    source_rows.append(_row(source,r,q,'greece_macro',False,conf))
                    if len(source_rows)>=2:break
                if len(source_rows)>=2:break

        seen=set()
        for e in source_rows:
            key=(e['source_url'],e['title'])
            if key in seen:continue
            seen.add(key);out.append(e)
            if sum(1 for x in out if x['metadata']['source_class']==source['source_class'])>=4:break

    dedup=[];seen=set()
    for e in out:
        key=(e['source_kind'],e['source_url'],e['title'])
        if key in seen:continue
        seen.add(key);dedup.append(e)
    return dedup[:18]
