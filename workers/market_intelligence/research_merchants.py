import os,re,json,math,time,datetime,requests
from urllib.parse import urlparse,urljoin
from bs4 import BeautifulSoup
from gateway import db_call

SEARXNG=os.getenv('SEARXNG_BASE_URL','http://127.0.0.1:8080').rstrip('/')
MAX_MERCHANTS=int(os.getenv('MERCHANT_RESEARCH_LIMIT','250'))
TIMEOUT=15
UA={'User-Agent':'Mozilla/5.0 SocialMarketResearch/1.0'}
REVIEW_DOMAINS=('trustpilot.','skroutz.','bestprice.','google.com/maps','facebook.com')
HIGH_CREDIBILITY=('trustpilot.','skroutz.','bestprice.','gov.gr','businessregistry.gr','businessportal.gr','capital.gr','naftemporiki.gr','kathimerini.gr')
EXCLUDE_OFFICIAL=('linkwi.se','linkwise','google.','bing.','yahoo.','duckduckgo.','facebook.','instagram.','youtube.','tiktok.','skroutz.','bestprice.','trustpilot.')
NEGATIVE=('απατη','απάτη','scam','fraud','καταγγελια','καταγγελία','δεν παρελαβα','δεν παρέλαβα','μη επιστροφη','μη επιστροφή','never arrived','refund problem','fake shop','μη αξιοπιστ')
POSITIVE=('αξιοπιστ','trusted','excellent','πολυ καλο','πολύ καλό','γρηγορη παραδοση','γρήγορη παράδοση','recommended','θετικ')
BUSINESS_MARKERS=('αφμ','γ.ε.μ.η','γεμη','εταιρεια','εταιρεία','επωνυμια','επωνυμία','οροι χρησης','όροι χρήσης','επιστροφ','τηλεφων','τηλέφων','διευθυν','διεύθυν')

def clamp(v,lo=0,hi=100): return max(lo,min(hi,float(v)))
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def host(url):
    try:return urlparse(url).netloc.lower().split(':')[0].removeprefix('www.')
    except:return ''
def credibility(domain):
    if any(x in domain for x in HIGH_CREDIBILITY):return 1
    if any(x in domain for x in REVIEW_DOMAINS):return 2
    if domain.endswith('.gr') or domain.endswith('.com'):return 3
    return 4

def fetch_merchants():
    rows=db_call('GET','merchant_profiles',params={'select':'id,merchant_name,trust_score,internal_trust_score,external_reputation_score,external_reputation_confidence,official_domain,evidence','order':'active_offer_count.desc','limit':str(MAX_MERCHANTS)}) or []
    return rows

def sample_tracking(merchant):
    rows=db_call('GET','products',params={'merchant_name':f'eq.{merchant}','hard_gate_pass':'eq.true','select':'tracking_url','tracking_url':'not.is.null','limit':'3'}) or []
    return [r.get('tracking_url') for r in rows if r.get('tracking_url')]

def resolve_tracking_domain(url):
    try:
        r=requests.get(url,headers=UA,allow_redirects=True,timeout=TIMEOUT,stream=True)
        d=host(r.url)
        return d if d and not any(x in d for x in EXCLUDE_OFFICIAL) else None
    except:return None

def search(q,limit=8):
    try:
        r=requests.get(f'{SEARXNG}/search',params={'q':q,'format':'json','language':'el-GR','safesearch':1},headers=UA,timeout=20)
        r.raise_for_status();return (r.json().get('results') or [])[:limit]
    except:return []
def discover_official_domain(merchant,tracking_urls):
    for u in tracking_urls:
        d=resolve_tracking_domain(u)
        if d:return d,'tracking_redirect',.92
    results=search(f'"{merchant}" official shop Ελλάδα',10)
    for x in results:
        d=host(x.get('url') or '')
        if d and not any(b in d for b in EXCLUDE_OFFICIAL):return d,'search_discovery',.62
    return None,'unknown',0.0

def rdap_age(domain):
    if not domain:return None,None
    try:
        r=requests.get(f'https://rdap.org/domain/{domain}',headers=UA,timeout=TIMEOUT)
        if not r.ok:return None,None
        data=r.json();dates=[]
        for e in data.get('events',[]):
            if e.get('eventAction') in ('registration','registered') and e.get('eventDate'):
                try:dates.append(datetime.datetime.fromisoformat(e['eventDate'].replace('Z','+00:00')))
                except:pass
        if not dates:return None,data.get('handle')
        first=min(dates);years=(datetime.datetime.now(datetime.timezone.utc)-first).days/365.25
        return max(0,years),data.get('handle')
    except:return None,None

