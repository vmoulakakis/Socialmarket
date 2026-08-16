"""Direct Linkwise dynamic-feed transport.

Production prefers the live Linkwise joined-program feed. The category universe is
fetched as deterministic parallel shards, then concatenated as one JSON array.
Google Drive remains emergency fallback at workflow level only.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import shutil
import time
from pathlib import Path

import requests

CLIENT='CD104'
CATEGORY_IDS='3,67,25,27,29,33,63,147,87,89,99,103,109,117,119'
BASE='https://affiliate.linkwi.se/feeds/1.2/{client}/programs-joined/columns-{columns}/catinc-{categories}/catex-0/proginc-0/progex-0/feed.json'
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
        result['root_char']=next((chr(b) for b in buf if chr(b).strip()),'')
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
    result['contract_ok']=result.get('status')==200 and not missing and has_image and bool(result.get('linkwise_tracking_shape')) and result.get('root_char')=='['
    print(json.dumps({'production_contract_probe':result},ensure_ascii=False),flush=True)
    if not result['contract_ok']:raise RuntimeError('Direct Linkwise production field contract failed: '+json.dumps(result,ensure_ascii=False))
    return result


def _download_shard(category,columns,directory,max_attempts=3):
    path=directory/f'cat-{category}.json';last=None
    for attempt in range(1,max_attempts+1):
        try:
            path.unlink(missing_ok=True)
            with _session().get(feed_url(columns,categories=category),stream=True,timeout=(30,900),allow_redirects=True) as r:
                r.raise_for_status();written=0
                with path.open('wb') as f:
                    for chunk in r.iter_content(1024*1024):
                        if chunk:f.write(chunk);written+=len(chunk)
            if written<2:raise RuntimeError(f'empty shard for category {category}')
            with path.open('rb') as f:
                while True:
                    b=f.read(1)
                    if not b:raise RuntimeError(f'empty shard for category {category}')
                    if not b.isspace():break
            if b!=b'[':raise RuntimeError(f'non-array shard root for category {category}: {b!r}')
            print(json.dumps({'linkwise_shard_complete':category,'bytes':written,'attempt':attempt}),flush=True)
            return category,path,written
        except Exception as exc:
            last=exc;print(json.dumps({'warning':'linkwise_shard_attempt_failed','category':category,'attempt':attempt,'error':str(exc)[:500]}),flush=True)
            if attempt<max_attempts:time.sleep(min(15,attempt*4))
    raise RuntimeError(f'category {category} failed after {max_attempts} attempts: {last}')


def _array_body_bounds(path):
    with path.open('rb') as f:
        pos=0
        while True:
            b=f.read(1)
            if not b:raise RuntimeError(f'empty JSON shard: {path}')
            if not b.isspace():break
            pos+=1
        if b!=b'[':raise RuntimeError(f'JSON shard root is not array: {path}')
        start=f.tell()
        f.seek(0,2);end=f.tell();p=end-1
        while p>=start:
            f.seek(p);b=f.read(1)
            if not b.isspace():break
            p-=1
        if b!=b']':raise RuntimeError(f'JSON shard is incomplete: {path}')
        body_end=p
        p=start
        first_non_ws=None
        while p<body_end:
            f.seek(p);b=f.read(1)
            if not b.isspace():first_non_ws=p;break
            p+=1
        return start,body_end,first_non_ws is not None


def _copy_range(src,dst,start,end,chunk_size=4*1024*1024):
    with src.open('rb') as f:
        f.seek(start);remaining=end-start
        while remaining>0:
            data=f.read(min(chunk_size,remaining))
            if not data:raise RuntimeError(f'unexpected EOF while merging {src}')
            dst.write(data);remaining-=len(data)


def _merge_shards(shards,output):
    tmp=Path(str(output)+'.part');tmp.unlink(missing_ok=True);total=0;nonempty=0
    with tmp.open('wb') as out:
        out.write(b'[')
        for category,path,written in sorted(shards,key=lambda x:int(x[0])):
            start,end,has_body=_array_body_bounds(path);total+=written
            if not has_body:continue
            if nonempty:out.write(b',')
            _copy_range(path,out,start,end);nonempty+=1
        out.write(b']')
    tmp.replace(output)
    return total,nonempty


def download(output,minimum_bytes=10_000_000,max_attempts=3):
    columns,deeplink_field=direct_columns();path=Path(output);shard_dir=Path(str(path)+'.shards');shutil.rmtree(shard_dir,ignore_errors=True);shard_dir.mkdir(parents=True,exist_ok=True)
    categories=[x.strip() for x in CATEGORY_IDS.split(',') if x.strip()];workers=max(1,min(8,int(os.getenv('LINKWISE_SHARD_WORKERS','6'))));shards=[]
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures={pool.submit(_download_shard,c,columns,shard_dir,max_attempts):c for c in categories}
            for future in concurrent.futures.as_completed(futures):shards.append(future.result())
        total_shard_bytes,nonempty=_merge_shards(shards,path);merged_bytes=path.stat().st_size
        if merged_bytes<minimum_bytes:raise RuntimeError(f'direct Linkwise merged response unexpectedly small: {merged_bytes}')
        print(json.dumps({'direct_linkwise_feed':{'merged_bytes':merged_bytes,'total_shard_bytes':total_shard_bytes,'shards':len(shards),'nonempty_shards':nonempty,'workers':workers,'deeplink_field':deeplink_field,'columns':list(columns),'source':'affiliate.linkwi.se_parallel_categories'}},flush=True))
        return {'path':str(path),'bytes':merged_bytes,'deeplink_field':deeplink_field,'columns':list(columns),'shards':len(shards)}
    finally:
        shutil.rmtree(shard_dir,ignore_errors=True)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--probe',action='store_true');ap.add_argument('--output',default=os.getenv('PRODUCT_SOURCE_FEED','linkwise-products.json'));args=ap.parse_args()
    if args.probe:
        field,results=resolve_deeplink_field();contract=probe_contract(field);print(json.dumps({'ok':True,'resolved_deeplink_field':field,'contract_ok':contract['contract_ok'],'supported_optional_fields':contract['supported_optional_fields'],'field_results':results},ensure_ascii=False));return 0
    download(args.output);return 0


if __name__=='__main__':raise SystemExit(main())
