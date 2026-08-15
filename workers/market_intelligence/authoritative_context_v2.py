from __future__ import annotations

from html.parser import HTMLParser
from urllib.parse import urlparse
import re
import unicodedata

import requests

UA={'User-Agent':'Mozilla/5.0 SocialMarketAuthoritativeContext/3.0 (+production market research)'}

# Stable primary-source entrypoints. These are read directly; no search-engine
# ranking decides whether official Greek context exists.
ENTRYPOINTS=(
    {
        'key':'elstat_retail',
        'url':'https://www.statistics.gr/en/statistics/-/publication/DKT39/-',
        'domain':'statistics.gr',
        'source_kind':'official_context',
        'source_class':'official_statistics',
        'authority_weight':1.0,
        'measure_family':'retail_turnover_volume',
        'fallback_priority':1,
    },
    {
        'key':'elstat_ict_households',
        'url':'https://www.statistics.gr/en/statistics/-/publication/SFA20/-',
        'domain':'statistics.gr',
        'source_kind':'official_context',
        'source_class':'official_statistics',
        'authority_weight':1.0,
        'measure_family':'household_ict_ecommerce',
        'fallback_priority':1,
    },
    {
        'key':'elstat_household_budget',
        'url':'https://www.statistics.gr/en/statistics/-/publication/SFA05/-',
        'domain':'statistics.gr',
        'source_kind':'official_context',
        'source_class':'official_statistics',
        'authority_weight':1.0,
        'measure_family':'household_expenditure_mix',
        'fallback_priority':2,
    },
    {
        'key':'eurostat_digitalisation_2026',
        'url':'https://ec.europa.eu/eurostat/web/interactive-publications/digitalisation-2026',
        'domain':'ec.europa.eu',
        'source_kind':'official_context',
        'source_class':'public_institution',
        'authority_weight':1.0,
        'measure_family':'digital_commerce_behavior',
        'fallback_priority':1,
    },
    {
        'key':'eurostat_digital_database',
        'url':'https://ec.europa.eu/eurostat/web/digital-economy-and-society/database/comprehensive-database',
        'domain':'ec.europa.eu',
        'source_kind':'official_context',
        'source_class':'public_institution',
        'authority_weight':1.0,
        'measure_family':'digital_economy_database',
        'fallback_priority':3,
    },
    {
        'key':'greca_state_ecommerce_2026',
        'url':'https://www.greekecommerce.gr/ereynes-gia-ellada/state-of-ecommerce-report-2026/',
        'domain':'greekecommerce.gr',
        'source_kind':'industry_context',
        'source_class':'industry_primary',
        'authority_weight':.82,
        'measure_family':'greek_ecommerce_industry_research',
        'fallback_priority':1,
    },
)


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts=[]
        self.title_parts=[]
        self._in_title=False
        self._skip=0

    def handle_starttag(self,tag,attrs):
        tag=tag.lower()
        if tag in {'script','style','noscript','svg'}:self._skip+=1
        if tag=='title':self._in_title=True

    def handle_endtag(self,tag):
        tag=tag.lower()
        if tag in {'script','style','noscript','svg'} and self._skip:self._skip-=1
        if tag=='title':self._in_title=False

    def handle_data(self,data):
        if self._skip:return
        text=' '.join(str(data or '').split())
        if not text:return
        self.parts.append(text)
        if self._in_title:self.title_parts.append(text)

    @property
    def text(self):return ' '.join(self.parts)

    @property
    def title(self):return ' '.join(self.title_parts)


def _host(url:str)->str:
    try:return urlparse(url).netloc.lower().split(':')[0].removeprefix('www.')
    except:return ''


def _fold(x:str)->str:
    x=unicodedata.normalize('NFKD',str(x or '')).encode('ascii','ignore').decode().lower()
    return ' '.join(re.sub(r'[^a-z0-9]+',' ',x).split())


def _fetch(entry):
    try:
        r=requests.get(entry['url'],headers=UA,timeout=35,allow_redirects=True)
        r.raise_for_status()
        if entry['domain'] not in _host(r.url):return None
        parser=_TextExtractor();parser.feed(r.text)
        text=' '.join(parser.text.split())
        if len(text)<80:return None
        return {'url':r.url,'title':parser.title or entry['key'],'text':text}
    except Exception:
        return None


