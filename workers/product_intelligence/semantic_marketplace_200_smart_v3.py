#!/usr/bin/env python3
"""AFFINITY Semantic Marketplace delta-first production runner v3.

Modes:
- normal: true NEW/CHANGED first, bounded refill from unchanged rows.
- policy_rebuild: larger bounded re-evaluation after scoring/policy changes.
- full_rebuild: exceptional diagnostic full scan, explicit only.

Quality gates are never relaxed. Merchant size is not a positive signal.
Retrieval trust uses merchant reliability evidence (rank/trust/research/no-risk),
while historical conversion/commercial metrics remain ranking signals rather than
hard admission gates. Final portfolio cap is max 2 products per merchant/seller.
"""
from __future__ import annotations

import collections
import concurrent.futures
import hashlib
import os
from typing import Any

import semantic_marketplace_200_smart_v2 as v2

base=v2.base
core=v2.core
MODE=os.getenv('MARKETPLACE200_RUN_MODE','normal').strip().lower()
MAX_PER_SOURCE=2
PROGRAM_WORKERS=max(2,min(8,int(os.getenv('LINKWISE_PROGRAM_WORKERS','6'))))


def merchant_reliability_ok(x:dict[str,Any])->bool:
    return bool(
        x.get('external_program_id')
        and not bool(x.get('risk_flag'))
        and float(x.get('trust_score') or 0)>=65
        and float(x.get('research_confidence') or 0)>=0.55
        and int(x.get('global_rank') or 9999)<=100
    )


def incremental_linkwise_v3(programs:list[dict[str,Any]],clusters:list[dict[str,Any]],excluded:set[str]):
    """Fetch only reliability-qualified merchant program deltas.

    Commercial history affects candidate ranking through existing retrieval_score,
    but cannot exclude a merchant that passes the canonical reliability gates.
    """
    st=base.inc('state');strict={str(x.get('merchant_program_id')):x for x in programs}
    state_programs=[]
    for x in st.get('programs') or []:
        canonical=strict.get(str(x.get('merchant_program_id')))
        if canonical:state_programs.append({**canonical,**x})
    if not st.get('linkwise_baseline_completed'):
        return base.baseline_scan(state_programs or programs,clusters,excluded)

    trusted=[x for x in state_programs if merchant_reliability_ok(x)]
    trusted.sort(key=lambda x:(int(x.get('global_rank') or 9999),-float(x.get('trust_score') or 0),-float(x.get('research_confidence') or 0),-float(x.get('commercial_score') or 0)))
    buckets={str(c['cluster_key']):[] for c in clusters};stats=collections.Counter();all_raw=[];program_stats=[]
    for c in clusters:c['_terms']=core.cluster_terms(c)

    with concurrent.futures.ThreadPoolExecutor(max_workers=PROGRAM_WORKERS) as pool:
        futures={pool.submit(base.fetch_program,m):m for m in trusted}
        for fut in concurrent.futures.as_completed(futures):
            merchant=futures[fut]
            try:
                rows,s=fut.result();all_raw.extend((merchant,x) for x in rows);program_stats.append(s)
                stats['programs_fetched']+=1;stats['records_seen']+=int(s.get('seen') or 0);stats['hard_eligible']+=int(s.get('eligible') or 0)
            except Exception as exc:
                stats['program_fetch_failed']+=1;program_stats.append({'merchant':merchant.get('canonical_name'),'error':str(exc)[:300]})

    ledger=[]
    for merchant,x in all_raw:
        p=x['p'];external=str(merchant.get('external_program_id'));source=hashlib.sha256(f"linkwise:{x['ledger_id']}".encode()).hexdigest()
        ledger.append({'source_product_id':x['ledger_id'],'source_record_hash':source,'product_fingerprint':x['fp'],'merchant_id':merchant.get('merchant_id'),'merchant_program_id':merchant.get('merchant_program_id'),'external_program_id':external,'product_name':p.get('product_name'),'sale_price_eur':p.get('price'),'expected_commission_eur':x['expected'],'metadata':{'provider_product_id':p.get('product_id'),'retrieval_tier':'reliability_qualified'}})

    statuses=base.delta_status('linkwise',ledger) if ledger else {}
    delta_ids={k for k,v in statuses.items() if v in ('new','changed')}
    stats['new_or_changed']=len(delta_ids);stats['unchanged']=sum(1 for v in statuses.values() if v=='unchanged')
    checkpoint=[x for x in ledger if x['source_product_id'] in delta_ids]
    if checkpoint:base.checkpoint('linkwise',checkpoint)

    for merchant,x in all_raw:
        if x['ledger_id'] not in delta_ids:continue
        cand=base.cluster_candidate(x['p'],merchant,clusters,x['expected'],x['comm'],str(merchant.get('external_program_id')),x['fp'])
        if cand and cand['source_record_hash'] not in excluded:buckets[str(cand['semantic_cluster_key'])].append(cand)

    shortlist=base.shortlist(buckets,clusters)
    base.inc('mark_source',source_network='linkwise',source_partition='reliability_qualified_programs',baseline_completed=True,changed=bool(delta_ids),metadata={'reliability_qualified_programs':len(trusted),'programs_fetched':stats['programs_fetched'],'new_or_changed':stats['new_or_changed'],'unchanged':stats['unchanged'],'commercial_history_is_ranking_not_gate':True})
    return shortlist,{'mode':'trusted_program_delta','trusted_programs':len(trusted),'retrieval_policy':'rank_trust_research_no_risk','program_stats':program_stats[:100],**dict(stats),'ai_shortlist':sum(len(v) for v in shortlist.values())}