def fetch_html(url):
    try:
        r=requests.get(url,headers=UA,timeout=TIMEOUT,allow_redirects=True)
        if r.ok and 'text/html' in r.headers.get('content-type',''):return r.text,r.url
    except:pass
    return '',url

def identity_score(domain):
    if not domain:return 0,{},[]
    urls=[f'https://{domain}/',f'https://{domain}/contact',f'https://{domain}/terms',f'https://{domain}/epikoinonia',f'https://{domain}/oroi-xrisis']
    text='';reached=[]
    for u in urls:
        html,final=fetch_html(u)
        if html:
            reached.append(final);text+=' '+BeautifulSoup(html,'html.parser').get_text(' ',strip=True)[:40000]
        if len(text)>70000:break
    low=text.lower();found=[m for m in BUSINESS_MARKERS if m in low]
    https=bool(reached and str(reached[0]).startswith('https://'))
    score=clamp((25 if https else 0)+min(60,len(set(found))*10)+(15 if len(reached)>=2 else 0))
    return score,{'markers':sorted(set(found))[:20],'pages_reached':len(reached),'https':https},reached

def extract_aggregate_rating(url):
    html,_=fetch_html(url)
    if not html:return None,None
    soup=BeautifulSoup(html,'html.parser')
    for tag in soup.find_all('script',attrs={'type':'application/ld+json'}):
        try:data=json.loads(tag.string or '')
        except:continue
        stack=data if isinstance(data,list) else [data]
        while stack:
            item=stack.pop()
            if isinstance(item,list):stack.extend(item);continue
            if not isinstance(item,dict):continue
            ar=item.get('aggregateRating')
            if isinstance(ar,dict):
                try:
                    rating=float(ar.get('ratingValue'));count=int(float(ar.get('reviewCount') or ar.get('ratingCount') or 0));return rating,count
                except:pass
            for v in item.values():
                if isinstance(v,(dict,list)):stack.append(v)
    return None,None

def text_signal(text):
    low=(text or '').lower();neg=sum(1 for k in NEGATIVE if k in low);pos=sum(1 for k in POSITIVE if k in low)
    if neg==pos==0:return 0
    return max(-100,min(100,(pos-neg)*35))
def evidence_for(merchant):
    queries=[
      (f'"{merchant}" αξιολογήσεις κριτικές','reviews'),
      (f'"{merchant}" trustpilot skroutz bestprice','review_platform'),
      (f'"{merchant}" απάτη καταγγελία','complaint'),
      (f'"{merchant}" επιστροφή χρημάτων πρόβλημα','complaint'),
    ]
    seen=set();rows=[]
    for q,etype in queries:
        for x in search(q,8):
            url=x.get('url') or '';d=host(url)
            if not url or url in seen:continue
            seen.add(url);title=x.get('title') or '';snippet=x.get('content') or x.get('snippet') or ''
            sig=text_signal(f'{title} {snippet}');rating=count=None
            if any(z in d for z in REVIEW_DOMAINS):rating,count=extract_aggregate_rating(url)
            if rating is not None:
                sig=clamp((rating/5)*100,0,100)-50
                sig*=2
            rows.append({'evidence_type':etype,'source_name':d,'source_url':url,'source_domain':d,'title':title[:500],'snippet':snippet[:1800],'credibility_tier':credibility(d),'signal_score':sig,'confidence':.78 if credibility(d)<=2 else .55,'review_rating':rating,'review_count':count,'metadata':{'query':q}})
        time.sleep(.25)
    return rows

