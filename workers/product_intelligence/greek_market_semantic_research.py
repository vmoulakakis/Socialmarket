#!/usr/bin/env python3
"""Evidence-first Greek market research for AFFINITY Semantic Marketplace 200.

This module performs deterministic web-evidence collection on a bounded shortlist.
It does not claim that a product is absent from Greece merely because one marketplace
has no result. Functional-equivalent judgment is intentionally left to the Research
+ Skeptic AI layer, which receives the evidence collected here.
"""
from __future__ import annotations

import concurrent.futures
import html
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any

MAJOR_SURFACES=(
    'skroutz.gr',
    'bestprice.gr',
    'public.gr',
    'kotsovolos.gr',
    'plaisio.gr',
)
USER_AGENT='Mozilla/5.0 (compatible; SocialMarketAI/1.0; +https://socialmarket-theta.vercel.app)'
STOP={
    'with','from','this','that','your','for','and','the','new','pro','plus','mini','portable','electric',
    'machine','tool','tools','home','professional','smart','automatic','wireless','black','white','blue',
    'set','kit','pcs','piece','pieces','version','model','product','device','high','quality','best','sale',
}


def fold(value:Any)->str:
    text=html.unescape(str(value or '')).casefold()
    text=re.sub(r'[^a-z0-9α-ωάέήίόύώϊϋΐΰ]+',' ',text)
    return ' '.join(text.split())


def tokens(value:Any)->list[str]:
    return [x for x in fold(value).split() if len(x)>=3 and x not in STOP]


def model_tokens(value:Any)->list[str]:
    out=[]
    for t in tokens(value):
        if any(c.isdigit() for c in t) and any(c.isalpha() for c in t):out.append(t)
    return out[:6]


def distinctive_tokens(value:Any)->list[str]:
    raw=tokens(value)
    models=set(model_tokens(value))
    words=[x for x in raw if x in models or len(x)>=6]
    seen=[]
    for x in words:
        if x not in seen:seen.append(x)
    return seen[:10]


def _rss(query:str,timeout:int=18)->dict[str,Any]:
    url='https://www.bing.com/search?format=rss&q='+urllib.parse.quote(query)
    req=urllib.request.Request(url,headers={'User-Agent':USER_AGENT,'Accept':'application/rss+xml,application/xml,text/xml'})
    try:
        with urllib.request.urlopen(req,timeout=timeout) as response:
            body=response.read(900_000)
        root=ET.fromstring(body)
        items=[]
        for item in root.findall('.//item')[:12]:
            title=(item.findtext('title') or '').strip()
            link=(item.findtext('link') or '').strip()
            desc=re.sub(r'<[^>]+>',' ',item.findtext('description') or '').strip()
            items.append({'title':title[:500],'link':link[:1600],'description':desc[:900]})
        return {'ok':True,'query':query,'items':items}
    except Exception as exc:
        return {'ok':False,'query':query,'error':str(exc)[:300],'items':[]}


