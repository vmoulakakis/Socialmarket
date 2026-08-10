import math,statistics,json,datetime
from collections import defaultdict
from gateway import db_call

MIN_TRUST=55

def clamp(v):return max(0.0,min(100.0,float(v)))
def valid_days(v):
    if not v:return -999
    try:return (datetime.datetime.fromisoformat(str(v).replace('Z','+00:00')).date()-datetime.datetime.now(datetime.timezone.utc).date()).days
    except:return -999

def fetch_profiles():
    rows=db_call('GET','merchant_profiles',params={'select':'merchant_name,trust_score,trust_confidence,external_reputation_confidence,external_risk_flag,external_risk_reason','limit':'1000'}) or []
    return {r['merchant_name']:r for r in rows}

def fetch_products():
    rows=[];offset=0;limit=1000
    while True:
        part=db_call('GET','products',params={'hard_gate_pass':'eq.true','travel_related':'eq.false','select':'id,canonical_group_key,merchant_name,product_name,price,full_price,discount_pct,times_bought,valid_to,image_url,thumb_url,market_eligible,offer_selection_reason','order':'canonical_group_key.asc','limit':str(limit),'offset':str(offset)}) or []
        rows.extend(part)
        if len(part)<limit:break
        offset+=limit
    return rows

def score_offer(p,profile,median,max_times):
    trust=float(profile.get('trust_score') or 50);price=float(p.get('price') or 0);dist=abs(price-median)/max(1,median) if median else 0;price_reason=clamp(100-dist*220)
    runway=clamp((valid_days(p.get('valid_to'))-20)/70*100);purchase=clamp(100*math.log1p(float(p.get('times_bought') or 0))/max(1,math.log1p(max_times))) if max_times else 0;image=100 if p.get('image_url') else 80 if p.get('thumb_url') else 0
    return trust*.68+price_reason*.12+runway*.08+purchase*.08+image*.04,{'merchant_trust':round(trust,2),'price_reasonableness':round(price_reason,2),'validity_runway':round(runway,2),'purchase_signal':round(purchase,2),'image_score':image}

def main():
    profiles=fetch_profiles();products=fetch_products();groups=defaultdict(list)
    for p in products:groups[p.get('canonical_group_key') or f"unique|{p['id']}"] .append(p)
    updates=[];selected=0;blocked=0
    for key,rows in groups.items():
        prices=[float(p.get('price') or 0) for p in rows if float(p.get('price') or 0)>0];median=statistics.median(prices) if prices else 0;max_times=max([float(p.get('times_bought') or 0) for p in rows] or [0]);ranked=[]
        for p in rows:
            prof=profiles.get(p.get('merchant_name') or '',{});risk=bool(prof.get('external_risk_flag'));trust=float(prof.get('trust_score') or p.get('merchant_trust_score') or 50);score,parts=score_offer(p,prof,median,max_times);ranked.append((score,p,prof,parts,risk,trust))
        safe=[r for r in ranked if not r[4] and r[5]>=MIN_TRUST]
        if not safe:
            blocked+=1
            for score,p,prof,parts,risk,trust in ranked:
                updates.append({'id':p['id'],'merchant_trust_score':round(trust,2),'is_preferred_offer':False,'offer_selection_reason':{'selected':False,'final_offer_score':round(score,2),'components':parts,'external_risk_flag':risk,'rule':'No trusted merchant passed final threshold'},'market_eligible':False,'market_exclusion_reason':'no_trusted_merchant_offer'})
            continue
        safe.sort(key=lambda r:r[0],reverse=True);winner=safe[0][1]['id'];selected+=1
        for score,p,prof,parts,risk,trust in ranked:
            iswin=p['id']==winner
            updates.append({'id':p['id'],'merchant_trust_score':round(trust,2),'is_preferred_offer':iswin,'offer_selection_reason':{'selected':iswin,'final_offer_score':round(score,2),'components':parts,'external_risk_flag':risk,'external_reputation_confidence':prof.get('external_reputation_confidence'),'rule':'Merchant trust dominates; price is secondary; externally risky merchants cannot win'},'market_eligible':bool(iswin and p.get('market_eligible') is not False),'market_exclusion_reason':None if iswin else ('external_merchant_risk' if risk else 'duplicate_nonpreferred_offer')})
    for start in range(0,len(updates),400):db_call('POST','rpc/apply_final_offer_updates',data={'updates':updates[start:start+400]})
    print(json.dumps({'identity_groups':len(groups),'preferred_offers':selected,'blocked_groups':blocked,'updates':len(updates)}))

if __name__=='__main__':main()