def score_external(domain,age_years,identity,ev):
    age_score=50 if age_years is None else clamp(20+age_years*9)
    ratings=[e for e in ev if e.get('review_rating') is not None]
    if ratings:
        weights=[max(1,math.log1p(e.get('review_count') or 1)) for e in ratings]
        review_score=sum((e['review_rating']/5*100)*w for e,w in zip(ratings,weights))/sum(weights)
        total_reviews=sum(e.get('review_count') or 0 for e in ratings)
    else:
        positive=[max(0,e['signal_score']) for e in ev if e['credibility_tier']<=3];negative=[max(0,-e['signal_score']) for e in ev if e['credibility_tier']<=3]
        review_score=clamp(50+(sum(positive)-sum(negative))/max(2,len(positive)+len(negative))) if ev else 50;total_reviews=0
    neg_sources={e['source_domain'] for e in ev if e['signal_score']<=-35 and e['credibility_tier']<=2}
    broad_neg={e['source_domain'] for e in ev if e['signal_score']<0 and e['credibility_tier']<=3}
    complaint_risk=clamp(len(neg_sources)*38+max(0,len(broad_neg)-len(neg_sources))*12)
    footprint=clamp(len({e['source_domain'] for e in ev})*13+math.log1p(total_reviews)*9)
    raw=clamp(age_score*.15+identity*.20+review_score*.35+footprint*.10+(100-complaint_risk)*.20)
    credible_domains=len({e['source_domain'] for e in ev if e['credibility_tier']<=2})
    confidence=clamp((.22 if domain else 0)+min(.38,credible_domains*.13)+min(.20,math.log1p(total_reviews)*.025)+min(.20,len(ev)*.018),0,1)
    risk_flag=complaint_risk>=80 and len(neg_sources)>=2 and confidence>=.70
    return {'raw':raw,'confidence':confidence,'age_score':age_score,'review_score':review_score,'footprint':footprint,'complaint_risk':complaint_risk,'risk_flag':risk_flag,'negative_credible_sources':sorted(neg_sources)}

def main():
    merchants=fetch_merchants();run=(db_call('POST','merchant_research_runs',data={'status':'running','merchant_count':len(merchants),'config':{'search':'searxng','rdap':'rdap.org','scoring':'bayesian-shrunk-external-v1'},'started_at':now()},prefer='return=representation') or [])[0];run_id=run['id'];evidence_total=0
    try:
        for idx,m in enumerate(merchants,1):
            name=m['merchant_name'];internal=float(m.get('internal_trust_score') or m.get('trust_score') or 50);tracking=sample_tracking(name);domain,domain_method,domain_conf=discover_official_domain(name,tracking);age,rdap_handle=rdap_age(domain);identity,identity_meta,pages=identity_score(domain);ev=evidence_for(name);score=score_external(domain,age,identity,ev)
            profile_id=m['id']
            base_evidence=[{'evidence_type':'official_domain','source_name':domain or 'unknown','source_url':f'https://{domain}/' if domain else None,'source_domain':domain,'title':'Official domain evidence','snippet':None,'credibility_tier':1,'signal_score':identity-50,'confidence':domain_conf,'review_rating':None,'review_count':None,'metadata':{'method':domain_method,'domain_age_years':age,'rdap_handle':rdap_handle,'identity':identity_meta}}]
            all_ev=base_evidence+ev
            for e in all_ev:
                payload={'run_id':run_id,'merchant_profile_id':profile_id,'merchant_name':name,**e}
                db_call('POST','merchant_reputation_evidence',data=payload,prefer='return=minimal');evidence_total+=1
            effective_external=50+(score['raw']-50)*score['confidence'];final_trust=clamp(internal*.65+effective_external*.35)
            db_call('PATCH','merchant_profiles',params={'id':f'eq.{profile_id}'},data={'internal_trust_score':round(internal,2),'external_reputation_score':round(score['raw'],2),'external_reputation_confidence':round(score['confidence'],4),'trust_score':round(final_trust,2),'official_domain':domain,'domain_age_years':round(age,2) if age is not None else None,'business_identity_score':round(identity,2),'review_footprint_score':round(score['footprint'],2),'complaint_risk_score':round(score['complaint_risk'],2),'external_risk_flag':score['risk_flag'],'external_risk_reason':'corroborated_external_complaint_risk' if score['risk_flag'] else None,'evidence_count':len(all_ev),'last_researched_at':now(),'evidence':{'internal_trust':internal,'external_raw':score['raw'],'effective_external':effective_external,'final_trust':final_trust,'negative_credible_sources':score['negative_credible_sources'],'domain_method':domain_method}})
            print(json.dumps({'progress':f'{idx}/{len(merchants)}','merchant':name,'domain':domain,'internal':round(internal,1),'external':round(score['raw'],1),'confidence':round(score['confidence'],2),'final':round(final_trust,1),'risk_flag':score['risk_flag']},ensure_ascii=False),flush=True)
        db_call('PATCH','merchant_research_runs',params={'id':f'eq.{run_id}'},data={'status':'completed','evidence_count':evidence_total,'finished_at':now()})
        print(json.dumps({'status':'completed','run_id':run_id,'merchants':len(merchants),'evidence':evidence_total},ensure_ascii=False))
    except Exception as e:
        db_call('PATCH','merchant_research_runs',params={'id':f'eq.{run_id}'},data={'status':'failed','evidence_count':evidence_total,'error':str(e)[:1500],'finished_at':now()});raise

if __name__=='__main__':main()
