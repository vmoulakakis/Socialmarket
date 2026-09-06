#!/usr/bin/env python3
"""AFFINITY production launcher: baseline once, then merchant/seller product deltas.

Linkwise:
- One baseline scan is allowed only until the persistent ledger is initialized.
- Baseline learns Linkwise external program IDs from tracking links and records
  fingerprints for hard-eligible products.
- Later runs fetch only program-specific feeds from trusted/ranked merchants.
- Only NEW or materially CHANGED products reach semantic research and AI QA.

AliExpress:
- Search/detail API remains the discovery surface, but fingerprints are compared
  before Greek-market research/AI.
- Trusted sellers are preferred; discovery sellers can become trusted only from
  repeated validated product evidence. Product evaluate_rate is never treated as
  seller trust by itself.
"""
from __future__ import annotations

import collections
import concurrent.futures
import hashlib
import json
import math
import os
import re
import time
import urllib.error
import urllib.request
from typing import Any

import ijson
import requests

import semantic_marketplace_200_parallel as parallel
import linkwise_direct_feed as lwfeed

core = parallel.core

INC_GATEWAY=os.getenv('MARKETPLACE_INCREMENTAL_GATEWAY','https://rpfadpdnnxequgvdcfoq.supabase.co/functions/v1/marketplace-incremental-gateway')
PROGRAM_WORKERS=max(2,min(8,int(os.getenv('LINKWISE_PROGRAM_WORKERS','6'))))
_PROGRAM_RE=re.compile(r'/z/(\d+)(?:-\d+)?/CD\d+(?:/|\?)',re.I)


def inc(action:str,**payload:Any)->dict[str,Any]:
    body=json.dumps({'action':action,**payload},ensure_ascii=False,default=str).encode()
    req=urllib.request.Request(INC_GATEWAY,data=body,headers={'Authorization':'Bearer '+core.oidc_token(),'Content-Type':'application/json'},method='POST')
    try:
        with urllib.request.urlopen(req,timeout=180) as response:data=json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        raw=exc.read().decode(errors='replace');raise RuntimeError(f'incremental gateway {action} {exc.code}: {raw[:1000]}') from exc
    if not data.get('ok'):raise RuntimeError(f'incremental gateway {action} failed: {data}')
    return data


def stable_json_hash(value:Any)->str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,default=str,separators=(',',':')).encode()).hexdigest()


def linkwise_external_program_id(url:Any)->str|None:
    m=_PROGRAM_RE.search(str(url or ''))
    return m.group(1) if m else None


def linkwise_fingerprint(p:dict[str,Any],expected:float)->str:
    material={
      'title':core.fold(p.get('product_name'))[:240],
      'category':core.fold(p.get('category'))[:160],
      'price':round(float(p.get('price') or 0),2),
      'commission':round(float(expected or 0),2),
      'in_stock':p.get('in_stock'),
      'availability':str(p.get('availability') or '')[:80],
      'valid_to':str(p.get('valid_to') or '')[:40],
      'target_domain':str(p.get('target_domain') or '')[:180],
    }
    return stable_json_hash(material)


def ali_fingerprint(x:dict[str,Any])->str:
    er=round(float(x.get('api_evaluate_rate') or 0),1)
    volume=float(x.get('api_latest_volume') or 0)
    volume_band=0 if volume<=0 else int(math.log10(volume+1))
    return stable_json_hash({
      'title':core.fold(x.get('product_name'))[:240],
      'price':round(float(x.get('sale_price_eur') or 0),2),
      'commission':round(float(x.get('expected_commission_eur') or 0),2),
      'evaluate_rate':er,
      'volume_band':volume_band,
      'ship_to_days':str(x.get('api_ship_to_days') or '')[:30],
      'shop_id':str(x.get('shop_id') or '')[:180],
    })


