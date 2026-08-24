"""Zero-paid Product Ranking/Creative execution for SocialMarket Autopilot.

Bulk Linkwise data never reaches a generative model. Deterministic streaming, hard
commercial gates and RAG preselection happen first. Only the bounded candidate
frontier is sent to the provider-neutral AI Task Router backed by local Ollama.
"""
from __future__ import annotations

import json
import os
import re
import sys
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

HERE=Path(__file__).resolve().parent
AI_RUNTIME=HERE.parent/'ai_runtime'
if str(AI_RUNTIME) not in sys.path:sys.path.insert(0,str(AI_RUNTIME))

from ollama_executor import OllamaExecutor
from router import AITaskRouter, InMemoryTaskCache
from supabase_runtime import SupabaseTaskCache, SupabaseTaskResultSink
from task_contract import AITask

import product_intelligence_v1 as v1
import product_ranking_v3 as v3
import product_ranking_v32 as v32

LOCAL_MODEL=os.getenv('PRODUCT_LOCAL_MODEL','qwen3.5:4b')
LOCAL_AI_WORKERS=max(1,min(2,int(os.getenv('PRODUCT_LOCAL_AI_WORKERS','1'))))
LOCAL_TIMEOUT=max(60,float(os.getenv('PRODUCT_LOCAL_AI_TIMEOUT_SECONDS','150')))
LOCAL_MIN_FINAL=max(100,int(os.getenv('PRODUCT_RANK_MIN_FINAL','100')))
LOCAL_CREATIVE_LIMIT=max(20,int(os.getenv('PRODUCT_RANK_CREATIVE_LIMIT','20')))
LOCAL_RANK_OUTPUT_TOKENS=max(300,min(800,int(os.getenv('PRODUCT_LOCAL_RANK_OUTPUT_TOKENS','520'))))
LOCAL_AUDIT_OUTPUT_TOKENS=max(220,min(650,int(os.getenv('PRODUCT_LOCAL_AUDIT_OUTPUT_TOKENS','380'))))
LOCAL_CREATIVE_OUTPUT_TOKENS=max(700,min(1800,int(os.getenv('PRODUCT_LOCAL_CREATIVE_OUTPUT_TOKENS','1200'))))
LOCAL_CREATIVE_AUDIT_TOKENS=max(260,min(700,int(os.getenv('PRODUCT_LOCAL_CREATIVE_AUDIT_TOKENS','420'))))
MAX_PAIN_CONTEXT=max(0,min(5,int(os.getenv('PRODUCT_LOCAL_MAX_PAIN_CONTEXT','3'))))
MAX_THEME_CONTEXT=max(0,min(3,int(os.getenv('PRODUCT_LOCAL_MAX_THEME_CONTEXT','2'))))
DURABLE=os.getenv('AI_TASK_RUNTIME_DURABLE','true').lower() in ('1','true','yes','on')


def _router(max_tokens:int)->AITaskRouter:
    cache=SupabaseTaskCache() if DURABLE else InMemoryTaskCache()
    sink=SupabaseTaskResultSink() if DURABLE else None
    return AITaskRouter(
        executors=(OllamaExecutor(name='local_qwen35_4b',tier=2,model=LOCAL_MODEL,timeout_seconds=LOCAL_TIMEOUT,max_output_tokens=max_tokens),),
        cache=cache,
        result_sink=sink,
    )


def _num(value:Any,default:float=0.0)->float:
    try:return float(default if value is None or value=='' else value)
    except Exception:return float(default)


def _clip_text(value:Any,n:int)->str:
    return str(value or '').strip()[:n]


