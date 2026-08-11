import os,json,re,math,unicodedata,statistics,collections
from rapidfuzz.fuzz import token_set_ratio

MAX_FINAL=int(os.getenv('FINAL_PRODUCT_LIMIT','1000'))
MAX_PER_MERCHANT=int(os.getenv('FINAL_MAX_PER_MERCHANT','80'))
MAX_PER_CATEGORY=int(os.getenv('FINAL_MAX_PER_CATEGORY','120'))
MAX_PER_BRAND=int(os.getenv('FINAL_MAX_PER_BRAND','100'))
MIN_FINAL_SCORE=float(os.getenv('FINAL_MIN_SCORE','48'))

def clamp(v,lo=0,hi=100):return max(lo,min(hi,float(v)))
def fold(v):
    s=str(v or '').lower();return ''.join(c for c in unicodedata.normalize('NFKD',s) if not unicodedata.combining(c))
def compact(v):return re.sub(r'[^a-z0-9]+','',fold(v))
def norm(v):return re.sub(r'[^a-z0-9]+',' ',fold(v)).strip()
def nums(v):return tuple(re.findall(r'\d+(?:[.,]\d+)?',fold(v)))
def strong_key(p):
    b=compact(p.get('brand_name'));m=compact(p.get('model_name'));s=compact(p.get('size'));c=compact(p.get('colour'));cat=compact(p.get('category_raw'))
    if b and m and len(m)>=3:return f'm|{b}|{m}|{s}|{c}'
    return f'n|{b}|{cat}|{compact(p.get("product_name"))}|{s}|{c}'
def compatible(a,b):
    if compact(a.get('brand_name'))!=compact(b.get('brand_name')):return False
    if compact(a.get('category_raw'))!=compact(b.get('category_raw')):return False
    for k in ('size','colour'):
        x,y=compact(a.get(k)),compact(b.get(k))
        if x and y and x!=y:return False
    na,nb=nums(a.get('product_name')),nums(b.get('product_name'))
    if na and nb and na!=nb:return False
    return token_set_ratio(norm(a.get('product_name')),norm(b.get('product_name')))>=97

def category_saturation(c):
    merchants=float(c.get('merchant_count') or 0);offers=float(c.get('eligible') or 0);brands=float(c.get('brand_count') or 0)
    return clamp(22*math.log1p(merchants)+10*math.log1p(max(0,offers/30))+8*math.log1p(brands))
def candidate_score(p,mr,cat):
    stream=float(p.get('_stream_score') or p.get('_pre_score') or 0);merchant=float(mr.get('merchant_suitability') or 50);opportunity=100-category_saturation(cat)
    return clamp(stream*.46+merchant*.34+opportunity*.20),opportunity

def dedupe(rows):
    exact=collections.defaultdict(list)
    for p in rows:exact[strong_key(p)].append(p)
    groups=[];single=[]
    for k,rs in exact.items():
        if len(rs)>1:groups.append((k,rs,'exact'))
        else:single.append(rs[0])
    blocks=collections.defaultdict(list)
    for p in single:blocks[(compact(p.get('brand_name')),compact(p.get('category_raw')),nums(p.get('product_name')))].append(p)
    used=set()
    for _,rs in blocks.items():
        rs=sorted(rs,key=lambda x:x['_final_base'],reverse=True)
        for i,a in enumerate(rs):
            if a['external_product_id'] in used:continue
            grp=[a];used.add(a['external_product_id'])
            if len(rs)<=120:
                for b in rs[i+1:]:
                    if b['external_product_id'] not in used and compatible(a,b):grp.append(b);used.add(b['external_product_id'])
            groups.append((strong_key(a),grp,'strict-fuzzy' if len(grp)>1 else 'unique'))
    return groups