def delta_status(network:str,rows:list[dict[str,Any]])->dict[str,str]:
    out={}
    for start in range(0,len(rows),800):
        batch=rows[start:start+800]
        r=inc('diff',source_network=network,items=[{'source_product_id':x['source_product_id'],'product_fingerprint':x['product_fingerprint']} for x in batch])
        out.update({str(x.get('source_product_id')):str(x.get('status')) for x in r.get('items') or []})
    return out


def checkpoint(network:str,rows:list[dict[str,Any]]):
    for start in range(0,len(rows),700):
        inc('checkpoint',source_network=network,items=rows[start:start+700])


def cluster_candidate(p:dict[str,Any],merchant:dict[str,Any],clusters:list[dict[str,Any]],expected:float,comm:dict[str,Any],external_id:str,fp:str)->dict[str,Any]|None:
    best=None;best_score=0.0
    for c in clusters:
        s=core.cluster_similarity(p,c)
        if s>best_score:best_score=s;best=c
    if not best or best_score<16:return None
    completeness=sum(bool(p.get(k)) for k in ('product_name','description','category','image_url','tracking_url','product_id'))/6*100
    trust=float(merchant.get('trust_score') or 0);rank=float(merchant.get('global_rank') or 100)
    commercial=float(merchant.get('commercial_score') or 0)
    retrieval=min(100,best_score*.40+min(100,expected/1.2)*.18+trust*.14+commercial*.12+completeness*.11+max(0,100-rank)*.05)
    provider_id=str(p.get('product_id') or '')
    ledger_id=f'{external_id}:{provider_id}'
    source=hashlib.sha256(f'linkwise:{ledger_id}'.encode()).hexdigest()
    return {
      'portfolio':'linkwise','source_network':'linkwise','source_record_hash':source,'source_product_id':ledger_id,'provider_product_id':provider_id,
      'product_fingerprint':fp,'external_program_id':external_id,
      'semantic_cluster_key':best['cluster_key'],'niche':best['niche'],'subniche':best.get('subniche'),'cluster':{k:v for k,v in best.items() if not k.startswith('_')},
      'product_name':str(p.get('product_name') or ''),'brand_name':p.get('brand_name') or p.get('brand'),'description':str(p.get('description') or '')[:2200],
      'category':p.get('category'),'image_url':p.get('image_url') or p.get('thumb_url'),'tracking_url':p.get('tracking_url'),'detail_url':p.get('target_url'),
      'sale_price_eur':float(p.get('price') or 0),'expected_commission_eur':expected,'merchant_id':str(merchant.get('merchant_id')),'merchant_program_id':str(merchant.get('merchant_program_id')),
      'merchant_name':merchant.get('canonical_name'),'merchant_global_rank':int(merchant.get('global_rank') or 9999),'merchant_trust_score':float(merchant.get('trust_score') or 0),
      'merchant_research_confidence':float(merchant.get('research_confidence') or 0),'merchant_risk_flag':bool(merchant.get('risk_flag')),
      'merchant_commercial_score':float(merchant.get('commercial_score') or 0),'merchant_data_confidence':float(merchant.get('data_confidence') or 0),
      'seller_quality_score':None,'retrieval_score':round(retrieval,2),'merchant_resolution_method':'external_program_id',
      'evidence_summary':{'source':'Linkwise program-specific feed','merchant_gate':{'global_rank':merchant.get('global_rank'),'trust_score':merchant.get('trust_score'),'research_confidence':merchant.get('research_confidence'),'commercial_score':merchant.get('commercial_score'),'data_confidence':merchant.get('data_confidence'),'risk_flag':merchant.get('risk_flag')},'external_program_id':external_id,'deterministic_retrieval_score':round(retrieval,2),'commission_rule':comm.get('commission_rule')}
    }


