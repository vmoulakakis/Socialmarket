import re,math,unicodedata,datetime,statistics
from collections import defaultdict,Counter
from rapidfuzz.fuzz import token_set_ratio
from gateway import db_call

MIN_VALIDITY_DAYS=20

def fold(v):
    s=str(v or '').lower().strip()
    return ''.join(c for c in unicodedata.normalize('NFKD',s) if not unicodedata.combining(c))
def norm(v): return re.sub(r'[^a-z0-9]+',' ',fold(v)).strip()
def compact(v): return re.sub(r'[^a-z0-9]+','',fold(v))
def nums(v): return tuple(re.findall(r'\d+(?:[.,]\d+)?',fold(v)))
def clamp(v): return max(0.0,min(100.0,float(v)))
def today(): return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3))).date()
def valid_days(v):
    if not v:return -999
    try:return (datetime.datetime.fromisoformat(str(v).replace('Z','+00:00')).date()-today()).days
    except:return -999

def fetch_products():
    rows=[];offset=0;limit=1000
    while True:
        part=db_call('GET','products',params={'hard_gate_pass':'eq.true','travel_related':'eq.false','price':'gte.150','select':'id,brand_name,model_name,product_name,category_raw,merchant_name,price,full_price,discount_pct,times_bought,tracking_url,image_url,thumb_url,extra_images,in_stock,valid_to,validity_days_remaining,size,colour','order':'category_raw.asc','limit':str(limit),'offset':str(offset)}) or []
        rows.extend(part)
        if len(part)<limit:break
        offset+=limit
    return [p for p in rows if valid_days(p.get('valid_to'))>MIN_VALIDITY_DAYS]

def strong_key(p):
    brand=compact(p.get('brand_name'));model=compact(p.get('model_name'));size=compact(p.get('size'));colour=compact(p.get('colour'))
    if brand and model and len(model)>=3:return f'm|{brand}|{model}|{size}|{colour}'
    title=norm(p.get('product_name'));cat=compact(p.get('category_raw'))
    if brand and title:return f'n|{brand}|{cat}|{title}|{size}|{colour}'
    return f'u|{cat}|{title}|{size}|{colour}'

def compatible(a,b):
    if compact(a.get('brand_name'))!=compact(b.get('brand_name')):return False
    if compact(a.get('category_raw'))!=compact(b.get('category_raw')):return False
    for k in ('size','colour'):
        av,bv=compact(a.get(k)),compact(b.get(k))
        if av and bv and av!=bv:return False
    na,nb=nums(a.get('product_name')),nums(b.get('product_name'))
    if na and nb and na!=nb:return False
    pa,pb=float(a.get('price') or 0),float(b.get('price') or 0)
    if pa and pb and max(pa,pb)/max(1,min(pa,pb))>1.35:return False
    return token_set_ratio(norm(a.get('product_name')),norm(b.get('product_name')))>=97

def identity_groups(products):
    exact=defaultdict(list)
    for p in products:exact[strong_key(p)].append(p)
    groups=[];single=[]
    for k,rows in exact.items():
        if len(rows)>1:groups.append((k,rows,'exact-identity',.99))
        else:single.append(rows[0])
    blocks=defaultdict(list)
    for p in single:blocks[(compact(p.get('brand_name')),compact(p.get('category_raw')),nums(p.get('product_name'))) ].append(p)
    used=set()
    for _,rows in blocks.items():
        for i,a in enumerate(rows):
            if a['id'] in used:continue
            grp=[a];used.add(a['id'])
            if len(rows)<=200:
                for b in rows[i+1:]:
                    if b['id'] not in used and compatible(a,b):grp.append(b);used.add(b['id'])
            key='f|'+compact(a.get('brand_name'))+'|'+compact(a.get('category_raw'))+'|'+compact(a.get('product_name'))[:80]
            groups.append((key,grp,'strict-fuzzy' if len(grp)>1 else 'unique',.96 if len(grp)>1 else 1.0))
    return groups

def merchant_base_stats(products):
    by=defaultdict(list)
    for p in products:by[p.get('merchant_name') or 'Unknown'].append(p)
    result={}
    for m,rows in by.items():
        n=len(rows);tracking=sum(bool(x.get('tracking_url')) for x in rows)/n;image=sum(bool(x.get('image_url') or x.get('thumb_url')) for x in rows)/n;stock=sum(x.get('in_stock') is not False for x in rows)/n;valid=sum(valid_days(x.get('valid_to'))>20 for x in rows)/n
        complete=sum(bool(x.get('brand_name')) and bool(x.get('product_name')) and bool(x.get('category_raw')) for x in rows)/n
        purchase=[math.log1p(float(x.get('times_bought') or 0)) for x in rows];purchase_signal=min(1.0,(sum(purchase)/max(1,n))/5)
        base=100*(tracking*.20+image*.15+stock*.15+valid*.15+complete*.15+purchase_signal*.20)
        confidence=.45+.55*(1-math.exp(-n/25))
        result[m]={'rows':n,'tracking':tracking,'image':image,'stock':stock,'validity':valid,'complete':complete,'purchase_signal':purchase_signal,'base':base,'confidence':confidence}
    return result

