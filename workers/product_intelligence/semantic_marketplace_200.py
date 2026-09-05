#!/usr/bin/env python3
"""AFFINITY Semantic Social Marketplace 200 autonomous production orchestrator.

Two independent portfolios:
- Linkwise Discovery 100: 10 semantic clusters x up to 10 products, >EUR30,
  strict merchant gate, max 3 products per merchant.
- AliExpress Exclusive 100: Affiliate API discovery, >EUR30, Greece delivery,
  Greek ABSENT/VERY_RARE evidence, max 3 products per shop.

Deterministic gates run before AI. Research Agent and independent Skeptic Agent
then decide semantic/product quality. Quotas never weaken quality gates.
"""
from __future__ import annotations

import collections
import hashlib
import json
import math
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import ijson

from creative_contract_v10 import excluded_vertical
from greek_market_semantic_research import research_rows
from linkwise_direct_feed import download as download_linkwise
from product_agents import canonical_key, parse_commission_rule
from stream_feed import iter_records, normalize, normalize_domain

GATEWAY=os.getenv('MARKETPLACE200_GATEWAY','https://rpfadpdnnxequgvdcfoq.supabase.co/functions/v1/marketplace200-agent-gateway')
ALI_GATEWAY=os.getenv('ALIEXPRESS_AFFILIATE_GATEWAY','https://rpfadpdnnxequgvdcfoq.supabase.co/functions/v1/aliexpress-affiliate-gateway')
AUDIENCE='socialmarket-supabase-worker'
FEED=Path(os.getenv('PRODUCT_SOURCE_FEED','linkwise-products.json'))
PROFILE=Path(os.getenv('MARKETPLACE200_PROFILE_PATH','semantic-marketplace-200-profile.json'))
MIN_COMMISSION=30.0
LINKWISE_PER_CLUSTER_AI=max(12,min(28,int(os.getenv('MARKETPLACE200_LINKWISE_AI_PER_CLUSTER','18'))))
ALI_PER_CLUSTER_RESEARCH=max(12,min(30,int(os.getenv('MARKETPLACE200_ALI_RESEARCH_PER_CLUSTER','20'))))
AI_BATCH=max(1,min(8,int(os.getenv('MARKETPLACE200_AI_BATCH','6'))))
HANDOFF_LIMIT=max(1,min(20,int(os.getenv('MARKETPLACE200_DAILY_HANDOFF','10'))))

_TOKEN=None

def oidc_token()->str:
    global _TOKEN
    if _TOKEN:return _TOKEN
    base=os.environ['ACTIONS_ID_TOKEN_REQUEST_URL'];sep='&' if '?' in base else '?'
    req=urllib.request.Request(base+sep+'audience='+urllib.parse.quote(AUDIENCE),headers={'Authorization':'Bearer '+os.environ['ACTIONS_ID_TOKEN_REQUEST_TOKEN']})
    with urllib.request.urlopen(req,timeout=30) as response:_TOKEN=str(json.loads(response.read().decode())['value'])
    return _TOKEN


def gateway(action:str,**payload:Any)->dict[str,Any]:
    body=json.dumps({'action':action,**payload},ensure_ascii=False,default=str).encode()
    req=urllib.request.Request(GATEWAY,data=body,headers={'Authorization':'Bearer '+oidc_token(),'Content-Type':'application/json'},method='POST')
    try:
        with urllib.request.urlopen(req,timeout=300) as response:data=json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        raw=exc.read().decode(errors='replace');raise RuntimeError(f'marketplace gateway {action} {exc.code}: {raw[:1200]}') from exc
    if not data.get('ok'):raise RuntimeError(f'marketplace gateway {action} failed: {data}')
    return data


