from __future__ import annotations

import concurrent.futures
import json
import os
import threading
import time
from urllib.parse import quote, urlparse

import requests

from semantic_taxonomy import TAXONOMY, fold
from market_query_aliases import market_query_terms

GATEWAY=os.getenv('EVIDENCE_GATEWAY','https://rpfadpdnnxequgvdcfoq.supabase.co/functions/v1/evidence-gateway')
SEARXNG=os.getenv('SEARXNG_BASE_URL','http://127.0.0.1:8080').rstrip('/')
LIMIT=max(1,min(int(os.getenv('CATEGORY_PAIN_LIMIT','80')),100))
WORKERS=max(1,min(int(os.getenv('CATEGORY_PAIN_WORKERS','3')),6))
BATCH=max(1,min(int(os.getenv('CATEGORY_PAIN_AI_BATCH','4')),6))
UA={'User-Agent':'Mozilla/5.0 SocialMarketSemanticPain/3.0'}
AUD='socialmarket-supabase-worker'
_token=None;_token_at=0.;_lock=threading.Lock()
BLOCK_DOMAINS=('bing.com','google.com','yahoo.com','duckduckgo.com','wikipedia.org','facebook.com','instagram.com','tiktok.com','youtube.com','reddit.com','pinterest.com','linkedin.com','x.com','twitter.com')
CONTENT_BLOCK=('zillow.','realtor.','redfin.','trulia.','homes.com','quora.com')
GENERIC={'home','garden','fashion','travel','health','beauty','sports','kids','baby','books','food','drink','automotive','pets','services','digital','accessories','care','product','products'}
AUTHORITATIVE_CONTEXT=(
    {'domain':'statistics.gr','source_kind':'official_context','source_class':'official_statistics','authority_weight':1.0,'themes':('λιανικό εμπόριο','Έρευνα Οικογενειακών Προϋπολογισμών','ηλεκτρονικό εμπόριο νοικοκυριά')},
    {'domain':'ec.europa.eu','source_kind':'official_context','source_class':'public_institution','authority_weight':1.0,'themes':('Eurostat Greece e-commerce','Eurostat Greece online shopping','Eurostat Greece retail')},
    {'domain':'greekecommerce.gr','source_kind':'industry_context','source_class':'industry_primary','authority_weight':.82,'themes':('έρευνα ηλεκτρονικού εμπορίου','Greek e-commerce research')},
)

def oidc():
    global _token,_token_at
    with _lock:
        if _token and time.time()-_token_at<170:return _token
        u=os.environ['ACTIONS_ID_TOKEN_REQUEST_URL'];rt=os.environ['ACTIONS_ID_TOKEN_REQUEST_TOKEN'];sep='&' if '?' in u else '?'
        r=requests.get(f'{u}{sep}audience={quote(AUD)}',headers={'Authorization':f'Bearer {rt}'},timeout=30);r.raise_for_status();_token=r.json()['value'];_token_at=time.time();return _token

def gateway(action,**payload):
    global _token
    def call():return requests.post(GATEWAY,headers={'Authorization':f'Bearer {oidc()}','Content-Type':'application/json'},json={'action':action,**payload},timeout=210)
    r=call()
    if r.status_code==401:_token=None;r=call()
    r.raise_for_status();j=r.json()
    if not j.get('ok'):raise RuntimeError(j)
    return j

def host(url):
    try:return urlparse(url).netloc.lower().split(':')[0].removeprefix('www.')
    except:return ''

def search(q,limit=12):
    try:
        r=requests.get(f'{SEARXNG}/search',params={'q':q,'format':'json','language':'el-GR','safesearch':1},headers=UA,timeout=25);r.raise_for_status()
        return [{'url':x.get('url',''),'title':x.get('title',''),'snippet':x.get('content') or x.get('snippet') or ''} for x in (r.json().get('results') or [])[:limit*2]]
    except Exception:return []

def keyword_set(category,subcategory,query_terms):
    terms=[]
    if subcategory and category in TAXONOMY and subcategory in TAXONOMY[category]:terms.extend(TAXONOMY[category][subcategory])
    elif category in TAXONOMY:
        for _,ks in TAXONOMY[category].items():terms.extend(ks)
    terms.extend([category,subcategory or '',*query_terms])
    out=[]
    for x in terms:
        f=fold(x)
        if len(f)>=4 and f not in GENERIC and f not in out:out.append(f)
    return out[:70]

