import collections, json, os, sys
from pathlib import Path

import product_intelligence_v1 as v1
from runtime_config import apply_runtime_config, load_runtime_config, save_run_profile

OUT=Path(os.getenv('PRODUCT_SCAN_PROFILE_PATH','product-commercial-scan-profile.json'))
SAMPLE=Path(os.getenv('PRODUCT_SCAN_SAMPLE_PATH','product-commercial-scan-sample.json'))


def summarize(db,stream_stats,context,cfg):
    unique_products=db.execute('select count(distinct canonical_key) from candidates').fetchone()[0]
    offers=db.execute('select count(*) from candidates').fetchone()[0]
    commission_bands=collections.Counter(); merchants=collections.Counter(); categories=collections.Counter(); top=[]
    for payload,expected,pre in db.execute('select payload,expected_commission,preliminary_score from candidates order by preliminary_score desc,expected_commission desc'):
        p=json.loads(payload); e=float(expected or 0)
        if e < 15: band='10-14.99'
        elif e < 25: band='15-24.99'
        elif e < 40: band='25-39.99'
        elif e < 75: band='40-74.99'
        else: band='75+'
        commission_bands[band]+=1
        merchants[p.get('merchant_name') or 'UNKNOWN']+=1
        categories[p.get('category_raw') or 'UNKNOWN']+=1
        if len(top)<200:
            top.append({
              'external_product_id':p.get('external_product_id'),'product_name':p.get('product_name'),
              'brand_name':p.get('brand_name'),'merchant_name':p.get('merchant_name'),'category_raw':p.get('category_raw'),
              'effective_price':p.get('price'),'discount_pct':p.get('discount_pct'),
              'expected_commission_eur':p.get('expected_commission_eur'),'price_integrity':p.get('price_integrity'),
              'potential_commission_eur':p.get('potential_commission_eur'),'commission_rule':p.get('commission_rule'),
              'merchant_solution_whitespace':p.get('merchant_context',{}).get('solution_whitespace_score'),
              'merchant_trust':p.get('merchant_context',{}).get('trust_score'),'preliminary_score':pre,
              'canonical_key':p.get('canonical_key')
            })
    policies=collections.Counter()
    for row in context.get('programs',[]):policies[str(row.get('promotion_mode') or 'eligible')]+=1
    return {
      **stream_stats,
      'runtime_config_version':cfg.get('_version'),'runtime_profile_name':cfg.get('profile_name'),
      'commission_eligible_offers':offers,'unique_commission_eligible_products':unique_products,
      'commission_bands':dict(commission_bands),'top_eligible_merchants':merchants.most_common(50),
      'top_eligible_categories':categories.most_common(50),'merchant_program_policy_counts':dict(policies),
      'validated_pain_clusters_available_for_phase_b':len(context.get('pain_clusters',[])),
      'active_themes_available_for_phase_b':len(context.get('themes',[])),
      'policy':{
        'phase':'A deterministic read-only commercial scan','raw_feed_imported':False,'supabase_products_written':False,
        'minimum_product_price':None,'minimum_expected_commission_eur':v1.MIN_COMMISSION,
        'minimum_merchant_trust':v1.MIN_MERCHANT_TRUST,
        'dominant_merchant_offers':'excluded; merchant intelligence retained as Demand Beacon/RAG evidence',
        'commission_range_policy':'conservative minimum for automatic eligibility',
        'price_integrity':'no auto-scale; suspicious merchant price units quarantined before commission',
        'dynamic_saturation':'feed-share + post-commission candidate-share gates',
        'next_phase':'AI Product Research + RAG + independent Skeptic Audit before persistence'
      },'top_candidate_sample_count':len(top)
    },top


def main(feed):
    cfg=load_runtime_config(v1); apply_runtime_config(v1,cfg)
    context=v1.gateway('context')
    db,stream_stats=v1.stage_feed(feed,context)
    profile,top=summarize(db,stream_stats,context,cfg)
    OUT.write_text(json.dumps(profile,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    SAMPLE.write_text(json.dumps(top,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    save_run_profile(v1,'A',profile)
    print(json.dumps({'product_commercial_scan':profile},ensure_ascii=False,default=str),flush=True)
    db.close()


if __name__=='__main__':main(sys.argv[1] if len(sys.argv)>1 else os.getenv('PRODUCT_SOURCE_FEED','linkwise-products.json'))
