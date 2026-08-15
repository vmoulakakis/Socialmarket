import collections, json, os, sqlite3, sys, time, urllib.parse, urllib.request
from pathlib import Path
import ijson

from stream_feed import iter_records, normalize, normalize_domain
from product_agents import (
    canonical_key, compact_product_for_ai, evidence_metrics, final_opportunity_score,
    fold, parse_commission_rule, select_pain_rag, select_theme_rag
)
from product_safety import build_feed_safety_profile, price_integrity_allows, prune_dynamic_candidate_saturation

GATEWAY=os.getenv('PRODUCT_INTELLIGENCE_GATEWAY','https://rpfadpdnnxequgvdcfoq.supabase.co/functions/v1/product-intelligence-gateway')
MIN_COMMISSION=float(os.getenv('PRODUCT_MIN_COMMISSION_EUR','10'))
MIN_MERCHANT_TRUST=float(os.getenv('PRODUCT_MIN_MERCHANT_TRUST','30'))
AI_BATCH=max(1,min(int(os.getenv('PRODUCT_AI_BATCH','8')),12))
AI_MAX_CANDIDATES=max(1,int(os.getenv('PRODUCT_AI_MAX_CANDIDATES','48')))
AI_OFFERS_PER_PRODUCT=max(1,min(int(os.getenv('PRODUCT_AI_OFFERS_PER_PRODUCT','1')),3))
MIN_VALIDATED_PAIN_CLUSTERS=max(1,int(os.getenv('PRODUCT_MIN_VALIDATED_PAIN_CLUSTERS','1')))
MIN_AUDIT_OVERALL=float(os.getenv('PRODUCT_MIN_AUDIT_OVERALL','70'))
MIN_PAIN_FIT=float(os.getenv('PRODUCT_MIN_PAIN_FIT','60'))
MIN_PRODUCT_EVIDENCE=float(os.getenv('PRODUCT_MIN_PRODUCT_EVIDENCE','60'))
MAX_AI_BATCH_FAILURE_RATE=max(0.0,min(float(os.getenv('PRODUCT_MAX_AI_BATCH_FAILURE_RATE','0.25')),1.0))
SOURCE_FEED=os.getenv('PRODUCT_SOURCE_FEED','linkwise-products.json')
PROFILE_PATH=Path(os.getenv('PRODUCT_PROFILE_PATH','product-intelligence-profile.json'))
STAGE_DB=os.getenv('PRODUCT_STAGE_DB','product-stage.sqlite3')
REUSE_STAGE=os.getenv('PRODUCT_REUSE_STAGE_DB','true').lower() in ('1','true','yes','on')


def oidc_token():
    url=os.getenv('ACTIONS_ID_TOKEN_REQUEST_URL'); token=os.getenv('ACTIONS_ID_TOKEN_REQUEST_TOKEN')
    if not url or not token:raise RuntimeError('GitHub OIDC environment is unavailable')
    sep='&' if '?' in url else '?'
    req=urllib.request.Request(url+sep+'audience='+urllib.parse.quote('socialmarket-supabase-worker'),headers={'Authorization':'Bearer '+token})
    with urllib.request.urlopen(req,timeout=20) as r:
        return json.loads(r.read().decode())['value']


_TOKEN=None
def gateway(action,**payload):
    global _TOKEN
    if _TOKEN is None:_TOKEN=oidc_token()
    body=json.dumps({'action':action,**payload},ensure_ascii=False).encode()
    req=urllib.request.Request(GATEWAY,data=body,headers={'authorization':'Bearer '+_TOKEN,'content-type':'application/json'},method='POST')
    try:
        with urllib.request.urlopen(req,timeout=180) as r:return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        msg=e.read().decode(errors='replace')
        raise RuntimeError(f'gateway {action} failed: {e.code} {msg[:1000]}')


