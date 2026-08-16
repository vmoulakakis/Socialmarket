"""Ranking V3.5: deterministic shortlist, resilient AI ranking, SEO, durable Top-20 creatives and canonical content handoff."""
import base64
import collections
import heapq
import json
import os
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import product_intelligence_v1 as v1
import product_ranking_v3 as v3
from creative_asset_renderer import render_pack

RAG_PRESELECT=max(v3.PRESELECT,int(os.getenv('PRODUCT_RANK_RAG_PRESELECT','16000')))
AI_WORKERS=max(1,min(3,int(os.getenv('PRODUCT_RANK_AI_WORKERS','3'))))
SEO_WORKERS=max(1,min(3,int(os.getenv('PRODUCT_RANK_SEO_WORKERS','3'))))
SEO_BATCH=max(1,min(10,int(os.getenv('PRODUCT_RANK_SEO_BATCH','10'))))
SEO_LIMIT=max(1,min(v3.SAVE_LIMIT,int(os.getenv('PRODUCT_RANK_SEO_LIMIT',str(v3.SAVE_LIMIT)))))
FINAL_MIN_RANKED=max(100,int(os.getenv('PRODUCT_RANK_MIN_FINAL','100')))
CREATIVE_LIMIT=max(20,min(v3.SAVE_LIMIT,int(os.getenv('PRODUCT_RANK_CREATIVE_LIMIT','20'))))
CREATIVE_BATCH=max(1,min(5,int(os.getenv('PRODUCT_RANK_CREATIVE_BATCH','5'))))
CREATIVE_WORKERS=max(1,min(3,int(os.getenv('PRODUCT_RANK_CREATIVE_WORKERS','3'))))
ASSET_WORKERS=max(1,min(4,int(os.getenv('PRODUCT_CREATIVE_ASSET_WORKERS','4'))))
CREATIVE_GATEWAY=os.getenv('PRODUCT_CREATIVE_GATEWAY','https://rpfadpdnnxequgvdcfoq.supabase.co/functions/v1/product-creative-gateway')
CREATIVE_BRAND_SLUG=os.getenv('PRODUCT_CREATIVE_BRAND_SLUG','lyseis-pou-axizoun')
ASSET_NAMESPACE=os.getenv('GITHUB_RUN_ID') or datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
BASE_RANK_GATEWAY=v3.rank_gateway
_CREATIVE_TOKEN=None


def creative_gateway(action,**payload):
    global _CREATIVE_TOKEN
    if _CREATIVE_TOKEN is None:_CREATIVE_TOKEN=v1.oidc_token()
    body=json.dumps({'action':action,**payload},ensure_ascii=False).encode()
    req=urllib.request.Request(CREATIVE_GATEWAY,data=body,headers={'authorization':'Bearer '+_CREATIVE_TOKEN,'content-type':'application/json'},method='POST')
    try:
        with urllib.request.urlopen(req,timeout=210) as r:return json.loads(r.read().decode())
    except urllib.error.HTTPError as exc:
        msg=exc.read().decode(errors='replace');raise RuntimeError(f'creative gateway {action} failed: {exc.code} {msg[:1000]}')


def assert_final_contract(rows,creative_count=None,asset_pack_count=None):
    if len(rows)<FINAL_MIN_RANKED:
        raise RuntimeError(f'final ranking contract requires at least {FINAL_MIN_RANKED} products; got {len(rows)}')
    if creative_count is not None and creative_count<CREATIVE_LIMIT:
        raise RuntimeError(f'creative contract requires {CREATIVE_LIMIT} Top-ranked creative packs; got {creative_count}')
    if asset_pack_count is not None and asset_pack_count<CREATIVE_LIMIT:
        raise RuntimeError(f'durable creative contract requires {CREATIVE_LIMIT} complete 3-asset packs; got {asset_pack_count}')
    return True


def _cheap_item(product,decision_index):
    item={'product':{},'merchant':product.get('merchant_context') or {},'_raw':product,'_pains':[],'_themes':[]}
    v3.attach_commercial_context(item,decision_index)
    item['_deep_demand']=v3.match_deep_demand(item,decision_index)
    item['_rank_metrics']=v3.deterministic_metrics(item)
    return item


