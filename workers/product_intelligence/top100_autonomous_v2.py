#!/usr/bin/env python3
"""Daily autonomous Top-100 affiliate selection for Greece.

Pipeline:
1. Fetches only >EUR20 expected-commission AliExpress candidates from the trusted
   Supabase gateway, excluding provider-confirmed published products.
2. Runs fail-closed live Greece scarcity checks.
3. Uses the existing DeepSeek reasoning gateway for demand/forecast/organic/ads
   synthesis with historical SocialScheduler feedback.
4. Selects at most five categories, de-duplicates near-identical SKUs and keeps
   up to 100 strongest evidence-qualified products.
5. Persists the run and hands a bounded daily tranche to SocialScheduler.

No gate is relaxed to manufacture 100 rows. Underfill is surfaced as truth.
"""
from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any

from greece_market_scarcity import qualify_rows

GATEWAY=os.getenv('TOP100_AGENT_GATEWAY','https://rpfadpdnnxequgvdcfoq.supabase.co/functions/v1/top100-agent-gateway')
AUDIENCE='socialmarket-supabase-worker'
POOL_LIMIT=max(150,min(500,int(os.getenv('TOP100_POOL_LIMIT','350'))))
SCARCITY_PROBE_LIMIT=max(120,min(400,int(os.getenv('TOP100_SCARCITY_PROBE_LIMIT','300'))))
SCARCITY_WORKERS=max(2,min(12,int(os.getenv('TOP100_SCARCITY_WORKERS','8'))))
HANDOFF_LIMIT=max(1,min(10,int(os.getenv('TOP100_DAILY_HANDOFF_LIMIT','5'))))
OUTPUT=Path(os.getenv('TOP100_PROFILE_PATH','top100-autonomous-v2-profile.json'))


def oidc_token() -> str:
    base=os.environ['ACTIONS_ID_TOKEN_REQUEST_URL']
    sep='&' if '?' in base else '?'
    url=f'{base}{sep}audience={urllib.parse.quote(AUDIENCE)}'
    req=urllib.request.Request(url,headers={'Authorization':'Bearer '+os.environ['ACTIONS_ID_TOKEN_REQUEST_TOKEN']})
    with urllib.request.urlopen(req,timeout=30) as response:
        return str(json.loads(response.read().decode())['value'])


def gateway(action: str, **payload: Any) -> dict[str, Any]:
    body=json.dumps({'action':action,**payload},ensure_ascii=False).encode()
    req=urllib.request.Request(GATEWAY,data=body,headers={'Authorization':'Bearer '+oidc_token(),'Content-Type':'application/json'},method='POST')
    try:
        with urllib.request.urlopen(req,timeout=240) as response:
            data=json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        raw=exc.read().decode(errors='replace')
        raise RuntimeError(f'top100 gateway {action} failed {exc.code}: {raw[:1200]}') from exc
    if not data.get('ok'):
        raise RuntimeError(f'top100 gateway {action} returned error: {data}')
    return data


def norm_tokens(text: Any) -> set[str]:
    folded=re.sub(r'[^a-z0-9α-ωάέήίόύώϊϋΐΰ]+',' ',str(text or '').casefold())
    stop={'the','and','for','with','new','set','pro','plus','black','white','blue','red','green','home','electric','machine','tool','product','portable'}
    return {t for t in folded.split() if len(t)>=3 and t not in stop}


def too_similar(a: dict[str, Any], b: dict[str, Any]) -> bool:
    ta,tb=norm_tokens(a.get('product_name')),norm_tokens(b.get('product_name'))
    if not ta or not tb:return False
    j=len(ta&tb)/max(1,len(ta|tb))
    return j>=.78


def merge_ai(rows: list[dict[str, Any]], ai: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by={str(x.get('source_record_hash')):x for x in ai if x.get('source_record_hash')}
    out=[]
    for row in rows:
        result=by.get(str(row.get('source_record_hash')))
        if not result:continue
        x=dict(row)
        for key in ('demand_score','forecast_score','organic_score','ads_score','viral_score','opportunity_score'):
            try:x[key]=max(0.0,min(100.0,float(result.get(key) or 0)))
            except Exception:x[key]=0.0
        x['audience']=str(result.get('audience') or '')[:800]
        x['hook']=str(result.get('hook') or '')[:600]
        x['caption']=str(result.get('caption') or '')[:2400]
        x['hashtags']=[str(h)[:80] for h in (result.get('hashtags') or []) if str(h).strip()][:9]
        x['reason']=str(result.get('reason') or '')[:1800]
        x['landing_candidate']=bool(result.get('landing_candidate')) and x['opportunity_score']>=86 and x['viral_score']>=78
        x['product_id']=str(row.get('id') or row.get('product_id') or '')
        x['product_name']=str(row.get('title') or row.get('product_name') or '')
        x['image_url']=str(row.get('mainImage') or row.get('image_url') or '')
        out.append(x)
    return out


def category_portfolio(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]],list[str],dict[str,Any]]:
    groups: dict[str,list[dict[str,Any]]]=defaultdict(list)
    for row in rows:
        groups[str(row.get('category') or 'uncategorized')].append(row)
    category_scores=[]
    for cat,items in groups.items():
        items.sort(key=lambda x:(float(x.get('opportunity_score') or 0),float(x.get('forecast_score') or 0),float(x.get('expected_commission_eur') or 0)),reverse=True)
        top=items[:min(20,len(items))]
        if not top:continue
        avg=sum(float(x.get('opportunity_score') or 0) for x in top)/len(top)
        forecast=sum(float(x.get('forecast_score') or 0) for x in top)/len(top)
        depth=min(12.0,len(items)*.45)
        category_scores.append((avg*.68+forecast*.20+depth,cat,len(items),round(avg,2),round(forecast,2)))
    category_scores.sort(reverse=True)
    chosen=[x[1] for x in category_scores[:5]]

    pool=[]
    for cat in chosen:pool.extend(groups[cat])
    pool.sort(key=lambda x:(float(x.get('opportunity_score') or 0),float(x.get('forecast_score') or 0),float(x.get('organic_score') or 0),float(x.get('expected_commission_eur') or 0)),reverse=True)
    selected=[]
    for row in pool:
        if any(str(old.get('category'))==str(row.get('category')) and too_similar(old,row) for old in selected):
            continue
        selected.append(row)
        if len(selected)>=100:break
    for rank,row in enumerate(selected,1):row['rank']=rank
    stats={'category_scores':[{'category':c,'portfolio_score':round(s,2),'eligible_depth':d,'avg_opportunity':a,'avg_forecast':f} for s,c,d,a,f in category_scores], 'chosen_categories':chosen}
    return selected,chosen,stats