def init_stage(path,reset=False):
    if reset:
        for suffix in ('','-wal','-shm'):
            try:Path(str(path)+suffix).unlink()
            except FileNotFoundError:pass
    db=sqlite3.connect(path)
    db.execute('pragma journal_mode=WAL')
    db.execute('pragma synchronous=NORMAL')
    db.execute('''create table if not exists candidates(
      source_hash text primary key, canonical_key text not null, merchant_id text not null,
      merchant_name text, competition_score real not null default 50, payload text not null,
      expected_commission real not null, preliminary_score real not null
    )''')
    db.execute('create index if not exists candidates_canonical_idx on candidates(canonical_key,preliminary_score desc)')
    db.execute('create index if not exists candidates_merchant_idx on candidates(merchant_id)')
    db.commit();return db


def _unique_row(rows):
    if not rows:return None
    by_program={str(r.get('merchant_program_id') or r.get('merchant_id')):r for r in rows}
    return next(iter(by_program.values())) if len(by_program)==1 else None


def merchant_maps(context):
    by_program={}; aliases={}; by_domain={}
    for row in context.get('programs',[]):
        pkey=fold(row.get('program_name'))
        if pkey:by_program[pkey]=row
        for a in row.get('aliases') or []:
            akey=fold(a)
            if akey:aliases[akey]=row
        dom=normalize_domain(row.get('official_domain'))
        if dom:by_domain.setdefault(dom,[]).append(row)
    return by_program,aliases,by_domain


def resolve_merchant(product,by_program,aliases,by_domain):
    """Resolve conservatively using authoritative destination domain first.

    The production Linkwise feed does not expose program_name. Its tracking_url
    carries an encoded destination (lnkurl), which normalize() turns into
    target_domain. Domain resolution is deterministic; broad fuzzy name matching
    is intentionally not used.
    """
    domain=normalize_domain(product.get('target_domain'))
    if domain:
        exact=_unique_row(by_domain.get(domain,[]))
        if exact:return exact,'target_domain_exact'
        # Safe O(labels) subdomain fallback: only exact suffixes in the canonical domain map.
        labels=domain.split('.')
        for i in range(1,max(1,len(labels)-1)):
            suffix=_unique_row(by_domain.get('.'.join(labels[i:]),[]))
            if suffix:return suffix,'target_domain_suffix'

    k=fold(product.get('program_name'))
    if k:
        if k in by_program:return by_program[k],'program_exact'
        if k in aliases:return aliases[k],'alias_exact'
    return None,None


def preliminary_score(p,merchant):
    # Cheap ordering only; final ranking is computed after RAG + AI audit.
    commission=min(100,max(0,(p['expected_commission_eur']-MIN_COMMISSION)*3+25))
    m=float(merchant.get('solution_whitespace_score') or 0)
    demand=float(merchant.get('demand_score') or 0)
    return round(commission*.45+m*.35+demand*.20,3)