def ali(action:str,**payload:Any)->dict[str,Any]:
    body=json.dumps({'action':action,**payload},ensure_ascii=False).encode()
    req=urllib.request.Request(ALI_GATEWAY,data=body,headers={'Content-Type':'application/json'},method='POST')
    try:
        with urllib.request.urlopen(req,timeout=90) as response:data=json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        raw=exc.read().decode(errors='replace');raise RuntimeError(f'aliexpress gateway {action} {exc.code}: {raw[:800]}') from exc
    if not data.get('ok'):raise RuntimeError(f'aliexpress gateway {action} failed: {data}')
    return data


def fold(value:Any)->str:
    return ' '.join(re.sub(r'[^a-z0-9α-ωάέήίόύώϊϋΐΰ]+',' ',str(value or '').casefold()).split())

STOP={'the','and','for','with','from','this','that','new','pro','plus','home','smart','professional','portable','electric','machine','tool','tools','product','set','kit','black','white','blue','red'}
def tokens(value:Any)->set[str]:return {t for t in fold(value).split() if len(t)>=3 and t not in STOP}


def unique_row(rows:list[dict[str,Any]])->dict[str,Any]|None:
    by={str(x.get('merchant_program_id') or x.get('merchant_id')):x for x in rows}
    return next(iter(by.values())) if len(by)==1 else None


def merchant_maps(programs:list[dict[str,Any]]):
    by_program={};aliases={};by_domain={}
    for row in programs:
        p=fold(row.get('program_name'))
        if p:by_program[p]=row
        for alias_name in row.get('aliases') or []:
            a=fold(alias_name)
            if a:aliases[a]=row
        dom=normalize_domain(row.get('official_domain'))
        if dom:by_domain.setdefault(dom,[]).append(row)
    return by_program,aliases,by_domain


def resolve_merchant(product:dict[str,Any],maps)->tuple[dict[str,Any]|None,str|None]:
    by_program,aliases,by_domain=maps
    dom=normalize_domain(product.get('target_domain'))
    if dom:
        exact=unique_row(by_domain.get(dom,[]))
        if exact:return exact,'target_domain_exact'
        labels=dom.split('.')
        for i in range(1,max(1,len(labels)-1)):
            row=unique_row(by_domain.get('.'.join(labels[i:]),[]))
            if row:return row,'target_domain_suffix'
    key=fold(product.get('program_name'))
    if key in by_program:return by_program[key],'program_exact'
    if key in aliases:return aliases[key],'alias_exact'
    return None,None


def cluster_terms(cluster:dict[str,Any])->set[str]:
    return tokens(' '.join([str(cluster.get(k) or '') for k in ('niche','subniche','job_to_be_done','pain_statement','gap_statement')]+[str(x) for x in cluster.get('search_queries') or []]))


def cluster_similarity(product:dict[str,Any],cluster:dict[str,Any])->float:
    terms=cluster.get('_terms') or cluster_terms(cluster)
    title=tokens(product.get('product_name'));cat=tokens(product.get('category'));desc=tokens(str(product.get('description') or '')[:1800])
    if not terms:return 0
    title_hit=len(terms&title);cat_hit=len(terms&cat);desc_hit=len(terms&desc)
    return min(100.0,(title_hit*16+cat_hit*10+min(desc_hit,6)*4)+(12 if title_hit>=2 else 0))


