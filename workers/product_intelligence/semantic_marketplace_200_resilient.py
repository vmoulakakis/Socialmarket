#!/usr/bin/env python3
"""Production launcher for AFFINITY Semantic Marketplace 200.

DB/context/persistence stays in marketplace200-agent-gateway. AI planning,
research and skeptic reasoning uses bounded micro-agent calls. AliExpress uses
its proven travelai server-side credential runtime through a compatibility
proxy. Missing tracking or weak evidence fails closed.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

import semantic_marketplace_200 as core

_BASE_GATEWAY=core.gateway
_ORIGINAL_DISCOVER=core.discover_aliexpress
AI_GATEWAY=os.getenv('MARKETPLACE200_AI_GATEWAY','https://rpfadpdnnxequgvdcfoq.supabase.co/functions/v1/marketplace200-ai-gateway')


def _ai(action:str,payload:dict[str,Any])->dict[str,Any]:
    body=json.dumps({'action':action,'payload':payload},ensure_ascii=False,default=str).encode()
    req=urllib.request.Request(AI_GATEWAY,data=body,headers={'Authorization':'Bearer '+core.oidc_token(),'Content-Type':'application/json'},method='POST')
    try:
        with urllib.request.urlopen(req,timeout=300) as response:data=json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        raw=exc.read().decode(errors='replace');raise RuntimeError(f'marketplace ai {action} {exc.code}: {raw[:1000]}') from exc
    if not data.get('ok'):raise RuntimeError(f'marketplace ai {action} failed: {data}')
    return data


def _clamp(v:Any)->float:
    try:return max(0.0,min(100.0,float(v or 0)))
    except:return 0.0


def _split_gateway(action:str,**payload:Any)->dict[str,Any]:
    if action=='plan':
        ctx=_BASE_GATEWAY('context')
        pains=list(ctx.get('pains') or [])[:48]
        markets=list(ctx.get('markets') or [])[:28]
        feedback=list(ctx.get('feedback') or [])[:20]
        merchants=[
            {'merchant_id':x.get('merchant_id'),'merchant':x.get('canonical_name'),'category':x.get('primary_category'),'subcategory':x.get('primary_subcategory'),'rank':x.get('global_rank'),'trust':x.get('trust_score'),'confidence':x.get('research_confidence')}
            for x in list(ctx.get('programs') or [])[:50]
        ]
        link_payload={'market':'GR','pain_clusters':pains,'market_context':markets,'eligible_merchants':merchants,'feedback':feedback,'policy':ctx.get('config') or {}}
        ali_payload={'market':'GR','pain_clusters':pains,'market_context':markets,'feedback':feedback,'policy':ctx.get('config') or {}}
        link=_ai('plan_linkwise',link_payload).get('plan') or {}
        ali=_ai('plan_aliexpress',ali_payload).get('plan') or {}
        return {'ok':True,'plan':{'linkwise_clusters':list(link.get('linkwise_clusters') or []),'aliexpress_clusters':list(ali.get('aliexpress_clusters') or [])}}
    if action=='evaluate':
        items=list(payload.get('items') or [])
        if not items:return {'ok':True,'items':[]}
        if len(items)>8:raise RuntimeError('evaluate_batch_must_be_1_to_8')
        research=_ai('research',{'market':'GR','items':items}).get('research') or {}
        research_items=list(research.get('items') or [])
        skeptic=_ai('skeptic',{'market':'GR','items':items,'research':research_items}).get('skeptic') or {}
        rm={str(x.get('source_record_hash')):x for x in research_items}
        sm={str(x.get('source_record_hash')):x for x in list(skeptic.get('items') or [])}
        merged=[]
        for raw in items:
            key=str(raw.get('source_record_hash'));r=rm.get(key,{}) or {};s=sm.get(key,{}) or {}
            availability=str(s.get('corrected_greek_availability') or r.get('greek_availability_assessment') or raw.get('greek_availability') or 'UNKNOWN')
            quality=min(_clamp(r.get('product_quality_score')),_clamp(s.get('product_quality_score')))
            verdict=str(s.get('verdict') or 'needs_review')
            selected=verdict=='validated' and quality>=75 and _clamp(r.get('affinity_score'))>=76 and (raw.get('portfolio')!='aliexpress' or availability in ('ABSENT','VERY_RARE'))
            merged.append({**raw,**r,'greek_availability':availability,'product_quality_score':quality,'skeptic_verdict':verdict,'quality_decision':'SELECTED' if selected else ('REJECTED' if verdict=='rejected' else 'HOLD'),'skeptic_reasons':list(s.get('reasons') or []),'skeptic_blockers':list(s.get('blockers') or []),'required_rechecks':list(s.get('required_rechecks') or []),'contradiction_score':_clamp(s.get('contradiction_score'))})
        return {'ok':True,'items':merged}
    return _BASE_GATEWAY(action,**payload)


core.gateway=_split_gateway


def _health()->dict[str,Any]:
    try:
        with urllib.request.urlopen(core.ALI_GATEWAY,timeout=30) as response:return json.loads(response.read().decode())
    except Exception as exc:return {'ok':False,'configured':False,'tracking_configured':False,'error':str(exc)[:400]}


def _find_tracking_url(value:Any)->str:
    if isinstance(value,str):return value.replace('http://','https://',1) if value.startswith(('https://s.click.aliexpress.com/','http://s.click.aliexpress.com/')) else ''
    if isinstance(value,dict):
        for key in ('promotion_link','promotion_url','tracking_url'):
            url=_find_tracking_url(value.get(key))
            if url:return url
        for child in value.values():
            url=_find_tracking_url(child)
            if url:return url
    if isinstance(value,list):
        for child in value:
            url=_find_tracking_url(child)
            if url:return url
    return ''


def discover_aliexpress_safe(clusters,excluded):
    health=_health()
    if not health.get('configured') or not health.get('tracking_configured'):
        print(json.dumps({'warning':'aliexpress_api_blocked','configured':bool(health.get('configured')),'tracking_configured':bool(health.get('tracking_configured')),'policy':'no_cache_fallback'}),flush=True)
        return ({str(c.get('cluster_key')):[] for c in clusters},{'api_blocked':True,'configured':bool(health.get('configured')),'tracking_configured':bool(health.get('tracking_configured')),'commission_gt30_unique':0,'ai_shortlist':0,'greek_research':{},'policy':'authenticated_api_required_no_cached_substitute'})
    buckets,stats=_ORIGINAL_DISCOVER(clusters,excluded)
    generated=0;dropped=0
    for key,rows in list(buckets.items()):
        valid=[]
        for row in rows:
            if not row.get('tracking_url') and row.get('detail_url'):
                try:
                    result=core.ali('generate_link',url=row['detail_url']);row['tracking_url']=_find_tracking_url(result.get('data'))
                    if row['tracking_url']:generated+=1
                except Exception as exc:row.setdefault('evidence_summary',{})['tracking_generation_error']=str(exc)[:400]
            if not _find_tracking_url(row.get('tracking_url')):dropped+=1;continue
            row['tracking_url']=_find_tracking_url(row.get('tracking_url'))
            row.setdefault('evidence_summary',{})['affiliate_tracking_verified_source']='AliExpress Affiliate API promotion link'
            row.setdefault('evidence_summary',{})['credential_runtime']='travelai server-side secrets via compatibility gateway'
            valid.append(row)
        buckets[key]=valid
    stats.update({'api_blocked':False,'configured':True,'tracking_configured':True,'tracking_links_generated':generated,'missing_tracking_dropped':dropped,'ai_shortlist':sum(len(v) for v in buckets.values()),'credential_runtime':'travelai server-side'})
    return buckets,stats


core.discover_aliexpress=discover_aliexpress_safe
if __name__=='__main__':raise SystemExit(core.main())
