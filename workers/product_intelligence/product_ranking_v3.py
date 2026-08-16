import collections
import heapq
import json
import math
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import product_intelligence_v1 as v1
from product_agents import clamp, commission_score, discount_score, fold
from runtime_config import apply_runtime_config, load_runtime_config

ENGINE_VERSION='ranking_v3.3'
RANK_GATEWAY=os.getenv('PRODUCT_RANKING_GATEWAY','https://rpfadpdnnxequgvdcfoq.supabase.co/functions/v1/product-ranking-gateway')
PRESELECT=max(500,int(os.getenv('PRODUCT_RANK_PRESELECT','4000')))
AI_MAX=max(20,int(os.getenv('PRODUCT_RANK_AI_MAX','240')))
AI_BATCH=max(1,min(10,int(os.getenv('PRODUCT_RANK_AI_BATCH','8'))))
MAX_PER_MERCHANT=max(2,int(os.getenv('PRODUCT_RANK_MAX_PER_MERCHANT','18')))
MAX_PER_CATEGORY=max(4,int(os.getenv('PRODUCT_RANK_MAX_PER_CATEGORY','36')))
SAVE_LIMIT=max(20,int(os.getenv('PRODUCT_RANK_SAVE_LIMIT','200')))
PROFILE=Path(os.getenv('PRODUCT_RANK_PROFILE_PATH','product-ranking-v3-profile.json'))


def rank_gateway(action,**payload):
    token=v1.oidc_token();body=json.dumps({'action':action,**payload},ensure_ascii=False).encode()
    req=urllib.request.Request(RANK_GATEWAY,data=body,headers={'authorization':'Bearer '+token,'content-type':'application/json'},method='POST')
    try:
        with urllib.request.urlopen(req,timeout=210) as r:return json.loads(r.read().decode())
    except urllib.error.HTTPError as exc:
        msg=exc.read().decode(errors='replace');raise RuntimeError(f'ranking gateway {action} failed: {exc.code} {msg[:1000]}')


def num(v,default=0.0):
    try:return float(default) if v is None or v=='' else float(v)
    except Exception:return float(default)


def maybe_num(v):
    if v is None or v=='':return None
    try:return float(v)
    except Exception:return None


def confidence_pct(v):
    value=maybe_num(v)
    if value is None:return 0.0
    if 0<=value<=1:value*=100
    return clamp(value)


def purchase_signal(times_bought):
    value=max(0.0,num(times_bought));return 0.0 if value<=0 else clamp(22.0*math.log1p(value))


def pain_signal(item):
    best=0.0
    for p in item.get('_pains') or []:
        best=max(best,clamp(num(p.get('retrieval_score')))*.45+clamp(num(p.get('pain_severity')))*.25+clamp(num(p.get('demand_score')))*.20+clamp(num(p.get('commercial_intent')))*.10)
    return round(best,3)


def seasonal_signal(item):
    themes=item.get('_themes') or []
    return 0.0 if not themes else round(max(clamp(num(t.get('retrieval_score')))*.45+clamp(num(t.get('seasonal_curve_score')))*.55 for t in themes),3)


def prepare_decision_context(payload):
    markets=payload.get('markets') or [];merchants=payload.get('merchants') or []
    program_kpis=payload.get('program_kpis') or [];first_party=payload.get('first_party_30d') or []
    by_pair={};by_category={};by_taxonomy={}
    for m in markets:
        cat=fold(m.get('category_name'));sub=fold(m.get('subcategory_name'));tax=fold(m.get('taxonomy_name'))
        if cat and sub:by_pair[(cat,sub)]=m
        if cat and not m.get('subcategory_name'):by_category[cat]=m
        if tax:by_taxonomy[tax]=m
    merchant_taxonomy={str(m.get('merchant_id')):(fold(m.get('primary_category')),fold(m.get('primary_subcategory'))) for m in merchants if m.get('merchant_id')}
    program_kpi_by_id={str(x.get('program_id')):x for x in program_kpis if x.get('program_id')}
    first_party_by_program={str(x.get('program_id')):x for x in first_party if x.get('program_id')}
    return {
        'by_pair':by_pair,'by_category':by_category,'by_taxonomy':by_taxonomy,'merchant_taxonomy':merchant_taxonomy,
        'program_kpi_by_id':program_kpi_by_id,'first_party_by_program':first_party_by_program,
        'market_count':len(markets),'model_count':sum(1 for m in markets if m.get('model_status')),
        'program_kpi_count':len(program_kpi_by_id),'first_party_program_count':len(first_party_by_program),
    }