def _compact_product(item:Mapping[str,Any])->dict[str,Any]:
    raw=item.get('_raw') or {};product=item.get('product') or {};merchant=item.get('merchant') or {};metrics=item.get('_rank_metrics') or {};deep=item.get('_deep_demand') or {}
    return {
        'source_record_hash':product.get('source_record_hash') or raw.get('source_record_hash'),
        'product':{
            'name':_clip_text(product.get('product_name') or raw.get('product_name'),220),
            'brand':_clip_text(product.get('brand_name') or raw.get('brand_name'),120) or None,
            'model':_clip_text(product.get('model_name') or raw.get('model_name'),120) or None,
            'category':_clip_text(raw.get('category_raw'),160) or None,
            'price_eur':raw.get('price'),'full_price_eur':raw.get('full_price'),'discount_pct':raw.get('discount_pct'),
            'expected_commission_eur':raw.get('expected_commission_eur'),'in_stock':raw.get('in_stock'),'times_bought':raw.get('times_bought'),
        },
        'merchant':{
            'name':_clip_text(merchant.get('canonical_name') or raw.get('merchant_name'),160),
            'trust_score':merchant.get('trust_score'),'demand_score':merchant.get('demand_score'),
            'competition_score':merchant.get('competition_score'),'solution_whitespace_score':merchant.get('solution_whitespace_score'),
        },
        'deterministic_metrics':{k:metrics.get(k) for k in (
            'merchant_demand_score','competition_score','inverse_competition_score','merchant_whitespace_score','merchant_trust_score',
            'commercial_score','network_performance_score','discount_score','purchase_signal_score','pain_signal_score','seasonal_score','deep_demand_score','deterministic_rank_score')},
        'deep_demand':{k:deep.get(k) for k in ('matched','score','status','category_name','subcategory_name','canonical_demand_score','canonical_competition_score','canonical_confidence')},
        'pain_evidence':[
            {k:p.get(k) for k in ('id','canonical_text','pain_severity','commercial_intent','confidence','retrieval_score','source_diversity','evidence_count')}
            for p in (item.get('pain_rag') or [])[:MAX_PAIN_CONTEXT]
        ],
        'themes':[
            {k:t.get(k) for k in ('id','name','semantic_brief','retrieval_score','seasonal_curve_score')}
            for t in (item.get('theme_rag') or [])[:MAX_THEME_CONTEXT]
        ],
        'hard_constraints':{'min_expected_commission_eur':float(v1.MIN_COMMISSION),'market':'GR','no_paid_provider_fallback':True},
    }


def _normalize_channels(value:Any)->list[str]:
    allowed=('instagram','facebook','tiktok','linkedin')
    raw=value if isinstance(value,list) else [value] if value else []
    out=[]
    for x in raw:
        s=str(x).strip().lower()
        if s in allowed and s not in out:out.append(s)
    return out or ['instagram','facebook']


def _rank_task(item:Mapping[str,Any])->AITask:
    return AITask(
        task_type='product_promotion_rank',role='Greek Affiliate Product Ranking Analyst',prompt_version='local-v1',max_tier=2,cacheable=True,material_change_capable=True,
        required_keys=('source_record_hash','product_market_fit_score','creative_potential_score','value_score','confidence_score','promotion_angle','promotion_reason','audience','recommended_channels','rationale'),
        instructions=(
            'Evaluate this already deterministic-eligible product as a promotion opportunity in Greece. The owner hard commission floor has absolute priority and cannot be changed. '
            'Score 0-100: product_market_fit_score, creative_potential_score, value_score, confidence_score. Missing pain evidence is not proof of no demand and is not automatic rejection; it gives no pain bonus. '
            'Missing competition evidence gives no inverse-competition bonus. Network KPIs are merchant/program baselines, never product sales. '
            'Use only supplied facts. Keep promotion_angle, promotion_reason, audience and rationale concise and in natural Greek. '
            'recommended_channels may contain only instagram, facebook, tiktok, linkedin. Return the exact supplied source_record_hash.'
        ),payload=_compact_product(item),metadata={'bounded_context':True,'bulk_feed_exposed':False},
    )


