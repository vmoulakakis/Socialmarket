from __future__ import annotations
import concurrent.futures, datetime, json, os, re, threading, time
from urllib.parse import quote, urlparse, urljoin
import requests
from bs4 import BeautifulSoup

GATEWAY=os.environ['MERCHANT_RESEARCH_GATEWAY']
SEARXNG=os.getenv('SEARXNG_BASE_URL','http://127.0.0.1:8080').rstrip('/')
MAX=int(os.getenv('MERCHANT_RESEARCH_LIMIT','350'))
WORKERS=max(1,min(int(os.getenv('MERCHANT_RESEARCH_WORKERS','6')),10))
UA={'User-Agent':'Mozilla/5.0 SocialMarketMerchantResearch/3.2'}
AUD='socialmarket-supabase-worker'
BLOCK=('linkwi','facebook.','instagram.','youtube.','tiktok.','skroutz.','bestprice.','trustpilot.','linkedin.','wikipedia.','google.','bing.')
POS=('excellent','recommended','reliable','trusted','great','γρηγορη','γρήγορη','αξιοπιστ','θετικ','ικανοποι','καλή εξυπηρέτηση')
NEG=('scam','fraud','refund','complaint','fake','απατη','απάτη','καταγγε','δεν παρελαβα','δεν παρέλαβα','καθυστερ','προβλημα','πρόβλημα','παράπονο','παραπονο')
RULES={
 'Fashion':('fashion','ρούχα','clothing','shoes','παπούτσια','jewelry','κοσμήματα','eyewear','γυαλιά'),
 'Beauty':('beauty','cosmetic','καλλυν','skincare','makeup','perfume','άρωμα'),
 'Health':('health','medical','φαρμακ','supplement','wellness','ορθοπεδ'),
 'Electronics':('electronics','technology','computer','laptop','mobile','κινητ','τηλεφων','gaming','gadget'),
 'Home & Garden':('home','σπίτι','furniture','έπιπλ','garden','κήπο','decor','κουζίνα','μπάνιο'),
 'Sports & Outdoors':('sport','fitness','outdoor','ποδήλα','scooter','camping','running'),
 'Kids & Baby':('baby','kids','παιδ','βρεφ','toy','παιχνιδ'),
 'Food & Drink':('food','coffee','καφέ','wine','κρασί','grocery','τροφ','restaurant'),
 'Travel':('travel','hotel','flight','airline','tour','διακοπ','ταξιδ','booking'),
 'Automotive':('auto','car','motor','αυτοκιν','μοτο','tyre','tire'),
 'Pets':('pet','dog','cat','κατοικιδ'),
 'Services':('service','insurance','finance','bank','education','course','software','hosting','delivery','courier')}
_token=None; _token_at=0.; _lock=threading.Lock()

def clamp(v,a=0,b=100): return max(a,min(b,float(v)))
def host(u):
    try:return urlparse(u).netloc.lower().split(':')[0].removeprefix('www.')
    except:return ''
def oidc():
    global _token,_token_at
    with _lock:
        if _token and time.time()-_token_at<180:return _token
        u=os.environ['ACTIONS_ID_TOKEN_REQUEST_URL']; rt=os.environ['ACTIONS_ID_TOKEN_REQUEST_TOKEN']; sep='&' if '?' in u else '?'
        r=requests.get(f'{u}{sep}audience={quote(AUD)}',headers={'Authorization':f'Bearer {rt}'},timeout=30);r.raise_for_status()
        _token=r.json()['value'];_token_at=time.time();return _token
def gateway(action,**kw):
    r=requests.post(GATEWAY,headers={'Authorization':f'Bearer {oidc()}','Content-Type':'application/json'},json={'action':action,**kw},timeout=180)
    if r.status_code==401:
        global _token; _token=None
        r=requests.post(GATEWAY,headers={'Authorization':f'Bearer {oidc()}','Content-Type':'application/json'},json={'action':action,**kw},timeout=180)
    r.raise_for_status(); body=r.json()
    if not body.get('ok'):raise RuntimeError(body)
    return body

def search(q,limit=10):
    try:
        r=requests.get(f'{SEARXNG}/search',params={'q':q,'format':'json','language':'el-GR','safesearch':1},headers=UA,timeout=25);r.raise_for_status()
        return [{'url':x.get('url',''),'title':x.get('title',''),'snippet':x.get('content') or x.get('snippet') or ''} for x in (r.json().get('results') or [])[:limit]]
    except:return []
def fetch(url,timeout=15):
    try:
        r=requests.get(url,headers=UA,timeout=timeout,allow_redirects=True)
        return r if r.ok else None
    except:return None