def attach_commercial_context(item,index):
    program_id=str((item.get('merchant') or {}).get('merchant_program_id') or '')
    item['_program_kpi']=index.get('program_kpi_by_id',{}).get(program_id,{})
    item['_first_party_kpi']=index.get('first_party_by_program',{}).get(program_id,{})
    return item


def match_deep_demand(item,index):
    merchant_id=str((item.get('merchant') or {}).get('merchant_id') or '')
    cat,sub=index['merchant_taxonomy'].get(merchant_id,('',''))
    market=None;method=None
    if cat and sub:
        market=index['by_pair'].get((cat,sub));method='merchant_category_subcategory' if market else None
    if market is None and cat:
        market=index['by_category'].get(cat);method='merchant_category' if market else None
    raw=fold((item.get('_raw') or {}).get('category_raw'))
    if market is None and raw:
        market=index['by_taxonomy'].get(raw);method='product_taxonomy_exact' if market else None
    if market is None:return {'matched':False,'score':0.0,'status':'unavailable','match_method':None}
    whitespace=market.get('whitespace') or {};ws=whitespace.get('score') if isinstance(whitespace,dict) else None
    model_status=market.get('model_status');confidence=num(market.get('confidence'))
    if confidence<=1:confidence*=100
    deep_score=0.0 if model_status is None or ws is None else clamp(num(ws))*(.65+.35*clamp(confidence)/100)
    return {
        'matched':True,'score':round(clamp(deep_score),3),'status':model_status or 'canonical_only','match_method':method,
        'taxonomy_id':market.get('taxonomy_id'),'category_name':market.get('category_name'),'subcategory_name':market.get('subcategory_name'),
        'canonical_demand_score':market.get('demand_score'),'canonical_competition_score':market.get('competition_score'),'canonical_confidence':market.get('confidence'),
        'whitespace':whitespace,'fuzzy_state':market.get('fuzzy_state') or {},'temporal_decision':market.get('temporal_decision'),
        'temporal_gate':market.get('temporal_gate') or {},'graph_summary':market.get('graph_summary') or {},'causal_readiness':market.get('causal_readiness') or {},
        'model_generated_at':market.get('model_generated_at'),'market_observed_at':market.get('observed_at'),
    }


def deterministic_metrics(item):
    raw,merchant=item.get('_raw') or {},item.get('merchant') or {};deep=item.get('_deep_demand') or {};program=item.get('_program_kpi') or {}
    demand=clamp(num(merchant.get('demand_score')));competition=merchant.get('competition_score');inverse=0.0 if competition is None else clamp(100-num(competition))
    whitespace=clamp(num(merchant.get('solution_whitespace_score')));trust=clamp(num(merchant.get('trust_score')));commission=commission_score(raw.get('expected_commission_eur'));discount=discount_score(raw.get('discount_pct'));purchase=purchase_signal(raw.get('times_bought'));pain=pain_signal(item);seasonal=seasonal_signal(item);deep_score=clamp(num(deep.get('score')))
    program_score=maybe_num(program.get('commercial_score'));program_conf=confidence_pct(program.get('data_confidence'))
    network=0.0 if program_score is None else clamp(program_score)*(.70+.30*program_conf/100)
    # Ranking-first deterministic layer. Missing metrics give no bonus; they are never interpreted as low competition/high opportunity.
    base=demand*.18+whitespace*.14+commission*.14+inverse*.10+trust*.08+discount*.05+purchase*.05+pain*.04+seasonal*.04+deep_score*.06+network*.12
    return {
        'merchant_demand_score':round(demand,3),'competition_score':None if competition is None else round(clamp(num(competition)),3),
        'inverse_competition_score':round(inverse,3),'merchant_whitespace_score':round(whitespace,3),'merchant_trust_score':round(trust,3),
        'commercial_score':round(commission,3),'network_performance_score':round(clamp(network),3),'network_data_confidence':round(program_conf,3),
        'discount_score':round(discount,3),'purchase_signal_score':round(purchase,3),'pain_signal_score':round(pain,3),'seasonal_score':round(seasonal,3),
        'deep_demand_score':round(deep_score,3),'deterministic_rank_score':round(clamp(base),3),
    }