def stage_feed(feed,context):
    safety=build_feed_safety_profile(feed,context,iter_records,normalize,resolve_merchant,merchant_maps)
    by_program,aliases,by_domain=merchant_maps(context)
    db=init_stage(STAGE_DB,reset=True)
    reasons=collections.Counter(); resolution_methods=collections.Counter(); seen=eligible=0
    try:
        iterator=iter_records(feed)
        while True:
            try:raw=next(iterator)
            except StopIteration:break
            except ijson.common.IncompleteJSONError as exc:
                reasons['feed_truncated_after_complete_records']+=1
                print(json.dumps({'warning':'truncated_feed_salvaged','error':str(exc)[:300],'seen':seen}),flush=True)
                break
            seen+=1
            p=normalize(raw)
            merchant,resolution_method=resolve_merchant(p,by_program,aliases,by_domain)
            if not merchant:
                reasons['merchant_unresolved']+=1;continue
            resolution_methods[resolution_method]+=1
            p['merchant_resolution_method']=resolution_method
            mid=str(merchant.get('merchant_id'))
            merchant_safety=safety.get('merchants',{}).get(mid,{})
            if merchant.get('promotion_mode') in ('demand_beacon_only','blocked') or merchant.get('dominant_market'):
                reasons['dominant_or_blocked_merchant']+=1;continue
            if merchant_safety.get('feed_saturated'):
                reasons['dynamic_feed_saturation']+=1;continue
            trust=float(merchant.get('trust_score') or 0)
            if trust<MIN_MERCHANT_TRUST:
                reasons['merchant_trust_below_gate']+=1;continue
            if p.get('in_stock') is False:
                reasons['out_of_stock']+=1;continue
            if not p.get('tracking_url'):
                reasons['missing_tracking_url']+=1;continue
            if not (p.get('image_url') or p.get('thumb_url')):
                reasons['missing_image']+=1;continue
            price=float(p.get('price') or 0)
            if price<=0:
                reasons['invalid_effective_price']+=1;continue
            if str(p.get('currency') or 'EUR').upper()!='EUR':
                reasons['non_eur_requires_fx']+=1;continue
            price_ok,price_reason,price_info=price_integrity_allows(price,merchant_safety)
            if not price_ok:
                reasons[price_reason]+=1;continue
            p['price_integrity']={
              'status':price_reason,'confidence':price_info.get('confidence'),
              'merchant_sample_count':price_info.get('sample_count'),'merchant_median':price_info.get('median'),
              'merchant_p90':price_info.get('p90'),'auto_scaled':False
            }
            comm=parse_commission_rule(merchant.get('raw_commission_pct'),merchant.get('raw_flat_commission'),price)
            p.update(comm)
            if p['expected_commission_eur']+1e-9<MIN_COMMISSION:
                reasons['commission_below_10']+=1;continue
            p['expected_commission_eur']=round(p['expected_commission_eur'],4)
            p['potential_commission_eur']=round(p['potential_commission_eur'],4)
            p['merchant_name']=merchant.get('canonical_name') or p.get('program_name') or p.get('target_domain')
            p['merchant_context']={k:merchant.get(k) for k in (
                'merchant_id','merchant_program_id','canonical_name','official_domain','solution_whitespace_score','demand_beacon_score',
                'demand_score','competition_score','trust_score','confidence','promotion_mode','dominant_market'
            )}
            p['merchant_context']['resolved_feed_share']=merchant_safety.get('resolved_feed_share')
            p['canonical_key']=canonical_key(p)
            pre=preliminary_score(p,merchant)
            db.execute('insert or replace into candidates(source_hash,canonical_key,merchant_id,merchant_name,competition_score,payload,expected_commission,preliminary_score) values(?,?,?,?,?,?,?,?)',(
                p['source_record_hash'],p['canonical_key'],mid,p['merchant_name'],float(merchant.get('competition_score') or 50),
                json.dumps(p,ensure_ascii=False,default=str),p['expected_commission_eur'],pre))
            eligible+=1
            if eligible%5000==0:db.commit()
            if seen%250000==0:
                print(json.dumps({'phase':'stream','seen':seen,'commission_eligible':eligible,'merchant_resolution_methods':resolution_methods.most_common(),'excluded':reasons.most_common(8)}),flush=True)
    finally:db.commit()
    removed,saturated=prune_dynamic_candidate_saturation(db,reasons)
    eligible=max(0,eligible-removed)
    return db,{
      'records_seen':seen,
      'commission_eligible_records':eligible,
      'merchant_resolution_methods':resolution_methods.most_common(),
      'excluded_reasons':reasons.most_common(),
      'dynamic_saturated_merchants':saturated,
      'price_integrity_policy':'no automatic cents/EUR conversion; suspicious merchant scales quarantined before commission',
      'safety_profile_path':'product-feed-safety-profile.json'
    }


def iter_best_offers(db,max_offers_per_product=1):
    # Keep up to three eligible offers per canonical product; AI can choose merchant-aware best offer.
    q='''select payload from (
      select payload,canonical_key,preliminary_score,
             row_number() over(partition by canonical_key order by preliminary_score desc,expected_commission desc) rn
      from candidates
    ) where rn<=? order by preliminary_score desc'''
    for (payload,) in db.execute(q,(max_offers_per_product,)):
        yield json.loads(payload)