def _audit_task(item:Mapping[str,Any],ranking:Mapping[str,Any])->AITask:
    payload=_compact_product(item)
    payload['proposed_ranking']={k:ranking.get(k) for k in (
        'source_record_hash','product_market_fit_score','creative_potential_score','value_score','confidence_score','promotion_angle','promotion_reason','audience','recommended_channels','rationale')}
    return AITask(
        task_type='product_promotion_skeptic',role='Independent Affiliate Product Skeptic',prompt_version='local-v1',max_tier=2,cacheable=True,material_change_capable=True,
        required_keys=('source_record_hash','verdict','risk_score','risk_flags','reasons','audit_summary'),
        instructions=(
            'Try to disprove the proposed product promotion ranking using only supplied evidence. Verify the € owner commission hard gate, factual grounding, product-pain fit, merchant evidence and unsupported claims. '
            'Do not reject solely because pain or forecast evidence is absent; instead lower confidence when evidence is weak. '
            'verdict must be VALIDATED, NEEDS_REVIEW, or REJECTED. risk_score is 0-100 where higher is riskier. '
            'Return exact source_record_hash. audit_summary and reasons must be concise Greek. Never invent missing facts.'
        ),payload=payload,metadata={'independent_skeptic':True,'bounded_context':True},
    )


def _run_task(router:AITaskRouter,task:AITask)->tuple[dict[str,Any]|None,dict[str,Any]]:
    result=router.execute(task)
    stats={'status':result.status,'from_cache':result.from_cache,'attempts':len(result.attempts)}
    if result.attempts:
        last=result.attempts[-1];stats.update({'model':last.model,'route':last.route,'latency_ms':last.latency_ms,'input_tokens':last.metadata.get('input_tokens'),'output_tokens':last.metadata.get('output_tokens'),'cost_usd':last.metadata.get('cost_usd',0)})
    return (dict(result.data) if result.ok and result.data is not None else None),stats


def _rank_one(item:Mapping[str,Any],router:AITaskRouter)->tuple[str,dict[str,Any]|None,dict[str,Any]]:
    h=str((item.get('product') or {}).get('source_record_hash') or '')
    if _num((item.get('_raw') or {}).get('expected_commission_eur'))+1e-9<float(v1.MIN_COMMISSION):
        return h,None,{'status':'hard_gate_reject','reason':'commission_below_owner_floor','cost_usd':0}
    data,stats=_run_task(router,_rank_task(item))
    if data is None:return h,None,stats
    if str(data.get('source_record_hash') or '')!=h:return h,None,{**stats,'status':'invalid_hash'}
    data['recommended_channels']=_normalize_channels(data.get('recommended_channels'))
    for key in ('product_market_fit_score','creative_potential_score','value_score','confidence_score'):data[key]=max(0,min(100,_num(data.get(key))))
    return h,data,stats


def _audit_one(item:Mapping[str,Any],ranking:Mapping[str,Any],router:AITaskRouter)->tuple[str,dict[str,Any]|None,dict[str,Any]]:
    h=str((item.get('product') or {}).get('source_record_hash') or '')
    data,stats=_run_task(router,_audit_task(item,ranking))
    if data is None:return h,None,stats
    if str(data.get('source_record_hash') or '')!=h:return h,None,{**stats,'status':'invalid_hash'}
    verdict=str(data.get('verdict') or '').upper()
    if verdict not in ('VALIDATED','NEEDS_REVIEW','REJECTED'):return h,None,{**stats,'status':'invalid_verdict'}
    data['verdict']=verdict;data['risk_score']=max(0,min(100,_num(data.get('risk_score'),50)))
    data['risk_flags']=data.get('risk_flags') if isinstance(data.get('risk_flags'),list) else []
    data['reasons']=data.get('reasons') if isinstance(data.get('reasons'),list) else []
    return h,data,stats


