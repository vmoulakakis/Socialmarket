from __future__ import annotations

"""Native Greek community acquisition for Category Pain V4.5.

Search engines remain discovery helpers, not the sole source of recall. This
collector enters verified public forum category pages directly, discovers real
thread URLs, fetches the threads and passes extracted text through the unchanged
V4 consumer scorer. It does not lower any validation threshold.
"""

import concurrent.futures
import hashlib
from urllib.parse import urljoin, urlparse

import requests
from lxml import html

import consumer_evidence_v4 as consumer

_ORIGINAL_COLLECT=consumer.collect_consumer_evidence
_APPLIED=False

# Curated entry pages are category surfaces, not evidence themselves.
# Their content never enters the audit unless a linked public thread is fetched
# and produces product-bound consumer statements via the normal V4 scorer.
SEEDS=(
    {
        'name':'Insomnia Gadgets','url':'https://www.insomnia.gr/forums/forum/67-gadgets/',
        'domains':('insomnia.gr',),'categories':('electronics & technology',),
        'sub_terms':('tv','audio','τηλε','ηχο','ακουσ','gadget','wearable','smart home'),
        'specific':False,'max_topics':14,
    },
    {
        'name':'Insomnia Smartphones','url':'https://www.insomnia.gr/forums/forum/10-smartphones/',
        'domains':('insomnia.gr',),'categories':('electronics & technology',),
        'sub_terms':('phone','smartphone','κινητ','mobile'),
        'specific':True,'max_topics':14,
    },
    {
        'name':'Insomnia Hardware','url':'https://www.insomnia.gr/forums/forum/14-hardware-genika/',
        'domains':('insomnia.gr',),'categories':('electronics & technology',),
        'sub_terms':('computer','computing','laptop','pc','hardware','audio','ηχο','ακουσ'),
        'specific':False,'max_topics':12,
    },
    {
        'name':'goRUN Shoes','url':'https://gorun.gr/forums/forum/running/%CF%80%CE%B1%CF%80%CE%BF%CF%8D%CF%84%CF%83%CE%B9%CE%B1/',
        'domains':('gorun.gr',),'categories':('sports & outdoors',),
        'sub_terms':('running','shoe','παπουτσ','τρεξ'),
        'specific':True,'max_topics':18,
    },
    {
        'name':'GreekEspresso Buying','url':'https://www.greekespresso.gr/forum/viewforum.php?f=2',
        'domains':('greekespresso.gr',),'categories':('food & drink','home & garden'),
        'sub_terms':('coffee','tea','espresso','καφ','μηχαν'),
        'specific':True,'max_topics':18,
    },
    {
        'name':'GreekEspresso Machines','url':'https://www.greekespresso.gr/forum/viewforum.php?f=5',
        'domains':('greekespresso.gr',),'categories':('food & drink','home & garden'),
        'sub_terms':('coffee','espresso','καφ','μηχαν'),
        'specific':True,'max_topics':18,
    },
    {
        'name':'GreekEspresso Maintenance','url':'https://www.greekespresso.gr/forum/viewforum.php?f=15',
        'domains':('greekespresso.gr',),'categories':('food & drink','home & garden'),
        'sub_terms':('coffee','espresso','καφ','μηχαν'),
        'specific':True,'max_topics':14,
    },
)


def _f(x):
    return consumer.fold(x)


def _seed_relevant(seed,category,subcategory,aliases,keywords):
    cat=_f(category); sub=_f(subcategory)
    if seed['categories'] and not any(_f(x) in cat for x in seed['categories']):
        return False
    hay=' '.join([sub,*[_f(x) for x in aliases],*[_f(x) for x in keywords]])
    return any(_f(x) in hay for x in seed['sub_terms'])


def _topic_path(url):
    p=(urlparse(url).path or '').lower()
    q=(urlparse(url).query or '').lower()
    return ('/forums/topic/' in p) or ('/topic/' in p) or ('viewtopic.php' in p) or ('viewtopic' in q)