def relevance(row,keywords,query_term):
    hay=fold(f"{row.get('title','')} {row.get('snippet','')} {row.get('url','')}")
    exact=fold(query_term)
    score=3 if exact and exact in hay else 0
    score+=sum(1 for k in keywords if k in hay)
    return score

def useful_rows(query,keywords,query_term,kind,limit=10):
    scored=[]
    for r in search(query,limit=limit):
        d=host(r['url'])
        if not d or any(x in d for x in CONTENT_BLOCK):continue
        s=relevance(r,keywords,query_term)
        if s<1:continue
        scored.append((s,r))
    scored.sort(key=lambda x:x[0],reverse=True)
    out=[];seen=set()
    for s,r in scored:
        key=(r['url'],r['title'])
        if key in seen:continue
        seen.add(key)
        out.append({'source_kind':kind,'source_url':r['url'],'title':r['title'][:500],'body':r['snippet'][:1600],'collector':'searxng_semantic_taxonomy_v3','confidence':min(.9,.56+s*.055),'metadata':{'query':query,'query_term':query_term,'semantic_matches':s,'geography':'GR','retrieval_version':'greek_alias_v3'}})
        if len(out)>=limit:break
    return out

def authoritative_context_rows(category,subcategory,aliases,keywords):
    """Discover Greek official/industry context. These rows never feed demand_score arithmetic."""
    out=[];terms=(aliases[:2] or [subcategory or category])
    for source in AUTHORITATIVE_CONTEXT:
        for term in terms:
            for theme in source['themes'][:2]:
                q=f"site:{source['domain']} {term} {theme}"
                for e in useful_rows(q,keywords,term,source['source_kind'],3):
                    if source['domain'] not in host(e.get('source_url')):continue
                    e['confidence']=max(float(e.get('confidence') or 0),.9 if source['authority_weight']>=1 else .78)
                    e['metadata'].update({'context_only':True,'source_class':source['source_class'],'authority_weight':source['authority_weight'],'does_not_feed_demand_score':True,'context_semantics':'exogenous/category context; not search volume unless directly measured','retrieval_version':'greek_authoritative_context_v1'})
                    out.append(e)
    dedup=[];seen=set()
    for e in out:
        k=(e['source_url'],e['title'])
        if k in seen:continue
        seen.add(k);dedup.append(e)
    return dedup[:28]

def commercial_domain(e):
    d=host(e.get('source_url'))
    if not d or any(x in d for x in BLOCK_DOMAINS) or any(x in d for x in CONTENT_BLOCK):return None
    text=fold(f"{e.get('title','')} {e.get('body','')}")
    commercial=('€' in str(e.get('body','')) or any(x in text for x in ('αγορα','τιμη','shop','store','buy','price','προιον','eshop','e-shop')))
    return d if commercial else None