def rank_with_local_ai(items:list[Mapping[str,Any]])->tuple[dict[str,dict[str,Any]],dict[str,Any]]:
    """Rank only the bounded frontier, then independently audit enough products for Top-100.

    This function never sees the multi-million-row feed. `items` is the diversified
    deterministic/RAG shortlist created upstream. Unchanged packets are served from
    the immutable hash cache with zero model calls.
    """
    rank_router=_router(LOCAL_RANK_OUTPUT_TOKENS);ranked={};telemetry=[]
    with ThreadPoolExecutor(max_workers=LOCAL_AI_WORKERS) as pool:
        futures={pool.submit(_rank_one,item,rank_router):item for item in items}
        for future in as_completed(futures):
            h,data,stats=future.result();telemetry.append(stats)
            if data is not None:ranked[h]=(futures[future],data)
    if len(ranked)<LOCAL_MIN_FINAL:
        raise RuntimeError(f'local ranking completeness requires at least {LOCAL_MIN_FINAL} ranked candidates; got {len(ranked)}')

    # Audit best candidates first so the independent skeptic is not wasted on the
    # bottom of the frontier. A zero-risk proxy is used only to order audit work;
    # it is never persisted as the final risk score.
    priority=[]
    for h,(item,ranking) in ranked.items():
        proxy=v3.final_row(item,{'ranking':ranking,'audit':{'risk_score':0}})
        priority.append((proxy['rank_score'],h,item,ranking))
    priority.sort(reverse=True,key=lambda x:x[0])

    audit_router=_router(LOCAL_AUDIT_OUTPUT_TOKENS);outputs={};audited=0;rejected=0;needs_review=0;audit_stats=[]
    for start in range(0,len(priority),LOCAL_AI_WORKERS):
        if len(outputs)>=LOCAL_MIN_FINAL:break
        chunk=priority[start:start+LOCAL_AI_WORKERS]
        with ThreadPoolExecutor(max_workers=LOCAL_AI_WORKERS) as pool:
            futures={pool.submit(_audit_one,item,ranking,audit_router):(h,item,ranking) for _,h,item,ranking in chunk}
            for future in as_completed(futures):
                h,item,ranking=futures[future];_,audit,stats=future.result();audited+=1;audit_stats.append(stats)
                if audit is None:continue
                if audit['verdict']=='REJECTED':rejected+=1;continue
                needs_review+=int(audit['verdict']=='NEEDS_REVIEW')
                outputs[h]={'ranking':ranking,'audit':audit}
    if len(outputs)<LOCAL_MIN_FINAL:
        raise RuntimeError(f'local skeptic completeness requires {LOCAL_MIN_FINAL} non-rejected products; got {len(outputs)} after auditing {audited}')

    calls=sum(1 for x in telemetry+audit_stats if not x.get('from_cache') and x.get('status')=='ok')
    cache_hits=sum(1 for x in telemetry+audit_stats if x.get('from_cache'))
    cost=sum(float(x.get('cost_usd') or 0) for x in telemetry+audit_stats)
    return outputs,{
        'ai_ranked':len(outputs),'local_rank_candidates':len(ranked),'local_audited':audited,'local_rejected':rejected,'local_needs_review':needs_review,
        'local_model':LOCAL_MODEL,'local_ai_workers':LOCAL_AI_WORKERS,'local_model_calls':calls,'local_cache_hits':cache_hits,'paid_inference_cost_usd':round(cost,6),
        'ai_route':'provider_neutral_local_router','bulk_feed_to_llm':False,'audit_policy':'rank bounded frontier then independently audit only until Top-100 contract is satisfied',
    }


def _slug(value:str,fallback:str)->str:
    text=unicodedata.normalize('NFKD',value or '').encode('ascii','ignore').decode().lower()
    text=re.sub(r'[^a-z0-9]+','-',text).strip('-')
    return (text[:90] or fallback[:32] or 'product')