def discover(name,current=None):
    if current:
        r=fetch(current,10)
        if r:return r.url
    s=name.strip().lower().replace('https://','').replace('http://','').strip('/')
    if re.fullmatch(r'[a-z0-9][a-z0-9.-]+\.(gr|com|eu|net|org|es|it|de|fr|co\.uk)',s):
        r=fetch('https://'+s,10)
        if r:return r.url
    for q in (f'"{name}" official shop Ελλάδα',f'"{name}" επίσημο site',f'"{name}" online store'):
        for x in search(q,10):
            d=host(x['url'])
            if d and not any(b in d for b in BLOCK):
                r=fetch(x['url'],10)
                if r:return r.url
    return None

def crawl(url):
    r=fetch(url,18)
    if not r:return {'ok':False,'url':url,'html':'','text':'','title':'','description':'','anchors':[],'pages':0,'robots':False,'sitemap':False,'status':0}
    soup=BeautifulSoup(r.text,'html.parser'); title=(soup.title.get_text(' ',strip=True) if soup.title else '')[:500]
    md=soup.find('meta',attrs={'name':re.compile('description',re.I)}); desc=(md.get('content','') if md else '')[:1500]
    anchors=[]; internal=[]; base=host(r.url)
    for a in soup.find_all('a',href=True):
        t=a.get_text(' ',strip=True)
        try:u=urljoin(r.url,a['href'])
        except:continue
        if host(u)==base and 3<=len(t)<=60:
            anchors.append(t); internal.append((u,t))
    text=soup.get_text(' ',strip=True)[:120000]; pages=1
    for u,t in internal:
        if pages>=5:break
        if re.search(r'about|company|category|product|shop|collection|προιο|προϊόν|κατηγ|service|υπηρεσ',u+' '+t,re.I):
            x=fetch(u,10)
            if x:text+=' '+BeautifulSoup(x.text,'html.parser').get_text(' ',strip=True)[:40000];pages+=1
    origin=f'{urlparse(r.url).scheme}://{urlparse(r.url).netloc}'
    rob=fetch(origin+'/robots.txt',7); sm=fetch(origin+'/sitemap.xml',8)
    if sm:text+=' '+BeautifulSoup(sm.text,'html.parser').get_text(' ',strip=True)[:60000]
    return {'ok':True,'url':r.url,'html':r.text[:500000],'text':text,'title':title,'description':desc,'anchors':list(dict.fromkeys(anchors))[:100],'pages':pages,'robots':bool(rob),'sitemap':bool(sm),'status':r.status_code}
def categories(text):
    low=text.lower(); out=[]
    for name,keys in RULES.items():
        n=sum(1 for k in keys if k in low)
        if n:out.append({'name':name,'score':n})
    return sorted(out,key=lambda x:x['score'],reverse=True)[:3]
def sentiment(rows):
    txt=' '.join((x.get('title','')+' '+x.get('snippet','')).lower() for x in rows);p=sum(1 for x in POS if x in txt);n=sum(1 for x in NEG if x in txt)
    return p,n,clamp(50+(p-n)*8)
def suggest(q):
    try:
        r=requests.get('https://suggestqueries.google.com/complete/search',params={'client':'firefox','hl':'el','q':q},headers=UA,timeout=10);j=r.json();return j[1][:10] if isinstance(j,list) and len(j)>1 else []
    except:return []
def seo(c):
    h=c['html'];s=0
    if c['url'].startswith('https://'):s+=15
    if c['title']:s+=15
    if c['description']:s+=15
    if re.search(r'name=["\']viewport',h,re.I):s+=10
    if re.search(r'rel=["\']canonical',h,re.I):s+=10
    if 'application/ld+json' in h.lower():s+=10
    if re.search(r'<h1[\s>]',h,re.I):s+=5
    if c['robots']:s+=10
    if c['sitemap']:s+=10
    return clamp(s)
def market(label):
    sug=suggest(label); need=suggest(label+' πρόβλημα'); buy=search(label+' αγορά Ελλάδα',12); pain=search(label+' πρόβλημα παράπονα λύση',12)
    domains=sorted({host(x['url']) for x in buy if host(x['url']) and not any(b in host(x['url']) for b in BLOCK)})
    _,neg,_=sentiment(pain); demand=clamp(20+len(sug)*5+min(20,len(buy)*2.5)+min(10,len(need)*2)); comp=clamp(len(domains)*9); gap=clamp(25+neg*10+min(20,len(pain)*2)+min(15,len(need)*3))
    return demand,comp,gap,sug,need,buy,pain,domains