def preselect(products,context,decision_index):
    heap=[];seq=0;considered=0;deep_matched=0
    for product in products:
        considered+=1;item=v1.build_ai_item(product,context);attach_commercial_context(item,decision_index);item['_deep_demand']=match_deep_demand(item,decision_index);deep_matched+=int(bool(item['_deep_demand'].get('matched')));item['_rank_metrics']=deterministic_metrics(item);seq+=1;entry=(item['_rank_metrics']['deterministic_rank_score'],seq,item)
        if len(heap)<PRESELECT:heapq.heappush(heap,entry)
        elif entry[0]>heap[0][0]:heapq.heapreplace(heap,entry)
    ordered=sorted(heap,key=lambda x:(x[0],x[1]),reverse=True);selected=[];mc=collections.Counter();cc=collections.Counter()
    for _,_,item in ordered:
        merchant=str((item.get('merchant') or {}).get('merchant_id') or 'unknown');category=str((item.get('_raw') or {}).get('category_raw') or 'unknown').lower()
        if mc[merchant]>=MAX_PER_MERCHANT or cc[category]>=MAX_PER_CATEGORY:continue
        selected.append(item);mc[merchant]+=1;cc[category]+=1
        if len(selected)>=AI_MAX:break
    if len(selected)<AI_MAX:
        chosen={str(x['product']['source_record_hash']) for x in selected}
        for _,_,item in ordered:
            h=str(item['product']['source_record_hash'])
            if h in chosen:continue
            selected.append(item);chosen.add(h)
            if len(selected)>=AI_MAX:break
    return selected,{'eligible_candidates_considered':considered,'preselected':len(ordered),'ai_shortlist':len(selected),'deep_demand_matched_candidates':deep_matched,'deep_demand_markets':decision_index['market_count'],'deep_demand_model_markets':decision_index['model_count'],'program_kpis_available':decision_index['program_kpi_count'],'first_party_programs_30d':decision_index['first_party_program_count'],'unique_merchants':len({str((x.get('merchant') or {}).get('merchant_id')) for x in selected}),'unique_categories':len({str((x.get('_raw') or {}).get('category_raw')) for x in selected})}


def concise_deep_context(item):
    d=item.get('_deep_demand') or {}
    return {k:d.get(k) for k in ('matched','score','status','match_method','taxonomy_id','category_name','subcategory_name','canonical_demand_score','canonical_competition_score','canonical_confidence','whitespace','fuzzy_state','temporal_decision','temporal_gate','graph_summary','causal_readiness','model_generated_at','market_observed_at')}


def wire_item(item):
    return {'product':item['product'],'merchant':item['merchant'],'pain_rag':item.get('pain_rag') or [],'theme_rag':item.get('theme_rag') or [],'deep_demand_context':concise_deep_context(item),'deterministic_metrics':item['_rank_metrics'],'network_program_kpi':item.get('_program_kpi') or {},'ranking_semantics':{'objective':'promotion opportunity in Greece','pain_missing_is_not_rejection':True,'missing_competition_gets_no_inverse_bonus':True,'deep_demand_is_derived_not_observed_sales':True,'network_kpis_are_program_baselines_not_product_sales':True,'withheld_forecast_cannot_create_trend_claim':True}}


def rank_with_ai(items):
    outputs={};stats=collections.Counter()
    for start in range(0,len(items),AI_BATCH):
        batch=items[start:start+AI_BATCH];wire=[wire_item(x) for x in batch];stats['ai_rank_batches']+=1
        try:
            ranked=rank_gateway('rank',items=wire,thinking='auto').get('items',[]);by_hash={str(x.get('source_record_hash')):x for x in ranked};audit_wire=[{**x,'ranking':by_hash[str(x['product']['source_record_hash'])]} for x in wire if str(x['product']['source_record_hash']) in by_hash];audited=rank_gateway('rank_audit',items=audit_wire,thinking='auto').get('items',[]) if audit_wire else [];audit_by={str(x.get('source_record_hash')):x for x in audited}
            for h,result in by_hash.items():outputs[h]={'ranking':result,'audit':audit_by.get(h,{})};stats['ai_ranked']+=1
        except Exception as exc:
            stats['ai_rank_failures']+=len(batch);print(json.dumps({'warning':'ranking_ai_batch_failed','error':str(exc)[:500],'items':len(batch)}),flush=True)
    return outputs,dict(stats)