def hard_linkwise(p:dict[str,Any],merchant:dict[str,Any])->tuple[float,dict[str,Any]]|None:
    if core.excluded_vertical({**p,'merchant_name':merchant.get('canonical_name')}):return None
    if p.get('in_stock') is False:return None
    if not p.get('tracking_url') or not (p.get('image_url') or p.get('thumb_url')):return None
    price=float(p.get('price') or 0)
    if price<=0:return None
    comm=core.parse_commission_rule(merchant.get('raw_commission_pct'),merchant.get('raw_flat_commission'),price)
    expected=float(comm.get('expected_commission_eur') or 0)
    if expected<=core.MIN_COMMISSION:return None
    return expected,comm


def baseline_scan(programs:list[dict[str,Any]],clusters:list[dict[str,Any]],excluded:set[str]):
    if not core.FEED.exists() or core.FEED.stat().st_size<10_000_000:core.download_linkwise(core.FEED)
    maps=core.merchant_maps(programs)
    for c in clusters:c['_terms']=core.cluster_terms(c)
    buckets={str(c['cluster_key']):[] for c in clusters};stats=collections.Counter();ledger=[];mappings={}
    iterator=core.iter_records(core.FEED)
    while True:
        try:raw=next(iterator)
        except StopIteration:break
        except ijson.common.IncompleteJSONError:stats['truncated_tail_after_complete_records']+=1;break
        stats['records_seen']+=1;p=core.normalize(raw);merchant,method=core.resolve_merchant(p,maps)
        if not merchant:continue
        hard=hard_linkwise(p,merchant)
        if not hard:continue
        expected,comm=hard;external=linkwise_external_program_id(p.get('tracking_url'))
        if not external:stats['missing_external_program_id']+=1;continue
        mappings[str(merchant['merchant_program_id'])]=external
        provider_id=str(p.get('product_id') or '')
        if not provider_id:continue
        ledger_id=f'{external}:{provider_id}';fp=linkwise_fingerprint(p,expected)
        source=hashlib.sha256(f'linkwise:{ledger_id}'.encode()).hexdigest()
        ledger.append({'source_product_id':ledger_id,'source_record_hash':source,'product_fingerprint':fp,'merchant_id':merchant.get('merchant_id'),'merchant_program_id':merchant.get('merchant_program_id'),'external_program_id':external,'product_name':p.get('product_name'),'sale_price_eur':p.get('price'),'expected_commission_eur':expected,'metadata':{'provider_product_id':provider_id,'baseline':True}})
        cand=cluster_candidate(p,merchant,clusters,expected,comm,external,fp)
        if cand and cand['source_record_hash'] not in excluded:buckets[str(cand['semantic_cluster_key'])].append(cand)
        if len(ledger)>=700:checkpoint('linkwise',ledger);stats['ledger_checkpointed']+=len(ledger);ledger=[]
    if ledger:checkpoint('linkwise',ledger);stats['ledger_checkpointed']+=len(ledger)
    learned=inc('learn_programs',mappings=[{'merchant_program_id':k,'external_program_id':v} for k,v in mappings.items()])
    inc('mark_source',source_network='linkwise',source_partition='baseline',baseline_completed=True,changed=True,metadata={'records_seen':stats['records_seen'],'eligible_checkpointed':stats['ledger_checkpointed'],'program_mappings':len(mappings),'learned':learned.get('learned'),'conflicts':learned.get('conflicts')})
    return shortlist(buckets,clusters),{'mode':'baseline_once','program_mappings':len(mappings),'learned_programs':learned.get('learned',0),**dict(stats)}


def program_url(external_id:str)->str:
    columns,_=lwfeed.direct_columns()
    url=lwfeed.feed_url(columns,categories='0')
    return url.replace('/proginc-0/',f'/proginc-{external_id}/')


