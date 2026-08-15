from __future__ import annotations

import concurrent.futures
import hashlib
import os
import re
from urllib.parse import urlparse

import requests
import trafilatura

SEARXNG=os.getenv('SEARXNG_BASE_URL','http://127.0.0.1:8080').rstrip('/')
UA={'User-Agent':'Mozilla/5.0 SocialMarketConsumerEvidence/4.2 (+public evidence research)'}
FETCH_WORKERS=max(2,min(int(os.getenv('CATEGORY_CONSUMER_FETCH_WORKERS','6')),10))
MAX_DISCOVERY_URLS=max(18,min(int(os.getenv('CATEGORY_CONSUMER_MAX_URLS','54')),90))

# Source-family confidence describes the collection surface, not truth of the
# consumer claim. The independent Skeptic and cross-source gates remain final.
SOURCE_RULES=(
    ('avsite.gr','community_forum',.86),
    ('myphone.gr','community_forum',.86),
    ('iphonehellas.gr','community_forum',.84),
    ('xiaomi-miui.gr','community_forum',.84),
    ('thelab.gr','community_forum',.84),
    ('adslgr.com','community_forum',.82),
    ('4troxoi.gr','community_forum',.82),
    ('mens-only.gr','community_forum',.82),
    ('beautyblog.gr','community_blog',.70),
    ('skroutz.gr','marketplace_review',.90),
    ('bestprice.gr','marketplace_review',.84),
    ('insomnia.gr','community_forum',.82),
    ('reddit.com','social_forum',.78),
    ('youtube.com','social_video',.72),
    ('youtu.be','social_video',.72),
)

# Crawlable Greek consumer communities get priority over generic public-web
# results. Blocked sources may still be discovered for provenance, but a 403
# never becomes validated evidence and is never bypassed.
COMMUNITY_DISCOVERY_DOMAINS=(
    'avsite.gr','myphone.gr','iphonehellas.gr','forums.xiaomi-miui.gr',
    'thelab.gr','adslgr.com','forum.4troxoi.gr','forum.mens-only.gr',
)
COMMUNITY_BLOG_DOMAINS=('beautyblog.gr',)

PAIN_STEMS=(
    'προβλημα','μειονεκ','δεν αξι','πολυ ακριβ','ακριβο','δυσκολ','ενοχλ','χαλα','κολλα','κολλη',
    'θορυβ','μπαταρι','υπερθερ','τσουζ','ερεθ','διαρρο','σπα','σπασ','βλαβ','δεν δουλευ','δεν λειτουργ',
    'δεν βρισκ','δεν μπορ','δεν στελ','δεν αποστελλ','out of stock','εξαντλη','λειπ','ελλειψ','επιστροφ',
    'service','εγγυησ','καθυστερ','παραδοση','λαθος προιον','κατεστραμ','damaged','overheat','battery drain',
    'too expensive','does not work','doesn t work','missing','hard to find','not available','poor quality',
    'απογοητ','χειροτερ','ποτε ξανα','δεν ταιρια','παρενεργ','δεν καλυπτ','τελειωνει γρηγ','δεν εφαρμοζ',
    'ξεφλουδ','σβην','κρασαρ','αποσυνδε','αργει','κακη ποιοτητα','στενο','φαρδυ','βαρυ','γλιστρα',
)
PURCHASE_STEMS=(
    'αγορα','αγορασ','παραγγελ','προιον','τιμη','ευρω','€','χρησιμοποι','δοκιμα','αξιζει','επιστροφη',
    'αντικαταστα','καταστημα','eshop','e-shop','shop','bought','purchase','price','order','return','refund',
    'πηρα','παρελαβα','φοραω','φορεσα','βαζω','εβαλα','δουλευω με','εχω το','εχω την','εχω τα','εχω ενα',
)
FIRST_PERSON_STEMS=(
    'εγω','μου ','με εμενα','πηρα ','αγορασα','δοκιμασα','χρησιμοποιω','εχω ','περιμενα','παρελαβα',
    'φοραω','φορεσα','εβαλα','με ενοχλει','μου κανει','μου χαλα','i bought','i have','my ','i use','i tried',
)
BOILERPLATE=(
    'μεταβαση στο περιεχομενο','κανενα προιον στο καλαθι','το καλαθι ειναι αδειο','συνδεση εγγραφη',
    'πολιτικη απορρητου','πολιτικη cookies','αποδοχη cookies','newsletter','δημιουργια λογαριασμου',
    'ξεχασατε τον κωδικο','comparison list','wish list','googleanalyticsobject','javascript','all rights reserved',
    'ο ιστοτοπος χρησιμοποιει cookies','αποδεχομαι τα cookies','cookie settings','privacy policy','terms of use',
)
EDITORIAL_TITLE_STEMS=(
    'ειδησεις','ειδηση','news','πολιτικ','celebrity','διασημ','ρεπορταζ','δελτιο τυπου','press release',
    'οδηγος αγορας','buying guide','top 10','καλυτερα ','best of','τι πρεπει να γνωριζετε','αρθρο',
)
FORUM_PATH_HINTS=('/forum','/forums','/topic','/threads','/thread','/community','showthread','viewtopic')
COMMENT_HINTS=('σχολιο','σχολια','comment','comments','απαντηση','απαντησεις','reply','replies')


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
    return 'public_web',.56