def _trim_value(v,depth=0):
    if depth>2:return None
    if isinstance(v,str):return v[:1200]
    if isinstance(v,(int,float,bool)) or v is None:return v
    if isinstance(v,list):return [_trim_value(x,depth+1) for x in v[:20]]
    if isinstance(v,dict):return {str(k)[:120]:_trim_value(val,depth+1) for k,val in list(v.items())[:40]}
    return str(v)[:500]


def product_attributes(raw):
    return {
        'original_description':(raw.get('description') or '')[:6000] or None,
        'availability':raw.get('availability'),'valid_from':raw.get('valid_from'),'valid_to':raw.get('valid_to'),'currency':raw.get('currency'),
        'colour':raw.get('colour'),'size':raw.get('size'),'gtin':raw.get('gtin'),'mpn':raw.get('mpn'),
        'target_url':raw.get('target_url'),'target_domain':raw.get('target_domain'),'linkwise_route':raw.get('linkwise_route'),
        'extra_images':[x for x in (raw.get('extra_images') or []) if isinstance(x,str)][:12],
        'extra_attributes':_trim_value(raw.get('extra_json') or {}),
    }


def kpi_snapshot(item):
    raw=item.get('_raw') or {};program=item.get('_program_kpi') or {};fp=item.get('_first_party_kpi') or {}
    conv=maybe_num(program.get('conversion_rate'));epc=maybe_num(program.get('epc'));approval=maybe_num(program.get('approval_rate'));approval_days=maybe_num(program.get('approval_days'));expected=maybe_num(raw.get('expected_commission_eur'))
    gross100=conv*expected if conv is not None and expected is not None else None
    approved100=gross100*approval/100 if gross100 is not None and approval is not None else None
    approved_conv100=conv*approval/100 if conv is not None and approval is not None else None
    break_even=approved100/100 if approved100 is not None else None
    impressions=int(num(fp.get('impressions')));clicks=int(num(fp.get('outbound_clicks')));approved_conversions=int(num(fp.get('conversions_approved')));revenue=num(fp.get('commission_approved_eur'));cost=num(fp.get('media_spend_eur'))+num(fp.get('content_cost_eur'))
    observed={
        'status':'observed' if fp else 'no_first_party_data','window_days':30,'impressions':impressions,'outbound_clicks':clicks,'approved_conversions':approved_conversions,
        'approved_commission_eur':round(revenue,4),'ctr_pct':round(clicks/impressions*100,3) if impressions else None,'approved_cvr_pct':round(approved_conversions/clicks*100,3) if clicks else None,
        'epc_eur':round(revenue/clicks,4) if clicks else None,'roi_pct':round((revenue-cost)/cost*100,2) if cost>0 else None,
    }
    return {
        'network_baseline':{'status':'observed_program_baseline' if program else 'unavailable','observed_at':program.get('observed_at'),'conversion_rate_pct':conv,'epc_eur':epc,'approval_rate_pct':approval,'approval_days':approval_days,'commercial_score':maybe_num(program.get('commercial_score')),'data_confidence':maybe_num(program.get('data_confidence'))},
        'first_party_30d':observed,
        'modeled_product_economics':{'status':'modeled_from_network_baseline' if approved100 is not None else 'insufficient_baseline','expected_conversions_per_100_clicks':round(conv,3) if conv is not None else None,'expected_approved_conversions_per_100_clicks':round(approved_conv100,3) if approved_conv100 is not None else None,'expected_gross_commission_per_100_clicks_eur':round(gross100,2) if gross100 is not None else None,'expected_approved_commission_per_100_clicks_eur':round(approved100,2) if approved100 is not None else None,'break_even_cpc_eur':round(break_even,4) if break_even is not None else None},
        'provenance':{'network':'Linkwise/program commercial snapshot','first_party':'ops.affiliate_performance_daily','forecast':'deterministic arithmetic; not observed product conversion'},
    }