def fetch_program(merchant:dict[str,Any])->tuple[list[dict[str,Any]],dict[str,Any]]:
    external=str(merchant.get('external_program_id') or '')
    if not external:return [],{'merchant':merchant.get('canonical_name'),'status':'no_external_id'}
    rows=[];seen=0;eligible=0
    with requests.get(program_url(external),stream=True,timeout=(20,300),headers={'User-Agent':'SocialMarketAI/4.0 incremental','Accept-Encoding':'gzip, deflate'}) as r:
        r.raise_for_status();r.raw.decode_content=True
        for raw in ijson.items(r.raw,'item'):
            seen+=1;p=core.normalize(raw);hard=hard_linkwise(p,merchant)
            if not hard:continue
            expected,comm=hard;provider_id=str(p.get('product_id') or '')
            if not provider_id:continue
            eligible+=1;ledger_id=f'{external}:{provider_id}';fp=linkwise_fingerprint(p,expected)
            rows.append({'p':p,'expected':expected,'comm':comm,'ledger_id':ledger_id,'fp':fp})
    return rows,{'merchant':merchant.get('canonical_name'),'external_program_id':external,'seen':seen,'eligible':eligible}


def shortlist(buckets:dict[str,list[dict[str,Any]]],clusters:list[dict[str,Any]]):
    out={}
    for c in clusters:
        key=str(c['cluster_key']);ordered=sorted(buckets.get(key,[]),key=lambda x:(x['retrieval_score'],x['expected_commission_eur']),reverse=True)
        pre=[];per=collections.Counter();dedup=set()
        for x in ordered:
            ck=core.canonical_key({'product_name':x['product_name'],'brand_name':x.get('brand_name'),'category':x.get('category'),'merchant_name':x.get('merchant_name'),'product_id':x.get('source_product_id')})
            if ck in dedup or per[str(x.get('merchant_id'))]>=4:continue
            dedup.add(ck);per[str(x.get('merchant_id'))]+=1;pre.append(x)
            if len(pre)>=core.LINKWISE_PER_CLUSTER_AI:break
        out[key]=pre
    return out


def incremental_linkwise_scan(programs:list[dict[str,Any]],clusters:list[dict[str,Any]],excluded:set[str]):
    st=inc('state');strict={str(x.get('merchant_program_id')):x for x in programs}
    state_programs=[]
    for x in st.get('programs') or []:
        base=strict.get(str(x.get('merchant_program_id')))
        if not base:continue
        state_programs.append({**base,**x})
    if not st.get('linkwise_baseline_completed'):
        print(json.dumps({'phase':'linkwise_baseline_once','reason':'persistent product ledger is not initialized'}),flush=True)
        return baseline_scan(state_programs or programs,clusters,excluded)
    trusted=[x for x in state_programs if x.get('retrieval_tier')=='trusted' and x.get('external_program_id')]
    trusted.sort(key=lambda x:(-float(x.get('commercial_score') or 0),int(x.get('global_rank') or 9999)))
    buckets={str(c['cluster_key']):[] for c in clusters};stats=collections.Counter();all_raw=[];program_stats=[]
    for c in clusters:c['_terms']=core.cluster_terms(c)
    with concurrent.futures.ThreadPoolExecutor(max_workers=PROGRAM_WORKERS) as pool:
        futures={pool.submit(fetch_program,m):m for m in trusted}
        for fut in concurrent.futures.as_completed(futures):
            try:rows,s=fut.result();all_raw.extend((futures[fut],x) for x in rows);program_stats.append(s);stats['programs_fetched']+=1;stats['records_seen']+=int(s.get('seen') or 0);stats['hard_eligible']+=int(s.get('eligible') or 0)
            except Exception as exc:stats['program_fetch_failed']+=1;program_stats.append({'merchant':futures[fut].get('canonical_name'),'error':str(exc)[:300]})
    ledger=[]
    for merchant,x in all_raw:
        p=x['p'];external=str(merchant.get('external_program_id'));source=hashlib.sha256(f"linkwise:{x['ledger_id']}".encode()).hexdigest()
        ledger.append({'source_product_id':x['ledger_id'],'source_record_hash':source,'product_fingerprint':x['fp'],'merchant_id':merchant.get('merchant_id'),'merchant_program_id':merchant.get('merchant_program_id'),'external_program_id':external,'product_name':p.get('product_name'),'sale_price_eur':p.get('price'),'expected_commission_eur':x['expected'],'metadata':{'provider_product_id':p.get('product_id'),'retrieval_tier':'trusted'}})
    statuses=delta_status('linkwise',ledger) if ledger else {}
    delta_ids={k for k,v in statuses.items() if v in ('new','changed')};stats['new_or_changed']=len(delta_ids);stats['unchanged']=sum(1 for v in statuses.values() if v=='unchanged')
    delta_checkpoint=[x for x in ledger if x['source_product_id'] in delta_ids]
    if delta_checkpoint:checkpoint('linkwise',delta_checkpoint)
    for merchant,x in all_raw:
        if x['ledger_id'] not in delta_ids:continue
        cand=cluster_candidate(x['p'],merchant,clusters,x['expected'],x['comm'],str(merchant.get('external_program_id')),x['fp'])
        if cand and cand['source_record_hash'] not in excluded:buckets[str(cand['semantic_cluster_key'])].append(cand)
    inc('mark_source',source_network='linkwise',source_partition='trusted_programs',baseline_completed=True,changed=bool(delta_ids),metadata={'trusted_programs':len(trusted),'programs_fetched':stats['programs_fetched'],'new_or_changed':stats['new_or_changed'],'unchanged':stats['unchanged']})
    return shortlist(buckets,clusters),{'mode':'trusted_program_delta','trusted_programs':len(trusted),'program_stats':program_stats[:80],**dict(stats),'ai_shortlist':sum(len(v) for v in shortlist(buckets,clusters).values())}