def _terms(category,subcategory,aliases,keywords):
    raw=[subcategory or '',category or '',*(aliases or [])[:5],*(keywords or [])[:25]]
    out=[]
    for x in raw:
        f=_fold(x)
        if len(f)<4:continue
        if f in {'home','travel','fashion','health','beauty','sports','services','digital','kids','baby','food','drink','pets'}:continue
        if f not in out:out.append(f)
    return out


def _match_score(text,terms):
    hay=_fold(text)
    score=0
    matched=[]
    for i,t in enumerate(terms):
        if t and t in hay:
            boost=4 if i<2 else 2 if i<7 else 1
            score+=boost;matched.append(t)
    return score,matched[:12]


def _excerpt(text,terms,limit=2200):
    clean=' '.join(str(text or '').split())
    folded=_fold(clean)
    positions=[]
    for t in terms:
        p=folded.find(t)
        if p>=0:positions.append(p)
    # folded and original offsets are not identical; this only selects a rough local window.
    if positions:
        ratio=len(clean)/max(1,len(folded));center=int(min(positions)*ratio)
        start=max(0,center-450);return clean[start:start+limit]
    anchors=('Retail trade','online shopping','e-commerce','Household Budget','Information and Communication Technologies','ηλεκτρονικού εμπορίου')
    for a in anchors:
        p=clean.lower().find(a.lower())
        if p>=0:return clean[max(0,p-280):max(0,p-280)+limit]
    return clean[:limit]


def _row(entry,page,scope,taxonomy_direct,score,matched):
    authority=float(entry['authority_weight'])
    confidence=(.94 if authority>=.99 else .84) if taxonomy_direct else (.78 if authority>=.99 else .68)
    return {
        'source_kind':entry['source_kind'],
        'source_url':page['url'],
        'title':str(page['title'])[:500],
        'body':_excerpt(page['text'],matched)[:2200],
        'collector':'direct_authoritative_context_v3',
        'confidence':confidence,
        'metadata':{
            'geography':'GR',
            'context_only':True,
            'context_scope':scope,
            'taxonomy_direct':taxonomy_direct,
            'taxonomy_match_score':score,
            'matched_terms':matched,
            'source_registry_key':entry['key'],
            'source_class':entry['source_class'],
            'authority_weight':authority,
            'measure_family':entry['measure_family'],
            'does_not_feed_demand_score':True,
            'context_semantics':'primary-source contextual evidence; never search volume, market size, market share or category demand unless the source directly measures that exact concept',
            'retrieval_version':'greek_authoritative_direct_v3'
        }
    }


def authoritative_context_rows(category,subcategory,aliases,keywords):
    """Read official/industry Greek market context directly from primary sources.

    Taxonomy-direct matches are preferred. If the official source does not publish the
    SocialMarket taxonomy label, a small macro/e-commerce context set is still returned
    as `taxonomy_direct=False`. All rows are `context_only` and excluded from demand,
    competition and pain score arithmetic by the canonical collector.
    """
    terms=_terms(category,subcategory,aliases,keywords)
    direct=[];fallback=[]
    for entry in ENTRYPOINTS:
        page=_fetch(entry)
        if not page:continue
        score,matched=_match_score(page['text'],terms)
        taxonomy_direct=score>=3
        row=_row(entry,page,'category_or_subcategory' if taxonomy_direct else 'greece_macro',taxonomy_direct,score,matched)
        if taxonomy_direct:direct.append((score,entry['fallback_priority'],row))
        else:fallback.append((entry['fallback_priority'],row))

    direct.sort(key=lambda x:(-x[0],x[1]))
    selected=[x[2] for x in direct[:6]]

    # Guarantee a minimal cross-source context frame when reachable: at least two
    # official/public-institution sources and one Greek industry-primary source.
    have_official=sum(1 for x in selected if x['metadata']['source_class'] in {'official_statistics','public_institution'})
    have_industry=any(x['metadata']['source_class']=='industry_primary' for x in selected)
    for _,row in sorted(fallback,key=lambda x:x[0]):
        is_industry=row['metadata']['source_class']=='industry_primary'
        if is_industry and have_industry:continue
        if not is_industry and have_official>=3:continue
        selected.append(row)
        if is_industry:have_industry=True
        else:have_official+=1
        if have_official>=3 and have_industry:break

    seen=set();out=[]
    for row in selected:
        key=(row['source_kind'],row['source_url'])
        if key in seen:continue
        seen.add(key);out.append(row)
    return out[:8]