def final_row(item,ai):
    raw,merchant,m=item['_raw'],item['merchant'],item['_rank_metrics'];deep=item.get('_deep_demand') or {};ranking,audit=ai.get('ranking') or {},ai.get('audit') or {}
    product_fit=clamp(num(ranking.get('product_market_fit_score')));creative=clamp(num(ranking.get('creative_potential_score')));value=clamp(num(ranking.get('value_score')));confidence=clamp(num(ranking.get('confidence_score')));risk=clamp(num(audit.get('risk_score'),50))
    raw_score=m['merchant_demand_score']*.15+m['merchant_whitespace_score']*.11+m['commercial_score']*.10+m['inverse_competition_score']*.09+m['merchant_trust_score']*.07+m['discount_score']*.05+m['purchase_signal_score']*.04+m['pain_signal_score']*.04+m['seasonal_score']*.04+m['deep_demand_score']*.05+m['network_performance_score']*.10+product_fit*.08+creative*.05+value*.02+confidence*.01
    score=clamp(raw_score*(.85+.15*(100-risk)/100));band='PROMOTE_NOW' if score>=82 else 'HIGH_POTENTIAL' if score>=72 else 'TEST' if score>=62 else 'WATCHLIST';channels=ranking.get('recommended_channels') or [];channels=channels if isinstance(channels,list) else [str(channels)];risk_flags=audit.get('risk_flags') or ranking.get('risk_flags') or [];risk_flags=risk_flags if isinstance(risk_flags,list) else [str(risk_flags)]
    return {
        'source_record_hash':raw['source_record_hash'],'canonical_key':raw['canonical_key'],'external_product_id':raw.get('external_product_id'),'merchant_id':merchant['merchant_id'],'merchant_program_id':merchant.get('merchant_program_id'),'merchant_name':raw.get('merchant_name') or merchant.get('canonical_name'),'product_name':raw.get('product_name') or item['product'].get('product_name') or 'Product','brand_name':raw.get('brand_name'),'model_name':raw.get('model_name'),'category':ranking.get('category') or raw.get('category_raw'),'subcategory':ranking.get('subcategory'),'effective_price':raw.get('price'),'full_price':raw.get('full_price'),'discount_pct':raw.get('discount_pct'),'expected_commission_eur':raw.get('expected_commission_eur'),'tracking_url':raw.get('tracking_url'),'image_url':raw.get('image_url') or raw.get('thumb_url'),'in_stock':raw.get('in_stock'),'times_bought':raw.get('times_bought'),
        'merchant_demand_score':m['merchant_demand_score'],'competition_score':m['competition_score'],'merchant_whitespace_score':m['merchant_whitespace_score'],'merchant_trust_score':m['merchant_trust_score'],'pain_signal_score':m['pain_signal_score'],'seasonal_score':m['seasonal_score'],'commercial_score':m['commercial_score'],'network_performance_score':m['network_performance_score'],'purchase_signal_score':m['purchase_signal_score'],'deep_demand_score':m['deep_demand_score'],'deep_demand_status':deep.get('status'),'deep_demand_context':concise_deep_context(item),
        'ai_product_fit_score':product_fit,'ai_creative_score':creative,'ai_value_score':value,'ai_confidence':confidence,'ai_risk_score':risk,'rank_score':round(score,3),'rank_band':band,'promotion_angle':ranking.get('promotion_angle'),'promotion_reason':ranking.get('promotion_reason') or ranking.get('rationale'),'audience':ranking.get('audience'),'recommended_channels':channels,'risk_flags':risk_flags,
        'product_attributes':product_attributes(raw),'kpi_snapshot':kpi_snapshot(item),'seo_content':{},'seo_generated_at':None,
        'evidence_summary':{'pain_matches':len(item.get('_pains') or []),'theme_matches':len(item.get('_themes') or []),'deep_demand_match':deep.get('match_method'),'deterministic_rank_score':m['deterministic_rank_score'],'network_performance_score':m['network_performance_score'],'audit_reasons':audit.get('reasons') or []},'ai_summary':audit.get('audit_summary') or ranking.get('rationale')
    }