def search(query:str,limit:int=8):
    try:
        r=requests.get(f'{SEARXNG}/search',params={'q':query,'format':'json','language':'el-GR','safesearch':1},headers=UA,timeout=25)
        r.raise_for_status()
        return [{'url':x.get('url',''),'title':x.get('title',''),'snippet':x.get('content') or x.get('snippet') or ''} for x in (r.json().get('results') or [])[:limit*2]]
    except Exception:
        return []


def _discover_queries(term:str):
    # Priority 1: known crawlable Greek consumer communities. Search is discovery
    # only; pages still need successful public fetch + extracted consumer text.
    queries=[]
    for domain_name in COMMUNITY_DISCOVERY_DOMAINS:
        queries.append((f'site:{domain_name} {term} πρόβλημα εμπειρία','community_forum'))
        queries.append((f'site:{domain_name} {term} αγορά γνώμη','community_forum'))
    for domain_name in COMMUNITY_BLOG_DOMAINS:
        queries.append((f'site:{domain_name} {term} εμπειρία σχόλια','community_blog'))

    # Priority 2: high-value sources which may be blocked from runner fetch. They
    # remain useful discovery diagnostics; HTTP 403/429 is never bypassed.
    queries.extend((
        (f'site:skroutz.gr/s/ {term}','marketplace_review'),
        (f'site:bestprice.gr {term} αξιολογήσεις','marketplace_review'),
        (f'site:insomnia.gr {term} πρόβλημα','community_forum'),
        (f'site:reddit.com/r/greece {term}','social_forum'),
        (f'site:youtube.com {term} review ελληνικά','social_video'),
    ))

    # Priority 3: generic public web is a discovery fallback. V4.2 requires much
    # stronger first-person + purchase/use evidence before it can become pain text.
    queries.extend((
        (f'{term} πρόβλημα κριτική Ελλάδα','public_web'),
        (f'{term} μειονεκτήματα εμπειρία αγοράς','public_web'),
        (f'{term} δεν αξίζει εναλλακτική','public_web'),
    ))
    return tuple(queries)


def discover_urls(aliases:list[str]):
    found=[];seen=set()
    for term in aliases[:3]:
        for query,expected_family in _discover_queries(term):
            for row in search(query,5):
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
        raw=r.text[:2_500_000]
        text=trafilatura.extract(raw,include_comments=True,include_links=False,include_images=False,deduplicate=True,favor_precision=True,output_format='txt')
        if not text:return row,None,'extract_empty'
        return row,text[:180_000],None
    except Exception as exc:
        return row,None,type(exc).__name__


def _split_segments(text:str):
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


def _looks_editorial(title:str,url:str,family:str):
    if family in ('community_forum','social_forum','marketplace_review'):return False
    t=fold(title)
    if any(x in t for x in EDITORIAL_TITLE_STEMS):return True
    path=(urlparse(url).path or '').lower()
    if family=='community_blog':
        # Editorial blog body is not consumer evidence by default. A segment must
        # later prove first-person/comment characteristics to pass.
        return False
    return any(h in path for h in ('/news/','/article/','/articles/','/press/','/magazine/'))


def _ugc_surface(url:str,family:str,text:str):
    if family in ('community_forum','social_forum','marketplace_review'):return True
    path=(urlparse(url).path or '').lower()
    f=fold(text)
    if any(h in path for h in FORUM_PATH_HINTS):return True
    if any(h in f for h in COMMENT_HINTS):return True
    return False


