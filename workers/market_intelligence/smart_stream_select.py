import os,json,math,heapq,collections,datetime
from pathlib import Path
import requests,ijson
from stream_feed import iter_records,normalize

MIN_PRICE=float(os.getenv('MIN_PRICE_EUR','100'))
MIN_VALIDITY_DAYS=int(os.getenv('MIN_VALIDITY_DAYS','20'))
GLOBAL_POOL=int(os.getenv('STREAM_GLOBAL_POOL','25000'))
PER_CATEGORY=int(os.getenv('STREAM_PER_CATEGORY_POOL','40'))
MAX_FINAL_POOL=int(os.getenv('STREAM_MAX_CANDIDATE_POOL','35000'))


def clamp(v,lo=0,hi=100): return max(lo,min(hi,float(v)))
def source_records(source):
    if str(source).startswith(('http://','https://')):
        with requests.get(source,stream=True,timeout=(30,900),headers={'Accept-Encoding':'gzip, deflate','User-Agent':'SocialMarketAI/1.0'}) as r:
            r.raise_for_status();r.raw.decode_content=True
            count=0
            for item in ijson.items(r.raw,'item'):
                if isinstance(item,dict):count+=1;yield item
            if count==0:raise RuntimeError('Linkwise stream returned no top-level product objects')
    else:
        yield from iter_records(source)
def score_candidate(p):
    times=max(0,float(p.get('times_bought') or 0));discount=max(0,float(p.get('discount_pct') or 0));days=max(0,float(p.get('validity_days_remaining') or 0));price=max(MIN_PRICE,float(p.get('price') or MIN_PRICE))
    purchase=clamp(18*math.log1p(times));disc=clamp(discount*2.2)
    runway=40 if days<=30 else 65 if days<=60 else 85 if days<=90 else 100
    data=35+15*bool(p.get('brand_name'))+15*bool(p.get('model_name'))+20*bool(p.get('description'))+15*bool(p.get('category_raw'))
    image=100 if p.get('image_url') and p.get('extra_images') else 85 if p.get('image_url') else 70
    price_score=clamp(45+18*math.log(max(1,price/MIN_PRICE)))
    return clamp(purchase*.32+disc*.20+runway*.15+data*.12+image*.10+price_score*.11)
def compact(p,pre):
    q={k:p.get(k) for k in ('external_product_id','product_name','model_name','description','brand_name','program_name','merchant_name','category_raw','price','full_price','discount_pct','currency','in_stock','availability','valid_from','valid_to','validity_days_remaining','validity_runway_score','times_bought','tracking_url','image_url','thumb_url','extra_images','colour','size','city','longitude','latitude','address','on_sale','is_active','hard_gate_pass','travel_related','market_eligible','market_exclusion_reason','eligibility_reason')}
    if q.get('description'): q['description']=q['description'][:1400]
    q['extra_images']=(q.get('extra_images') or [])[:4];q['_pre_score']=round(pre,3);return q
def push(heap,item,limit,seq):
    row=(item['_pre_score'],seq,item)
    if len(heap)<limit:heapq.heappush(heap,row)
    elif row[0]>heap[0][0]:heapq.heapreplace(heap,row)
def main(source):
    global_heap=[];category_heaps=collections.defaultdict(list);merchant=collections.defaultdict(lambda:{'seen':0,'eligible':0,'times':0.0,'price_sum':0.0,'categories':collections.Counter()});category=collections.defaultdict(lambda:{'eligible':0,'times':0.0,'merchants':collections.Counter(),'brands':collections.Counter()});reasons=collections.Counter();seen=eligible=0;seq=0
    for raw in source_records(source):
        seen+=1;seq+=1;p=normalize(raw);m=p.get('merchant_name') or p.get('program_name') or 'Unknown';ms=merchant[m];ms['seen']+=1
        if not p.get('hard_gate_pass'):
            for rr in (p.get('eligibility_reason') or {}).get('reasons',[]):reasons[rr]+=1
            if seen%250000==0:print(json.dumps({'seen':seen,'eligible':eligible,'pool':len(global_heap)}),flush=True)
            continue
        eligible+=1;cat=p.get('category_raw') or 'Uncategorized';pre=score_candidate(p);q=compact(p,pre)
        ms['eligible']+=1;ms['times']+=float(p.get('times_bought') or 0);ms['price_sum']+=float(p.get('price') or 0);ms['categories'][cat]+=1
        cs=category[cat];cs['eligible']+=1;cs['times']+=float(p.get('times_bought') or 0);cs['merchants'][m]+=1
        if p.get('brand_name'):cs['brands'][p['brand_name']]+=1
        push(global_heap,q,GLOBAL_POOL,seq);push(category_heaps[cat],q,PER_CATEGORY,seq)
        if seen%250000==0:print(json.dumps({'seen':seen,'eligible':eligible,'global_pool':len(global_heap),'categories':len(category)}),flush=True)
    union={}
    for _,_,p in global_heap:union[p['external_product_id']]=p
    for h in category_heaps.values():
        for _,_,p in h:union[p['external_product_id']]=p
    ranked=[]
    for p in union.values():
        c=category[p.get('category_raw') or 'Uncategorized']['eligible'];bonus=clamp(10/math.sqrt(max(1,c/50)),0,10);p['_stream_score']=round(clamp(p['_pre_score']+bonus),3);ranked.append(p)
    ranked.sort(key=lambda x:x['_stream_score'],reverse=True);ranked=ranked[:MAX_FINAL_POOL]
    with open('candidate-pool.jsonl','w',encoding='utf-8') as f:
        for p in ranked:f.write(json.dumps(p,ensure_ascii=False,default=str)+'\n')
    merchant_out={m:{'seen':s['seen'],'eligible':s['eligible'],'total_times_bought':round(s['times'],2),'avg_price':round(s['price_sum']/max(1,s['eligible']),2),'category_count':len(s['categories']),'top_categories':s['categories'].most_common(12),'eligible_share':s['eligible']/max(1,eligible)} for m,s in merchant.items() if s['eligible']}
    category_out={c:{'eligible':s['eligible'],'total_times_bought':round(s['times'],2),'merchant_count':len(s['merchants']),'brand_count':len(s['brands']),'top_merchants':s['merchants'].most_common(12)} for c,s in category.items()}
    Path('merchant-stream-stats.json').write_text(json.dumps(merchant_out,ensure_ascii=False),encoding='utf-8');Path('category-stream-stats.json').write_text(json.dumps(category_out,ensure_ascii=False),encoding='utf-8')
    profile={'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'records_seen':seen,'eligible_after_hard_gates':eligible,'candidate_pool':len(ranked),'min_price_eur':MIN_PRICE,'min_validity_days':MIN_VALIDITY_DAYS,'excluded_reasons':reasons.most_common(),'merchant_count':len(merchant_out),'category_count':len(category_out),'method':'direct-linkwise-http-ijson-bounded-stream-v2'}
    Path('stream-profile.json').write_text(json.dumps(profile,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(profile,ensure_ascii=False))
if __name__=='__main__':
    import sys
    main(sys.argv[1] if len(sys.argv)>1 else os.environ.get('SOURCE_FEED_URL','linkwise-products.json'))
