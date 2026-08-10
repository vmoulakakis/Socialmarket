import ijson, json, gzip
from pathlib import Path
from datetime import datetime

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
            if event=='start_array' and prefix:return f'{prefix}.item'
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

def clean(v):
    if isinstance(v,str):return v.strip() or None
    return v

def as_float(v):
    if v in (None,''):return None
    try:return float(str(v).replace('%','').replace('€','').replace(' ','').replace(',','.'))
    except:return None

def as_int(v):
    if v in (None,''):return None
    try:return int(float(str(v).replace(',','.')))
    except:return None

def as_bool(v):
    if isinstance(v,bool):return v
    if v is None:return None
    s=str(v).strip().lower()
    if s in {'1','true','yes','y','available','in stock','instock'}:return True
    if s in {'0','false','no','n','unavailable','out of stock','outofstock'}:return False
    return None

def iso_date(v):
    s=clean(v)
    if not s:return None
    for candidate in (s,s.replace('Z','+00:00')):
        try:return datetime.fromisoformat(candidate).isoformat()
        except:pass
    return None

def valid_url(v):
    s=clean(v)
    return s if s and (s.startswith('https://') or s.startswith('http://')) else None

def normalize(r):
    price=as_float(r.get('price'));full=as_float(r.get('full_price'));discount=as_float(r.get('discount'))
    if discount is None and price is not None and full and full>0:discount=round(max(0,(1-price/full)*100),2)
    extra=r.get('extra_images') or []
    if isinstance(extra,str):
        try:extra=json.loads(extra)
        except:extra=[x.strip() for x in extra.split(',') if x.strip()]
    if not isinstance(extra,list):extra=[]
    image=valid_url(r.get('image_url'));thumb=valid_url(r.get('thumb_url'));tracking=valid_url(r.get('tracking_url'))
    stock=as_bool(r.get('in_stock'))
    availability=clean(r.get('availability'))
    if stock is None and availability:
        low=availability.lower()
        if any(x in low for x in ('available','in stock','διαθέ')):stock=True
        elif any(x in low for x in ('unavailable','out of stock','μη διαθέ')):stock=False
    program=clean(r.get('program_name'))
    hard_gate=bool(price is not None and price>=150 and stock is not False and tracking and (image or thumb))
    unknown={k:r.get(k) for k in r.keys() if k not in KNOWN_FIELDS}
    if r.get('custom') is not None:unknown['custom']=r.get('custom')
    return {
      'external_product_id':str(r.get('product_id') or r.get('id') or ''),
      'product_name':clean(r.get('product_name') or r.get('name')) or 'Unnamed product',
      'model_name':clean(r.get('model_name')),'description':clean(r.get('description')),'brand_name':clean(r.get('brand_name')),
      'program_name':program,'merchant_name':program,'category_raw':clean(r.get('category')),'price':price,'full_price':full,
      'discount_pct':discount,'currency':clean(r.get('currency')) or 'EUR','in_stock':stock,'availability':availability,
      'valid_from':iso_date(r.get('valid_from')),'valid_to':iso_date(r.get('valid_to')),'on_sale':as_bool(r.get('on_sale')),
      'times_bought':as_int(r.get('times_bought')),'tracking_url':tracking,'image_url':image,'thumb_url':thumb,'extra_images':extra,
      'city':clean(r.get('city')),'longitude':as_float(r.get('longitude')),'latitude':as_float(r.get('latitude')),'address':clean(r.get('address')),
      'colour':clean(r.get('colour')),'size':clean(r.get('size')),'extra_json':unknown,'is_active':True,'hard_gate_pass':hard_gate
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
