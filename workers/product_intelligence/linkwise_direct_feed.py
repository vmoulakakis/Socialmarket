"""Direct Linkwise dynamic-feed transport.

The Google Drive 3.84 GB JSON is a cache/snapshot. Production prefers the live
Linkwise joined-program feed and retains Drive only as an emergency fallback.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path

import requests

CLIENT='CD104'
CATEGORY_IDS='3,67,25,27,29,33,63,147,87,89,99,103,109,117,119'
BASE='https://affiliate.linkwi.se/feeds/1.2/{client}/programs-joined/columns-{columns}/catinc-{categories}/catex-0/proginc-0/progex-0/feed.json'

# Verified against the live joined-program feed on 2026-08-16. Unsupported tags
# are deliberately omitted rather than synthesized from product text.
CORE_FIELDS=(
    'product_id','product_name','description','category','image_url','in_stock','availability',
    'valid_from','valid_to','price','full_price','discount','times_bought','size','colour','sku'
)
VERIFIED_OPTIONAL_FIELDS=('thumb_url',)
OPTIONAL_FIELD_CANDIDATES=('brand','brand_name','manufacturer','maker','model','model_name','mpn','ean','gtin','currency','thumb_url')
DEEPLINK_CANDIDATES=('deep_link','deeplink','aw_deep_link','tracking_url')
MINIMUM_CONTRACT={'product_id','product_name','category','price','tracking_url'}


def feed_url(columns,client=CLIENT,categories=CATEGORY_IDS):
    return BASE.format(client=client,columns=','.join(columns),categories=categories)


def _session():
    s=requests.Session();s.headers.update({'User-Agent':'SocialMarketAI/3.6 direct-feed','Accept-Encoding':'gzip, deflate'});return s


def _sample(url,limit=524288,session=None):
    s=session or _session()
    with s.get(url,stream=True,timeout=(15,45),allow_redirects=True) as r:
        result={'status':r.status_code,'content_type':r.headers.get('content-type'),'content_length':r.headers.get('content-length')}
        if r.status_code>=400:result['error']=r.text[:240];return result
        buf=b''
        for chunk in r.iter_content(32768):
            if chunk:
                buf+=chunk
                if len(buf)>=limit:break
        text=buf.decode('utf-8','replace')
        result['keys']=sorted(set(re.findall(r'"([A-Za-z0-9_]+)"\s*:',text)))[:120]
        result['bytes_sampled']=len(buf)
        result['linkwise_tracking_shape']=bool(re.search(r'https?[^"\\]*(?:go|affiliate)\.linkwi\.se',text,re.I))
        result['image_shape']=bool(re.search(r'https?[^"\\]+\.(?:jpg|jpeg|png|webp)(?:[?"\\]|$)',text,re.I))
        return result


def probe_field(field,session=None):
    result=_sample(feed_url(('product_id',field,'price')),196608,session);result['field']=field;result['field_present']=field in (result.get('keys') or []);return result


def resolve_deeplink_field():
    s=_session();results=[]
    for field in DEEPLINK_CANDIDATES:
        result=probe_field(field,s);results.append(result);print(json.dumps({'probe':result},ensure_ascii=False),flush=True)
        if result.get('status')==200 and result.get('field_present') and result.get('linkwise_tracking_shape'):return field,results
    present=[x for x in results if x.get('status')==200 and x.get('field_present')]
    if len(present)==1:return str(present[0]['field']),results
    raise RuntimeError('Could not resolve one unambiguous Linkwise deeplink field: '+json.dumps(results,ensure_ascii=False))


def probe_optional_fields():
    result=_sample(feed_url(('product_id','price',*OPTIONAL_FIELD_CANDIDATES)),524288)
    keys=set(result.get('keys') or []);supported=tuple(x for x in OPTIONAL_FIELD_CANDIDATES if x in keys);result['supported_optional_fields']=supported
    print(json.dumps({'optional_field_probe':result},ensure_ascii=False),flush=True);return supported,result


def direct_columns():
    explicit=os.getenv('LINKWISE_DEEPLINK_FIELD','').strip();field=explicit or 'tracking_url'
    optional_env=os.getenv('LINKWISE_OPTIONAL_FIELDS','').strip()
    optional=tuple(x.strip() for x in optional_env.split(',') if x.strip()) if optional_env else VERIFIED_OPTIONAL_FIELDS
    invalid=[x for x in optional if x not in VERIFIED_OPTIONAL_FIELDS]
    if invalid:raise RuntimeError(f'unverified Linkwise optional fields requested: {invalid}')
    return (*CORE_FIELDS,*optional,field),field


def probe_contract(deeplink_field='tracking_url'):
    supported_optional,_=probe_optional_fields();columns=(*CORE_FIELDS,*supported_optional,deeplink_field);result=_sample(feed_url(columns),786432)
    keys=set(result.get('keys') or []);result['requested_columns']=list(columns);result['present_columns']=sorted(keys)
    missing=sorted(MINIMUM_CONTRACT-keys);has_image='image_url' in keys and bool(result.get('image_shape'))
    result['missing_required']=missing;result['has_usable_image_field']=has_image;result['supported_optional_fields']=supported_optional
    result['contract_ok']=result.get('status')==200 and not missing and has_image and bool(result.get('linkwise_tracking_shape'))
    print(json.dumps({'production_contract_probe':result},ensure_ascii=False),flush=True)
    if not result['contract_ok']:raise RuntimeError('Direct Linkwise production field contract failed: '+json.dumps(result,ensure_ascii=False))
    return result


def download(output,minimum_bytes=10_000_000,max_attempts=3):
    columns,deeplink_field=direct_columns();url=feed_url(columns);path=Path(output);tmp=path.with_suffix(path.suffix+'.part');last=None
    for attempt in range(1,max_attempts+1):
        try:
            if tmp.exists():tmp.unlink()
            with _session().get(url,stream=True,timeout=(30,900),allow_redirects=True) as r:
                r.raise_for_status();written=0
                with tmp.open('wb') as f:
                    for chunk in r.iter_content(1024*1024):
                        if not chunk:continue
                        f.write(chunk);written+=len(chunk)
                        if written and written%(250*1024*1024)<1024*1024:print(json.dumps({'direct_linkwise_download_bytes':written,'attempt':attempt}),flush=True)
            if written<minimum_bytes:raise RuntimeError(f'direct Linkwise response unexpectedly small: {written}')
            tmp.replace(path)
            print(json.dumps({'direct_linkwise_feed':{'bytes':written,'deeplink_field':deeplink_field,'columns':list(columns),'source':'affiliate.linkwi.se'}}),flush=True)
            return {'path':str(path),'bytes':written,'deeplink_field':deeplink_field,'columns':list(columns)}
        except Exception as exc:
            last=exc;print(json.dumps({'warning':'direct_linkwise_download_attempt_failed','attempt':attempt,'error':str(exc)[:600]}),flush=True)
            if attempt<max_attempts:time.sleep(min(20,attempt*5))
    raise RuntimeError(f'direct Linkwise feed download failed after {max_attempts} attempts: {last}')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--probe',action='store_true');ap.add_argument('--output',default=os.getenv('PRODUCT_SOURCE_FEED','linkwise-products.json'));args=ap.parse_args()
    if args.probe:
        field,results=resolve_deeplink_field();contract=probe_contract(field);print(json.dumps({'ok':True,'resolved_deeplink_field':field,'contract_ok':contract['contract_ok'],'supported_optional_fields':contract['supported_optional_fields'],'field_results':results},ensure_ascii=False));return 0
    download(args.output);return 0


if __name__=='__main__':raise SystemExit(main())
