#!/usr/bin/env python3
"""Production launcher for AFFINITY Semantic SocialMarket.

Evidence-grounded opportunity planning is deterministic and bounded. AI is used
where it adds value: product research, skeptic QA and creative interpretation.
AliExpress uses the proven travelai server-side credential runtime through a
compatibility proxy. Missing tracking or weak evidence fails closed.
"""
from __future__ import annotations
import json,os,re,unicodedata,urllib.error,urllib.request
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


def _confidence100(v:Any)->float:
    try:
        x=float(v or 0);return _clamp(x*100 if x<=1 else x)
    except:return 0.0


def _slug(v:Any)->str:
    raw=unicodedata.normalize('NFKD',str(v or '')).encode('ascii','ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+','-',raw).strip('-')[:48] or 'need'


def _semantic_value(p:dict[str,Any])->float:
    return round(_clamp(p.get('commercial_intent'))*.34+_clamp(p.get('pain_severity'))*.27+_clamp(p.get('demand_score'))*.24+_clamp(p.get('audit_score'))*.09+_confidence100(p.get('confidence'))*.06,3)


def _market_map(markets:list[dict[str,Any]])->dict[str,dict[str,Any]]:
    out={}
    for m in markets:
        for key in (_slug(m.get('subcategory_name')),_slug(m.get('category_name'))):
            if key and (key not in out or _clamp(m.get('confidence'))>_clamp(out[key].get('confidence'))):out[key]=m
    return out


def _cluster_from_pain(p:dict[str,Any],portfolio:str,rank:int,markets:dict[str,dict[str,Any]])->dict[str,Any]:
    category=str(p.get('category') or 'Everyday life').strip();sub=str(p.get('subcategory') or category).strip();pain=str(p.get('canonical_text') or '').strip()
    market=markets.get(_slug(sub)) or markets.get(_slug(category)) or {}
    market_gap=_clamp(market.get('pain_gap_score'))
    competition=_clamp(p.get('competition_score'))
    whitespace=market_gap if market_gap>0 else _clamp(_clamp(p.get('pain_severity'))*.62+max(0,100-competition)*.38)
    demand=_clamp(p.get('demand_score'));intent=_clamp(p.get('commercial_intent'));conf=max(_confidence100(p.get('confidence')),_confidence100(market.get('confidence')))
    ident=str(p.get('id') or rank)
    prefix='lw' if portfolio=='linkwise' else 'ax'
    key=f"{prefix}-{rank:02d}-{_slug(sub)}-{_slug(ident)[-8:]}"[:80]
    job=f"Να λύσω πιο πρακτικά: {pain}"[:260]
    gap=f"Το συγκεκριμένο pain έχει τεκμηριωμένο ενδιαφέρον και χρειάζεται λύση με σαφές use-case fit, όχι generic επιλογή."[:300]
    return {
        'cluster_key':key,'niche':category,'subniche':sub,'job_to_be_done':job,'pain_statement':pain[:420],'gap_statement':gap,
        'demand_score':round(demand,2),'whitespace_score':round(whitespace,2),'commercial_intent_score':round(intent,2),'confidence':round(conf,2),
        'evidence_ids':[ident],'rationale':'Evidence-grounded AFFINITY opportunity selected from validated pain, intent and market signals.',
        'search_queries':[pain[:90],f'{sub} solution'.strip()[:90],f'{category} problem solver'.strip()[:90]],
    }