def _topic_links(seed,aliases,keywords):
    diagnostics=[]
    try:
        r=requests.get(seed['url'],headers=consumer.UA,timeout=24,allow_redirects=True)
        if not r.ok:
            return [],[{'source_kind':'consumer_discovery','source_url':seed['url'],'title':seed['name'],'body':'','collector':'native_community_index_v45','confidence':.4,'metadata':{'evidence_mode':'discovery_only','eligible_for_pain_audit':False,'native_seed':True,'fetch_error':f'http_{r.status_code}','source_family':'community_forum','retrieval_version':'consumer_evidence_v4.5'}}]
        doc=html.fromstring(r.content)
    except Exception as exc:
        return [],[{'source_kind':'consumer_discovery','source_url':seed['url'],'title':seed['name'],'body':'','collector':'native_community_index_v45','confidence':.4,'metadata':{'evidence_mode':'discovery_only','eligible_for_pain_audit':False,'native_seed':True,'fetch_error':type(exc).__name__,'source_family':'community_forum','retrieval_version':'consumer_evidence_v4.5'}}]

    terms=[]
    for x in [*aliases,*keywords]:
        fx=_f(x)
        if len(fx)>=4 and fx not in terms:terms.append(fx)
    found=[];seen=set()
    for a in doc.xpath('//a[@href]'):
        href=str(a.get('href') or '')
        text=' '.join(str(t) for t in a.itertext()).strip()
        url=urljoin(seed['url'],href)
        h=consumer.host(url)
        if not any(h==d or h.endswith('.'+d) for d in seed['domains']):continue
        if not _topic_path(url):continue
        if url in seen:continue
        hay=_f(f'{text} {url}')
        term_hits=sum(1 for t in terms if t in hay)
        # Specific vertical forums may expose generic model thread titles; the
        # downstream full-page scorer still requires taxonomy + pain binding.
        if not seed['specific'] and term_hits<1:continue
        seen.add(url)
        found.append({'url':url,'title':text[:500],'snippet':'','query':f'native:{seed["name"]}','query_term':subcategory or category,'source_family':'community_forum','expected_family':'community_forum','base_confidence':.86 if consumer.host(url)!='insomnia.gr' else .82,'native_seed':seed['name'],'term_hits':term_hits})
        if len(found)>=seed['max_topics']:break
    diagnostics.append({'source_kind':'consumer_discovery','source_url':seed['url'],'title':seed['name'],'body':f'Native public forum index: {len(found)} candidate threads discovered.','collector':'native_community_index_v45','confidence':.72,'metadata':{'evidence_mode':'discovery_only','eligible_for_pain_audit':False,'native_seed':True,'candidate_threads':len(found),'source_family':'community_forum','retrieval_version':'consumer_evidence_v4.5'}})
    return found,diagnostics


def _collect_native(category,subcategory,aliases,keywords,max_rows=60):
    seeds=[s for s in SEEDS if _seed_relevant(s,category,subcategory,aliases,keywords)]
    if not seeds:return [],[]
    rows=[];diagnostics=[];seen_urls=set()
    for seed in seeds:
        topics,diag=_topic_links(seed,aliases,keywords);diagnostics.extend(diag)
        for t in topics:
            if t['url'] not in seen_urls:
                seen_urls.add(t['url']);rows.append(t)
    extracted=[]
    if rows:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(4,len(rows))) as pool:
            futures=[pool.submit(consumer._fetch_text,row) for row in rows[:36]]
            for future in concurrent.futures.as_completed(futures):
                row,text,error=future.result()
                if text:
                    for e in consumer._evidence_from_page(row,text,keywords):
                        e['collector']='native_community_thread_v45'
                        e['metadata']['native_seed']=row.get('native_seed')
                        e['metadata']['retrieval_version']='consumer_evidence_v4.5'
                        extracted.append(e)
                diagnostics.append({'source_kind':'consumer_discovery','source_url':row['url'],'title':row.get('title') or '','body':'','collector':'native_community_thread_v45','confidence':.45 if error else .7,'metadata':{'evidence_mode':'discovery_only','eligible_for_pain_audit':False,'native_seed':row.get('native_seed'),'fetch_error':error,'source_family':'community_forum','retrieval_version':'consumer_evidence_v4.5'}})
    out=[];seen=set()
    for e in sorted(extracted,key=lambda x:(x.get('confidence',0),x.get('metadata',{}).get('consumer_language_score',0)),reverse=True):
        key=(consumer.host(e['source_url']),e.get('content_hash'))
        if key in seen:continue
        seen.add(key);out.append(e)
        if len(out)>=max_rows:break
    return out,diagnostics


def collect_consumer_evidence(category:str,subcategory:str|None,aliases:list[str],keywords:list[str],max_rows:int=100):
    base=_ORIGINAL_COLLECT(category,subcategory,aliases,keywords,max_rows=max_rows)
    native,diagnostics=_collect_native(category,subcategory,aliases,keywords,max_rows=max(20,max_rows//2))
    pains=[x for x in base if x.get('source_kind')=='pain_candidate']
    nonpain=[x for x in base if x.get('source_kind')!='pain_candidate']
    seen={(consumer.host(x.get('source_url')),x.get('content_hash')) for x in pains}
    for e in native:
        key=(consumer.host(e.get('source_url')),e.get('content_hash'))
        if key in seen:continue
        seen.add(key);pains.append(e)
        if len(pains)>=max_rows:break
    return pains+(nonpain+diagnostics)[:min(60,max_rows)]


def apply():
    global _APPLIED
    if _APPLIED:return
    existing={x[0] for x in consumer.SOURCE_RULES}
    additions=[]
    if 'gorun.gr' not in existing:additions.append(('gorun.gr','community_forum',.86))
    if 'greekespresso.gr' not in existing:additions.append(('greekespresso.gr','community_forum',.88))
    consumer.SOURCE_RULES=tuple(additions)+tuple(consumer.SOURCE_RULES)
    consumer.collect_consumer_evidence=collect_consumer_evidence
    _APPLIED=True
