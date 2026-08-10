import json,datetime
from gateway import db_call

def clamp(v):return max(0.0,min(100.0,float(v)))
def latest_niche_run():
    rows=db_call('GET','niche_runs',params={'status':'eq.completed','select':'id','order':'created_at.desc','limit':'1'}) or []
    return rows[0]['id'] if rows else None

def page(resource,params,limit=1000):
    rows=[];offset=0
    while True:
        p=dict(params);p['limit']=str(limit);p['offset']=str(offset);part=db_call('GET',resource,params=p) or [];rows.extend(part)
        if len(part)<limit:break
        offset+=limit
    return rows

def decision(score,confidence):
    if score>=92 and confidence>=.78:return 'PRIORITY'
    if score>=85 and confidence>=.70:return 'CREATE_CREATIVE'
    if score>=75:return 'WATCHLIST'
    if score>=60:return 'MONITOR'
    return 'DROP'

def main():
    nr=latest_niche_run();niche_by_id={};product_niche={}
    if nr:
        niches=page('niche_candidates',{'run_id':f'eq.{nr}','select':'id,label,market_score,market_confidence,competition_kill,kill_reason,status'})
        niche_by_id={n['id']:n for n in niches}
        memberships=page('niche_product_memberships',{'run_id':f'eq.{nr}','select':'product_id,niche_id'})
        for m in memberships:product_niche[m['product_id']]=niche_by_id.get(m['niche_id'])
    products=page('products',{'hard_gate_pass':'eq.true','select':'id,is_preferred_offer,merchant_trust_score,merchant_name,canonical_group_key,duplicate_group_size'})
    pmap={p['id']:p for p in products}
    scores=page('opportunity_scores',{'select':'id,product_id,higo_raw,higo_adjusted,confidence,merchant_reliability_score,decision,competition_kill,explanation','order':'calculated_at.desc'})
    seen=set();updated=0;dropped_dup=0;dropped_niche=0
    for s in scores:
        pid=s.get('product_id')
        if not pid or pid in seen:continue
        seen.add(pid);p=pmap.get(pid)
        if not p:continue
        conf=float(s.get('confidence') or 0);raw=float(s.get('higo_raw') or 0);old_merchant=float(s.get('merchant_reliability_score') or 80);trust=float(p.get('merchant_trust_score') or old_merchant or 60)
        explanation=s.get('explanation') or {};explanation['merchant_resolution']={'merchant':p.get('merchant_name'),'trust_score':round(trust,2),'preferred_offer':bool(p.get('is_preferred_offer')),'duplicate_group_size':p.get('duplicate_group_size'),'canonical_group_key':p.get('canonical_group_key')}
        if not p.get('is_preferred_offer',True):
            db_call('PATCH','opportunity_scores',params={'id':f"eq.{s['id']}"},data={'merchant_reliability_score':round(trust,2),'higo_adjusted':0,'decision':'DROP','skeptic_status':'duplicate_nonpreferred','explanation':{**explanation,'final_kill':'duplicate_nonpreferred_offer'}});dropped_dup+=1;updated+=1;continue
        merchant_raw=clamp(raw-old_merchant*.04+trust*.04);n=product_niche.get(pid)
        if n and n.get('competition_kill'):
            db_call('PATCH','opportunity_scores',params={'id':f"eq.{s['id']}"},data={'merchant_reliability_score':round(trust,2),'higo_raw':round(merchant_raw,2),'higo_adjusted':0,'decision':'DROP','competition_kill':True,'skeptic_status':'niche_competition_kill','explanation':{**explanation,'niche':{'label':n.get('label'),'market_score':n.get('market_score'),'kill_reason':n.get('kill_reason')},'final_kill':'micro_niche_high_competition'}});dropped_niche+=1;updated+=1;continue
        if n and n.get('market_score') is not None:
            nscore=float(n.get('market_score') or 0);nconf=float(n.get('market_confidence') or .5);refined_raw=clamp(merchant_raw*.80+nscore*.20);ref_conf=min(1.0,conf*.80+nconf*.20);adjusted=clamp(refined_raw-(1-ref_conf)*20);final_decision=decision(adjusted,ref_conf);explanation['niche']={'label':n.get('label'),'market_score':nscore,'market_confidence':nconf,'weight':.20}
        else:
            refined_raw=merchant_raw;ref_conf=conf;adjusted=clamp(refined_raw-(1-ref_conf)*20);final_decision=decision(adjusted,ref_conf);explanation['niche']={'available':False}
        db_call('PATCH','opportunity_scores',params={'id':f"eq.{s['id']}"},data={'merchant_reliability_score':round(trust,2),'higo_raw':round(refined_raw,2),'higo_adjusted':round(adjusted,2),'confidence':round(ref_conf,4),'decision':final_decision,'explanation':explanation});updated+=1
    print(json.dumps({'updated':updated,'dropped_duplicate_offers':dropped_dup,'dropped_by_niche_competition':dropped_niche,'niche_run':nr},ensure_ascii=False))
if __name__=='__main__':main()