def incremental_aliexpress(clusters:list[dict[str,Any]],excluded:set[str]):
    state=inc('state');seller_state={str(x.get('seller_id')):x for x in state.get('sellers') or []}
    raw_by_pid={};api_calls=0
    for cluster in clusters:
        queries=(cluster.get('search_queries') or [])[:3] or [cluster.get('subniche') or cluster.get('niche')]
        for query in queries:
            for action in ('search','hotproducts'):
                try:response=core.ali(action,keywords=str(query),ship_to='GR',currency='EUR',language='EN',page=1,page_size=50);api_calls+=1
                except Exception as exc:print(json.dumps({'warning':'aliexpress_discovery_call_failed','cluster':cluster.get('cluster_key'),'query':query,'action':action,'error':str(exc)[:300]}),flush=True);continue
                for raw in core.walk_products(response.get('data')):
                    x=core.ali_normalize(raw,cluster)
                    if not x or x['source_record_hash'] in excluded:continue
                    old=raw_by_pid.get(x['source_product_id'])
                    if not old or x['expected_commission_eur']>old['expected_commission_eur']:raw_by_pid[x['source_product_id']]=x
    candidates=list(raw_by_pid.values());refreshed={};ids=[x['source_product_id'] for x in candidates]
    for start in range(0,len(ids),40):
        try:res=core.ali('details',product_ids=ids[start:start+40],ship_to='GR',currency='EUR',language='EN');api_calls+=1
        except Exception:continue
        for raw in core.walk_products(res.get('data')):refreshed[str(raw.get('product_id'))]=raw
    normalized=[]
    for x in candidates:
        raw=refreshed.get(x['source_product_id']);nx=core.ali_normalize(raw,x['cluster']) if raw else x
        if not nx:continue
        nx['product_fingerprint']=ali_fingerprint(nx);seller=seller_state.get(str(nx.get('shop_id'))) or {}
        nx['seller_trust_state']=seller.get('trust_state','discovery');nx['seller_evidence_score']=float(seller.get('evidence_score') or 0);nx['seller_trust_confidence']=float(seller.get('confidence') or 0)
        normalized.append(nx)
    ledger=[{'source_product_id':x['source_product_id'],'source_record_hash':x['source_record_hash'],'product_fingerprint':x['product_fingerprint'],'seller_id':x.get('shop_id'),'product_name':x.get('product_name'),'sale_price_eur':x.get('sale_price_eur'),'expected_commission_eur':x.get('expected_commission_eur'),'metadata':{'seller_name':x.get('merchant_name'),'seller_url':x.get('shop_url'),'evaluate_rate':x.get('api_evaluate_rate'),'latest_volume':x.get('api_latest_volume'),'ship_to_days':x.get('api_ship_to_days')}} for x in normalized]
    statuses=delta_status('aliexpress_affiliate_api',ledger) if ledger else {};delta_ids={k for k,v in statuses.items() if v in ('new','changed')}
    delta=[x for x in normalized if x['source_product_id'] in delta_ids]
    if delta:checkpoint('aliexpress_affiliate_api',[x for x in ledger if x['source_product_id'] in delta_ids])
    buckets={str(c['cluster_key']):[] for c in clusters}
    for x in delta:buckets[str(x['semantic_cluster_key'])].append(x)
    evidence={};research_stats={}
    for cluster in clusters:
        key=str(cluster['cluster_key']);ordered=sorted(buckets[key],key=lambda x:(1 if x.get('seller_trust_state')=='trusted' else 0,float(x.get('seller_evidence_score') or 0),float(x.get('seller_quality_score') or 0),float(x.get('expected_commission_eur') or 0)),reverse=True)[:core.ALI_PER_CLUSTER_RESEARCH]
        researched,stats=core.research_rows(ordered,limit=len(ordered),workers=8);research_stats[key]=stats;evidence[key]=researched
    inc('mark_source',source_network='aliexpress_affiliate_api',source_partition='semantic_discovery',baseline_completed=True,changed=bool(delta),metadata={'api_candidates':len(normalized),'new_or_changed':len(delta),'unchanged':sum(1 for v in statuses.values() if v=='unchanged'),'api_calls':api_calls})
    return evidence,{'mode':'product_delta','api_calls':api_calls,'api_candidates':len(normalized),'commission_gt30_unique':len(normalized),'new_or_changed':len(delta),'unchanged':sum(1 for v in statuses.values() if v=='unchanged'),'trusted_sellers_seen':sum(1 for x in delta if x.get('seller_trust_state')=='trusted'),'greek_research':research_stats,'ai_shortlist':sum(len(v) for v in evidence.values())}


