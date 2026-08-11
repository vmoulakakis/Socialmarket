import os,json,math,datetime,time,requests
from urllib.parse import urlparse
from collections import defaultdict

SEARXNG=os.getenv('SEARXNG_BASE_URL','http://127.0.0.1:8080').rstrip('/')
MAX_EXTERNAL=int(os.getenv('MERCHANT_EXTERNAL_RESEARCH_LIMIT','220'))
TIMEOUT=15
UA={'User-Agent':'Mozilla/5.0 SocialMarketSelection/1.0'}
NEG=('scam','fraud','απατη','απάτη','καταγγελια','καταγγελία','δεν παρελαβα','δεν παρέλαβα','refund problem','fake shop')
POS=('trusted','excellent','recommended','αξιοπιστ','πολύ καλό','πολυ καλο','γρήγορη παράδοση','γρηγορη παραδοση')
CREDIBLE=('trustpilot.','skroutz.','bestprice.','gov.gr','businessportal.gr','businessregistry.gr')
EXCLUDE_DOMAIN=('linkwi.se','linkwise','google.','facebook.','instagram.','youtube.','tiktok.')

def clamp(v,lo=0,hi=100):return max(lo,min(hi,float(v)))
def host(u):
    try:return urlparse(u).netloc.lower().removeprefix('www.')
    except:return ''
def search(q,limit=10):
    if not SEARXNG:return []
    try:
        r=requests.get(f'{SEARXNG}/search',params={'q':q,'format':'json','language':'el-GR','safesearch':1},headers=UA,timeout=20);r.raise_for_status();return (r.json().get('results') or [])[:limit]
    except:return []
def resolve_domain(url):
    try:
        r=requests.get(url,headers=UA,timeout=TIMEOUT,allow_redirects=True,stream=True);d=host(r.url)
        return d if d and not any(x in d for x in EXCLUDE_DOMAIN) else None
    except:return None
def rdap_age(domain):
    if not domain:return None
    try:
        r=requests.get(f'https://rdap.org/domain/{domain}',headers=UA,timeout=TIMEOUT)
        if not r.ok:return None
        ds=[]
        for e in r.json().get('events',[]):
            if e.get('eventAction') in ('registration','registered') and e.get('eventDate'):
                try:ds.append(datetime.datetime.fromisoformat(e['eventDate'].replace('Z','+00:00')))
                except:pass
        return max(0,(datetime.datetime.now(datetime.timezone.utc)-min(ds)).days/365.25) if ds else None
    except:return None
def text_signal(t):
    low=(t or '').lower();n=sum(k in low for k in NEG);p=sum(k in low for k in POS);return clamp(50+(p-n)*18)
def representative_terms(rows):
    seen=[]
    for p in sorted(rows,key=lambda x:float(x.get('_stream_score') or 0),reverse=True):
        t=(p.get('category_raw') or p.get('product_name') or '').strip()
        if t and t not in seen:seen.append(t)
        if len(seen)>=3:break
    return seen

def internal_metrics(m,rows,stats):
    s=stats.get(m,{}) ;eligible=max(1,int(s.get('eligible') or len(rows)));share=float(s.get('eligible_share') or 0);avg_times=float(s.get('total_times_bought') or 0)/eligible
    purchase=clamp(18*math.log1p(avg_times));stability=clamp(35+16*math.log1p(eligible));internal=clamp(purchase*.62+stability*.38);feed_visibility=clamp(share*1800)
    return s,eligible,share,internal,feed_visibility