def preselect_v32(products,context,decision_index):
    cheap_heap=[];seq=0;considered=0;deep_matched=0
    for product in products:
        considered+=1;item=_cheap_item(product,decision_index);deep_matched+=int(bool(item['_deep_demand'].get('matched')));seq+=1
        entry=(item['_rank_metrics']['deterministic_rank_score'],seq,product)
        if len(cheap_heap)<RAG_PRESELECT:heapq.heappush(cheap_heap,entry)
        elif entry[0]>cheap_heap[0][0]:heapq.heapreplace(cheap_heap,entry)

    full_heap=[];rag_evaluated=0
    for _,seq,product in sorted(cheap_heap,key=lambda x:(x[0],x[1]),reverse=True):
        item=v1.build_ai_item(product,context);v3.attach_commercial_context(item,decision_index);item['_deep_demand']=v3.match_deep_demand(item,decision_index);item['_rank_metrics']=v3.deterministic_metrics(item);rag_evaluated+=1
        entry=(item['_rank_metrics']['deterministic_rank_score'],seq,item)
        if len(full_heap)<v3.PRESELECT:heapq.heappush(full_heap,entry)
        elif entry[0]>full_heap[0][0]:heapq.heapreplace(full_heap,entry)

    ordered=sorted(full_heap,key=lambda x:(x[0],x[1]),reverse=True);selected=[];merchant_counts=collections.Counter();category_counts=collections.Counter()
    for _,_,item in ordered:
        merchant=str((item.get('merchant') or {}).get('merchant_id') or 'unknown');category=str((item.get('_raw') or {}).get('category_raw') or 'unknown').lower()
        if merchant_counts[merchant]>=v3.MAX_PER_MERCHANT or category_counts[category]>=v3.MAX_PER_CATEGORY:continue
        selected.append(item);merchant_counts[merchant]+=1;category_counts[category]+=1
        if len(selected)>=v3.AI_MAX:break
    if len(selected)<v3.AI_MAX:
        chosen={str(x['product']['source_record_hash']) for x in selected}
        for _,_,item in ordered:
            h=str(item['product']['source_record_hash'])
            if h in chosen:continue
            selected.append(item);chosen.add(h)
            if len(selected)>=v3.AI_MAX:break

    return selected,{
        'eligible_candidates_considered':considered,'cheap_preselected':len(cheap_heap),'rag_evaluated':rag_evaluated,'preselected':len(ordered),'ai_shortlist':len(selected),'ai_workers':AI_WORKERS,
        'deep_demand_matched_candidates':deep_matched,'deep_demand_markets':decision_index['market_count'],'deep_demand_model_markets':decision_index['model_count'],
        'program_kpis_available':decision_index['program_kpi_count'],'first_party_programs_30d':decision_index['first_party_program_count'],
        'unique_merchants':len({str((x.get('merchant') or {}).get('merchant_id')) for x in selected}),'unique_categories':len({str((x.get('_raw') or {}).get('category_raw')) for x in selected}),
        'preselection_policy':'all eligible -> O(1) deterministic conversion-aware heap -> high-recall RAG pool -> full deterministic score -> diversified AI shortlist'
    }


def _run_ai_batch_once(batch):
    wire=[v3.wire_item(x) for x in batch]
    ranked=v3.rank_gateway('rank',items=wire,thinking='auto').get('items',[]);by_hash={str(x.get('source_record_hash')):x for x in ranked}
    audit_wire=[{**x,'ranking':by_hash[str(x['product']['source_record_hash'])]} for x in wire if str(x['product']['source_record_hash']) in by_hash]
    audited=v3.rank_gateway('rank_audit',items=audit_wire,thinking='auto').get('items',[]) if audit_wire else [];audit_by={str(x.get('source_record_hash')):x for x in audited}
    return {h:{'ranking':result,'audit':audit_by.get(h,{})} for h,result in by_hash.items()}