def _deterministic_plan(ctx:dict[str,Any])->dict[str,Any]:
    pains=[p for p in list(ctx.get('pains') or []) if str(p.get('canonical_text') or '').strip()]
    pains=sorted(pains,key=_semantic_value,reverse=True)
    if len(pains)<20:raise RuntimeError(f'validated_pain_pool_too_small:{len(pains)}')
    markets=_market_map(list(ctx.get('markets') or []))
    merchant_terms={_slug(x.get('primary_category')) for x in list(ctx.get('programs') or [])}|{_slug(x.get('primary_subcategory')) for x in list(ctx.get('programs') or [])}
    matched=[p for p in pains if _slug(p.get('category')) in merchant_terms or _slug(p.get('subcategory')) in merchant_terms]
    link_source=(matched+pains) if matched else pains
    link=[];used=set()
    for p in link_source:
        pid=str(p.get('id') or '')
        if pid in used:continue
        used.add(pid);link.append(_cluster_from_pain(p,'linkwise',len(link)+1,markets))
        if len(link)==10:break
    ali=[]
    for p in pains:
        pid=str(p.get('id') or '')
        if pid in used:continue
        used.add(pid);ali.append(_cluster_from_pain(p,'aliexpress',len(ali)+1,markets))
        if len(ali)==10:break
    if len(ali)<10:
        for p in pains:
            if len(ali)==10:break
            pid=str(p.get('id') or '')
            if any(pid in c.get('evidence_ids',[]) for c in ali):continue
            ali.append(_cluster_from_pain(p,'aliexpress',len(ali)+1,markets))
    if len(link)!=10 or len(ali)!=10:raise RuntimeError(f'deterministic_plan_incomplete:{len(link)}+{len(ali)}')
    return {'linkwise_clusters':link,'aliexpress_clusters':ali,'planner':'deterministic_evidence_affinity_v1'}


def _split_gateway(action:str,**payload:Any)->dict[str,Any]:
    if action=='plan':
        ctx=_BASE_GATEWAY('context')
        plan=_deterministic_plan(ctx)
        print(json.dumps({'phase':'opportunity_plan','planner':plan['planner'],'validated_pains':len(ctx.get('pains') or []),'markets':len(ctx.get('markets') or []),'eligible_programs':len(ctx.get('programs') or [])}),flush=True)
        return {'ok':True,'plan':plan}
    if action=='evaluate':
        items=list(payload.get('items') or [])
        if not items:return {'ok':True,'items':[]}
        if len(items)>2:raise RuntimeError('evaluate_batch_must_be_1_to_2')
        research=_ai('research',{'market':'GR','items':items}).get('research') or {};research_items=list(research.get('items') or [])
        skeptic=_ai('skeptic',{'market':'GR','items':items,'research':research_items}).get('skeptic') or {}
        rm={str(x.get('source_record_hash')):x for x in research_items};sm={str(x.get('source_record_hash')):x for x in list(skeptic.get('items') or [])};merged=[]
        for raw in items:
            key=str(raw.get('source_record_hash'));r=rm.get(key,{}) or {};s=sm.get(key,{}) or {}
            availability=str(s.get('corrected_greek_availability') or r.get('greek_availability_assessment') or raw.get('greek_availability') or 'UNKNOWN')
            quality=min(_clamp(r.get('product_quality_score')),_clamp(s.get('product_quality_score')));verdict=str(s.get('verdict') or 'needs_review')
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
    buckets,stats=_ORIGINAL_DISCOVER(clusters,excluded);generated=0;dropped=0
    for key,rows in list(buckets.items()):
        valid=[]
        for row in rows:
            if not row.get('tracking_url') and row.get('detail_url'):
                try:
                    result=core.ali('generate_link',url=row['detail_url']);row['tracking_url']=_find_tracking_url(result.get('data'))
                    if row['tracking_url']:generated+=1
                except Exception as exc:row.setdefault('evidence_summary',{})['tracking_generation_error']=str(exc)[:400]
            if not _find_tracking_url(row.get('tracking_url')):dropped+=1;continue
            row['tracking_url']=_find_tracking_url(row.get('tracking_url'));row.setdefault('evidence_summary',{})['affiliate_tracking_verified_source']='AliExpress Affiliate API promotion link';row.setdefault('evidence_summary',{})['credential_runtime']='travelai server-side secrets via compatibility gateway';valid.append(row)
        buckets[key]=valid
    stats.update({'api_blocked':False,'configured':True,'tracking_configured':True,'tracking_links_generated':generated,'missing_tracking_dropped':dropped,'ai_shortlist':sum(len(v) for v in buckets.values()),'credential_runtime':'travelai server-side'})
    return buckets,stats

core.discover_aliexpress=discover_aliexpress_safe
if __name__=='__main__':raise SystemExit(core.main())