def main():
    stats=json.load(open('merchant-stream-stats.json',encoding='utf-8'));json.load(open('category-stream-stats.json',encoding='utf-8'))
    by=defaultdict(list)
    with open('candidate-pool.jsonl',encoding='utf-8') as f:
        for line in f:
            p=json.loads(line);by[p.get('merchant_name') or p.get('program_name') or 'Unknown'].append(p)
    # Research externally only merchants with meaningful shortlist presence/potential.
    ordering=[]
    for m,rows in by.items():
        _,_,_,internal,feed_visibility=internal_metrics(m,rows,stats);potential=max(float(x.get('_stream_score') or 0) for x in rows)*.65+internal*.25+(100-feed_visibility)*.10;ordering.append((potential,m))
    external_set={m for _,m in sorted(ordering,reverse=True)[:MAX_EXTERNAL]}
    result={}
    for i,(m,rows) in enumerate(sorted(by.items(),key=lambda kv:len(kv[1]),reverse=True),1):
        s,eligible,share,internal,feed_visibility=internal_metrics(m,rows,stats);researched=m in external_set
        domain=None;age=None;external=50;evidence_conf=0;review_results=[];neg_domains=set();credible_domains=set();dominance=0
        terms=representative_terms(rows)
        if researched:
            for p in rows[:8]:
                if p.get('tracking_url'):
                    domain=resolve_domain(p['tracking_url'])
                    if domain:break
            if not domain:
                for x in search(f'"{m}" official shop Ελλάδα',8):
                    d=host(x.get('url') or '')
                    if d and not any(z in d for z in EXCLUDE_DOMAIN+('skroutz.','bestprice.','trustpilot.')):domain=d;break
            age=rdap_age(domain);age_score=50 if age is None else clamp(25+age*8)
            review_results=search(f'"{m}" αξιολογήσεις κριτικές trustpilot skroutz bestprice',12)+search(f'"{m}" απάτη καταγγελία επιστροφή χρημάτων',10)
            sigs=[]
            for x in review_results:
                d=host(x.get('url') or '');txt=f"{x.get('title') or ''} {x.get('content') or x.get('snippet') or ''}";sc=text_signal(txt);sigs.append(sc)
                if any(c in d for c in CREDIBLE):credible_domains.add(d)
                if sc<=32 and (any(c in d for c in CREDIBLE) or d.endswith('.gr')):neg_domains.add(d)
            review_score=sum(sigs)/len(sigs) if sigs else 50;external=clamp(age_score*.25+review_score*.55+(65 if domain else 35)*.20)
            evidence_conf=clamp(.18+(.18 if domain else 0)+min(.32,len(credible_domains)*.12)+min(.22,len(review_results)*.02),0,1)
            appear=queries=0
            if domain:
                for term in terms:
                    rs=search(f'{term} Ελλάδα αγορά τιμή',10);queries+=1
                    if any(domain in host(x.get('url') or '') for x in rs):appear+=1
                    time.sleep(.1)
            dominance=appear/max(1,queries) if queries else 0
        effective_external=50+(external-50)*evidence_conf;trust=clamp(internal*.62+effective_external*.38)
        visibility=clamp(dominance*62+feed_visibility*.38)
        risk_flag=len(neg_domains)>=2 and evidence_conf>=.65
        mega_kill=visibility>=88 and dominance>=.50
        suitability=clamp(trust*.76+(100-visibility)*.24-(18 if risk_flag else 0))
        result[m]={'merchant':m,'externally_researched':researched,'domain':domain,'internal_trust':round(internal,2),'external_reputation':round(external,2),'external_confidence':round(evidence_conf,4),'trust_score':round(trust,2),'feed_share':round(share,6),'serp_dominance':round(dominance,4),'visibility_penalty':round(visibility,2),'merchant_suitability':round(suitability,2),'risk_flag':risk_flag,'mega_visibility_kill':mega_kill,'domain_age_years':round(age,2) if age is not None else None,'negative_credible_domains':sorted(neg_domains),'evidence_count':len(review_results),'representative_terms':terms}
        if i%20==0:print(json.dumps({'processed':i,'merchants':len(by),'external_budget':MAX_EXTERNAL}),flush=True)
    with open('merchant-pool-research.json','w',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps({'merchants':len(result),'externally_researched':sum(x['externally_researched'] for x in result.values()),'risk_flags':sum(x['risk_flag'] for x in result.values()),'mega_visibility_kills':sum(x['mega_visibility_kill'] for x in result.values())}))
if __name__=='__main__':main()