def linkwise_scan(programs:list[dict[str,Any]],clusters:list[dict[str,Any]],excluded:set[str])->tuple[dict[str,list[dict[str,Any]]],dict[str,Any]]:
    if not FEED.exists() or FEED.stat().st_size<10_000_000:download_linkwise(FEED)
    maps=merchant_maps(programs)
    for c in clusters:c['_terms']=cluster_terms(c)
    buckets={str(c['cluster_key']):[] for c in clusters};stats=collections.Counter();seen=0
    try:iterator=iter_records(FEED)
    except Exception as exc:raise RuntimeError(f'linkwise_stream_init_failed:{exc}')
    while True:
        try:raw=next(iterator)
        except StopIteration:break
        except ijson.common.IncompleteJSONError:
            stats['truncated_tail_after_complete_records']+=1;break
        seen+=1;p=normalize(raw)
        merchant,method=resolve_merchant(p,maps)
        if not merchant:stats['merchant_not_in_strict_gate']+=1;continue
        if excluded_vertical({**p,'merchant_name':merchant.get('canonical_name')}):stats['unsafe_or_excluded_vertical']+=1;continue
        if p.get('in_stock') is False:stats['out_of_stock']+=1;continue
        if not p.get('tracking_url') or not (p.get('image_url') or p.get('thumb_url')):stats['missing_tracking_or_image']+=1;continue
        price=float(p.get('price') or 0)
        if price<=0:stats['bad_price']+=1;continue
        comm=parse_commission_rule(merchant.get('raw_commission_pct'),merchant.get('raw_flat_commission'),price)
        expected=float(comm.get('expected_commission_eur') or 0)
        if expected<=MIN_COMMISSION:stats['commission_lte_30']+=1;continue
        p.update(comm);p['expected_commission_eur']=round(expected,4)
        source=str(p.get('source_record_hash') or hashlib.sha256(f"linkwise:{merchant.get('merchant_id')}:{p.get('product_id')}:{p.get('tracking_url')}".encode()).hexdigest())
        if source in excluded:stats['already_socialized_or_published']+=1;continue
        best=None;best_score=0.0
        for c in clusters:
            s=cluster_similarity(p,c)
            if s>best_score:best_score=s;best=c
        if not best or best_score<16:stats['no_semantic_retrieval_match']+=1;continue
        completeness=sum(bool(p.get(k)) for k in ('product_name','description','category','image_url','tracking_url','product_id'))/6*100
        trust=float(merchant.get('trust_score') or 0);rank=float(merchant.get('global_rank') or 100)
        retrieval=min(100,best_score*.45+min(100,expected/1.2)*.18+trust*.20+completeness*.12+max(0,100-rank)*.05)
        candidate={
            'portfolio':'linkwise','source_network':'linkwise','source_record_hash':source,'source_product_id':str(p.get('product_id') or ''),
            'semantic_cluster_key':best['cluster_key'],'niche':best['niche'],'subniche':best.get('subniche'),'cluster':{k:v for k,v in best.items() if not k.startswith('_')},
            'product_name':str(p.get('product_name') or ''),'brand_name':p.get('brand_name') or p.get('brand'),'description':str(p.get('description') or '')[:2200],
            'category':p.get('category'),'image_url':p.get('image_url') or p.get('thumb_url'),'tracking_url':p.get('tracking_url'),'detail_url':p.get('target_url'),
            'sale_price_eur':price,'expected_commission_eur':expected,'merchant_id':str(merchant.get('merchant_id')),'merchant_program_id':str(merchant.get('merchant_program_id')),
            'merchant_name':merchant.get('canonical_name'),'merchant_global_rank':int(merchant.get('global_rank') or 9999),'merchant_trust_score':float(merchant.get('trust_score') or 0),
            'merchant_research_confidence':float(merchant.get('research_confidence') or 0),'merchant_risk_flag':bool(merchant.get('risk_flag')),
            'seller_quality_score':None,'retrieval_score':round(retrieval,2),'merchant_resolution_method':method,
            'evidence_summary':{'source':'live Linkwise full feed','merchant_gate':{'global_rank':merchant.get('global_rank'),'trust_score':merchant.get('trust_score'),'research_confidence':merchant.get('research_confidence'),'risk_flag':merchant.get('risk_flag')},'merchant_resolution_method':method,'deterministic_retrieval_score':round(retrieval,2),'commission_rule':comm.get('commission_rule')}
        }
        buckets[str(best['cluster_key'])].append(candidate);stats['commission_and_merchant_eligible']+=1
        if seen%300000==0:print(json.dumps({'phase':'linkwise_scan','seen':seen,'eligible':stats['commission_and_merchant_eligible']},ensure_ascii=False),flush=True)
    # AI sees a bounded, diverse shortlist rather than the multi-million feed.
    out={}
    for c in clusters:
        key=str(c['cluster_key']);ordered=sorted(buckets[key],key=lambda x:(x['retrieval_score'],x['expected_commission_eur']),reverse=True)
        pre=[];per_merchant=collections.Counter();dedup=set()
        for x in ordered:
            ck=canonical_key({'product_name':x['product_name'],'brand_name':x.get('brand_name'),'category':x.get('category'),'merchant_name':x.get('merchant_name'),'product_id':x.get('source_product_id')})
            if ck in dedup:continue
            mid=x['merchant_id']
            if per_merchant[mid]>=4:continue
            dedup.add(ck);per_merchant[mid]+=1;pre.append(x)
            if len(pre)>=LINKWISE_PER_CLUSTER_AI:break
        out[key]=pre
    return out,{'records_seen':seen,**dict(stats),'ai_shortlist':sum(len(v) for v in out.values())}