def main():
    merchants=json.load(open('merchant-pool-research.json',encoding='utf-8'));cats=json.load(open('category-stream-stats.json',encoding='utf-8'))
    rows=[];killed_risk=killed_mega=0
    with open('candidate-pool.jsonl',encoding='utf-8') as f:
        for line in f:
            p=json.loads(line);m=p.get('merchant_name') or p.get('program_name') or 'Unknown';mr=merchants.get(m,{})
            if mr.get('risk_flag'):killed_risk+=1;continue
            if mr.get('mega_visibility_kill'):killed_mega+=1;continue
            base,catopp=candidate_score(p,mr,cats.get(p.get('category_raw') or 'Uncategorized',{}));p['_final_base']=round(base,3);p['_category_opportunity']=round(catopp,3);p['_merchant_research']=mr;rows.append(p)
    groups=dedupe(rows);winners=[]
    for key,offers,method in groups:
        prices=[float(x.get('price') or 0) for x in offers if float(x.get('price') or 0)>0];med=statistics.median(prices) if prices else 0
        ranked=[]
        for p in offers:
            mr=p['_merchant_research'];price=float(p.get('price') or 0);price_reason=clamp(100-abs(price-med)/max(1,med)*180) if med else 70
            offer=clamp(p['_final_base']*.55+float(mr.get('trust_score') or 50)*.35+price_reason*.10);ranked.append((offer,p,price_reason))
        ranked.sort(key=lambda x:x[0],reverse=True);offer,p,price_reason=ranked[0];p['canonical_group_key']=key;p['duplicate_group_size']=len(offers);p['is_preferred_offer']=True;p['merchant_trust_score']=round(float(p['_merchant_research'].get('trust_score') or 50),2);p['_rank_score']=round(offer,3);p['offer_selection_reason']={'method':method,'duplicate_offers':len(offers),'merchant_trust':p['merchant_trust_score'],'merchant_visibility_penalty':p['_merchant_research'].get('visibility_penalty'),'merchant_suitability':p['_merchant_research'].get('merchant_suitability'),'category_opportunity':p['_category_opportunity'],'price_reasonableness':round(price_reason,2),'rule':'trusted merchant + low visibility/competition + product quality; cheapest does not automatically win'};winners.append(p)
    winners.sort(key=lambda x:x['_rank_score'],reverse=True)
    selected=[];mc=collections.Counter();cc=collections.Counter();bc=collections.Counter()
    for p in winners:
        if len(selected)>=MAX_FINAL:break
        if p['_rank_score']<MIN_FINAL_SCORE:continue
        m=p.get('merchant_name') or 'Unknown';c=p.get('category_raw') or 'Uncategorized';b=p.get('brand_name') or 'Unknown'
        if mc[m]>=MAX_PER_MERCHANT or cc[c]>=MAX_PER_CATEGORY or bc[b]>=MAX_PER_BRAND:continue
        mc[m]+=1;cc[c]+=1;bc[b]+=1;selected.append(p)
    # If strict diversity caps leave a small list, relax only category/brand caps; merchant cap stays protective.
    if len(selected)<min(MAX_FINAL,600):
        chosen={x['external_product_id'] for x in selected}
        for p in winners:
            if len(selected)>=MAX_FINAL:break
            if p['external_product_id'] in chosen or p['_rank_score']<MIN_FINAL_SCORE:continue
            m=p.get('merchant_name') or 'Unknown'
            if mc[m]>=MAX_PER_MERCHANT:continue
            mc[m]+=1;selected.append(p);chosen.add(p['external_product_id'])
    clean=[]
    for p in selected:
        q={k:v for k,v in p.items() if not k.startswith('_')};q['selection_score']=p['_rank_score'];q['selection_policy']='selection-v5-smart-stream';clean.append(q)
    with open('final-selection.jsonl','w',encoding='utf-8') as f:
        for p in clean:f.write(json.dumps(p,ensure_ascii=False,default=str)+'\n')
    report={'candidate_pool':len(rows),'identity_groups':len(groups),'final_selected':len(clean),'max_final':MAX_FINAL,'killed_external_risk_candidates':killed_risk,'killed_mega_visibility_candidates':killed_mega,'merchant_count':len(mc),'category_count':len({p.get('category_raw') for p in clean}),'top_merchants':mc.most_common(15),'top_categories':collections.Counter(p.get('category_raw') for p in clean).most_common(15),'score_min':round(min([p['selection_score'] for p in clean] or [0]),2),'score_max':round(max([p['selection_score'] for p in clean] or [0]),2),'method':'full-stream -> bounded pool -> merchant trust/visibility -> strict identity dedupe -> diversified top1000'}
    json.dump(report,open('final-selection-report.json','w',encoding='utf-8'),ensure_ascii=False,indent=2);print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