def build_ai_item(p,context):
    merchant=p['merchant_context']
    pains=select_pain_rag(p,context.get('pain_clusters',[]),8)
    themes=select_theme_rag(p,context.get('themes',[]),5)
    return {
      'product':compact_product_for_ai(p),
      'merchant':merchant,
      'pain_rag':[{k:x.get(k) for k in ('id','cluster_type','canonical_text','category','subcategory','evidence_count','source_diversity','demand_score','competition_score','pain_severity','commercial_intent','confidence','retrieval_score')} for x in pains],
      'theme_rag':[{k:x.get(k) for k in ('id','slug','name','semantic_brief','active_from','peak_date','active_to','retrieval_score','seasonal_curve_score')} for x in themes],
      '_pains':pains,'_themes':themes,'_raw':p,
    }


def process_batch(items,stats):
    stats['ai_batches_attempted']+=1
    wire=[{k:v for k,v in x.items() if not k.startswith('_')} for x in items]
    try:
        enrich_res=gateway('enrich',items=wire,thinking='auto')
    except Exception as exc:
        stats['ai_batch_failures']+=1;stats['enrich_batch_failures']+=1;stats['ai_items_quarantined']+=len(items)
        print(json.dumps({'warning':'ai_enrich_batch_quarantined','items':len(items),'error':str(exc)[:500]}),flush=True)
        return 0
    decision=enrich_res.get('thinking') or {}
    stats['enrich_thinking_on' if decision.get('enabled') else 'enrich_thinking_off']+=1
    enriched=enrich_res.get('items',[])
    by_hash={str(x.get('source_record_hash')):x for x in enriched}
    audit_input=[]
    for x in items:
        h=x['product']['source_record_hash']
        if h not in by_hash:
            stats['ai_enrichment_missing']+=1;continue
        audit_input.append({**{k:v for k,v in x.items() if not k.startswith('_')},'enrichment':by_hash[h]})
    if not audit_input:return 0
    try:
        audit_res=gateway('audit',items=audit_input,thinking='auto')
    except Exception as exc:
        stats['ai_batch_failures']+=1;stats['audit_batch_failures']+=1;stats['ai_items_quarantined']+=len(audit_input)
        print(json.dumps({'warning':'ai_audit_batch_quarantined','items':len(audit_input),'error':str(exc)[:500]}),flush=True)
        return 0
    decision=audit_res.get('thinking') or {}
    stats['audit_thinking_on' if decision.get('enabled') else 'audit_thinking_off']+=1
    audited=audit_res.get('items',[])
    audit_by={str(x.get('source_record_hash')):x for x in audited}
    saves=[]
    for x in items:
        p=x['_raw']; h=p['source_record_hash']; enrich=by_hash.get(h); audit=audit_by.get(h)
        if not enrich or not audit:continue
        selected_ids=set(str(z) for z in audit.get('pain_cluster_ids') or [])
        selected_pains=[c for c in x['_pains'] if str(c.get('id')) in selected_ids]
        selected_theme_ids=set(str(z) for z in audit.get('theme_ids') or [])
        selected_themes=[t for t in x['_themes'] if str(t.get('id')) in selected_theme_ids]
        metrics=evidence_metrics(selected_pains,p['merchant_context'])
        seasonal=max([float(t.get('seasonal_curve_score') or 0) for t in selected_themes]+[float(audit.get('seasonal_theme_score') or 0)])
        pain=float(audit.get('pain_gap_fit_score') or 0)
        mopp=float(p['merchant_context'].get('solution_whitespace_score') or 0)
        trust=float(p['merchant_context'].get('trust_score') or 0)
        evidence_conf=max(metrics['evidence_confidence'],float(audit.get('product_evidence_confidence') or 0))
        final,components=final_opportunity_score(
          pain_gap_fit=pain,merchant_opportunity=mopp,greek_demand=metrics['greek_demand_score'],
          competition=metrics['competition_score'],seasonal_theme=seasonal,merchant_trust=trust,
          expected_commission=p['expected_commission_eur'],discount=p.get('discount_pct'),evidence_confidence=evidence_conf)
        verdict=str(audit.get('verdict') or 'needs_review').lower()
        if verdict not in ('validated','needs_review','rejected'):verdict='needs_review'
        stats['audited_'+verdict]+=1
        if verdict!='validated':
            stats['not_persisted_nonvalidated']+=1;continue
        if not selected_pains:
            stats['not_persisted_no_validated_pain']+=1;continue
        if float(audit.get('overall_score') or 0)<MIN_AUDIT_OVERALL:
            stats['not_persisted_audit_score']+=1;continue
        if pain<MIN_PAIN_FIT:
            stats['not_persisted_pain_fit']+=1;continue
        if evidence_conf<MIN_PRODUCT_EVIDENCE:
            stats['not_persisted_evidence_confidence']+=1;continue
        saves.append({
          'source_feed':SOURCE_FEED,'canonical_key':p['canonical_key'],'source_record_hash':h,
          'external_product_id':p.get('external_product_id'),'merchant_id':p['merchant_context']['merchant_id'],
          'merchant_program_id':p['merchant_context'].get('merchant_program_id'),'program_name_raw':p.get('program_name'),
          'product_name_raw':p.get('product_name'),'description_raw':p.get('description'),'category_raw':p.get('category_raw'),
          'canonical_title':enrich.get('canonical_title') or p.get('product_name'),'human_description':enrich.get('human_description'),
          'brand_name':enrich.get('brand_name') or p.get('brand_name'),'model_name':enrich.get('model_name') or p.get('model_name'),
          'gtin':p.get('gtin'),'mpn':p.get('mpn'),'category':enrich.get('category') or p.get('category_raw'),
          'subcategory':enrich.get('subcategory'),'semantic_text':enrich.get('semantic_text'),
          'effective_price':p.get('price'),'full_price':p.get('full_price'),'discount_pct':p.get('discount_pct'),'currency':p.get('currency'),
          'commission_rate_pct':p.get('commission_rate_pct'),'flat_commission_eur':p.get('flat_commission_eur'),
          'expected_commission_eur':p.get('expected_commission_eur'),'commission_rule':p.get('commission_rule'),
          'commission_confidence':p.get('commission_confidence'),'tracking_url':p.get('tracking_url'),'image_url':p.get('image_url'),
          'thumb_url':p.get('thumb_url'),'in_stock':p.get('in_stock'),'availability':p.get('availability'),'times_bought':p.get('times_bought'),
          'valid_from':p.get('valid_from'),'valid_to':p.get('valid_to'),'price_integrity':p.get('price_integrity'),'pain_matches':[
              {'id':c['id'],'score':float(audit.get('pain_scores',{}).get(str(c['id']),pain)),'confidence':c.get('confidence'),'rationale':audit.get('pain_rationale')} for c in selected_pains],
          'theme_matches':[{'id':t['id'],'relevance_score':float(audit.get('theme_scores',{}).get(str(t['id']),t.get('retrieval_score') or 0)),'seasonal_score':t.get('seasonal_curve_score'),'rationale':audit.get('theme_rationale')} for t in selected_themes],
          'scores':{**components,'final_opportunity_score':final},'validation_status':'validated',
          'audit_summary':audit.get('audit_summary'),'audit':audit,'enrichment':enrich,
          'evidence_count':sum(int(c.get('evidence_count') or 0) for c in selected_pains),
          'resolution':{'method':p.get('merchant_resolution_method'),'target_domain':p.get('target_domain'),'linkwise_route':p.get('linkwise_route')}
        })
    if saves:
        res=gateway('save_batch',items=saves)
        stats['saved']+=int(res.get('saved') or 0)
    return len(saves)


