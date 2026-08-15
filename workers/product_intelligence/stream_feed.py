import ijson, json, unicodedata, urllib.parse, hashlib
from datetime import datetime
from zoneinfo import ZoneInfo

KNOWN_FIELDS={
 'product_id','id','model_name','product_name','name','description','category','brand_name','tracking_url',
 'thumb_url','image_url','in_stock','availability','valid_from','valid_to','on_sale','currency','price',
 'full_price','discount','city','times_bought','longitude','latitude','address','size','colour','program_name',
 'custom','extra_images','ean','gtin','mpn','sku'
}
ATHENS=ZoneInfo('Europe/Athens')


def _first_non_ws(path):
    with open(path,'rb') as f:
        while True:
            b=f.read(1)
            if not b:return b''
            if not b.isspace():return b


def discover_array_prefix(path,max_events=5000):
    if _first_non_ws(path)==b'[':return 'item'
    with open(path,'rb') as f:
        for n,(prefix,event,_value) in enumerate(ijson.parse(f)):
            if event=='start_array' and prefix:return f'{prefix}.item'
            if n>=max_events:break
    return None


def iter_records(path):
    first=_first_non_ws(path)
    if first==b'[':
        with open(path,'rb') as f:
            yield from ijson.items(f,'item')
        return
    if first==b'{':
        prefix=discover_array_prefix(path)
        if prefix:
            with open(path,'rb') as f:
                yield from ijson.items(f,prefix)
            return
        with open(path,'rb') as f:
            for _,value in ijson.kvitems(f,''):
                if isinstance(value,dict):yield value
        return
    raise ValueError('Unsupported JSON root; expected array or object')


def clean(v):
    if isinstance(v,str):return v.strip() or None
    return v


def fold_text(v):
    s=str(v or '').lower()
    return ''.join(ch for ch in unicodedata.normalize('NFKD',s) if not unicodedata.combining(ch))


def as_float(v):
    if v in (None,''):return None
    s=str(v).strip().replace('€','').replace('%','').replace(' ','')
    if ',' in s and '.' in s:
        if s.rfind(',')>s.rfind('.'):
            s=s.replace('.','').replace(',','.')
        else:
            s=s.replace(',','')
    else:
        s=s.replace(',','.')
    try:return float(s)
    except:return None


def as_int(v):
    x=as_float(v)
    return int(x) if x is not None else None


def as_bool(v):
    if isinstance(v,bool):return v
    if v is None:return None
    s=fold_text(v).strip()
    if s in {'1','true','yes','y','available','in stock','instock','διαθεσιμο','διαθεσιμη'}:return True
    if s in {'0','false','no','n','unavailable','out of stock','outofstock','μη διαθεσιμο','μη διαθεσιμη'}:return False
    return None


def parse_datetime(v):
    s=clean(v)
    if not s:return None
    for candidate in (s,s.replace('Z','+00:00')):
        try:return datetime.fromisoformat(candidate)
        except:pass
    for fmt in ('%d/%m/%Y','%Y/%m/%d','%d-%m-%Y','%Y-%m-%d %H:%M:%S'):
        try:return datetime.strptime(s,fmt)
        except:pass
    return None


def iso_datetime(v):
    dt=parse_datetime(v)
    return dt.isoformat() if dt else None


def valid_url(v):
    s=clean(v)
    return s if s and (s.startswith('https://') or s.startswith('http://')) else None


def normalize_domain(v):
    s=str(v or '').strip().lower().rstrip('.')
    if '://' in s:
        try:s=urllib.parse.urlparse(s).hostname or ''
        except:s=''
    s=s.split(':',1)[0].removeprefix('www.')
    return s or None