def select_linkwise_cap2(clusters:list[dict[str,Any]],evaluated:dict[str,list[dict[str,Any]]])->list[dict[str,Any]]:
    selected=[];merchant=collections.Counter();used=set()
    rows_by_cluster=[]
    for cluster in clusters:
        key=str(cluster['cluster_key']);rows=sorted(evaluated.get(key,[]),key=lambda x:(float(x.get('demand_score') or 0),float(x.get('whitespace_score') or 0),float(x.get('affinity_score') or 0),float(x.get('product_quality_score') or 0),float(x.get('expected_commission_eur') or 0)),reverse=True);rows_by_cluster.append((cluster,rows))
    for cluster,rows in rows_by_cluster:
        count=0
        for x in rows:
            if x.get('quality_decision')!='SELECTED' or x.get('skeptic_verdict')!='validated':continue
            src=str(x.get('source_record_hash'));mid=str(x.get('merchant_id'))
            if not src or not mid or src in used or merchant[mid]>=MAX_PER_SOURCE:continue
            selected.append(x);used.add(src);merchant[mid]+=1;count+=1
            if count>=10:break
    if len(selected)<100:
        remainder=[x for rows in evaluated.values() for x in rows]
        remainder.sort(key=lambda x:(float(x.get('demand_score') or 0),float(x.get('whitespace_score') or 0),float(x.get('affinity_score') or 0),float(x.get('product_quality_score') or 0)),reverse=True)
        for x in remainder:
            if len(selected)>=100:break
            if x.get('quality_decision')!='SELECTED' or x.get('skeptic_verdict')!='validated':continue
            src=str(x.get('source_record_hash'));mid=str(x.get('merchant_id'))
            if not src or not mid or src in used or merchant[mid]>=MAX_PER_SOURCE:continue
            selected.append(x);used.add(src);merchant[mid]+=1
    return selected[:100]


def select_aliexpress_cap2(clusters:list[dict[str,Any]],evaluated:dict[str,list[dict[str,Any]]])->list[dict[str,Any]]:
    state=base.inc('state');trusted={str(x.get('seller_id')) for x in state.get('sellers') or [] if x.get('trust_state')=='trusted'}
    selected=[];seller=collections.Counter();used=set()
    def eligible(x:dict[str,Any])->bool:
        shop=str(x.get('shop_id') or x.get('merchant_name') or '')
        return bool(shop and shop in trusted and x.get('quality_decision')=='SELECTED' and x.get('skeptic_verdict')=='validated' and x.get('greek_availability') in ('ABSENT','VERY_RARE'))
    for cluster in clusters:
        key=str(cluster['cluster_key']);rows=sorted(evaluated.get(key,[]),key=lambda x:(float(x.get('demand_score') or 0),float(x.get('whitespace_score') or 0),float(x.get('affinity_score') or 0),float(x.get('product_quality_score') or 0)),reverse=True);count=0
        for x in rows:
            if not eligible(x):continue
            src=str(x.get('source_record_hash'));shop=str(x.get('shop_id') or x.get('merchant_name'))
            if not src or src in used or seller[shop]>=MAX_PER_SOURCE:continue
            selected.append(x);used.add(src);seller[shop]+=1;count+=1
            if count>=10:break
    if len(selected)<100:
        remainder=[x for rows in evaluated.values() for x in rows];remainder.sort(key=lambda x:(float(x.get('demand_score') or 0),float(x.get('whitespace_score') or 0),float(x.get('affinity_score') or 0),float(x.get('product_quality_score') or 0)),reverse=True)
        for x in remainder:
            if len(selected)>=100 or not eligible(x):continue
            src=str(x.get('source_record_hash'));shop=str(x.get('shop_id') or x.get('merchant_name'))
            if not src or src in used or seller[shop]>=MAX_PER_SOURCE:continue
            selected.append(x);used.add(src);seller[shop]+=1
    return selected[:100]


core.linkwise_scan=incremental_linkwise_v3
core.select_linkwise=select_linkwise_cap2
core.select_aliexpress=select_aliexpress_cap2

if MODE=='policy_rebuild':
    v2.REFILL_LINKWISE=max(v2.REFILL_LINKWISE,500);v2.REFILL_ALI=max(v2.REFILL_ALI,500);v2.FORCE_BOUNDED_REEVAL=True
elif MODE=='full_rebuild':
    import importlib
    raw=importlib.reload(core);raw.select_linkwise=select_linkwise_cap2;raw.select_aliexpress=select_aliexpress_cap2;core=raw
elif MODE!='normal':
    raise SystemExit(f'unsupported MARKETPLACE200_RUN_MODE={MODE}')

if __name__=='__main__':
    raise SystemExit(core.main())