def analyze(job):
    name=job['canonical_name']; mid=job['id']; url=discover(name,job.get('official_url')); c=crawl(url) if url else crawl('')
    corpus=' '.join([name,c['title'],c['description'],c['text'],' '.join(c['anchors'])]); cats=categories(corpus); category=(cats[0]['name'] if cats else job.get('primary_category') or 'Other')
    sub=next((x for x in c['anchors'] if 4<len(x)<36 and x.lower()!=category.lower() and not re.search(r'home|about|contact|blog|αρχική|επικοινων',x,re.I)),'')
    reviews=search(f'"{name}" αξιολογήσεις κριτικές',12); complaints=search(f'"{name}" παράπονα καταγγελίες',12); allrev=reviews+complaints;pos,neg,sat=sentiment(allrev)
    seo_score=seo(c); identity=clamp(35+(20 if c['ok'] else 0)+(20 if c['title'] else 0)+(25 if re.search(r'contact|επικοινων|terms|όροι|επιστροφ|about|εταιρ',corpus,re.I) else 0)); complaint=clamp(100-sat+min(20,len(complaints)*2));trust=clamp(identity*.4+sat*.6)
    demand,comp,gap,sug,need,buy,pain,domains=market(sub or category);opp=clamp(demand*.35+gap*.40+(100-comp)*.20+sat*.05);opp=min(opp,45) if trust<35 else opp
    conf=clamp((.35 if c['ok'] else .10)+(.15 if allrev else 0)+(.15 if buy else 0)+(.15 if sug else 0)+(.10 if c['pages']>1 else 0)+(.10 if cats else 0),0,1)
    evidence=allrev[:15]+[{'type':'official_site','url':c['url'],'title':c['title'],'snippet':c['description']}]
    return {'job_id':job['job_id'],'merchant_id':mid,'merchant_name':name,'official_url':c['url'] or None,'official_domain':host(c['url']) or None,'http_status':c['status'],'site_title':c['title'] or None,'site_description':c['description'] or None,'category':category,'subcategory':sub or None,'category_candidates':cats,'subcategory_candidates':c['anchors'][:25],'seo_technical_score':seo_score,'seo_organic_visibility_score':clamp((100-comp)*.4+seo_score*.6),'seo_brand_serp_score':clamp(len(search(f'"{name}"',10))*10),'business_identity_score':identity,'review_footprint_score':clamp(len(allrev)*7),'satisfaction_score':sat,'complaint_risk_score':complaint,'trust_score':trust,'demand_score':demand,'competition_score':comp,'pain_gap_score':gap,'confidence':conf,'risk_flag':bool(trust<25 or complaint>80),'risk_reason':'low_trust' if trust<25 else ('high_complaint_risk' if complaint>80 else None),'competitors':domains,'demand_evidence':{'suggestions':sug,'problem_suggestions':need},'competition_evidence':buy[:12],'pain_evidence':pain[:12],'evidence':evidence,'evidence_count':len(evidence)+len(pain)+len(buy),'semantic_text':' | '.join(filter(None,[name,category,sub,c['title'],c['description'],f'Greek demand {demand}',f'competition {comp}',f'pain gap {gap}',f'satisfaction {sat}',f'trust {trust}'])),'summary':f'Demand {demand:.0f}; competition {comp:.0f}; pain gap {gap:.0f}; satisfaction {sat:.0f}; trust {trust:.0f}; opportunity {opp:.0f}.','strengths':[f'SEO {seo_score:.0f}',f'Demand {demand:.0f}',f'Pain gap {gap:.0f}'],'weaknesses':[f'Competition {comp:.0f}',f'Complaint risk {complaint:.0f}'],'metadata':{'pages_crawled':c['pages'],'search_backend':'searxng','methodology':'greek_gap_v2'}}
def process(job):
    try:r=analyze(job);gateway('save',result=r);return {'ok':True,'merchant':job['canonical_name'],'url':r['official_url'],'category':r['category'],'subcategory':r['subcategory'],'demand':r['demand_score'],'competition':r['competition_score'],'pain_gap':r['pain_gap_score']}
    except Exception as e:
        try:gateway('fail',job_id=job['job_id'],error=str(e)[:1200])
        except:pass
        return {'ok':False,'merchant':job.get('canonical_name'),'error':str(e)[:300]}
def main():
    done=0
    while done<MAX:
        batch=min(40,MAX-done);jobs=gateway('claim',limit=batch,worker='github-searxng-v3.2').get('jobs') or []
        if not jobs:break
        with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
            for result in ex.map(process,jobs):print(json.dumps(result,ensure_ascii=False),flush=True);done+=1
    print(json.dumps({'status':'completed','processed':done,'workers':WORKERS,'at':datetime.datetime.now(datetime.timezone.utc).isoformat()}))
if __name__=='__main__':main()
