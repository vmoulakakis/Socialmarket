from __future__ import annotations

"""Direct public-social acquisition for Category Pain V4.4.

SearXNG remains useful discovery, but social evidence must not depend on search
index coverage alone. This module adds two independent public acquisition paths:
- Reddit public JSON search for user-authored posts
- YouTube public search/comments via yt-dlp

Only product/category-bound first-person or purchase/use pain statements survive
the existing V4 consumer scorer. No likes/views are used as pain proof.
"""

import hashlib
import json
import subprocess
from urllib.parse import quote

import requests
import consumer_evidence_v4 as consumer

UA={'User-Agent':'SocialMarketConsumerResearch/4.4 (+public evidence; contact admin)'}
_ORIGINAL_COLLECT=consumer.collect_consumer_evidence
_APPLIED=False


def _row(source_url:str,title:str,body:str,keywords:list[str],family:str,collector:str,metadata:dict|None=None,base_confidence:float=.72):
    score,pain,purchase,first=consumer._consumer_score(body,title,keywords,family,source_url)
    if score < 10:return None
    digest=hashlib.sha256(body.encode('utf-8','ignore')).hexdigest()
    return {
        'source_kind':'pain_candidate',
        'source_url':source_url,
        'title':str(title or '')[:500],
        'body':str(body or '')[:1600],
        'collector':collector,
        'confidence':round(min(.94,base_confidence+min(.07,score*.002)),3),
        'content_hash':digest,
        'metadata':{
            'geography':'GR','source_family':family,'evidence_mode':'direct_public_social_text',
            'consumer_text':True,'page_extracted':True,'pain_language':pain[:12],
            'purchase_language':purchase[:10],'first_person_signal':first,
            'consumer_language_score':score,'retrieval_version':'consumer_evidence_v4.4',
            'metric_semantics':'observed public user statement; not a population estimate',
            **(metadata or {})
        }
    }


def _reddit(aliases:list[str],keywords:list[str],limit:int=24):
    out=[];seen=set()
    for term in aliases[:3]:
        try:
            r=requests.get('https://www.reddit.com/search.json',params={
                'q':f'"{term}" Greece','sort':'new','t':'year','limit':20,'raw_json':1
            },headers=UA,timeout=20)
            if not r.ok:continue
            children=((r.json().get('data') or {}).get('children') or [])
            for item in children:
                d=item.get('data') or {}
                title=str(d.get('title') or '')
                body=str(d.get('selftext') or '')
                if len(body.strip())<35:continue
                permalink=str(d.get('permalink') or '')
                url='https://www.reddit.com'+permalink if permalink.startswith('/') else str(d.get('url') or '')
                row=_row(url,title,body,keywords,'social_forum','reddit_public_json_v44',{
                    'query_term':term,'platform':'reddit','subreddit':d.get('subreddit'),
                    'published_utc':d.get('created_utc')
                },.76)
                if not row:continue
                key=(row['source_url'],row['content_hash'])
                if key in seen:continue
                seen.add(key);out.append(row)
                if len(out)>=limit:return out
        except Exception:
            continue
    return out


def _youtube_search(term:str):
    query=f'{term} review ελληνικά εμπειρία'
    try:
        p=subprocess.run([
            'yt-dlp','--flat-playlist','--dump-json','--no-warnings',f'ytsearch3:{query}'
        ],capture_output=True,text=True,timeout=45,check=False)
        if p.returncode!=0:return []
        found=[]
        for line in p.stdout.splitlines():
            try:
                j=json.loads(line)
                vid=j.get('id')
                if vid:found.append({'url':f'https://www.youtube.com/watch?v={vid}','title':j.get('title') or ''})
            except Exception:pass
        return found[:2]
    except Exception:
        return []


def _youtube_video(video:dict,term:str,keywords:list[str],limit:int=24):
    try:
        p=subprocess.run([
            'yt-dlp','--skip-download','--dump-single-json','--no-warnings',
            '--extractor-args','youtube:max_comments=30,all,all,30',video['url']
        ],capture_output=True,text=True,timeout=90,check=False)
        if p.returncode!=0 or not p.stdout.strip():return []
        j=json.loads(p.stdout)
        title=str(j.get('title') or video.get('title') or '')
        url=str(j.get('webpage_url') or video['url'])
        out=[];seen=set()
        for c in (j.get('comments') or [])[:30]:
            text=str(c.get('text') or '').strip()
            if len(text)<35:continue
            row=_row(url,title,text,keywords,'social_video','yt_dlp_comments_v44',{
                'query_term':term,'platform':'youtube','video_id':j.get('id'),
                'comment_id':c.get('id'),'published_at':c.get('timestamp')
            },.74)
            if not row:continue
            key=row['content_hash']
            if key in seen:continue
            seen.add(key);out.append(row)
            if len(out)>=limit:break
        return out
    except Exception:
        return []


def _youtube(aliases:list[str],keywords:list[str],limit:int=30):
    out=[];seen=set();videos_seen=set()
    for term in aliases[:3]:
        for video in _youtube_search(term):
            if video['url'] in videos_seen:continue
            videos_seen.add(video['url'])
            for row in _youtube_video(video,term,keywords,12):
                key=(row['source_url'],row['content_hash'])
                if key in seen:continue
                seen.add(key);out.append(row)
                if len(out)>=limit:return out
            # one successfully attempted video per alias keeps runtime bounded
            break
    return out


def collect_consumer_evidence(category:str,subcategory:str|None,aliases:list[str],keywords:list[str],max_rows:int=100):
    base=_ORIGINAL_COLLECT(category,subcategory,aliases,keywords,max_rows=max_rows)
    direct=_reddit(aliases,keywords,24)+_youtube(aliases,keywords,30)
    pains=[x for x in base if x.get('source_kind')=='pain_candidate']
    diagnostics=[x for x in base if x.get('source_kind')!='pain_candidate']
    seen={(consumer.host(x.get('source_url')),x.get('content_hash')) for x in pains}
    for e in sorted(direct,key=lambda x:(x.get('confidence',0),x.get('metadata',{}).get('consumer_language_score',0)),reverse=True):
        key=(consumer.host(e.get('source_url')),e.get('content_hash'))
        if key in seen:continue
        seen.add(key);pains.append(e)
        if len(pains)>=max_rows:break
    return pains+diagnostics[:min(40,max_rows//2)]


def apply():
    global _APPLIED
    if _APPLIED:return
    consumer.collect_consumer_evidence=collect_consumer_evidence
    _APPLIED=True