def enrich_final_rows(rows):
    return rows,{'seo_enriched':0,'seo_failures':0,'seo_generation':'disabled_in_base_engine'}


def main(feed):
    cfg=load_runtime_config(v1);apply_runtime_config(v1,cfg);health=rank_gateway('health')
    if not health.get('deepseek_configured'):raise SystemExit('Ranking V3 requires AI for the final promotion list; DeepSeek is not configured.')
    context=v1.gateway('context');decision_payload=rank_gateway('decision_context');decision_index=prepare_decision_context(decision_payload);reused=False
    if v1.REUSE_STAGE and Path(v1.STAGE_DB).exists():
        try:db=v1.init_stage(v1.STAGE_DB,reset=False);staged=db.execute('select count(*) from candidates').fetchone()[0];reused=staged>0
        except Exception:reused=False
    if reused:stream_stats={'stage_reused_from_phase_a':True,'commission_eligible_records':staged}
    else:db,stream_stats=v1.stage_feed(feed,context);stream_stats=dict(stream_stats)
    shortlist,shortlist_stats=preselect(v1.iter_best_offers(db,v1.AI_OFFERS_PER_PRODUCT),context,decision_index);ai_outputs,ai_stats=rank_with_ai(shortlist)
    rows=[final_row(item,ai_outputs[str(item['product']['source_record_hash'])]) for item in shortlist if str(item['product']['source_record_hash']) in ai_outputs]
    rows.sort(key=lambda x:(x['rank_score'],x['ai_confidence'],num(x['expected_commission_eur'])),reverse=True);rows=rows[:SAVE_LIMIT];rows,content_stats=enrich_final_rows(rows)
    run_key=f"{os.getenv('GITHUB_RUN_ID') or datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{os.getenv('GITHUB_RUN_ATTEMPT','1')}"
    start=rank_gateway('ranking_start',run_key=run_key,engine_version=ENGINE_VERSION,metadata={'runtime_config_version':cfg.get('_version'),'pain_clusters_available':len(context.get('pain_clusters') or []),'themes_available':len(context.get('themes') or []),'deep_demand_markets':decision_index['market_count'],'deep_demand_model_markets':decision_index['model_count'],'program_kpis_available':decision_index['program_kpi_count'],'first_party_programs_30d':decision_index['first_party_program_count'],'policy':'ranking-first; pain optional; Deep Demand additive; network KPIs are observed program baselines; product forecasts are deterministic'})
    run_id=start['run_id'];saved=0
    for i in range(0,len(rows),40):saved+=int(rank_gateway('save_rankings',run_id=run_id,items=rows[i:i+40]).get('saved') or 0)
    rank_gateway('ranking_complete',run_id=run_id,records_seen=int(stream_stats.get('records_seen') or 0),eligible_candidates=int(stream_stats.get('commission_eligible_records') or 0),ai_ranked=int(ai_stats.get('ai_ranked') or 0),saved_count=saved,metadata={'shortlist':shortlist_stats,'ai':ai_stats,'content':content_stats})
    bands=collections.Counter(x['rank_band'] for x in rows);profile={'engine_version':ENGINE_VERSION,'run_key':run_key,**stream_stats,**shortlist_stats,**ai_stats,**content_stats,'saved_rankings':saved,'bands':dict(bands),'top_20':[{k:x.get(k) for k in ('product_name','merchant_name','rank_score','rank_band','expected_commission_eur','network_performance_score','promotion_angle','recommended_channels')}|{'kpis':x.get('kpi_snapshot'),'seo_title':(x.get('seo_content') or {}).get('title')} for x in rows[:20]],'ranking_policy':'Every deterministic eligible product can compete. Network commercial performance is an evidence-backed conversion signal. Deep Demand is additive modeled context; missing pain/forecast never automatically excludes.'}
    PROFILE.write_text(json.dumps(profile,ensure_ascii=False,indent=2,default=str),encoding='utf-8');print(json.dumps({'product_ranking_v3':profile},ensure_ascii=False,default=str),flush=True);db.close()


if __name__=='__main__':main(sys.argv[1] if len(sys.argv)>1 else v1.SOURCE_FEED)
