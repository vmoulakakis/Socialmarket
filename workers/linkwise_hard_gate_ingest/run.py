# Production full-feed streaming worker using GitHub OIDC -> Supabase gateway.
import os,json,hashlib,requests,ijson
from decimal import Decimal,InvalidOperation
from datetime import datetime,timezone

FEED_URL=os.environ['LINKWISE_FEED_URL']
GATEWAY_URL=os.environ['SUPABASE_GATEWAY_URL']
OIDC_TOKEN=os.environ['SUPABASE_OIDC_TOKEN']
MIN_COMMISSION=Decimal(os.getenv('MIN_EXPECTED_COMMISSION_EUR','10'))
BATCH=int(os.getenv('UPSERT_BATCH_SIZE','500'))
CHECKPOINT_EVERY=int(os.getenv('CHECKPOINT_EVERY','10000'))
SOURCE='linkwise'

def api(method,path,params=None,data=None,prefer=None):
    payload={'method':method,'resource':path,'params':params or {}}
    if data is not None: payload['data']=data
    if prefer: payload['prefer']=prefer
    r=requests.post(GATEWAY_URL,headers={'Authorization':f'Bearer {OIDC_TOKEN}','Content-Type':'application/json'},json=payload,timeout=180)
    r.raise_for_status()
    body=r.json()
    if not body.get('ok'): raise RuntimeError(body)
    return body.get('result')

def dec(v):
    try:return Decimal(str(v))
    except (InvalidOperation,TypeError,ValueError):return None

def truthy(v): return str(v).strip().lower() in {'1','true','yes','y','in stock','available'}

def commission_map():
    rows=[]; offset=0
    while True:
        page=api('GET','merchant_product_discovery_eligible',params={'select':'id,legacy_merchant_id,merchant_name,flat_commission_min_eur,flat_commission_max_eur,percent_commission_min,percent_commission_max,hard_gate_pass,eligible_for_product_discovery','hard_gate_pass':'eq.true','eligible_for_product_discovery':'eq.true','limit':'1000','offset':str(offset)}) or []
        rows.extend(page)
        if len(page)<1000: break
        offset+=1000
    return {str(x['legacy_merchant_id']):x for x in rows if x.get('legacy_merchant_id') is not None}

def expected_commission(price,m):
    vals=[]
    flat=dec(m.get('flat_commission_min_eur')); pct=dec(m.get('percent_commission_min'))
    if flat is not None: vals.append((flat,'flat_min'))
    if pct is not None: vals.append((price*pct/Decimal('100'),'percent_min'))
    return max(vals,key=lambda x:x[0]) if vals else (None,None)

def stable_hash(p,expected):
    keys=('product_id','program_id','sku','model_name','product_name','category','price','discount','in_stock','valid_from','valid_to','tracking_url')
    return hashlib.sha256(('|'.join(str(p.get(k) or '') for k in keys)+f'|{expected}').encode()).hexdigest()

def flush(rows):
    if not rows:return 0
    api('POST','commerce_feed_eligible_offers',params={'on_conflict':'source_key,program_id,source_product_id'},data=rows,prefer='resolution=merge-duplicates,return=minimal'); return len(rows)

def patch_run(rid,counts,status='running',extra=None):
    api('PATCH','commerce_feed_runs',params={'id':f'eq.{rid}'},data={**counts,'status':status,'checkpoint':{'streaming':True,'batch_size':BATCH,'checkpoint_every':CHECKPOINT_EVERY,**(extra or {})}},prefer='return=minimal')

def product_stream(raw):
    # Linkwise full feed is expected as a top-level array. Keep parsing streaming/bounded-memory.
    yield from ijson.items(raw,'item')

def main():
    merchants=commission_map(); counts={'scanned':0,'invalid':0,'commission_unknown':0,'commission_rejected':0,'inactive':0,'expired':0,'duplicate':0,'eligible':0,'inserted':0,'updated':0,'unchanged':0,'bytes_read':0}; out=[]
    run=(api('POST','commerce_feed_runs',data={'source_key':SOURCE,'run_type':'full_stream','status':'running','min_commission_eur':float(MIN_COMMISSION),'batch_size':BATCH},prefer='return=representation') or [])[0]; rid=run['id']
    try:
        with requests.get(FEED_URL,stream=True,timeout=(30,900)) as r:
            r.raise_for_status(); r.raw.decode_content=True
            for p in product_stream(r.raw):
                counts['scanned']+=1; pid=p.get('product_id'); prog=p.get('program_id'); price=dec(p.get('price'))
                if not pid or not prog or not p.get('tracking_url') or not p.get('product_name') or price is None or price<=0: counts['invalid']+=1; continue
                if p.get('in_stock') is not None and not truthy(p.get('in_stock')): counts['inactive']+=1; continue
                m=merchants.get(str(prog))
                if not m: counts['commission_unknown']+=1; continue
                exp,basis=expected_commission(price,m)
                if exp is None: counts['commission_unknown']+=1; continue
                if exp<MIN_COMMISSION: counts['commission_rejected']+=1; continue
                raw={'product_id':pid,'program_id':prog,'program_name':p.get('program_name') or m.get('merchant_name'),'sku':p.get('sku'),'model_name':p.get('model_name'),'product_name':p.get('product_name'),'category':p.get('category'),'price':float(price),'tracking_url':p.get('tracking_url'),'image_url':p.get('image_url') or p.get('thumb_url'),'in_stock':True,'valid_from':p.get('valid_from'),'valid_to':p.get('valid_to'),'on_sale':p.get('on_sale'),'discount':p.get('discount'),'times_bought':p.get('times_bought')}
                out.append({'source_key':SOURCE,'source_product_id':str(pid),'program_id':str(prog),'program_name':raw['program_name'],'sku':str(p['sku']) if p.get('sku') else None,'model_name':p.get('model_name'),'product_name':str(p.get('product_name')),'category_raw':p.get('category'),'price_eur':float(price),'expected_commission_eur':float(exp),'commission_basis':basis,'tracking_url':p.get('tracking_url'),'image_url':raw['image_url'],'in_stock':True,'valid_from':p.get('valid_from') or None,'valid_to':p.get('valid_to') or None,'on_sale':truthy(p.get('on_sale')),'discount':float(dec(p.get('discount'))) if dec(p.get('discount')) is not None else None,'times_bought':int(dec(p.get('times_bought')) or 0),'content_hash':stable_hash(p,exp),'raw_snapshot':raw,'last_seen_at':datetime.now(timezone.utc).isoformat(),'is_active':True,'intelligence_status':'pending'})
                counts['eligible']+=1
                if len(out)>=BATCH: counts['inserted']+=flush(out); out=[]
                if counts['scanned']%CHECKPOINT_EVERY==0:
                    try: counts['bytes_read']=r.raw.tell() or counts['bytes_read']
                    except Exception: pass
                    patch_run(rid,counts); print(json.dumps({'run_id':rid,**counts}),flush=True)
        counts['inserted']+=flush(out)
        patch_run(rid,counts,'completed',{'all_eligible_products':True}); api('PATCH','commerce_feed_runs',params={'id':f'eq.{rid}'},data={'finished_at':datetime.now(timezone.utc).isoformat()},prefer='return=minimal'); print(json.dumps({'run_id':rid,**counts},indent=2),flush=True)
    except Exception as e:
        api('PATCH','commerce_feed_runs',params={'id':f'eq.{rid}'},data={'status':'failed','error':str(e)[:2000],'finished_at':datetime.now(timezone.utc).isoformat(),'checkpoint':{'streaming':True,'batch_size':BATCH}},prefer='return=minimal'); raise
if __name__=='__main__':main()
