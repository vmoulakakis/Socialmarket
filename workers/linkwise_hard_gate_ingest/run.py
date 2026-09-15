import os,json,hashlib,requests,ijson
from decimal import Decimal,InvalidOperation
from collections import defaultdict
from datetime import datetime,timezone

FEED_URL=os.environ['LINKWISE_FEED_URL']
SUPABASE_URL=os.environ['SUPABASE_URL'].rstrip('/')
SERVICE_KEY=os.environ['SUPABASE_SERVICE_ROLE_KEY']
MIN_COMMISSION=Decimal(os.getenv('MIN_EXPECTED_COMMISSION_EUR','10'))
MAX_PER_MERCHANT=int(os.getenv('MAX_PRODUCTS_PER_MERCHANT','30'))
BATCH=int(os.getenv('UPSERT_BATCH_SIZE','500'))
SOURCE='linkwise'
H={'apikey':SERVICE_KEY,'Authorization':f'Bearer {SERVICE_KEY}','Content-Type':'application/json'}

def api(method,path,params=None,data=None,prefer=None):
    h=dict(H)
    if prefer:h['Prefer']=prefer
    r=requests.request(method,f'{SUPABASE_URL}/rest/v1/{path}',headers=h,params=params,json=data,timeout=120)
    r.raise_for_status(); return r.json() if r.content else None

def dec(v):
    try:return Decimal(str(v))
    except (InvalidOperation,TypeError,ValueError):return None

def truthy(v): return str(v).strip().lower() in {'1','true','yes','y','in stock','available'}

def commission_map():
    rows=api('GET','merchant_profiles',params={'select':'id,affiliate_program_id,legacy_merchant_id,merchant_name,active,program_approved,tracking_verified,flat_commission_min_eur,flat_commission_max_eur,percent_commission_min,percent_commission_max','limit':'1000'}) or []
    out={}
    for x in rows:
        for k in (x.get('affiliate_program_id'),x.get('legacy_merchant_id')):
            if k is not None: out[str(k)]=x
    return out

def expected_commission(p,m):
    price=dec(p.get('price'))
    if price is None or price<=0:return None,None
    flat=dec(m.get('flat_commission_min_eur'))
    pct=dec(m.get('percent_commission_min'))
    vals=[]
    if flat is not None: vals.append((flat,'flat_min'))
    if pct is not None: vals.append((price*pct/Decimal('100'),'percent_min'))
    return max(vals,key=lambda x:x[0]) if vals else (None,None)

def stable_hash(p,expected):
    keys=('product_id','program_id','sku','model_name','product_name','category','price','discount','in_stock','valid_from','valid_to','tracking_url')
    s='|'.join(str(p.get(k) or '') for k in keys)+f'|{expected}'
    return hashlib.sha256(s.encode()).hexdigest()

def flush(rows):
    if not rows:return
    api('POST','commerce_feed_eligible_offers',params={'on_conflict':'source_key,program_id,source_product_id'},data=rows,prefer='resolution=merge-duplicates,return=minimal')

def main():
    merchants=commission_map(); counts=defaultdict(int); accepted=defaultdict(list); out=[]
    run=(api('POST','commerce_feed_runs',data={'source_key':SOURCE,'run_type':'bootstrap','status':'running','min_commission_eur':float(MIN_COMMISSION),'batch_size':BATCH},prefer='return=representation') or [])[0]
    rid=run['id']
    try:
        with requests.get(FEED_URL,stream=True,timeout=(30,900)) as r:
            r.raise_for_status(); r.raw.decode_content=True
            for p in ijson.items(r.raw,'item'):
                counts['scanned']+=1
                pid=p.get('product_id'); prog=p.get('program_id'); price=dec(p.get('price'))
                if not pid or not prog or not p.get('tracking_url') or price is None or price<=0:
                    counts['invalid']+=1; continue
                if not truthy(p.get('in_stock')):
                    counts['inactive']+=1; continue
                m=merchants.get(str(prog))
                if not m or not m.get('active'):
                    counts['commission_unknown']+=1; continue
                exp,basis=expected_commission(p,m)
                if exp is None:
                    counts['commission_unknown']+=1; continue
                if exp<MIN_COMMISSION:
                    counts['commission_rejected']+=1; continue
                mid=str(m['id'])
                candidate={'source_key':SOURCE,'source_product_id':str(pid),'program_id':str(prog),'merchant_id':m['id'],'sku':p.get('sku'),'model_name':p.get('model_name'),'product_name':p.get('product_name'),'category':p.get('category'),'price_eur':float(price),'expected_commission_eur':float(exp),'commission_basis':basis,'tracking_url':p.get('tracking_url'),'image_url':p.get('image_url') or p.get('thumb_url'),'in_stock':True,'valid_from':p.get('valid_from') or None,'valid_to':p.get('valid_to') or None,'on_sale':truthy(p.get('on_sale')),'discount':dec(p.get('discount')) and float(dec(p.get('discount'))),'times_bought':int(dec(p.get('times_bought')) or 0),'content_hash':stable_hash(p,exp),'is_active':True,'intelligence_status':'pending'}
                accepted[mid].append(candidate)
        # hard cap: retain strongest commercial candidates per merchant before AI layer
        for mid,rows in accepted.items():
            rows.sort(key=lambda x:(x['expected_commission_eur'],x.get('times_bought',0),x['price_eur']),reverse=True)
            for x in rows[:MAX_PER_MERCHANT]:
                out.append(x)
                if len(out)>=BATCH: flush(out); counts['inserted']+=len(out); out=[]
        flush(out); counts['inserted']+=len(out); counts['eligible']=counts['inserted']
        api('PATCH','commerce_feed_runs',params={'id':f'eq.{rid}'},data={**counts,'status':'completed','finished_at':datetime.now(timezone.utc).isoformat(),'checkpoint':{'max_products_per_merchant':MAX_PER_MERCHANT}},prefer='return=minimal')
        print(json.dumps(dict(counts),indent=2))
    except Exception as e:
        api('PATCH','commerce_feed_runs',params={'id':f'eq.{rid}'},data={'status':'failed','error':str(e)[:2000],'finished_at':datetime.now(timezone.utc).isoformat()},prefer='return=minimal')
        raise
if __name__=='__main__':main()
