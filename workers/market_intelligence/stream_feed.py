import ijson, json, gzip, os
from pathlib import Path

KNOWN_FIELDS={'product_id','model_name','product_name','description','category','brand_name','tracking_url','thumb_url','image_url','in_stock','availability','valid_from','valid_to','on_sale','currency','price','full_price','discount','city','times_bought','longitude','latitude','address','size','colour','program_name','custom','extra_images'}

def _first_non_ws(path):
    with open(path,'rb') as f:
        while True:
            b=f.read(1)
            if not b:return b''
            if not b.isspace():return b

def discover_array_prefix(path,max_events=5000):
    if _first_non_ws(path)==b'[':return 'item'
    with open(path,'rb') as f:
        for n,(prefix,event,value) in enumerate(ijson.parse(f)):
            if event=='start_array' and prefix:
                return f'{prefix}.item'
            if n>=max_events:break
    return None

def iter_records(path):
    first=_first_non_ws(path)
    if first==b'[':
        with open(path,'rb') as f:yield from ijson.items(f,'item');return
    if first==b'{':
        prefix=discover_array_prefix(path)
        if prefix:
            with open(path,'rb') as f:yield from ijson.items(f,prefix);return
        with open(path,'rb') as f:
            for _,value in ijson.kvitems(f,''):
                if isinstance(value,dict):yield value
        return
    raise ValueError('Unsupported JSON root; expected array or object')

def normalize(r):
    def n(v):
        if isinstance(v,str):return v.strip() or None
        return v
    price=n(r.get('price'));full=n(r.get('full_price'));discount=n(r.get('discount'))
    try:price=float(str(price).replace(',','.')) if price is not None else None
    except:price=None
    try:full=float(str(full).replace(',','.')) if full is not None else None
    except:full=None
    try:discount=float(str(discount).replace('%','').replace(',','.')) if discount is not None else None
    except:discount=None
    if discount is None and price is not None and full and full>0:discount=round(max(0,(1-price/full)*100),2)
    extra=r.get('extra_images') or []
    if isinstance(extra,str):
        try:extra=json.loads(extra)
        except:extra=[x.strip() for x in extra.split(',') if x.strip()]
    return {
      'external_product_id':str(r.get('product_id') or r.get('id') or ''),
      'product_name':n(r.get('product_name') or r.get('name')) or 'Unnamed product',
      'model_name':n(r.get('model_name')),'description':n(r.get('description')),'brand_name':n(r.get('brand_name')),
      'program_name':n(r.get('program_name')),'category_raw':n(r.get('category')),'price':price,'full_price':full,
      'discount_percent':discount,'currency':n(r.get('currency')) or 'EUR','in_stock':r.get('in_stock'),
      'availability':n(r.get('availability')),'valid_from':n(r.get('valid_from')),'valid_to':n(r.get('valid_to')),
      'times_bought':r.get('times_bought'),'tracking_url':n(r.get('tracking_url')),'image_url':n(r.get('image_url')),
      'thumb_url':n(r.get('thumb_url')),'extra_images':extra,'city':n(r.get('city')),'colour':n(r.get('colour')),
      'size':n(r.get('size')),'raw':{k:r.get(k) for k in r.keys() if k not in KNOWN_FIELDS}
    }

def shard(path,out_dir,shard_size=25000):
    out=Path(out_dir);out.mkdir(parents=True,exist_ok=True);fh=None;count=0;shard_no=0
    try:
        for record in iter_records(path):
            if count%shard_size==0:
                if fh:fh.close()
                shard_no+=1;fh=gzip.open(out/f'products-{shard_no:05d}.jsonl.gz','wt',encoding='utf-8')
            fh.write(json.dumps(normalize(record),ensure_ascii=False,default=str)+'\n');count+=1
    finally:
        if fh:fh.close()
    return {'records':count,'shards':shard_no,'output':str(out)}

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('path');p.add_argument('--out',default='shards');p.add_argument('--size',type=int,default=25000);a=p.parse_args()
    print(json.dumps(shard(a.path,a.out,a.size)))
