from __future__ import annotations

import hashlib
from datetime import datetime,timezone
from typing import Any
from .common import SupabaseREST,first_row

def now_iso():return datetime.now(timezone.utc).isoformat()
def slug_for(pid:str,url:str):return f"p-{pid.replace('-','')[:8]}-{hashlib.sha256(url.encode()).hexdigest()[:6]}"

def incident(db:SupabaseREST,kind:str,message:str,platform:str|None=None,entity_id:str|None=None,details:dict[str,Any]|None=None):
    db.post('social_incidents',{'severity':'warning','incident_type':kind,'platform':platform,'entity_type':'calendar_item','entity_id':entity_id,'message':message[:1500],'details':details or {},'status':'open','last_seen_at':now_iso()},return_representation=False)

def caption(platform:str,variant:dict,url:str,slug:str):
    parts=[str(variant.get('caption') or '').strip()]
    tags=variant.get('hashtags') or []
    if tags:parts.append(' '.join(tags[:12]))
    disclosure=str(variant.get('disclosure') or 'Affiliate / διαφημιστικό περιεχόμενο').strip()
    if disclosure:parts.append(disclosure)
    if platform in {'facebook','linkedin'}:parts.append(url)
    elif platform=='instagram':parts.append('🔎 Δες την προσφορά από το QR της εικόνας.')
    elif platform=='tiktok':parts.append(f'🔗 Link στο bio · κωδικός {slug}')
    return '\n\n'.join(x for x in parts if x)

def run(db:SupabaseREST,limit:int=250):
    settings=(first_row(db.get('app_settings','key=eq.autonomous_social_engine&select=value&limit=1')) or {}).get('value') or {}
    if settings.get('enabled') is False or settings.get('auto_publish') is False:return {'approved':0,'blocked':0,'queued':0}
    minq=float(settings.get('min_creative_quality') or 80);minprice=float(settings.get('min_price_eur') or 100)
    rows=db.get('social_content_calendar',f'status=eq.needs_approval&select=*&order=scheduled_at.asc&limit={max(1,min(limit,1000))}') or []
    approved=blocked=queued=0
    for cal in rows:
        asset=first_row(db.get('creative_assets',f"id=eq.{cal.get('creative_asset_id')}&select=*&limit=1"))
        variant=first_row(db.get('social_post_variants',f"id=eq.{cal['variant_id']}&select=*&limit=1"))
        item=first_row(db.get('product_to_post_items',f"id=eq.{cal['item_id']}&select=*&limit=1"))
        product=first_row(db.get('products',f"id=eq.{(item or {}).get('product_id')}&select=id,product_name,merchant_name,price,image_url,tracking_url,valid_to&limit=1"))
        reasons=[]
        if not asset:reasons.append('creative_asset_missing')
        else:
            if float(asset.get('quality_score') or 0)<minq:reasons.append('creative_quality_below_threshold')
            if str((asset.get('visual_audit') or {}).get('status') or '').lower() in {'block','failed','rejected'}:reasons.append('creative_audit_blocked')
        if not variant or not product:reasons.append('variant_or_product_missing')
        elif not product.get('tracking_url') or not product.get('image_url'):reasons.append('tracking_or_product_image_missing')
        elif float(product.get('price') or 0)<minprice:reasons.append('price_below_campaign_floor')
        if reasons:
            blocked+=1
            db.patch('social_content_calendar',f"id=eq.{cal['id']}",{'status':'failed','updated_at':now_iso(),'metadata':{**(cal.get('metadata') or {}),'autopublish_block':reasons}})
            incident(db,'autopublish_blocked',','.join(reasons),cal.get('platform'),cal['id'],{'reasons':reasons});continue
        s=slug_for(product['id'],product['tracking_url'])
        redirect=first_row(db.post('affiliate_redirects?on_conflict=slug',{'slug':s,'product_id':product['id'],'platform':cal['platform'],'tracking_url_snapshot':product['tracking_url'],'label':product.get('product_name') or 'Προϊόν','merchant_name':product.get('merchant_name'),'price':product.get('price'),'image_url':product.get('image_url'),'active':True,'valid_until':product.get('valid_to'),'updated_at':now_iso()},upsert=True))
        cap=caption(cal['platform'],variant,product['tracking_url'],s)
        db.patch('social_post_variants',f"id=eq.{variant['id']}",{'status':'approved','caption':cap})
        db.patch('social_content_calendar',f"id=eq.{cal['id']}",{'status':'approved','updated_at':now_iso(),'metadata':{**(cal.get('metadata') or {}),'auto_approved':True,'affiliate_slug':s,'redirect_id':(redirect or {}).get('id')}})
        approved+=1
        idem=hashlib.sha256(f"{cal['id']}|{cal['scheduled_at']}|{cal['platform']}".encode()).hexdigest()
        db.post('social_publish_jobs?on_conflict=calendar_item_id',{'calendar_item_id':cal['id'],'platform':cal['platform'],'preferred_provider':'auto','status':'queued','idempotency_key':idem,'next_attempt_at':now_iso(),'updated_at':now_iso()},upsert=True,return_representation=False);queued+=1
    return {'approved':approved,'blocked':blocked,'queued':queued}

if __name__=='__main__':print(run(SupabaseREST()))