def _run_ai_batch_resilient(batch):
    try:return _run_ai_batch_once(batch),0,0
    except Exception:
        if len(batch)<=1:return {},len(batch),1
        mid=max(1,len(batch)//2);outputs={};failed=0;splits=1
        for part in (batch[:mid],batch[mid:]):
            result,part_failed,part_splits=_run_ai_batch_resilient(part);outputs.update(result);failed+=part_failed;splits+=part_splits
        return outputs,failed,splits


def rank_with_ai_v32(items):
    batches=[items[i:i+v3.AI_BATCH] for i in range(0,len(items),v3.AI_BATCH)];outputs={};stats=collections.Counter({'ai_rank_batches':len(batches),'ai_workers':AI_WORKERS})
    with ThreadPoolExecutor(max_workers=AI_WORKERS) as pool:
        futures={pool.submit(_run_ai_batch_resilient,batch):len(batch) for batch in batches}
        for future in as_completed(futures):
            size=futures[future]
            try:
                result,failed,splits=future.result();outputs.update(result);stats['ai_ranked']+=len(result);stats['ai_rank_failures']+=failed;stats['ai_split_retries']+=splits
            except Exception:stats['ai_rank_failures']+=size
    return outputs,dict(stats)


def _seo_wire(row):
    attrs=row.get('product_attributes') or {};kpis=row.get('kpi_snapshot') or {}
    return {'source_record_hash':row.get('source_record_hash'),'product_name':row.get('product_name'),'brand_name':row.get('brand_name'),'model_name':row.get('model_name'),'category':row.get('category'),'subcategory':row.get('subcategory'),'merchant_name':row.get('merchant_name'),'effective_price':row.get('effective_price'),'full_price':row.get('full_price'),'discount_pct':row.get('discount_pct'),'promotion_angle':row.get('promotion_angle'),'promotion_reason':row.get('promotion_reason'),'audience':row.get('audience'),'recommended_channels':row.get('recommended_channels') or [],'attributes':{k:attrs.get(k) for k in ('original_description','availability','colour','size','gtin','mpn','extra_attributes')},'network_baseline':kpis.get('network_baseline') or {},'modeled_product_economics':kpis.get('modeled_product_economics') or {}}


def _run_seo_batch_once(batch):
    result=v3.rank_gateway('seo_enrich',items=[_seo_wire(x) for x in batch],thinking='off').get('items',[]);return {str(x.get('source_record_hash')):x for x in result if x.get('source_record_hash')}


def _run_seo_batch_resilient(batch):
    try:return _run_seo_batch_once(batch),0,0
    except Exception:
        if len(batch)<=1:return {},len(batch),1
        mid=max(1,len(batch)//2);outputs={};failed=0;splits=1
        for part in (batch[:mid],batch[mid:]):
            result,part_failed,part_splits=_run_seo_batch_resilient(part);outputs.update(result);failed+=part_failed;splits+=part_splits
        return outputs,failed,splits


def enrich_seo(rows):
    target=rows[:SEO_LIMIT];batches=[target[i:i+SEO_BATCH] for i in range(0,len(target),SEO_BATCH)];outputs={};stats=collections.Counter({'seo_batches':len(batches),'seo_workers':SEO_WORKERS,'seo_target':len(target)})
    with ThreadPoolExecutor(max_workers=SEO_WORKERS) as pool:
        futures={pool.submit(_run_seo_batch_resilient,batch):len(batch) for batch in batches}
        for future in as_completed(futures):
            size=futures[future]
            try:
                result,failed,splits=future.result();outputs.update(result);stats['seo_enriched']+=len(result);stats['seo_failures']+=failed;stats['seo_split_retries']+=splits
            except Exception:stats['seo_failures']+=size
    generated_at=datetime.now(timezone.utc).isoformat()
    for row in rows:
        seo=outputs.get(str(row.get('source_record_hash')))
        if seo:row['seo_content']={k:seo.get(k) for k in ('title','meta_description','short_description','description','keywords','search_intent','slug','feature_bullets')};row['seo_generated_at']=generated_at
    stats['seo_generation']='DeepSeek evidence-constrained rewrite; product facts only; no invented specifications';return rows,dict(stats)


def _creative_wire(row):
    attrs=row.get('product_attributes') or {};seo=row.get('seo_content') or {}
    return {'source_record_hash':row.get('source_record_hash'),'rank_score':row.get('rank_score'),'rank_band':row.get('rank_band'),'product':{'name':row.get('product_name'),'brand':row.get('brand_name'),'model':row.get('model_name'),'category':row.get('category'),'subcategory':row.get('subcategory'),'price':row.get('effective_price'),'full_price':row.get('full_price'),'discount_pct':row.get('discount_pct'),'image_url':row.get('image_url'),'tracking_url':row.get('tracking_url')},'verified_attributes':{k:attrs.get(k) for k in ('original_description','availability','colour','size','gtin','mpn')},'promotion':{'angle':row.get('promotion_angle'),'reason':row.get('promotion_reason'),'audience':row.get('audience'),'channels':row.get('recommended_channels') or []},'seo':{k:seo.get(k) for k in ('title','short_description','keywords','search_intent','feature_bullets')},'rules':{'use_real_product_image':True,'tracking_url_immutable':True,'no_internal_kpis_in_consumer_copy':True,'no_invented_features':True}}


def _run_creative_batch_once(batch):
    wires=[_creative_wire(x) for x in batch];generated=creative_gateway('generate',items=wires).get('items',[]);packs={str(x.get('source_record_hash')):x for x in generated if x.get('source_record_hash')};audit_input=[{**w,'creative_pack':packs[str(w['source_record_hash'])]} for w in wires if str(w['source_record_hash']) in packs];audited=creative_gateway('audit',items=audit_input).get('items',[]) if audit_input else [];audits={str(x.get('source_record_hash')):x for x in audited if x.get('source_record_hash')};return {h:{'creative_pack':pack,'creative_audit':audits.get(h,{})} for h,pack in packs.items()}


def _run_creative_batch_resilient(batch):
    try:return _run_creative_batch_once(batch),0,0
    except Exception:
        if len(batch)<=1:return {},len(batch),1
        mid=max(1,len(batch)//2);outputs={};failed=0;splits=1
        for part in (batch[:mid],batch[mid:]):
            result,part_failed,part_splits=_run_creative_batch_resilient(part);outputs.update(result);failed+=part_failed;splits+=part_splits
        return outputs,failed,splits


def _render_upload_one(row):
    rendered=render_pack(row);pack=row.get('creative_pack') or {};variants=pack.get('variants') or [];by_id={str(x['variant_id']):x['png'] for x in rendered}
    if len(by_id)!=3:raise RuntimeError('renderer did not return exactly 3 assets')
    for variant in variants:
        variant_id=str(variant.get('id') or '');png=by_id.get(variant_id)
        if not png:raise RuntimeError(f'missing rendered asset for {variant_id}')
        uploaded=creative_gateway('upload_asset',run_id=ASSET_NAMESPACE,source_record_hash=row.get('source_record_hash'),variant_id=variant_id,base64_png=base64.b64encode(png).decode('ascii'));asset_url=str(uploaded.get('asset_url') or '')
        if not asset_url.startswith('https://'):raise RuntimeError(f'asset upload failed for {variant_id}')
        variant['asset_url']=asset_url;variant['asset_bytes']=int(uploaded.get('bytes') or len(png));variant['asset_mime']='image/png'
    row['creative_pack']=pack;row['creative_asset_count']=3;return row


def attach_durable_assets(rows):
    target=rows[:CREATIVE_LIMIT];complete=0;failures=[]
    with ThreadPoolExecutor(max_workers=ASSET_WORKERS) as pool:
        futures={pool.submit(_render_upload_one,row):row for row in target}
        for future in as_completed(futures):
            row=futures[future]
            try:future.result();complete+=1
            except Exception as exc:failures.append({'source_record_hash':row.get('source_record_hash'),'error':str(exc)[:500]})
    if failures:raise RuntimeError('creative asset rendering/upload failures: '+json.dumps(failures[:5],ensure_ascii=False))
    assert_final_contract(rows,CREATIVE_LIMIT,complete);return rows,{'creative_asset_packs':complete,'creative_assets':complete*3,'creative_asset_workers':ASSET_WORKERS,'creative_asset_namespace':ASSET_NAMESPACE}


def enrich_creatives(rows):
    target=rows[:CREATIVE_LIMIT];batches=[target[i:i+CREATIVE_BATCH] for i in range(0,len(target),CREATIVE_BATCH)];outputs={};stats=collections.Counter({'creative_target':len(target),'creative_batches':len(batches),'creative_workers':CREATIVE_WORKERS,'variants_per_product':3})
    with ThreadPoolExecutor(max_workers=CREATIVE_WORKERS) as pool:
        futures={pool.submit(_run_creative_batch_resilient,batch):len(batch) for batch in batches}
        for future in as_completed(futures):
            size=futures[future]
            try:
                result,failed,splits=future.result();outputs.update(result);stats['creative_generated']+=len(result);stats['creative_failures']+=failed;stats['creative_split_retries']+=splits
            except Exception:stats['creative_failures']+=size
    assert_final_contract(rows,len(outputs));generated_at=datetime.now(timezone.utc).isoformat()
    for idx,row in enumerate(target,1):
        result=outputs[str(row.get('source_record_hash'))];audit=result.get('creative_audit') or {};verdict=str(audit.get('verdict') or '').upper();row['creative_pack']=result.get('creative_pack') or {};row['creative_audit']=audit;row['creative_status']='ready' if verdict=='READY' else 'needs_review';row['creative_generated_at']=generated_at;row['creative_global_rank']=idx;stats['creative_ready' if verdict=='READY' else 'creative_needs_review']+=1
    rows,asset_stats=attach_durable_assets(rows);stats['creative_policy']='Top 20; 3 durable PNG variants each; real product image + exact tracking URL + QR; independent Creative Skeptic; canonical content persistence';return rows,{**dict(stats),**asset_stats}


def enrich_final_rows_v34(rows):
    assert_final_contract(rows);rows,seo_stats=enrich_seo(rows);rows,creative_stats=enrich_creatives(rows);return rows,{**seo_stats,**creative_stats,'final_min_ranked':FINAL_MIN_RANKED,'final_creative_products':CREATIVE_LIMIT,'final_creative_assets':CREATIVE_LIMIT*3}


def _persist_creative_content(run_id,item):
    result=creative_gateway('persist_content',run_id=run_id,source_record_hash=item.get('source_record_hash'),brand_slug=CREATIVE_BRAND_SLUG,merchant_id=item.get('merchant_id'),merchant_name=item.get('merchant_name'),product_name=item.get('product_name'),tracking_url=item.get('tracking_url'),image_url=item.get('image_url'),global_rank=item.get('creative_global_rank'),creative_pack=item.get('creative_pack') or {},creative_audit=item.get('creative_audit') or {},priority=max(50,101-int(item.get('creative_global_rank') or 50)))
    if len(result.get('content_items') or [])!=3:raise RuntimeError(f'canonical creative content persistence incomplete for {item.get("source_record_hash")}')
    return result


def rank_gateway_final(action,**payload):
    if action=='save_rankings':
        result=BASE_RANK_GATEWAY(action,**payload);creative_items=[x for x in (payload.get('items') or []) if x.get('creative_pack')]
        if creative_items:
            saved=int(creative_gateway('save_creatives',run_id=payload.get('run_id'),items=creative_items).get('saved') or 0)
            if saved<len(creative_items):raise RuntimeError(f'creative persistence incomplete: {saved}/{len(creative_items)}')
            persisted=0
            for item in creative_items:_persist_creative_content(payload.get('run_id'),item);persisted+=1
            if persisted<len(creative_items):raise RuntimeError(f'canonical content persistence incomplete: {persisted}/{len(creative_items)}')
        return result
    if action=='ranking_complete':return creative_gateway('finalize',minimum_ranked=FINAL_MIN_RANKED,minimum_creatives=CREATIVE_LIMIT,minimum_content_packs=CREATIVE_LIMIT,**payload)
    return BASE_RANK_GATEWAY(action,**payload)


def main(feed):
    health=creative_gateway('health')
    if not health.get('deepseek_configured'):raise SystemExit('Ranking V3.5 requires the creative AI gateway; DeepSeek is not configured.')
    v3.ENGINE_VERSION='ranking_v3.5';v3.preselect=preselect_v32;v3.rank_with_ai=rank_with_ai_v32;v3.enrich_final_rows=enrich_final_rows_v34;v3.rank_gateway=rank_gateway_final;return v3.main(feed)


if __name__=='__main__':main(sys.argv[1] if len(sys.argv)>1 else v1.SOURCE_FEED)
