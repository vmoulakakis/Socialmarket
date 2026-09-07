#!/usr/bin/env python3
"""AFFINITY smart incremental launcher v2.

Fast production strategy:
- Linkwise keeps merchant-first program feeds + conditional HTTP refresh.
- AliExpress fingerprints lightweight search results before expensive details.
- NEW / materially CHANGED products always have priority.
- If a delta is too small, a bounded deterministic slice of unchanged products
  is re-evaluated so the portfolio can refill without a full catalogue AI run.
- Refilled products still pass every existing commission, merchant/seller,
  Greek-market, Product Research, Skeptic, quality and AFFINITY gate.
"""
from __future__ import annotations

import json
import math
import os
from typing import Any

import semantic_marketplace_200_smart as smart

base=smart.base
core=smart.core

REFILL_LINKWISE=max(40,min(500,int(os.getenv('MARKETPLACE200_DELTA_REFILL_LINKWISE','300'))))
REFILL_ALI=max(40,min(500,int(os.getenv('MARKETPLACE200_DELTA_REFILL_ALIEXPRESS','300'))))
FORCE_BOUNDED_REEVAL=os.getenv('MARKETPLACE200_FORCE_BOUNDED_REEVAL','0')=='1'
_ORIGINAL_DELTA_STATUS=base.delta_status


def smart_delta_status(network:str,rows:list[dict[str,Any]])->dict[str,str]:
    """Preserve true deltas and add only a bounded refill slice when needed."""
    statuses=_ORIGINAL_DELTA_STATUS(network,rows)
    if not statuses:return statuses
    floor=REFILL_ALI if network=='aliexpress_affiliate_api' else REFILL_LINKWISE
    real_delta=[k for k,v in statuses.items() if v in ('new','changed')]
    unchanged=[k for k,v in statuses.items() if v=='unchanged']
    needed=floor if FORCE_BOUNDED_REEVAL else max(0,floor-len(real_delta))
    if needed<=0:return statuses
    for key in sorted(unchanged)[:needed]:statuses[key]='changed'
    return statuses


# Both Linkwise and AliExpress now share the same bounded-refill delta contract.
base.delta_status=smart_delta_status


def ali_search_fingerprint(x:dict[str,Any])->str:
    """Material fingerprint using fields available on affiliate search/hotproduct results."""
    er=round(float(x.get('api_evaluate_rate') or 0),1)
    volume=float(x.get('api_latest_volume') or 0)
    volume_band=0 if volume<=0 else int(math.log10(volume+1))
    return base.stable_json_hash({
      'title':core.fold(x.get('product_name'))[:240],
      'price':round(float(x.get('sale_price_eur') or 0),2),
      'commission':round(float(x.get('expected_commission_eur') or 0),2),
      'evaluate_rate':er,
      'volume_band':volume_band,
      'ship_to_days':str(x.get('api_ship_to_days') or '')[:30],
      'shop_id':str(x.get('shop_id') or '')[:180],
    })