def _consumer_score(text:str,title:str,keywords:list[str],family:str,url:str=''):
    f=fold(text)
    if any(x in f for x in BOILERPLATE):return 0,[],[],False
    pain=[x for x in PAIN_STEMS if x in f]
    if not pain:return 0,[],[],False
    purchase=[x for x in PURCHASE_STEMS if x in f]
    first=any(x in f for x in FIRST_PERSON_STEMS)
    taxonomy=_keyword_hits(text,keywords,title)
    title_binding=bool(_keyword_hits('',keywords,title))
    if not taxonomy and not title_binding:return 0,pain,purchase,first
    if _looks_editorial(title,url,family):return 0,pain,purchase,first

    ugc=_ugc_surface(url,family,text)
    if family=='public_web':
        # Generic web was the V4.1 contamination source. It now requires explicit
        # first-person AND purchase/use language; article/merchant copy cannot pass
        # merely because it contains the words "problem" and "buy".
        if not first or not purchase:return 0,pain,purchase,first
    elif family=='community_blog':
        # Blogs can mix editorial copy and user comments. Only comment-like or
        # strong first-person use/purchase segments survive.
        if not first or (not purchase and not ugc):return 0,pain,purchase,first
    elif family in ('community_forum','social_forum','marketplace_review'):
        if not first and not purchase:return 0,pain,purchase,first
    elif family=='social_video':
        if not first and not purchase:return 0,pain,purchase,first

    family_bonus={
        'marketplace_review':7,'community_forum':7,'social_forum':6,
        'community_blog':3,'social_video':3,'public_web':0,
    }.get(family,0)
    score=(
        len(pain)*3+min(4,len(purchase))*2+(5 if first else 0)
        +(5 if taxonomy else 2)+(3 if ugc else 0)+family_bonus
    )
    return score,pain,purchase,first


def _evidence_from_page(row,text,keywords):
    family,base_conf=source_family(row['url'])
    rows=[]
    for segment in _split_segments(text):
        score,pain,purchase,first=_consumer_score(segment,row.get('title') or '',keywords,family,row['url'])
        minimum=12 if family=='public_web' else 10
        if score<minimum:continue
        digest=hashlib.sha256(segment.encode('utf-8','ignore')).hexdigest()
        confidence=min(.96,base_conf+min(.07,score*.002))
        rows.append({
            'source_kind':'pain_candidate',
            'source_url':row['url'],
            'title':str(row.get('title') or '')[:500],
            'body':segment[:1600],
            'collector':'consumer_page_extract_v42',
            'confidence':round(confidence,3),
            'content_hash':digest,
            'metadata':{
                'query':row.get('query'),'query_term':row.get('query_term'),'geography':'GR',
                'source_family':family,'evidence_mode':'extracted_consumer_text','consumer_text':True,
                'page_extracted':True,'pain_language':pain[:12],'purchase_language':purchase[:10],
                'first_person_signal':first,'consumer_language_score':score,
                'ugc_surface':_ugc_surface(row['url'],family,segment),
                'retrieval_version':'consumer_evidence_v4.2',
                'metric_semantics':'observed public consumer/reviewer statement; not a population estimate'
            }
        })
    rows.sort(key=lambda x:(x['metadata']['consumer_language_score'],x['confidence']),reverse=True)
    return rows[:14]


def collect_consumer_evidence(category:str,subcategory:str|None,aliases:list[str],keywords:list[str],max_rows:int=100):
    discovered=discover_urls(aliases)
    extracted=[];diagnostics=[]
    if discovered:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(FETCH_WORKERS,len(discovered))) as pool:
            futures=[pool.submit(_fetch_text,row) for row in discovered]
            for future in concurrent.futures.as_completed(futures):
                row,text,error=future.result()
                if text:
                    extracted.extend(_evidence_from_page(row,text,keywords))
                diagnostics.append({
                    'source_kind':'consumer_discovery',
                    'source_url':row['url'],'title':str(row.get('title') or '')[:500],
                    'body':str(row.get('snippet') or '')[:900],
                    'collector':'consumer_discovery_v42','confidence':.45 if error else .62,
                    'metadata':{
                        'query':row.get('query'),'query_term':row.get('query_term'),'geography':'GR',
                        'source_family':row.get('source_family'),'expected_family':row.get('expected_family'),
                        'evidence_mode':'discovery_only','eligible_for_pain_audit':False,
                        'fetch_error':error,'retrieval_version':'consumer_evidence_v4.2'
                    }
                })
    out=[];seen=set()
    for e in sorted(extracted,key=lambda x:(x['confidence'],x['metadata']['consumer_language_score']),reverse=True):
        key=(host(e['source_url']),e.get('content_hash'))
        if key in seen:continue
        seen.add(key);out.append(e)
        if len(out)>=max_rows:break
    return out+diagnostics[:min(40,max_rows//2)]