def main(feed):
    health=gateway('health')
    if not health.get('deepseek_configured'):
        raise SystemExit('Product Intelligence requires DeepSeek configuration for Phase B; refusing non-AI persistence fallback.')
    context=gateway('context')
    pain_count=len(context.get('pain_clusters',[]))
    if pain_count<MIN_VALIDATED_PAIN_CLUSTERS:
        raise SystemExit(f'Product Intelligence requires at least {MIN_VALIDATED_PAIN_CLUSTERS} validated pain clusters; found {pain_count}.')
    print(json.dumps({'phase':'context','programs':len(context.get('programs',[])),'pain_clusters':pain_count,'themes':len(context.get('themes',[])),'deepseek_model':health.get('deepseek_model'),'ai_max_candidates':AI_MAX_CANDIDATES}),flush=True)
    reused=False
    if REUSE_STAGE and Path(STAGE_DB).exists():
        try:
            db=init_stage(STAGE_DB,reset=False)
            staged=db.execute('select count(*) from candidates').fetchone()[0]
            reused=staged>0
        except Exception:
            reused=False
    if reused:
        stream_stats={'stage_reused_from_phase_a':True,'commission_eligible_records':staged}
    else:
        db,stream_stats=stage_feed(feed,context)
    stats=collections.Counter(); batch=[]; submitted=0
    for p in iter_best_offers(db,AI_OFFERS_PER_PRODUCT):
        if submitted+len(batch)>=AI_MAX_CANDIDATES:break
        batch.append(build_ai_item(p,context))
        if len(batch)>=AI_BATCH:
            process_batch(batch,stats);submitted+=len(batch);batch=[]
            print(json.dumps({'phase':'ai','submitted':submitted,**stats}),flush=True)
    if batch:process_batch(batch,stats);submitted+=len(batch)
    unique_products=db.execute('select count(distinct canonical_key) from candidates').fetchone()[0]
    attempted=int(stats.get('ai_batches_attempted') or 0); failures=int(stats.get('ai_batch_failures') or 0)
    failure_rate=(failures/attempted) if attempted else 0.0
    stats['ai_batch_failure_rate']=round(failure_rate,4)
    profile={**stream_stats,'unique_commission_eligible_products':unique_products,'ai_offers_submitted':submitted,**stats,'policy':{
      'commission_gate_eur':MIN_COMMISSION,'merchant_trust_gate':MIN_MERCHANT_TRUST,
      'merchant_resolution':'Linkwise tracking_url destination domain -> authoritative merchant official_domain; exact program/alias only as secondary path',
      'dominant_merchants':'static + dynamic feed/candidate saturation excluded from promotion; evidence retained as demand beacons',
      'price_integrity':'no automatic cents/EUR conversion; statistically suspicious scales are quarantined before commission',
      'ai_max_candidates':AI_MAX_CANDIDATES,'ai_offers_per_product':AI_OFFERS_PER_PRODUCT,
      'max_ai_batch_failure_rate':MAX_AI_BATCH_FAILURE_RATE,
      'persistence':'VALIDATED only + validated pain + audit/pain/evidence thresholds',
      'ranking':'25 pain + 20 merchant whitespace + 15 Greek demand + 12 commission + 10 inverse competition + 8 seasonal + 5 trust + 3 discount + 2 evidence confidence',
      'raw_feed_imported':False,'ai_fallback_allowed':False
    }}
    PROFILE_PATH.write_text(json.dumps(profile,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    print(json.dumps({'product_intelligence_final':profile},ensure_ascii=False,default=str),flush=True)
    db.close()
    if failure_rate>MAX_AI_BATCH_FAILURE_RATE:
        raise SystemExit(f'AI batch circuit breaker: failure_rate={failure_rate:.3f} exceeds {MAX_AI_BATCH_FAILURE_RATE:.3f}')


if __name__=='__main__':
    main(sys.argv[1] if len(sys.argv)>1 else SOURCE_FEED)