def walk_products(obj:Any):
    if isinstance(obj,dict):
        keys={str(k).lower() for k in obj}
        if 'product_id' in keys and ('product_title' in keys or 'sale_price' in keys or 'target_sale_price' in keys):yield obj
        for value in obj.values():yield from walk_products(value)
    elif isinstance(obj,list):
        for value in obj:yield from walk_products(value)


def pct(value:Any)->float:
    try:return float(re.sub(r'[^0-9.]','',str(value or '0')) or 0)
    except Exception:return 0.0


def money_num(value:Any)->float:
    try:return float(re.sub(r'[^0-9.]','',str(value or '0')) or 0)
    except Exception:return 0.0


def ali_normalize(raw:dict[str,Any],cluster:dict[str,Any])->dict[str,Any]|None:
    pid=str(raw.get('product_id') or '').strip();title=str(raw.get('product_title') or '').strip()
    price=money_num(raw.get('target_sale_price') or raw.get('sale_price') or raw.get('app_sale_price'))
    rate=pct(raw.get('commission_rate') or raw.get('hot_product_commission_rate') or raw.get('relevant_market_commission_rate'))
    expected=price*rate/100
    if not pid or not title or price<=0 or expected<=MIN_COMMISSION:return None
    image=str(raw.get('product_main_image_url') or '').strip();tracking=str(raw.get('promotion_link') or '').strip();detail=str(raw.get('product_detail_url') or '').strip()
    if not image or not (tracking or detail):return None
    er=pct(raw.get('evaluate_rate'));volume=money_num(raw.get('lastest_volume'));shop_id=str(raw.get('shop_id') or raw.get('shop_url') or 'unknown')
    evidence_quality=min(100,(er*.65 if er else 35)+min(30,math.log10(volume+1)*10)+(5 if raw.get('ship_to_days') else 0))
    source=f'aliexpress-api:{pid}'
    return {
      'portfolio':'aliexpress','source_network':'aliexpress_affiliate_api','source_record_hash':source,'source_product_id':pid,
      'semantic_cluster_key':cluster['cluster_key'],'niche':cluster['niche'],'subniche':cluster.get('subniche'),'cluster':cluster,
      'product_name':title,'brand_name':None,'description':'','category':raw.get('second_level_category_name') or raw.get('first_level_category_name'),
      'image_url':image,'tracking_url':tracking,'detail_url':detail,'sale_price_eur':price,'expected_commission_eur':round(expected,4),
      'merchant_id':None,'merchant_name':f'AliExpress Shop {shop_id}','shop_id':shop_id,'shop_url':raw.get('shop_url'),'merchant_global_rank':None,'merchant_trust_score':None,'merchant_research_confidence':None,'merchant_risk_flag':False,
      'seller_quality_score':round(evidence_quality,2),'api_evaluate_rate':er or None,'api_latest_volume':volume or None,'api_ship_to_days':raw.get('ship_to_days'),
      'evidence_summary':{'source':'AliExpress Affiliate API','product_positive_rating_rate':er or None,'recent_volume':volume or None,'shop_id':raw.get('shop_id'),'shop_url':raw.get('shop_url'),'ship_to_days':raw.get('ship_to_days'),'commission_rate_pct':rate,'quality_note':'evaluate_rate is product positive-rating evidence, not an independent seller trust score'}
    }