def enrich_seo_deterministic(rows:list[dict[str,Any]])->tuple[list[dict[str,Any]],dict[str,Any]]:
    """Factual SEO without any generative inference."""
    generated=datetime.now(timezone.utc).isoformat();count=0
    for row in rows:
        name=_clip_text(row.get('product_name'),120) or 'Προϊόν';merchant=_clip_text(row.get('merchant_name'),80);brand=_clip_text(row.get('brand_name'),60);category=_clip_text(row.get('category'),80)
        price=_num(row.get('effective_price'));discount=_num(row.get('discount_pct'))
        title=(f'{name} | {merchant}' if merchant else name)[:65]
        price_text=f' Τιμή €{price:.2f}.' if price>0 else ''
        discount_text=f' Έκπτωση {discount:.0f}%.' if discount>0 else ''
        short=(f'{name}'+(f' από {merchant}' if merchant else '')+'.'+price_text+discount_text).strip()
        keywords=[]
        for x in (name,brand,category,merchant):
            if x and x not in keywords:keywords.append(x)
        bullets=[];attrs=row.get('product_attributes') or {}
        for label,key in (('Διαθεσιμότητα','availability'),('Χρώμα','colour'),('Μέγεθος','size')):
            val=_clip_text(attrs.get(key),100)
            if val:bullets.append(f'{label}: {val}')
        row['seo_content']={
            'title':title,'meta_description':short[:160],'short_description':short[:260],'description':short[:600],
            'keywords':keywords[:8],'search_intent':'product_comparison','slug':_slug(name,str(row.get('source_record_hash') or 'product')),'feature_bullets':bullets[:5],
        }
        row['seo_generated_at']=generated;count+=1
    return rows,{'seo_enriched':count,'seo_failures':0,'seo_generation':'deterministic_verified_facts_only','seo_llm_calls':0}


def _creative_payload(row:Mapping[str,Any])->dict[str,Any]:
    return {
        'source_record_hash':row.get('source_record_hash'),
        'product':{'name':row.get('product_name'),'brand':row.get('brand_name'),'model':row.get('model_name'),'category':row.get('category'),'price_eur':row.get('effective_price'),'discount_pct':row.get('discount_pct')},
        'merchant_name':row.get('merchant_name'),
        'merchant_media':{'image_url':row.get('image_url'),'image_provenance':row.get('image_provenance') or 'merchant_feed'},
        'tracking':{'url_present':bool(str(row.get('tracking_url') or '').startswith('https://')),'immutable':True},
        'promotion':{'angle':row.get('promotion_angle'),'reason':row.get('promotion_reason'),'audience':row.get('audience'),'recommended_channels':row.get('recommended_channels') or []},
        'seasonality':row.get('seasonality') or row.get('seasonal_context') or {},
        'risk_flags':row.get('risk_flags') or [],
        'verified_bullets':(row.get('seo_content') or {}).get('feature_bullets') or [],
        'rules':{'language':'el-GR','no_invented_features':True,'no_fake_scarcity':True,'no_internal_kpis':True,'affiliate_disclosure':True,'use_real_merchant_image':True},
    }


def _creative_task(row:Mapping[str,Any])->AITask:
    return AITask(
        task_type='product_promotion_creative',role='Greek Affiliate Creative Director',prompt_version='local-v1',max_tier=2,cacheable=True,
        required_keys=('source_record_hash','campaign_theme','emotional_angle','audience','primary_message','variants'),
        instructions=(
            'Create exactly three concise Greek social variants from supplied verified facts only. Never invent features, reviews, guarantees, shipping, scarcity or savings. '
            'Variants must have ids feed_4x5, reel_9x16, square_1x1. For each return hook, headline, subheadline, cta, caption, hashtags (5-8 strings), visual_direction. '
            'Do not include QR payloads or URLs; software adds the immutable affiliate URL deterministically. Keep copy useful rather than hype-heavy.'
        ),payload=_creative_payload(row),metadata={'top20_only':True,'bulk_feed_exposed':False},
    )


def _creative_audit_task(row:Mapping[str,Any],pack:Mapping[str,Any])->AITask:
    return AITask(
        task_type='product_promotion_creative_skeptic',role='Independent Creative Skeptic',prompt_version='local-v1',max_tier=2,cacheable=True,
        required_keys=('source_record_hash','verdict','risk_score','unsupported_claims','fidelity_risks','corrections','audit_summary'),
        instructions=(
            'Audit the proposed Greek creative against supplied product facts. Reject unsupported features, wrong price/discount, fake scarcity/social proof, misleading benefit claims or internal KPI language. '
            'verdict must be READY or NEEDS_REVIEW. Return exact source_record_hash. Do not invent replacement facts.'
        ),payload={**_creative_payload(row),'creative_pack':pack},metadata={'independent_skeptic':True,'top20_only':True},
    )


