#!/usr/bin/env python3
"""AFFINITY Semantic Marketplace delta-first production runner v3.

Modes:
- normal: true NEW/CHANGED first, bounded refill from unchanged ledger rows.
- policy_rebuild: bounded re-evaluation of the known catalogue after scoring/policy changes.
- full_rebuild: exceptional diagnostic mode; use the full scanner only when explicitly requested.

Quality gates are never relaxed. Final portfolio diversification is stricter than the
candidate pool: max 2 selected products per Linkwise merchant or AliExpress seller.
"""
from __future__ import annotations

import collections
import os
from typing import Any

import semantic_marketplace_200_smart_v2 as v2

base=v2.base
core=v2.core
MODE=os.getenv('MARKETPLACE200_RUN_MODE','normal').strip().lower()
MAX_PER_SOURCE=2


def select_linkwise_cap2(clusters:list[dict[str,Any]],evaluated:dict[str,list[dict[str,Any]]])->list[dict[str,Any]]:
    selected=[];merchant=collections.Counter();used=set()
    for cluster in clusters:
        key=str(cluster['cluster_key'])
        rows=sorted(
            evaluated.get(key,[]),
            key=lambda x:(
                float(x.get('demand_score') or 0),
                float(x.get('whitespace_score') or 0),
                float(x.get('affinity_score') or 0),
                float(x.get('product_quality_score') or 0),
                float(x.get('expected_commission_eur') or 0),
            ),
            reverse=True,
        )
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
    # Keep the incremental seller-trust requirement before applying final cap=2.
    state=base.inc('state')
    trusted={str(x.get('seller_id')) for x in state.get('sellers') or [] if x.get('trust_state')=='trusted'}
    selected=[];seller=collections.Counter();used=set()
    def eligible(x:dict[str,Any])->bool:
        shop=str(x.get('shop_id') or x.get('merchant_name') or '')
        return bool(
            shop and shop in trusted
            and x.get('quality_decision')=='SELECTED'
            and x.get('skeptic_verdict')=='validated'
            and x.get('greek_availability') in ('ABSENT','VERY_RARE')
        )
    for cluster in clusters:
        key=str(cluster['cluster_key'])
        rows=sorted(
            evaluated.get(key,[]),
            key=lambda x:(float(x.get('demand_score') or 0),float(x.get('whitespace_score') or 0),float(x.get('affinity_score') or 0),float(x.get('product_quality_score') or 0)),
            reverse=True,
        )
        count=0
        for x in rows:
            if not eligible(x):continue
            src=str(x.get('source_record_hash'));shop=str(x.get('shop_id') or x.get('merchant_name'))
            if not src or src in used or seller[shop]>=MAX_PER_SOURCE:continue
            selected.append(x);used.add(src);seller[shop]+=1;count+=1
            if count>=10:break
    if len(selected)<100:
        remainder=[x for rows in evaluated.values() for x in rows]
        remainder.sort(key=lambda x:(float(x.get('demand_score') or 0),float(x.get('whitespace_score') or 0),float(x.get('affinity_score') or 0),float(x.get('product_quality_score') or 0)),reverse=True)
        for x in remainder:
            if len(selected)>=100 or not eligible(x):continue
            src=str(x.get('source_record_hash'));shop=str(x.get('shop_id') or x.get('merchant_name'))
            if not src or src in used or seller[shop]>=MAX_PER_SOURCE:continue
            selected.append(x);used.add(src);seller[shop]+=1
    return selected[:100]


# Final selection policy: merchant/seller diversity is enforced after all quality gates.
core.select_linkwise=select_linkwise_cap2
core.select_aliexpress=select_aliexpress_cap2

if MODE=='policy_rebuild':
    # Re-score a larger but still bounded known-catalogue slice; no full multi-million AI run.
    v2.REFILL_LINKWISE=max(v2.REFILL_LINKWISE,500)
    v2.REFILL_ALI=max(v2.REFILL_ALI,500)
    v2.FORCE_BOUNDED_REEVAL=True
elif MODE=='full_rebuild':
    # Exceptional mode only: restore the original full-feed discovery functions.
    # All downstream research/skeptic/quality gates and cap=2 selectors remain active.
    import importlib
    raw=importlib.reload(core)
    raw.select_linkwise=select_linkwise_cap2
    raw.select_aliexpress=select_aliexpress_cap2
    core=raw
elif MODE!='normal':
    raise SystemExit(f'unsupported MARKETPLACE200_RUN_MODE={MODE}')

if __name__=='__main__':
    raise SystemExit(core.main())
