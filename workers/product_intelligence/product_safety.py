import collections
import json
import os
import random
from pathlib import Path

import ijson

PRICE_SAMPLE_PER_MERCHANT=max(20,int(os.getenv('PRODUCT_PRICE_SAMPLE_PER_MERCHANT','400')))
PRICE_MIN_SAMPLE=max(5,int(os.getenv('PRODUCT_PRICE_MIN_SAMPLE','20')))
PRICE_INTEGER_RATIO_RISK=float(os.getenv('PRODUCT_PRICE_INTEGER_RATIO_RISK','0.97'))
PRICE_MINOR_RISK_MEDIAN=float(os.getenv('PRODUCT_PRICE_MINOR_RISK_MEDIAN','1200'))
PRICE_MINOR_RISK_P90=float(os.getenv('PRODUCT_PRICE_MINOR_RISK_P90','3000'))
PRICE_HIGH_VALUE_UNVERIFIED=float(os.getenv('PRODUCT_PRICE_HIGH_VALUE_UNVERIFIED','1000'))

MAX_MERCHANT_FEED_SHARE=float(os.getenv('PRODUCT_MAX_MERCHANT_FEED_SHARE','0.08'))
SECONDARY_FEED_SHARE=float(os.getenv('PRODUCT_SECONDARY_FEED_SHARE','0.03'))
FEED_COMPETITION_GATE=float(os.getenv('PRODUCT_FEED_COMPETITION_GATE','85'))

MAX_ELIGIBLE_MERCHANT_SHARE=float(os.getenv('PRODUCT_MAX_ELIGIBLE_MERCHANT_SHARE','0.12'))
SECONDARY_ELIGIBLE_SHARE=float(os.getenv('PRODUCT_SECONDARY_ELIGIBLE_SHARE','0.06'))
ELIGIBLE_COMPETITION_GATE=float(os.getenv('PRODUCT_ELIGIBLE_COMPETITION_GATE','80'))
ELIGIBLE_ABSOLUTE_COUNT=max(1000,int(os.getenv('PRODUCT_ELIGIBLE_ABSOLUTE_COUNT','50000')))
ELIGIBLE_ABSOLUTE_COMPETITION=float(os.getenv('PRODUCT_ELIGIBLE_ABSOLUTE_COMPETITION','70'))

SAFETY_PROFILE_PATH=Path(os.getenv('PRODUCT_SAFETY_PROFILE_PATH','product-feed-safety-profile.json'))


def _pct(sorted_values,q):
    if not sorted_values:
        return None
    idx=max(0,min(len(sorted_values)-1,int(round((len(sorted_values)-1)*q))))
    return float(sorted_values[idx])


def _integerish(value):
    return abs(float(value)-round(float(value))) < 1e-9


def classify_price_sample(values):
    vals=sorted(float(x) for x in values if x is not None and float(x)>0)
    n=len(vals)
    if not n:
        return {'status':'no_price_evidence','sample_count':0,'confidence':0.0}
    integer_ratio=sum(1 for x in vals if _integerish(x))/n
    median=_pct(vals,0.50)
    p90=_pct(vals,0.90)
    risk=(
        n>=PRICE_MIN_SAMPLE
        and integer_ratio>=PRICE_INTEGER_RATIO_RISK
        and (median or 0)>=PRICE_MINOR_RISK_MEDIAN
        and (p90 or 0)>=PRICE_MINOR_RISK_P90
    )
    status='minor_unit_risk' if risk else ('major_unit_probable' if n>=PRICE_MIN_SAMPLE else 'limited_evidence')
    confidence=min(0.98,0.45+min(n,PRICE_SAMPLE_PER_MERCHANT)/PRICE_SAMPLE_PER_MERCHANT*0.50)
    return {
        'status':status,
        'sample_count':n,
        'median':round(median,4) if median is not None else None,
        'p90':round(p90,4) if p90 is not None else None,
        'integer_ratio':round(integer_ratio,4),
        'confidence':round(confidence,3),
        'policy':'never auto-divide by 100; quarantine statistically suspicious merchant price scales',
    }