def incremental_aliexpress_v2(clusters:list[dict[str,Any]],excluded:set[str]):
    state=base.inc('state');seller_state={str(x.get('seller_id')):x for x in state.get('sellers') or []}
    raw_by_pid={};api_calls=0

    # Phase A: lightweight discovery only.
    for cluster in clusters:
        queries=(cluster.get('search_queries') or [])[:3] or [cluster.get('subniche') or cluster.get('niche')]
        for query in queries:
            for action in ('search','hotproducts'):
                try:
                    response=core.ali(action,keywords=str(query),ship_to='GR',currency='EUR',language='EN',page=1,page_size=50);api_calls+=1
                except Exception as exc:
                    print(json.dumps({'warning':'aliexpress_discovery_call_failed','cluster':cluster.get('cluster_key'),'query':query,'action':action,'error':str(exc)[:300]}),flush=True);continue
                for raw in core.walk_products(response.get('data')):
                    x=core.ali_normalize(raw,cluster)
                    if not x or x['source_record_hash'] in excluded:continue
                    x['product_fingerprint']=ali_search_fingerprint(x)
                    old=raw_by_pid.get(x['source_product_id'])
                    if not old or x['expected_commission_eur']>old['expected_commission_eur']:
                        raw_by_pid[x['source_product_id']]=x

    candidates=list(raw_by_pid.values())
    preview_ledger=[{
      'source_product_id':x['source_product_id'],'source_record_hash':x['source_record_hash'],'product_fingerprint':x['product_fingerprint'],
      'seller_id':x.get('shop_id'),'product_name':x.get('product_name'),'sale_price_eur':x.get('sale_price_eur'),'expected_commission_eur':x.get('expected_commission_eur'),
      'metadata':{'seller_name':x.get('merchant_name'),'seller_url':x.get('shop_url'),'stage':'search_result','evaluate_rate':x.get('api_evaluate_rate'),'latest_volume':x.get('api_latest_volume'),'ship_to_days':x.get('api_ship_to_days')}
    } for x in candidates]
    statuses=base.delta_status('aliexpress_affiliate_api',preview_ledger) if preview_ledger else {}
    delta_ids={k for k,v in statuses.items() if v in ('new','changed')}
    delta_preview=[x for x in candidates if x['source_product_id'] in delta_ids]

    # Phase B: expensive detail refresh only for true deltas + bounded refill.
    refreshed={};ids=[x['source_product_id'] for x in delta_preview]
    for start in range(0,len(ids),40):
        try:
            res=core.ali('details',product_ids=ids[start:start+40],ship_to='GR',currency='EUR',language='EN');api_calls+=1
        except Exception as exc:
            print(json.dumps({'warning':'aliexpress_delta_details_failed','batch_start':start,'error':str(exc)[:300]}),flush=True);continue
        for raw in core.walk_products(res.get('data')):refreshed[str(raw.get('product_id'))]=raw

    delta=[];ledger=[]
    for x in delta_preview:
        raw=refreshed.get(x['source_product_id'])
        nx=core.ali_normalize(raw,x['cluster']) if raw else x
        if not nx:continue
        nx['product_fingerprint']=ali_search_fingerprint(nx)
        seller=seller_state.get(str(nx.get('shop_id'))) or {}
        nx['seller_trust_state']=seller.get('trust_state','discovery')
        nx['seller_evidence_score']=float(seller.get('evidence_score') or 0)
        nx['seller_trust_confidence']=float(seller.get('confidence') or 0)
        delta.append(nx)
        ledger.append({
          'source_product_id':nx['source_product_id'],'source_record_hash':nx['source_record_hash'],'product_fingerprint':nx['product_fingerprint'],
          'seller_id':nx.get('shop_id'),'product_name':nx.get('product_name'),'sale_price_eur':nx.get('sale_price_eur'),'expected_commission_eur':nx.get('expected_commission_eur'),
          'metadata':{'seller_name':nx.get('merchant_name'),'seller_url':nx.get('shop_url'),'stage':'detail_delta','evaluate_rate':nx.get('api_evaluate_rate'),'latest_volume':nx.get('api_latest_volume'),'ship_to_days':nx.get('api_ship_to_days')}
        })
    if ledger:base.checkpoint('aliexpress_affiliate_api',ledger)

    # Phase C: only bounded delta/refill rows reach Greek-market research.
    buckets={str(c['cluster_key']):[] for c in clusters}
    for x in delta:buckets[str(x['semantic_cluster_key'])].append(x)
    evidence={};research_stats={}
    for cluster in clusters:
        key=str(cluster['cluster_key'])
        ordered=sorted(buckets[key],key=lambda x:(1 if x.get('seller_trust_state')=='trusted' else 0,float(x.get('seller_evidence_score') or 0),float(x.get('seller_quality_score') or 0),float(x.get('expected_commission_eur') or 0)),reverse=True)[:core.ALI_PER_CLUSTER_RESEARCH]
        researched,stats=core.research_rows(ordered,limit=len(ordered),workers=8);research_stats[key]=stats;evidence[key]=researched

    unchanged=sum(1 for v in statuses.values() if v=='unchanged')
    base.inc('mark_source',source_network='aliexpress_affiliate_api',source_partition='semantic_discovery',baseline_completed=True,changed=bool(delta),metadata={
      'strategy':'search_fingerprint_then_details_on_delta_with_bounded_refill','search_candidates':len(candidates),'new_changed_or_refill':len(delta_preview),'details_candidates':len(ids),'unchanged_after_refill':unchanged,'api_calls':api_calls
    })
    return evidence,{
      'mode':'product_delta','delta_strategy':'search_fingerprint_then_details_with_bounded_refill','api_calls':api_calls,'api_candidates':len(candidates),
      'commission_gt30_unique':len(candidates),'new_or_changed':len(delta_preview),'details_requested':len(ids),'unchanged':unchanged,
      'trusted_sellers_seen':sum(1 for x in delta if x.get('seller_trust_state')=='trusted'),'greek_research':research_stats,
      'ai_shortlist':sum(len(v) for v in evidence.values())
    }


core.discover_aliexpress=incremental_aliexpress_v2

if __name__=='__main__':
    raise SystemExit(core.main())
