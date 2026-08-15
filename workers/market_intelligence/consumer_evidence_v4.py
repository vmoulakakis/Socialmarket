from __future__ import annotations

import concurrent.futures
import hashlib
import os
import re
from urllib.parse import urlparse

import requests
import trafilatura

SEARXNG=os.getenv('SEARXNG_BASE_URL','http://127.0.0.1:8080').rstrip('/')
UA={'User-Agent':'Mozilla/5.0 SocialMarketConsumerEvidence/4.0 (+public evidence research)'}
FETCH_WORKERS=max(2,min(int(os.getenv('CATEGORY_CONSUMER_FETCH_WORKERS','6')),10))
MAX_DISCOVERY_URLS=max(12,min(int(os.getenv('CATEGORY_CONSUMER_MAX_URLS','36')),60))

# Domain-specific confidence is about the evidence collection surface, not the
# truth of the consumer's claim. The Skeptic still decides cluster validity.
SOURCE_RULES=(
    ('skroutz.gr','marketplace_review',.90),
    ('bestprice.gr','marketplace_review',.84),
    ('insomnia.gr','community_forum',.82),
    ('reddit.com','social_forum',.78),
    ('youtube.com','social_video',.72),
    ('youtu.be','social_video',.72),
)

PAIN_STEMS=(
    'προβλημα','μειονεκ','δεν αξι','πολυ ακριβ','ακριβο','δυσκολ','ενοχλ','χαλα','κολλα','κολλη',
    'θορυβ','μπαταρι','υπερθερ','τσουζ','ερεθ','διαρρο','σπα','σπασ','βλαβ','δεν δουλευ','δεν λειτουργ',
    'δεν βρισκ','δεν μπορ','δεν στελ','δεν αποστελλ','out of stock','εξαντλη','λειπ','ελλειψ','επιστροφ',
    'service','εγγυησ','καθυστερ','παραδοση','λαθος προιον','κατεστραμ','damaged','overheat','battery drain',
    'too expensive','does not work','doesn t work','missing','hard to find','not available','poor quality',
    'απογοητ','χειροτερ','ποτε ξανα','δεν ταιρια','παρενεργ','δεν καλυπτ','τελειωνει γρηγ','δεν εφαρμοζ',
)
PURCHASE_STEMS=(
    'αγορα','αγορασ','παραγγελ','προιον','τιμη','ευρω','€','χρησιμοποι','δοκιμα','αξιζει','επιστροφη',
    'αντικαταστα','καταστημα','eshop','e-shop','shop','bought','purchase','price','order','return','refund',
)
FIRST_PERSON_STEMS=('εγω','μου ','με εμενα','πηρα ','αγορασα','δοκιμασα','χρησιμοποιω','εχω ','περιμενα','i bought','i have','my ')
BOILERPLATE=(
    'μεταβαση στο περιεχομενο','κανενα προιον στο καλαθι','το καλαθι ειναι αδειο','συνδεση εγγραφη',
    'πολιτικη απορρητου','πολιτικη cookies','αποδοχη cookies','newsletter','δημιουργια λογαριασμου',
    'ξεχασατε τον κωδικο','comparison list','wish list','googleanalyticsobject','javascript','all rights reserved',
)


def host(url:str)->str:
    try:return urlparse(url).netloc.lower().split(':')[0].removeprefix('www.')
    except:return ''


def fold(text:str)->str:
    import unicodedata
    text=str(text or '').lower().replace('’',"'").replace('–','-')
    text=''.join(c for c in unicodedata.normalize('NFKD',text) if not unicodedata.combining(c))
    return re.sub(r'\s+',' ',text).strip()


def source_family(url:str)->tuple[str,float]:
    d=host(url)
    for suffix,family,confidence in SOURCE_RULES:
        if d==suffix or d.endswith('.'+suffix):return family,confidence
    return 'public_web',.64


def search(query:str,limit:int=8):
    try:
        r=requests.get(f'{SEARXNG}/search',params={'q':query,'format':'json','language':'el-GR','safesearch':1},headers=UA,timeout=25)
        r.raise_for_status()
        return [{'url':x.get('url',''),'title':x.get('title',''),'snippet':x.get('content') or x.get('snippet') or ''} for x in (r.json().get('results') or [])[:limit*2]]
    except Exception:
        return []


def _discover_queries(term:str):
    # Search is discovery only. Raw search snippets are never eligible for a
    # validated pain cluster in V4.
    return (
        (f'{term} πρόβλημα κριτική Ελλάδα','public_web'),
        (f'{term} μειονεκτήματα εμπειρία αγοράς','public_web'),
        (f'{term} δεν αξίζει εναλλακτική','public_web'),
        (f'site:skroutz.gr/s/ {term}','marketplace_review'),
        (f'site:bestprice.gr {term} αξιολογήσεις','marketplace_review'),
        (f'site:insomnia.gr {term} πρόβλημα','community_forum'),
        (f'site:reddit.com/r/greece {term}','social_forum'),
        (f'site:youtube.com {term} review ελληνικά','social_video'),
    )


def discover_urls(aliases:list[str]):
    found=[];seen=set()
    for term in aliases[:3]:
        for query,expected_family in _discover_queries(term):
            for row in search(query,6):
                url=str(row.get('url') or '')
                d=host(url)
                if not d or url in seen:continue
                seen.add(url)
                family,confidence=source_family(url)
                found.append({**row,'query':query,'query_term':term,'source_family':family,'expected_family':expected_family,'base_confidence':confidence})
                if len(found)>=MAX_DISCOVERY_URLS:return found
    return found