def _normalize_pack(row:Mapping[str,Any],data:Mapping[str,Any])->dict[str,Any]|None:
    h=str(row.get('source_record_hash') or '')
    if str(data.get('source_record_hash') or '')!=h:return None
    raw_variants=data.get('variants') if isinstance(data.get('variants'),list) else []
    by_id={str(x.get('id') or ''):x for x in raw_variants if isinstance(x,Mapping)}
    specs=(('feed_4x5',['instagram','facebook'],'4:5'),('reel_9x16',['instagram','tiktok'],'9:16'),('square_1x1',['facebook','instagram'],'1:1'))
    variants=[]
    for vid,platforms,aspect in specs:
        src=by_id.get(vid)
        if not src:return None
        headline=_clip_text(src.get('headline'),120);caption=_clip_text(src.get('caption'),900);cta=_clip_text(src.get('cta'),80)
        if not headline or not caption or not cta:return None
        hashtags=src.get('hashtags') if isinstance(src.get('hashtags'),list) else []
        variants.append({
            'id':vid,'platform':platforms,'aspect_ratio':aspect,'hook':_clip_text(src.get('hook'),120),'headline':headline,
            'subheadline':_clip_text(src.get('subheadline'),180),'cta':cta,'caption':caption,'hashtags':[str(x)[:60] for x in hashtags[:8]],
            'visual_direction':_clip_text(src.get('visual_direction'),300),'composition':'real product image prominent','lighting':'preserve source image fidelity',
            'product_image_treatment':'use supplied real product image; do not regenerate product','qr_spec':{'payload_rule':'exact_tracking_url','placement':'bottom-right','contrast_rule':'high contrast','min_relative_size':'10%'},
            'fidelity_rules':['no invented product features','preserve real product identity','use exact affiliate tracking URL'],
            'reel_storyboard':[] if vid!='reel_9x16' else [{'scene':1,'text':_clip_text(src.get('hook'),100)},{'scene':2,'text':headline},{'scene':3,'text':_clip_text(src.get('subheadline'),120)},{'scene':4,'text':cta}],
        })
    return {'source_record_hash':h,'campaign_theme':_clip_text(data.get('campaign_theme'),160),'emotional_angle':_clip_text(data.get('emotional_angle'),160),'audience':_clip_text(data.get('audience'),180),'primary_message':_clip_text(data.get('primary_message'),220),'variants':variants}


def _seasonal_angle_grounded(row:Mapping[str,Any])->bool:
    """Reject obvious seasonal/category mismatches before creative generation."""
    angle=' '.join(str(row.get(k) or '') for k in ('promotion_angle','promotion_reason','audience')).lower()
    product=' '.join(str(row.get(k) or '') for k in ('product_name','category','subcategory')).lower()
    markers=('back to school','σχολ','μαθητ','φοιτητ')
    relevant=('σχολ','γραφ','τετράδ','τσάντ','laptop','tablet','εκτυπωτ','καρέκλ','γραφείο','ακουστικ','power bank','οργάνω')
    return not (any(x in angle for x in markers) and not any(x in product for x in relevant))