def discover_aliexpress(clusters:list[dict[str,Any]],excluded:set[str])->tuple[dict[str,list[dict[str,Any]]],dict[str,Any]]:
    raw_by_pid={};api_calls=0
    for cluster in clusters:
        queries=(cluster.get('search_queries') or [])[:3]
        if not queries:queries=[cluster.get('subniche') or cluster.get('niche')]
        for query in queries:
            for action in ('search','hotproducts'):
                try:response=ali(action,keywords=str(query),ship_to='GR',currency='EUR',language='EN',page=1,page_size=50);api_calls+=1
                except Exception as exc:
                    print(json.dumps({'warning':'aliexpress_discovery_call_failed','cluster':cluster.get('cluster_key'),'query':query,'action':action,'error':str(exc)[:300]}),flush=True);continue
                for raw in walk_products(response.get('data')):
                    x=ali_normalize(raw,cluster)
                    if not x or x['source_record_hash'] in excluded:continue
                    old=raw_by_pid.get(x['source_product_id'])
                    if not old or x['expected_commission_eur']>old['expected_commission_eur']:raw_by_pid[x['source_product_id']]=x
    candidates=list(raw_by_pid.values())
    # Refresh exact API details in bounded batches.
    refreshed={}
    ids=[x['source_product_id'] for x in candidates]
    for start in range(0,len(ids),40):
        try:res=ali('details',product_ids=ids[start:start+40],ship_to='GR',currency='EUR',language='EN');api_calls+=1
        except Exception:continue
        for raw in walk_products(res.get('data')):refreshed[str(raw.get('product_id'))]=raw
    for i,x in enumerate(candidates):
        raw=refreshed.get(x['source_product_id'])
        if raw:
            nx=ali_normalize(raw,x['cluster'])
            if nx:candidates[i]=nx
    buckets={str(c['cluster_key']):[] for c in clusters}
    for x in candidates:buckets[str(x['semantic_cluster_key'])].append(x)
    evidence_qualified={};research_stats={}
    for cluster in clusters:
        key=str(cluster['cluster_key']);ordered=sorted(buckets[key],key=lambda x:(x['seller_quality_score'],x['expected_commission_eur'],x.get('api_latest_volume') or 0),reverse=True)[:ALI_PER_CLUSTER_RESEARCH]
        researched,stats=research_rows(ordered,limit=len(ordered),workers=8);research_stats[key]=stats;evidence_qualified[key]=researched
    return evidence_qualified,{'api_calls':api_calls,'commission_gt30_unique':len(candidates),'greek_research':research_stats,'ai_shortlist':sum(len(v) for v in evidence_qualified.values())}


