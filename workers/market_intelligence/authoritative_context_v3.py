from __future__ import annotations

import hashlib
import re
from urllib.parse import urlparse

import requests
import trafilatura

UA={'User-Agent':'Mozilla/5.0 SocialMarketAuthoritativeContext/3.0 (+public market research)'}

# Stable primary/industry pages. These are exogenous context only. They never
# enter the category demand/pain score unless a future dedicated parser maps a
# directly measured statistic to the exact canonical taxonomy with provenance.
SOURCES=(
    {
        'url':'https://www.statistics.gr/en/home',
        'title':'ELSTAT — latest Greek economy and retail indicators',
        'source_kind':'official_context','source_class':'official_statistics','authority_weight':1.0,
        'scope':'greece_retail_macro','categories':(),
    },
    {
        'url':'https://www.statistics.gr/en/statistics/-/publication/DKT39/2026-M04',
        'title':'ELSTAT — Retail Trade Turnover and Volume Index 2026',
        'source_kind':'official_context','source_class':'official_statistics','authority_weight':1.0,
        'scope':'greece_retail','categories':('Fashion & Accessories','Beauty & Personal Care','Electronics & Technology','Home & Garden','Kids & Baby','Books & Education','Food & Drink','Automotive','Pets','Sports & Outdoors'),
    },
    {
        'url':'https://www.statistics.gr/en/statistics/-/publication/SFA20/2025',
        'title':'ELSTAT — ICT use by households and individuals 2025',
        'source_kind':'official_context','source_class':'official_statistics','authority_weight':1.0,
        'scope':'greece_digital_commerce','categories':(),
    },
    {
        'url':'https://www.statistics.gr/en/statistics/-/publication/SFA05/2024',
        'title':'ELSTAT — Household Budget Survey 2024',
        'source_kind':'official_context','source_class':'official_statistics','authority_weight':1.0,
        'scope':'greece_household_expenditure','categories':(),
    },
    {
        'url':'https://ec.europa.eu/eurostat/web/interactive-publications/digitalisation-2026',
        'title':'Eurostat — Digitalisation in Europe 2026',
        'source_kind':'official_context','source_class':'public_institution','authority_weight':1.0,
        'scope':'eu_greece_online_shopping','categories':(),
    },
    {
        'url':'https://www.greekecommerce.gr/news/nea-toy-syndesmoy/erevna-ilektronikou-emporiou-greca-2026/',
        'title':'GR.EC.A — Έρευνα Ηλεκτρονικού Εμπορίου 2026',
        'source_kind':'industry_context','source_class':'industry_primary','authority_weight':.88,
        'scope':'greece_ecommerce_consumer_survey','categories':(),
    },
    {
        'url':'https://www.greekecommerce.gr/news/member-announcements/greek-ecommerce-review-2025-by-aftersalespro/',
        'title':'GR.EC.A / AfterSalesPro — Greek eCommerce Review 2025',
        'source_kind':'industry_context','source_class':'industry_primary','authority_weight':.84,
        'scope':'greece_ecommerce_orders_operations','categories':(),
    },
    {
        'url':'https://corporate.skroutz.gr/press-el/skroutz-etisia-anaskopisi-2025/',
        'title':'Skroutz — Ετήσια ανασκόπηση αγοραστικής συμπεριφοράς 2025',
        'source_kind':'industry_context','source_class':'marketplace_primary','authority_weight':.84,
        'scope':'greece_marketplace_activity','categories':(),
    },
)


def _host(url):
    try:return urlparse(url).netloc.lower().removeprefix('www.')
    except:return ''


def _fold(text):
    import unicodedata
    text=str(text or '').lower()
    text=''.join(c for c in unicodedata.normalize('NFKD',text) if not unicodedata.combining(c))
    return re.sub(r'\s+',' ',text).strip()


def _fetch(source):
    try:
        r=requests.get(source['url'],headers=UA,timeout=28,allow_redirects=True)
        if not r.ok:return None
        raw=r.text[:3_000_000]
        text=trafilatura.extract(raw,include_comments=False,include_links=False,include_images=False,deduplicate=True,favor_precision=True,output_format='txt')
        if not text:return None
        return re.sub(r'\s+',' ',text).strip()[:10000]
    except Exception:
        return None


def authoritative_context_rows(category,subcategory,aliases,keywords):
    """Fetch direct Greek/EU market context without using SearXNG as authority discovery.

    Rows are context_only and cannot support consumer-pain validation or inflate the
    demand index. `taxonomy_direct` merely records whether the fetched source text
    explicitly contains one of the category aliases; it does not make it a score.
    """
    out=[]
    terms=[x for x in [subcategory,category,*(aliases or [])] if x]
    folded=[_fold(x) for x in terms if len(_fold(x))>=4]
    for source in SOURCES:
        allowed=source.get('categories') or ()
        if allowed and category not in allowed:continue
        body=_fetch(source)
        if not body:continue
        hay=_fold(body)
        hits=sorted({term for term in folded if term in hay})
        taxonomy_direct=bool(hits)
        # Generic macro rows remain useful context even when taxonomy_direct=False.
        confidence=(.95 if source['authority_weight']>=1 else .82) if taxonomy_direct else (.86 if source['authority_weight']>=1 else .74)
        out.append({
            'source_kind':source['source_kind'],
            'source_url':source['url'],
            'title':source['title'],
            'body':body,
            'collector':'direct_authoritative_context_v3',
            'confidence':confidence,
            'content_hash':hashlib.sha256((source['url']+'|'+body).encode('utf-8','ignore')).hexdigest(),
            'metadata':{
                'geography':'GR' if 'eurostat' not in _host(source['url']) else 'EU+GR',
                'context_only':True,'eligible_for_pain_audit':False,
                'context_scope':source['scope'],'taxonomy_direct':taxonomy_direct,
                'taxonomy_matches':hits[:12],'source_class':source['source_class'],
                'source_family':'official_statistics' if source['authority_weight']>=1 else source['source_class'],
                'authority_weight':source['authority_weight'],'does_not_feed_demand_score':True,
                'context_semantics':'direct official/industry exogenous context; not category demand, market size, pain prevalence, search volume or market share unless a dedicated measured-statistic parser says so',
                'retrieval_version':'greek_authoritative_context_v3'
            }
        })
    return out[:12]