def enrich_creatives_local(rows:list[dict[str,Any]])->tuple[list[dict[str,Any]],dict[str,Any]]:
    if len(rows)<LOCAL_CREATIVE_LIMIT:raise RuntimeError(f'local creative contract requires {LOCAL_CREATIVE_LIMIT} ranked rows')
    creative_router=_router(LOCAL_CREATIVE_OUTPUT_TOKENS);audit_router=_router(LOCAL_CREATIVE_AUDIT_TOKENS)
    generated=0;calls=0;cache_hits=0;skipped=[];ready_rows=[];attempt_limit=min(len(rows),LOCAL_CREATIVE_LIMIT*3)
    for row in rows[:attempt_limit]:
        h=str(row.get('source_record_hash') or '')
        if not str(row.get('image_url') or '').startswith(('https://','http://')):
            row['creative_status']='needs_review';skipped.append({'source_record_hash':h,'reason':'missing_merchant_image'});continue
        if not str(row.get('tracking_url') or '').startswith('https://'):
            row['creative_status']='needs_review';skipped.append({'source_record_hash':h,'reason':'missing_exact_tracking_url'});continue
        if row.get('risk_flags'):
            row['creative_status']='needs_review';skipped.append({'source_record_hash':h,'reason':'risk_flags_present'});continue
        if not _seasonal_angle_grounded(row):
            row['creative_status']='needs_review';skipped.append({'source_record_hash':h,'reason':'seasonality_category_mismatch'});continue
        try:
            pack_raw,stats=_run_task(creative_router,_creative_task(row));calls+=int(stats.get('status')=='ok' and not stats.get('from_cache'));cache_hits+=int(bool(stats.get('from_cache')))
            pack=_normalize_pack(row,pack_raw or {}) if pack_raw else None
            if not pack:raise RuntimeError('invalid_creative_json')
            audit,astats=_run_task(audit_router,_creative_audit_task(row,pack));calls+=int(astats.get('status')=='ok' and not astats.get('from_cache'));cache_hits+=int(bool(astats.get('from_cache')))
            if not audit:raise RuntimeError('creative_audit_unavailable')
            verdict=str(audit.get('verdict') or '').upper();audit=dict(audit);audit['verdict']=verdict
            row['creative_pack']=pack;row['creative_audit']=audit;row['creative_status']='ready' if verdict=='READY' else 'needs_review';row['creative_generated_at']=datetime.now(timezone.utc).isoformat()
            generated+=1
            if verdict!='READY':
                skipped.append({'source_record_hash':h,'reason':f'audit_{verdict.lower() or "invalid"}'});continue
            ready_rows.append(row)
            if len(ready_rows)>=LOCAL_CREATIVE_LIMIT:break
        except Exception as exc:
            row['creative_status']='needs_review';skipped.append({'source_record_hash':h,'reason':str(exc)[:180]});continue
    if len(ready_rows)<LOCAL_CREATIVE_LIMIT:
        raise RuntimeError(f'only {len(ready_rows)}/{LOCAL_CREATIVE_LIMIT} verified creatives after {attempt_limit} candidates; rejected={json.dumps(skipped[:8],ensure_ascii=False)}')
    ready_ids={id(x) for x in ready_rows}
    rows=ready_rows+[x for x in rows if id(x) not in ready_ids]
    for idx,row in enumerate(rows[:LOCAL_CREATIVE_LIMIT],1):row['creative_global_rank']=idx
    rows,asset_stats=v32.attach_durable_assets(rows)
    return rows,{
        'creative_target':LOCAL_CREATIVE_LIMIT,'creative_candidates_attempted':attempt_limit,'creative_generated':generated,'creative_ready':len(ready_rows),
        'creative_rejected':len(skipped),'creative_rejection_sample':skipped[:8],'creative_model':LOCAL_MODEL,'creative_local_model_calls':calls,'creative_cache_hits':cache_hits,
        'creative_paid_inference_cost_usd':0,'creative_policy':'verified replacements; merchant image only; grounded seasonality; independent skeptic; exact QR; 3 durable platform assets',**asset_stats,
    }

def enrich_final_rows_local(rows:list[dict[str,Any]])->tuple[list[dict[str,Any]],dict[str,Any]]:
    v32.assert_final_contract(rows)
    rows,seo=enrich_seo_deterministic(rows)
    rows,creative=enrich_creatives_local(rows)
    return rows,{**seo,**creative,'final_min_ranked':LOCAL_MIN_FINAL,'final_creative_products':LOCAL_CREATIVE_LIMIT,'final_creative_assets':LOCAL_CREATIVE_LIMIT*3,'paid_llm_required':False}