def main() -> int:
    stage='candidate_pool'
    profile: dict[str,Any]={'version':'top100-autonomous-v2','policy':{'market':'GR','active_limit':100,'max_categories':5,'commission_floor_eur':20,'published_excluded':True,'scarcity_fail_closed':True}}
    try:
        source=gateway('candidate_pool',limit=POOL_LIMIT)
        candidates=list(source.get('items') or [])
        profile['source_count']=len(candidates)
        profile['published_excluded']=int(source.get('published_excluded') or 0)

        stage='greece_scarcity'
        scarcity_input=[]
        for row in candidates:
            x=dict(row)
            x['product_name']=row.get('title')
            x['image_url']=row.get('mainImage') or row.get('image_url')
            x['product_attributes']={'target_domain':'aliexpress.com'}
            scarcity_input.append(x)
        qualified,scarcity_stats=qualify_rows(scarcity_input,limit=SCARCITY_PROBE_LIMIT,workers=SCARCITY_WORKERS)
        profile['scarcity']=scarcity_stats
        if not qualified:raise RuntimeError('no candidates passed live Greece scarcity evidence gate')

        stage='ai_rank'
        ai_outputs=[]
        markets=list(source.get('markets') or [])
        feedback=list(source.get('feedback') or [])
        for start in range(0,len(qualified),10):
            batch=qualified[start:start+10]
            response=gateway('rank',items=batch,markets=markets,feedback=feedback)
            ai_outputs.extend(response.get('items') or [])
        ranked=merge_ai(qualified,ai_outputs)
        profile['ai_ranked_count']=len(ranked)
        if not ranked:raise RuntimeError('AI ranking returned no usable candidates')

        stage='portfolio'
        selected,categories,portfolio_stats=category_portfolio(ranked)
        profile['portfolio']=portfolio_stats
        profile['selected_count']=len(selected)
        profile['selected_categories']=categories
        profile['underfilled']=len(selected)<100
        if len(categories)>5:raise RuntimeError('max-five-category invariant failed')
        if any(float(x.get('expected_commission_eur') or 0)<=20 for x in selected):raise RuntimeError('commission hard gate failed after selection')
        if any(str(x.get('greece_scarcity_status'))!='rare_or_not_found_major_greek_search' for x in selected):raise RuntimeError('Greece scarcity hard gate failed after selection')

        stage='persist'
        persisted=gateway('persist',items=selected,source_count=len(candidates),eligible_count=len(qualified),metadata={'engine':'top100_autonomous_v2','underfilled':len(selected)<100,'scarcity':scarcity_stats,'portfolio':portfolio_stats})
        profile['run_id']=persisted['run_id']

        stage='handoff'
        handoff=gateway('handoff',run_id=persisted['run_id'],limit=HANDOFF_LIMIT)
        profile['handoff']=handoff
        profile['landing_candidates']=[{'product_id':x.get('product_id'),'source_record_hash':x.get('source_record_hash'),'product_name':x.get('product_name'),'opportunity_score':x.get('opportunity_score'),'viral_score':x.get('viral_score'),'tracking_url':x.get('tracking_url')} for x in selected if x.get('landing_candidate')][:5]
        profile['status']='completed'
        profile['stage']='complete'
        OUTPUT.write_text(json.dumps(profile,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'ok':True,'run_id':profile['run_id'],'selected':len(selected),'categories':categories,'handed_off':handoff.get('products_handed_off'),'landing_candidates':len(profile['landing_candidates']),'underfilled':profile['underfilled']},ensure_ascii=False))
        return 0
    except Exception as exc:
        profile.update({'status':'failed','stage':stage,'error':str(exc)[:1800]})
        OUTPUT.write_text(json.dumps(profile,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'ok':False,'stage':stage,'error':str(exc)},ensure_ascii=False))
        return 1


if __name__=='__main__':
    raise SystemExit(main())