def add_price_reliability(groups,stats):
    outliers=Counter();seen=Counter()
    for _,rows,_,_ in groups:
        if len(rows)<2:continue
        prices=[float(x.get('price') or 0) for x in rows if float(x.get('price') or 0)>0]
        if not prices:continue
        med=statistics.median(prices)
        for p in rows:
            m=p.get('merchant_name') or 'Unknown';price=float(p.get('price') or 0);seen[m]+=1
            if price and abs(price-med)/max(1,med)>.30:outliers[m]+=1
    for m,s in stats.items():
        ratio=outliers[m]/max(1,seen[m]);s['price_outlier_ratio']=ratio;s['trust']=clamp(s['base']*.85+(1-ratio)*100*.15)

def offer_score(p,trust,median_price,max_times):
    price=float(p.get('price') or 0);distance=abs(price-median_price)/max(1,median_price) if median_price else 0;price_reason=clamp(100-distance*220)
    runway=clamp((valid_days(p.get('valid_to'))-20)/70*100);purchase=clamp(100*math.log1p(float(p.get('times_bought') or 0))/max(1,math.log1p(max_times))) if max_times else 0
    image=100 if p.get('image_url') else 80 if p.get('thumb_url') else 0
    return trust*.60+price_reason*.15+runway*.10+purchase*.10+image*.05,{'merchant_trust':round(trust,2),'price_reasonableness':round(price_reason,2),'validity_runway':round(runway,2),'purchase_signal':round(purchase,2),'image_score':image}

def main():
    products=fetch_products();groups=identity_groups(products);stats=merchant_base_stats(products);add_price_reliability(groups,stats)
    wins=Counter();updates=[];identity_rows=[]
    for key,rows,method,match_conf in groups:
        prices=[float(x.get('price') or 0) for x in rows if float(x.get('price') or 0)>0];med=statistics.median(prices) if prices else 0;max_times=max([float(x.get('times_bought') or 0) for x in rows] or [0])
        ranked=[]
        for p in rows:
            m=p.get('merchant_name') or 'Unknown';trust=stats[m]['trust'];score,parts=offer_score(p,trust,med,max_times);ranked.append((score,p,parts))
        ranked.sort(key=lambda x:x[0],reverse=True);winner=ranked[0][1];wins[winner.get('merchant_name') or 'Unknown']+=1
        identity_rows.append({'canonical_group_key':key,'canonical_name':winner.get('product_name'),'brand_name':winner.get('brand_name'),'model_name':winner.get('model_name'),'category_raw':winner.get('category_raw'),'offer_count':len(rows),'preferred_product_id':winner['id'],'matching_method':method,'match_confidence':match_conf,'evidence':{'merchant_count':len(set((x.get('merchant_name') or 'Unknown') for x in rows)),'median_price':med}})
        winner_score=ranked[0][0]
        for score,p,parts in ranked:
            m=p.get('merchant_name') or 'Unknown';updates.append({'id':p['id'],'canonical_group_key':key,'merchant_trust_score':round(stats[m]['trust'],2),'is_preferred_offer':p['id']==winner['id'],'duplicate_group_size':len(rows),'offer_selection_reason':{'selected':p['id']==winner['id'],'offer_score':round(score,2),'winner_score':round(winner_score,2),'components':parts,'matching_method':method,'match_confidence':match_conf,'rule':'merchant trust is primary; cheapest offer does not automatically win'}})
    for m,s in stats.items():
        s['win_rate']=wins[m]/max(1,s['rows'])
        payload={'merchant_name':m,'trust_score':round(s['trust'],2),'trust_confidence':round(s['confidence'],4),'active_offer_count':s['rows'],'valid_tracking_ratio':round(s['tracking'],4),'image_quality_ratio':round(s['image'],4),'stock_reliability_ratio':round(s['stock'],4),'validity_reliability_ratio':round(s['validity'],4),'price_outlier_ratio':round(s.get('price_outlier_ratio',0),4),'duplicate_win_rate':round(s['win_rate'],4),'evidence':{'data_completeness':round(s['complete'],4),'purchase_signal':round(s['purchase_signal'],4),'method':'internal-offer-evidence-v1'}}
        db_call('POST','merchant_profiles',params={'on_conflict':'merchant_name'},data=payload,prefer='resolution=merge-duplicates,return=minimal')
    for start in range(0,len(identity_rows),200):db_call('POST','product_identity_groups',params={'on_conflict':'canonical_group_key'},data=identity_rows[start:start+200],prefer='resolution=merge-duplicates,return=minimal')
    for start in range(0,len(updates),500):db_call('POST','rpc/apply_product_identity_updates',data={'updates':updates[start:start+500]})
    print({'products':len(products),'identity_groups':len(groups),'duplicate_groups':sum(len(r)>1 for _,r,_,_ in groups),'merchants':len(stats),'preferred_offers':len(groups)})

if __name__=='__main__':main()