def _fetch_text(row):
    url=row['url']
    try:
        r=requests.get(url,headers=UA,timeout=22,allow_redirects=True)
        if r.status_code in (401,403,429) or not r.ok:return row,None,'http_'+str(r.status_code)
        ctype=(r.headers.get('content-type') or '').lower()
        if 'html' not in ctype and 'text' not in ctype:return row,None,'non_html'
        # Prevent unexpectedly large public pages from consuming runner memory.
        raw=r.text[:2_500_000]
        text=trafilatura.extract(raw,include_comments=True,include_links=False,include_images=False,deduplicate=True,favor_precision=True,output_format='txt')
        if not text:return row,None,'extract_empty'
        return row,text[:180_000],None
    except Exception as exc:
        return row,None,type(exc).__name__


def _split_segments(text:str):
    # Reviews/forums often preserve paragraph boundaries. We keep medium-size
    # text units so the Skeptic can audit a real consumer statement rather than
    # an entire page or a search snippet.
    raw=[]
    for paragraph in re.split(r'\n{1,}',text or ''):
        paragraph=re.sub(r'\s+',' ',paragraph).strip()
        if len(paragraph)<45:continue
        if len(paragraph)<=900:
            raw.append(paragraph);continue
        for sentence in re.split(r'(?<=[.!?;])\s+',paragraph):
            sentence=sentence.strip()
            if 45<=len(sentence)<=900:raw.append(sentence)
    return raw[:500]


def _keyword_hits(text:str,keywords:list[str],title:str):
    hay=fold(f'{title} {text}')
    hits=[]
    for keyword in keywords:
        k=fold(keyword)
        if len(k)>=4 and k in hay:hits.append(k)
    return sorted(set(hits))


def _consumer_score(text:str,title:str,keywords:list[str],family:str):
    f=fold(text);title_f=fold(title)
    if any(x in f for x in BOILERPLATE):return 0,[],[],False
    pain=[x for x in PAIN_STEMS if x in f]
    if not pain:return 0,[],[],False
    purchase=[x for x in PURCHASE_STEMS if x in f]
    first=any(x in f for x in FIRST_PERSON_STEMS)
    taxonomy=_keyword_hits(text,keywords,title)
    # Require category/product binding in the segment OR product/review context
    # in the page title. Generic news/social-problem paragraphs are discarded.
    title_binding=bool(_keyword_hits('',keywords,title))
    if not taxonomy and not title_binding:return 0,pain,purchase,first
    family_bonus={'marketplace_review':5,'community_forum':4,'social_forum':4,'social_video':2,'public_web':1}.get(family,1)
    score=len(pain)*3+min(4,len(purchase))*2+(3 if first else 0)+(4 if taxonomy else 2)+family_bonus
    return score,pain,purchase,first


def _evidence_from_page(row,text,keywords):
    family,base_conf=source_family(row['url'])
    rows=[]
    for segment in _split_segments(text):
        score,pain,purchase,first=_consumer_score(segment,row.get('title') or '',keywords,family)
        if score<9:continue
        digest=hashlib.sha256(segment.encode('utf-8','ignore')).hexdigest()
        confidence=min(.96,base_conf+min(.06,score*.002))
        rows.append({
            'source_kind':'pain_candidate',
            'source_url':row['url'],
            'title':str(row.get('title') or '')[:500],
            'body':segment[:1600],
            'collector':'consumer_page_extract_v4',
            'confidence':round(confidence,3),
            'content_hash':digest,
            'metadata':{
                'query':row.get('query'),'query_term':row.get('query_term'),'geography':'GR',
                'source_family':family,'evidence_mode':'extracted_consumer_text','consumer_text':True,
                'page_extracted':True,'pain_language':pain[:12],'purchase_language':purchase[:10],
                'first_person_signal':first,'consumer_language_score':score,
                'retrieval_version':'consumer_evidence_v4',
                'metric_semantics':'observed public consumer/reviewer statement; not a population estimate'
            }
        })
    rows.sort(key=lambda x:(x['metadata']['consumer_language_score'],x['confidence']),reverse=True)
    return rows[:12]


def collect_consumer_evidence(category:str,subcategory:str|None,aliases:list[str],keywords:list[str],max_rows:int=90):
    discovered=discover_urls(aliases)
    extracted=[];diagnostics=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(FETCH_WORKERS,max(1,len(discovered)))) as pool:
        futures=[pool.submit(_fetch_text,row) for row in discovered]
        for future in concurrent.futures.as_completed(futures):
            row,text,error=future.result()
            if text:
                extracted.extend(_evidence_from_page(row,text,keywords))
            diagnostics.append({
                'source_kind':'consumer_discovery',
                'source_url':row['url'],'title':str(row.get('title') or '')[:500],
                'body':str(row.get('snippet') or '')[:900],
                'collector':'consumer_discovery_v4','confidence':.45 if error else .62,
                'metadata':{
                    'query':row.get('query'),'query_term':row.get('query_term'),'geography':'GR',
                    'source_family':row.get('source_family'),'evidence_mode':'discovery_only',
                    'eligible_for_pain_audit':False,'fetch_error':error,'retrieval_version':'consumer_evidence_v4'
                }
            })
    # Deduplicate exact consumer statements while preserving cross-domain support.
    out=[];seen=set()
    for e in sorted(extracted,key=lambda x:(x['confidence'],x['metadata']['consumer_language_score']),reverse=True):
        key=(host(e['source_url']),e.get('content_hash'))
        if key in seen:continue
        seen.add(key);out.append(e)
        if len(out)>=max_rows:break
    # Discovery rows are persisted as provenance but cannot support validated pain.
    return out+diagnostics[:min(30,max_rows//2)]
