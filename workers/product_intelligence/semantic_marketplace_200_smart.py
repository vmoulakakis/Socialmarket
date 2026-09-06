#!/usr/bin/env python3
"""Smart incremental AFFINITY launcher.

Adds two guarantees on top of semantic_marketplace_200_incremental:
1) During the one-time baseline, learn Linkwise external program IDs as soon as
   a strict merchant is resolved, before the >EUR30 product gate.
2) For trusted program feeds, persist ETag/Last-Modified and issue conditional
   GETs. A 304 means no JSON body is downloaded or parsed.
"""
from __future__ import annotations

import collections
import hashlib
import json
from typing import Any

import ijson
import requests

import semantic_marketplace_200_incremental as base

core=base.core
_STATE_CACHE:dict[str,Any]={}
_ORIGINAL_INC=base.inc


def inc_capture(action:str,**payload:Any):
    result=_ORIGINAL_INC(action,**payload)
    if action=='state':
        _STATE_CACHE.clear();_STATE_CACHE.update(result)
    return result


base.inc=inc_capture


def baseline_scan_smart(programs:list[dict[str,Any]],clusters:list[dict[str,Any]],excluded:set[str]):
    if not core.FEED.exists() or core.FEED.stat().st_size<10_000_000:core.download_linkwise(core.FEED)
    maps=core.merchant_maps(programs)
    for c in clusters:c['_terms']=core.cluster_terms(c)
    buckets={str(c['cluster_key']):[] for c in clusters};stats=collections.Counter();ledger=[];mappings={}
    iterator=core.iter_records(core.FEED)
    while True:
        try:raw=next(iterator)
        except StopIteration:break
        except ijson.common.IncompleteJSONError:stats['truncated_tail_after_complete_records']+=1;break
        stats['records_seen']+=1;p=core.normalize(raw);merchant,_=core.resolve_merchant(p,maps)
        if not merchant:continue
        external=base.linkwise_external_program_id(p.get('tracking_url'))
        if external:mappings[str(merchant['merchant_program_id'])]=external
        else:stats['resolved_merchant_without_external_program_id']+=1
        hard=base.hard_linkwise(p,merchant)
        if not hard or not external:continue
        expected,comm=hard;provider_id=str(p.get('product_id') or '')
        if not provider_id:continue
        ledger_id=f'{external}:{provider_id}';fp=base.linkwise_fingerprint(p,expected)
        source=hashlib.sha256(f'linkwise:{ledger_id}'.encode()).hexdigest()
        ledger.append({'source_product_id':ledger_id,'source_record_hash':source,'product_fingerprint':fp,'merchant_id':merchant.get('merchant_id'),'merchant_program_id':merchant.get('merchant_program_id'),'external_program_id':external,'product_name':p.get('product_name'),'sale_price_eur':p.get('price'),'expected_commission_eur':expected,'metadata':{'provider_product_id':provider_id,'baseline':True}})
        cand=base.cluster_candidate(p,merchant,clusters,expected,comm,external,fp)
        if cand and cand['source_record_hash'] not in excluded:buckets[str(cand['semantic_cluster_key'])].append(cand)
        if len(ledger)>=700:base.checkpoint('linkwise',ledger);stats['ledger_checkpointed']+=len(ledger);ledger=[]
    if ledger:base.checkpoint('linkwise',ledger);stats['ledger_checkpointed']+=len(ledger)
    learned=base.inc('learn_programs',mappings=[{'merchant_program_id':k,'external_program_id':v} for k,v in mappings.items()])
    base.inc('mark_source',source_network='linkwise',source_partition='baseline',baseline_completed=True,changed=True,metadata={'records_seen':stats['records_seen'],'eligible_checkpointed':stats['ledger_checkpointed'],'program_mappings':len(mappings),'learned':learned.get('learned'),'conflicts':learned.get('conflicts'),'strategy':'program_ids_learned_before_product_gate'})
    return base.shortlist(buckets,clusters),{'mode':'baseline_once','program_mappings':len(mappings),'learned_programs':learned.get('learned',0),**dict(stats)}


def prior_program_state(external_id:str)->dict[str,Any]:
    partition=f'program:{external_id}'
    for row in _STATE_CACHE.get('source_states') or []:
        if row.get('source_network')=='linkwise' and row.get('source_partition')==partition:return row
    return {}


def fetch_program_conditional(merchant:dict[str,Any]):
    external=str(merchant.get('external_program_id') or '')
    if not external:return [],{'merchant':merchant.get('canonical_name'),'status':'no_external_id'}
    prior=prior_program_state(external);headers={'User-Agent':'SocialMarketAI/4.1 conditional-delta','Accept-Encoding':'gzip, deflate'}
    if prior.get('etag'):headers['If-None-Match']=str(prior['etag'])
    if prior.get('last_modified'):headers['If-Modified-Since']=str(prior['last_modified'])
    rows=[];seen=0;eligible=0
    with requests.get(base.program_url(external),stream=True,timeout=(20,300),headers=headers) as r:
        if r.status_code==304:
            base.inc('mark_source',source_network='linkwise',source_partition=f'program:{external}',baseline_completed=True,changed=False,etag=prior.get('etag'),last_modified=prior.get('last_modified'),content_length=prior.get('content_length'),metadata={'merchant':merchant.get('canonical_name'),'http_status':304,'body_downloaded':False})
            return [],{'merchant':merchant.get('canonical_name'),'external_program_id':external,'status':'not_modified','http_status':304,'seen':0,'eligible':0}
        r.raise_for_status();r.raw.decode_content=True
        for raw in ijson.items(r.raw,'item'):
            seen+=1;p=core.normalize(raw);hard=base.hard_linkwise(p,merchant)
            if not hard:continue
            expected,comm=hard;provider_id=str(p.get('product_id') or '')
            if not provider_id:continue
            eligible+=1;ledger_id=f'{external}:{provider_id}';fp=base.linkwise_fingerprint(p,expected)
            rows.append({'p':p,'expected':expected,'comm':comm,'ledger_id':ledger_id,'fp':fp})
        base.inc('mark_source',source_network='linkwise',source_partition=f'program:{external}',baseline_completed=True,changed=True,etag=r.headers.get('ETag'),last_modified=r.headers.get('Last-Modified'),content_length=r.headers.get('Content-Length'),metadata={'merchant':merchant.get('canonical_name'),'http_status':r.status_code,'body_downloaded':True,'records_seen':seen,'hard_eligible':eligible})
    return rows,{'merchant':merchant.get('canonical_name'),'external_program_id':external,'status':'downloaded','http_status':200,'seen':seen,'eligible':eligible,'etag':bool(r.headers.get('ETag')),'last_modified':bool(r.headers.get('Last-Modified'))}


base.baseline_scan=baseline_scan_smart
base.fetch_program=fetch_program_conditional

if __name__=='__main__':
    raise SystemExit(core.main())