def target_url(tracking_url):
    """Return the decoded merchant destination carried by a Linkwise tracking URL.

    The real 3.84 GB feed has no program_name field; merchant identity is carried by
    tracking_url query parameters such as lnkurl. Decode conservatively and never
    follow the URL over the network.
    """
    try:
        raw=str(tracking_url or '').strip()
        if not raw:return None
        u=urllib.parse.urlparse(raw)
        q=urllib.parse.parse_qs(u.query,keep_blank_values=False)
        target=(q.get('lnkurl') or q.get('url') or q.get('redirect') or [None])[0]
        if not target:return None
        for _ in range(3):
            decoded=urllib.parse.unquote(target)
            if decoded==target:break
            target=decoded
        t=urllib.parse.urlparse(target)
        if t.scheme in ('http','https') and t.hostname:return target
    except:pass
    return None


def target_domain(tracking_url):
    t=target_url(tracking_url)
    if not t:return None
    try:return normalize_domain(urllib.parse.urlparse(t).hostname)
    except:return None


def linkwise_route(tracking_url):
    """Extract stable Linkwise route hints, e.g. /z/205-0/CD104/ -> 205-0/CD104."""
    try:
        u=urllib.parse.urlparse(str(tracking_url or ''))
        parts=[urllib.parse.unquote(x) for x in u.path.split('/') if x]
        if len(parts)>=3 and parts[0].lower()=='z':
            return '/'.join(parts[1:3])
    except:pass
    return None


def normalize(raw):
    price=as_float(raw.get('price'))
    full=as_float(raw.get('full_price'))
    raw_discount=as_float(raw.get('discount'))
    discount=None
    if price is not None and full and full>0 and price<=full:
        discount=round(max(0.0,(1-price/full)*100),3)
    elif raw_discount is not None:
        discount=max(0.0,raw_discount)

    extra=raw.get('extra_images') or []
    if isinstance(extra,str):
        try:extra=json.loads(extra)
        except:extra=[x.strip() for x in extra.split(',') if x.strip()]
    if not isinstance(extra,list):extra=[]

    image=valid_url(raw.get('image_url'))
    thumb=valid_url(raw.get('thumb_url'))
    tracking=valid_url(raw.get('tracking_url'))
    stock=as_bool(raw.get('in_stock'))
    availability=clean(raw.get('availability'))
    if stock is None and availability:
        low=fold_text(availability)
        if any(x in low for x in ('available','in stock','διαθε')):stock=True
        elif any(x in low for x in ('unavailable','out of stock','μη διαθε')):stock=False

    program=clean(raw.get('program_name'))
    category=clean(raw.get('category'))
    name=clean(raw.get('product_name') or raw.get('name')) or 'Unnamed product'
    description=clean(raw.get('description'))
    gtin=clean(raw.get('gtin') or raw.get('ean'))
    mpn=clean(raw.get('mpn') or raw.get('sku'))
    destination=target_url(tracking)
    destination_domain=target_domain(tracking)
    route=linkwise_route(tracking)

    unknown={k:raw.get(k) for k in raw.keys() if k not in KNOWN_FIELDS}
    if raw.get('custom') is not None:unknown['custom']=raw.get('custom')

    identity='|'.join(str(x or '') for x in (
        program,destination_domain,route,raw.get('product_id') or raw.get('id'),gtin,mpn,name,raw.get('model_name'),price,tracking
    ))
    record_hash=hashlib.sha256(identity.encode('utf-8','ignore')).hexdigest()

    return {
      'external_product_id':str(raw.get('product_id') or raw.get('id') or ''),
      'product_name':name,'model_name':clean(raw.get('model_name')),'description':description,
      'brand_name':clean(raw.get('brand_name')),'program_name':program,'merchant_name':program,
      'category_raw':category,'price':price,'full_price':full,'discount_pct':discount,
      'currency':clean(raw.get('currency')) or 'EUR','in_stock':stock,'availability':availability,
      'valid_from':iso_datetime(raw.get('valid_from')),'valid_to':iso_datetime(raw.get('valid_to')),
      'times_bought':as_int(raw.get('times_bought')),'tracking_url':tracking,'target_url':destination,
      'target_domain':destination_domain,'linkwise_route':route,
      'image_url':image,'thumb_url':thumb,'extra_images':extra,'colour':clean(raw.get('colour')),
      'size':clean(raw.get('size')),'gtin':gtin,'mpn':mpn,'extra_json':unknown,'source_record_hash':record_hash
    }