def build_feed_safety_profile(feed,context,iter_records,normalize,resolve_merchant,merchant_maps):
    """Read-only first pass that profiles merchant share and price-scale risk."""
    by_program,aliases,by_domain=merchant_maps(context)
    counts=collections.Counter()
    resolution=collections.Counter()
    price_seen=collections.Counter()
    samples=collections.defaultdict(list)
    rng=random.Random(20260815)
    seen=resolved=0
    truncated=False

    iterator=iter_records(feed)
    while True:
        try:
            raw=next(iterator)
        except StopIteration:
            break
        except ijson.common.IncompleteJSONError:
            truncated=True
            break
        seen+=1
        product=normalize(raw)
        merchant,method=resolve_merchant(product,by_program,aliases,by_domain)
        if not merchant:
            continue
        resolved+=1
        resolution[method]+=1
        mid=str(merchant.get('merchant_id'))
        counts[mid]+=1
        price=float(product.get('price') or 0)
        if price>0 and str(product.get('currency') or 'EUR').upper()=='EUR':
            price_seen[mid]+=1
            arr=samples[mid]
            if len(arr)<PRICE_SAMPLE_PER_MERCHANT:
                arr.append(price)
            else:
                j=rng.randint(0,price_seen[mid]-1)
                if j<PRICE_SAMPLE_PER_MERCHANT:
                    arr[j]=price
        if seen%500000==0:
            print(json.dumps({'phase':'safety_profile','seen':seen,'resolved':resolved}),flush=True)

    by_mid={str(row.get('merchant_id')):row for row in context.get('programs',[])}
    merchants={}
    for mid,count in counts.items():
        row=by_mid.get(mid,{})
        share=(count/resolved) if resolved else 0.0
        competition=float(row.get('competition_score') or 50)
        saturated=(
            share>=MAX_MERCHANT_FEED_SHARE
            or (share>=SECONDARY_FEED_SHARE and competition>=FEED_COMPETITION_GATE)
        )
        merchants[mid]={
            'merchant_id':mid,
            'merchant_name':row.get('canonical_name'),
            'official_domain':row.get('official_domain'),
            'resolved_records':int(count),
            'resolved_feed_share':round(share,6),
            'competition_score':competition,
            'feed_saturated':saturated,
            'feed_saturation_reason':(
                'feed_share'
                if share>=MAX_MERCHANT_FEED_SHARE
                else ('feed_share_plus_competition' if saturated else None)
            ),
            'price_integrity':classify_price_sample(samples.get(mid,[])),
        }

    profile={
        'records_seen':seen,
        'resolved_records':resolved,
        'truncated_tail':truncated,
        'resolution_methods':resolution.most_common(),
        'thresholds':{
            'max_merchant_feed_share':MAX_MERCHANT_FEED_SHARE,
            'secondary_feed_share':SECONDARY_FEED_SHARE,
            'feed_competition_gate':FEED_COMPETITION_GATE,
            'price_integer_ratio_risk':PRICE_INTEGER_RATIO_RISK,
            'price_minor_risk_median':PRICE_MINOR_RISK_MEDIAN,
            'price_minor_risk_p90':PRICE_MINOR_RISK_P90,
        },
        'merchants':merchants,
    }
    SAFETY_PROFILE_PATH.write_text(json.dumps(profile,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    return profile


def price_integrity_allows(price,merchant_safety):
    info=(merchant_safety or {}).get('price_integrity') or {'status':'no_price_evidence','confidence':0}
    status=info.get('status')
    if status in ('minor_unit_risk','no_price_evidence'):
        return False,'price_scale_unverified',info
    if status=='limited_evidence' and price>=PRICE_HIGH_VALUE_UNVERIFIED and _integerish(price):
        return False,'price_scale_insufficient_evidence_high_value',info
    return True,'price_major_unit_probable',info


def prune_dynamic_candidate_saturation(db,reasons):
    rows=db.execute(
        'select merchant_id,max(merchant_name),max(competition_score),count(*) '
        'from candidates group by merchant_id'
    ).fetchall()
    total=sum(int(row[3]) for row in rows)
    removed=[]
    removed_count=0
    for mid,name,competition,count in rows:
        share=(count/total) if total else 0.0
        competition=float(competition or 50)
        saturated=(
            share>=MAX_ELIGIBLE_MERCHANT_SHARE
            or (share>=SECONDARY_ELIGIBLE_SHARE and competition>=ELIGIBLE_COMPETITION_GATE)
            or (count>=ELIGIBLE_ABSOLUTE_COUNT and competition>=ELIGIBLE_ABSOLUTE_COMPETITION)
        )
        if not saturated:
            continue
        db.execute('delete from candidates where merchant_id=?',(mid,))
        removed_count+=int(count)
        removed.append({
            'merchant_id':mid,
            'merchant_name':name,
            'candidate_count':int(count),
            'candidate_share':round(share,6),
            'competition_score':competition,
        })
    if removed_count:
        reasons['dynamic_candidate_saturation']+=removed_count
        db.commit()
    removed.sort(key=lambda x:x['candidate_count'],reverse=True)
    return removed_count,removed