_ORIGINAL_EVALUATE_BUCKETS=core.evaluate_buckets
_ORIGINAL_SELECT_ALI=core.select_aliexpress


def evaluate_and_record(buckets):
    result=_ORIGINAL_EVALUATE_BUCKETS(buckets)
    flat=[x for rows in result.values() for x in rows]
    link=[x for x in flat if x.get('portfolio')=='linkwise'];ali=[x for x in flat if x.get('portfolio')=='aliexpress']
    if link:inc('record_evaluations',source_network='linkwise',items=link)
    if ali:inc('record_evaluations',source_network='aliexpress_affiliate_api',items=ali)
    return result


def select_aliexpress_trusted(clusters,evaluated):
    state=inc('state');trusted={str(x.get('seller_id')) for x in state.get('sellers') or [] if x.get('trust_state')=='trusted'}
    filtered={}
    for key,rows in evaluated.items():
        filtered[key]=[x for x in rows if str(x.get('shop_id') or '') in trusted]
    return _ORIGINAL_SELECT_ALI(clusters,filtered)


core.linkwise_scan=incremental_linkwise_scan
core.discover_aliexpress=incremental_aliexpress
core.evaluate_buckets=evaluate_and_record
core.select_aliexpress=select_aliexpress_trusted

if __name__=='__main__':
    raise SystemExit(core.main())