def evaluate_resilient(items:list[dict[str,Any]],depth:int=0)->list[dict[str,Any]]:
    if not items:return []
    try:return list(gateway('evaluate',items=items).get('items') or [])
    except Exception as exc:
        if len(items)==1:
            print(json.dumps({'warning':'marketplace_candidate_quarantined','source_record_hash':items[0].get('source_record_hash'),'error':str(exc)[:500]}),flush=True);return []
        mid=max(1,len(items)//2);time.sleep(min(2,0.35*(depth+1)))
        return evaluate_resilient(items[:mid],depth+1)+evaluate_resilient(items[mid:],depth+1)


def evaluate_buckets(buckets:dict[str,list[dict[str,Any]]])->dict[str,list[dict[str,Any]]]:
    out={}
    for key,items in buckets.items():
        results=[]
        for start in range(0,len(items),AI_BATCH):results.extend(evaluate_resilient(items[start:start+AI_BATCH]))
        out[key]=results
    return out


def select_linkwise(clusters:list[dict[str,Any]],evaluated:dict[str,list[dict[str,Any]]])->list[dict[str,Any]]:
    selected=[];merchant=collections.Counter();used=set()
    for cluster in clusters:
        key=str(cluster['cluster_key']);rows=sorted(evaluated.get(key,[]),key=lambda x:(float(x.get('affinity_score') or 0),float(x.get('product_quality_score') or 0),float(x.get('demand_score') or 0)),reverse=True)
        count=0
        for x in rows:
            if x.get('quality_decision')!='SELECTED' or x.get('skeptic_verdict')!='validated':continue
            src=str(x.get('source_record_hash'));mid=str(x.get('merchant_id'))
            if src in used or merchant[mid]>=3:continue
            selected.append(x);used.add(src);merchant[mid]+=1;count+=1
            if count>=10:break
    return selected


def select_aliexpress(clusters:list[dict[str,Any]],evaluated:dict[str,list[dict[str,Any]]])->list[dict[str,Any]]:
    selected=[];seller=collections.Counter();used=set()
    # First pass: semantic breadth up to 10 per cluster.
    for cluster in clusters:
        key=str(cluster['cluster_key']);rows=sorted(evaluated.get(key,[]),key=lambda x:(float(x.get('affinity_score') or 0),float(x.get('product_quality_score') or 0),float(x.get('demand_score') or 0)),reverse=True)
        count=0
        for x in rows:
            if x.get('quality_decision')!='SELECTED' or x.get('skeptic_verdict')!='validated' or x.get('greek_availability') not in ('ABSENT','VERY_RARE'):continue
            src=str(x.get('source_record_hash'));shop=str(x.get('shop_id') or x.get('merchant_name'))
            if src in used or seller[shop]>=3:continue
            selected.append(x);used.add(src);seller[shop]+=1;count+=1
            if count>=10:break
    # Second pass can fill unused capacity from the strongest remaining semantic opportunities.
    if len(selected)<100:
        remainder=[]
        for rows in evaluated.values():remainder.extend(rows)
        remainder.sort(key=lambda x:(float(x.get('affinity_score') or 0),float(x.get('product_quality_score') or 0),float(x.get('whitespace_score') or 0)),reverse=True)
        for x in remainder:
            if len(selected)>=100:break
            if x.get('quality_decision')!='SELECTED' or x.get('skeptic_verdict')!='validated' or x.get('greek_availability') not in ('ABSENT','VERY_RARE'):continue
            src=str(x.get('source_record_hash'));shop=str(x.get('shop_id') or x.get('merchant_name'))
            if src in used or seller[shop]>=3:continue
            selected.append(x);used.add(src);seller[shop]+=1
    return selected[:100]


def cluster_rows(plan:dict[str,Any])->list[dict[str,Any]]:
    out=[]
    for portfolio,key in (('linkwise','linkwise_clusters'),('aliexpress','aliexpress_clusters')):
        for rank,c in enumerate(plan.get(key) or [],1):out.append({**c,'portfolio':portfolio,'cluster_rank':rank,'evidence':{'evidence_ids':c.get('evidence_ids') or [],'rationale':c.get('rationale'),'search_queries':c.get('search_queries') or []}})
    return out


def main()->int:
    profile={'version':'affinity-semantic-marketplace-200-v1','status':'running','stages':{},'hard_policy':{'commission_gt_eur':30,'max_products_per_merchant':3,'max_products_per_seller':3,'linkwise_merchant_trust_min':65,'linkwise_research_confidence_min':0.55,'linkwise_global_rank_max':100,'product_quality_min':75,'affinity_min':76}}
    stage='context'
    try:
        ctx=gateway('context');profile['stages']['context']={'strict_merchant_programs':len(ctx.get('programs') or []),'pain_clusters':len(ctx.get('pains') or []),'market_snapshots':len(ctx.get('markets') or [])}
        excluded=set(str(x) for x in ctx.get('published_source_hashes') or [])
        stage='opportunity_plan';planned=gateway('plan');plan=planned.get('plan') or {};link_clusters=list(plan.get('linkwise_clusters') or [])[:10];ali_clusters=list(plan.get('aliexpress_clusters') or [])[:10]
        if len(link_clusters)!=10 or len(ali_clusters)!=10:raise RuntimeError(f'opportunity planner must return 10+10 clusters, got {len(link_clusters)}+{len(ali_clusters)}')
        profile['stages']['opportunity_plan']={'linkwise_clusters':[c.get('cluster_key') for c in link_clusters],'aliexpress_clusters':[c.get('cluster_key') for c in ali_clusters]}

        stage='linkwise_full_feed';link_buckets,link_stats=linkwise_scan(list(ctx.get('programs') or []),link_clusters,excluded);profile['stages']['linkwise_full_feed']=link_stats
        stage='linkwise_agents';link_eval=evaluate_buckets(link_buckets);link_selected=select_linkwise(link_clusters,link_eval);profile['stages']['linkwise_agents']={'evaluated':sum(len(x) for x in link_eval.values()),'selected':len(link_selected),'underfilled':len(link_selected)<100}

        stage='aliexpress_api';ali_buckets,ali_stats=discover_aliexpress(ali_clusters,excluded);profile['stages']['aliexpress_api']=ali_stats
        stage='aliexpress_agents';ali_eval=evaluate_buckets(ali_buckets);ali_selected=select_aliexpress(ali_clusters,ali_eval);profile['stages']['aliexpress_agents']={'evaluated':sum(len(x) for x in ali_eval.values()),'selected':len(ali_selected),'underfilled':len(ali_selected)<100}

        all_items=link_selected+ali_selected
        stage='persist';persisted=gateway('persist',items=all_items,clusters=cluster_rows(plan),source_counts={'linkwise_records_seen':link_stats.get('records_seen'),'aliexpress_api_candidates':ali_stats.get('commission_gt30_unique')},eligible_counts={'linkwise_ai_shortlist':link_stats.get('ai_shortlist'),'aliexpress_ai_shortlist':ali_stats.get('ai_shortlist')},metadata={'engine':'semantic_marketplace_200','quality_first':True,'linkwise_underfilled':len(link_selected)<100,'aliexpress_underfilled':len(ali_selected)<100});profile['run_id']=persisted['run_id'];profile['selected_counts']=persisted['selected_counts'];profile['caps']={'merchant_max':persisted.get('merchant_max'),'seller_max':persisted.get('seller_max')}
        stage='socialscheduler_handoff';handoff=gateway('handoff',run_id=persisted['run_id'],limit=HANDOFF_LIMIT);profile['handoff']=handoff
        profile['status']='completed';profile['stage']='complete';PROFILE.write_text(json.dumps(profile,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
        print(json.dumps({'ok':True,'run_id':profile['run_id'],'linkwise':len(link_selected),'aliexpress':len(ali_selected),'total':len(all_items),'merchant_max':persisted.get('merchant_max'),'seller_max':persisted.get('seller_max'),'handoff':handoff.get('products_handed_off')},ensure_ascii=False),flush=True);return 0
    except Exception as exc:
        profile.update({'status':'failed','stage':stage,'error':str(exc)[:2400]});PROFILE.write_text(json.dumps(profile,ensure_ascii=False,indent=2,default=str),encoding='utf-8');print(json.dumps({'ok':False,'stage':stage,'error':str(exc)},ensure_ascii=False),flush=True);return 1

if __name__=='__main__':raise SystemExit(main())