def _match_strength(product:dict[str,Any],result:dict[str,Any])->str:
    hay=fold(f"{result.get('title','')} {result.get('description','')} {result.get('link','')}")
    title=str(product.get('product_name') or product.get('title') or '')
    brand=fold(product.get('brand_name') or product.get('brand') or '')
    models=model_tokens(title+' '+str(product.get('model_name') or ''))
    distinct=distinctive_tokens(title)
    if models and any(m in hay for m in models):
        return 'exact_or_model'
    if brand and len(brand)>=3 and brand in hay:
        overlap=sum(1 for t in distinct if t in hay)
        if overlap>=2:return 'strong_brand_match'
    overlap=sum(1 for t in distinct if t in hay)
    if distinct and overlap>=max(3,min(5,len(distinct)//2+1)):
        return 'strong_title_match'
    generic=[t for t in tokens(title) if not any(c.isdigit() for c in t)]
    generic_overlap=sum(1 for t in generic[:12] if t in hay)
    if generic_overlap>=4:return 'possible_functional_match'
    return 'none'


def _search_surface(surface:str,product:dict[str,Any])->dict[str,Any]:
    title=str(product.get('product_name') or product.get('title') or '')
    brand=str(product.get('brand_name') or product.get('brand') or '')
    model=' '.join(model_tokens(title+' '+str(product.get('model_name') or ''))[:3])
    query=' '.join(x for x in [f'site:{surface}',brand,model or ' '.join(distinctive_tokens(title)[:6])] if x).strip()
    data=_rss(query)
    hits=[]
    for item in data.get('items') or []:
        host=urllib.parse.urlparse(item.get('link') or '').netloc.casefold()
        if surface not in host:continue
        strength=_match_strength(product,item)
        if strength!='none':hits.append({**item,'strength':strength})
    return {'surface':surface,'ok':bool(data.get('ok')),'query':query,'hits':hits[:6],'error':data.get('error')}


def research_product(product:dict[str,Any],workers:int=6)->dict[str,Any]:
    title=str(product.get('product_name') or product.get('title') or '')
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(2,min(workers,len(MAJOR_SURFACES)))) as pool:
        surface_results=list(pool.map(lambda s:_search_surface(s,product),MAJOR_SURFACES))

    exact=[];possible=[]
    for sr in surface_results:
        for hit in sr.get('hits') or []:
            rec={'surface':sr['surface'],**hit}
            if hit.get('strength') in ('exact_or_model','strong_brand_match','strong_title_match'):exact.append(rec)
            elif hit.get('strength')=='possible_functional_match':possible.append(rec)

    general_query=' '.join(x for x in [
        str(product.get('brand_name') or product.get('brand') or ''),
        ' '.join(model_tokens(title+' '+str(product.get('model_name') or ''))[:3]) or ' '.join(distinctive_tokens(title)[:7]),
        'Ελλάδα OR αγορά OR τιμή OR κατάστημα'
    ] if x).strip()
    general=_rss(general_query)
    general_hits=[]
    for item in general.get('items') or []:
        host=urllib.parse.urlparse(item.get('link') or '').netloc.casefold()
        if host.endswith('.gr') or '.gr.' in host:
            strength=_match_strength(product,item)
            if strength!='none':general_hits.append({**item,'strength':strength})
    general_exact=[x for x in general_hits if x.get('strength') in ('exact_or_model','strong_brand_match','strong_title_match')]
    general_possible=[x for x in general_hits if x.get('strength')=='possible_functional_match']

    successful=sum(1 for x in surface_results if x.get('ok'))
    if exact or general_exact:
        preliminary='AVAILABLE'
        confidence=min(100,75+min(25,8*(len(exact)+len(general_exact))))
    elif successful<len(MAJOR_SURFACES) or not general.get('ok'):
        preliminary='UNKNOWN';confidence=0
    elif possible or general_possible:
        preliminary='VERY_RARE';confidence=72
    else:
        preliminary='ABSENT';confidence=90

    return {
        'classification':preliminary,
        'confidence':confidence,
        'surface_searches_successful':successful,
        'surface_searches_required':len(MAJOR_SURFACES),
        'major_surface_evidence':surface_results,
        'general_greek_web':{
            'ok':bool(general.get('ok')),
            'query':general_query,
            'hits':general_hits[:10],
            'error':general.get('error'),
        },
        'exact_match_count':len(exact)+len(general_exact),
        'possible_equivalent_count':len(possible)+len(general_possible),
        'policy':'fail_closed_multi_surface_exact_oem_functional_evidence_v1',
        'caveat':'ABSENT means not found on the sampled major Greek surfaces and broader Greek indexed search; it is not proof that no seller anywhere in Greece exists.',
    }


def research_rows(rows:list[dict[str,Any]],limit:int=240,workers:int=8)->tuple[list[dict[str,Any]],dict[str,int]]:
    sample=rows[:max(1,limit)]
    out=[]
    stats={'probed':len(sample),'ABSENT':0,'VERY_RARE':0,'AVAILABLE':0,'UNKNOWN':0}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(2,min(workers,12))) as pool:
        futures={pool.submit(research_product,row,5):row for row in sample}
        for future in concurrent.futures.as_completed(futures):
            row=futures[future]
            try:evidence=future.result()
            except Exception as exc:evidence={'classification':'UNKNOWN','confidence':0,'error':str(exc)[:500]}
            x=dict(row);x['greek_market_evidence']=evidence;x['greek_availability']=evidence.get('classification','UNKNOWN')
            stats[x['greek_availability']]=stats.get(x['greek_availability'],0)+1
            if x['greek_availability'] in ('ABSENT','VERY_RARE'):out.append(x)
    return out,stats


if __name__=='__main__':
    import sys
    payload=json.load(sys.stdin)
    print(json.dumps(research_product(payload),ensure_ascii=False,indent=2))