def collect(job):
    p=job.get('payload') or {};category=str(p.get('category') or p.get('name') or '').strip();subcategory=(str(p.get('subcategory')).strip() if p.get('subcategory') else None)
    aliases=market_query_terms(category,subcategory);keys=keyword_set(category,subcategory,aliases)
    evidence=[]
    for term in aliases[:3]:
        demand_queries=[f'{term} αγορά Ελλάδα',f'{term} κριτικές Ελλάδα',f'{term} τι να προσέξω',f'{term} καλύτερη επιλογή']
        pain_queries=[f'{term} πρόβλημα',f'{term} παράπονα',f'{term} πολύ ακριβό',f'{term} μειονεκτήματα',f'{term} εναλλακτική',f'{term} δεν αξίζει']
        competition_queries=[f'{term} αγορά shop Ελλάδα',f'{term} τιμές eshop Ελλάδα']
        for q in demand_queries:evidence.extend(useful_rows(q,keys,term,'demand',7))
        for q in pain_queries:evidence.extend(useful_rows(q,keys,term,'pain_candidate',8))
        for q in competition_queries:evidence.extend(useful_rows(q,keys,term,'competition',9))
    evidence.extend(authoritative_context_rows(category,subcategory,aliases,keys))
    dedup=[];seen=set()
    for e in evidence:
        k=(e['source_kind'],e['source_url'],e['title'])
        if k in seen:continue
        seen.add(k);dedup.append(e)
    evidence=dedup[:180]
    demand_rows=[e for e in evidence if e['source_kind']=='demand'];pain_rows=[e for e in evidence if e['source_kind']=='pain_candidate'];comp_rows=[e for e in evidence if e['source_kind']=='competition'];context_rows=[e for e in evidence if e['source_kind'] in ('official_context','industry_context')]
    demand_domains={host(e['source_url']) for e in demand_rows if host(e['source_url'])};pain_domains={host(e['source_url']) for e in pain_rows if host(e['source_url'])};comp_domains=sorted({d for e in comp_rows if (d:=commercial_domain(e))})
    demand_score=min(100,20+min(48,len(demand_rows)*3)+min(32,len(demand_domains)*3)) if demand_rows else None
    competition_score=min(100,15+len(comp_domains)*7) if len(comp_domains)>=3 else None
    confidence=min(.94,.35+min(.30,len(demand_domains)*.025)+min(.25,len(pain_domains)*.025)+(.10 if competition_score is not None else 0))
    market={'demand_score':demand_score,'competition_score':competition_score,'confidence':confidence,'query_aliases':aliases,'demand_evidence':[{'source_url':e['source_url'],'title':e['title']} for e in demand_rows[:24]],'competition_evidence':{'domains':comp_domains,'results':[{'source_url':e['source_url'],'title':e['title']} for e in comp_rows[:30]]},'pain_evidence':[{'source_url':e['source_url'],'title':e['title']} for e in pain_rows[:40]],'context_evidence':[{'source_kind':e['source_kind'],'source_url':e['source_url'],'title':e['title'],'source_class':e['metadata'].get('source_class'),'authority_weight':e['metadata'].get('authority_weight')} for e in context_rows[:28]],'metric_semantics':{'demand':'derived from relevant observed demand evidence density only; authoritative context rows excluded from score arithmetic; not search volume','competition':'derived from distinct relevant commercial domains; null when insufficient','pain':'AI skeptic validated clusters','context':'official/industry exogenous context only; cannot inflate demand'}}
    return {'job_id':job['id'],'entity_id':job['entity_id'],'category':category,'subcategory':subcategory,'evidence':evidence,'market':market}

def process_batch(jobs):
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(WORKERS,len(jobs))) as ex:items=list(ex.map(collect,jobs))
    audit=gateway('audit_batch',items=items);audits={str(x.get('entity_id')):x for x in (audit.get('items') or [])}
    results=[]
    for item in items:
        a=audits.get(str(item['entity_id']),{});item['clusters']=a.get('clusters') or []
        item['market']['ai_audit_summary']=a.get('audit_summary');item['market']['rejected_patterns']=a.get('rejected_patterns') or []
        try:
            saved=gateway('save',result=item).get('result') or {};results.append({'ok':True,'category':item['category'],'subcategory':item['subcategory'],'aliases':item['market']['query_aliases'],'evidence':len(item['evidence']),'official_context':len([e for e in item['evidence'] if e['source_kind']=='official_context']),'industry_context':len([e for e in item['evidence'] if e['source_kind']=='industry_context']),'pain_candidates':len([e for e in item['evidence'] if e['source_kind']=='pain_candidate']),'validated_clusters':saved.get('validated_clusters',0),'competition':item['market']['competition_score'],'demand':item['market']['demand_score']})
        except Exception as e:
            try:gateway('fail',job_id=item['job_id'],error=str(e)[:1000])
            except Exception:pass
            results.append({'ok':False,'category':item['category'],'subcategory':item['subcategory'],'error':str(e)[:250]})
    return results

def main():
    seeded=gateway('seed');print(json.dumps({'seed':seeded},ensure_ascii=False),flush=True);done=0
    while done<LIMIT:
        jobs=(gateway('claim',limit=min(BATCH,LIMIT-done),worker='github-semantic-category-pain-v3').get('jobs') or [])
        if not jobs:break
        for r in process_batch(jobs):print(json.dumps(r,ensure_ascii=False),flush=True);done+=1
    print(json.dumps({'status':'completed','processed':done,'limit':LIMIT,'retrieval':'greek-natural-alias-v3+authoritative-context-v1'},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
