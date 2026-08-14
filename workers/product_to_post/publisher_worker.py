from __future__ import annotations

import json,os,socket,traceback
from datetime import datetime,timedelta,timezone
from typing import Any
from .common import SupabaseREST,first_row
from .publishers import PublisherRouter

def now_iso():return datetime.now(timezone.utc).isoformat()
def add_incident(db:SupabaseREST,job:dict[str,Any],message:str,details=None):
    db.post('social_incidents',{'severity':'critical' if int(job.get('attempt_count') or 0)>=4 else 'warning','incident_type':'publish_failure','platform':job.get('platform'),'provider':job.get('actual_provider'),'entity_type':'publish_job','entity_id':job.get('id'),'message':message[:1500],'details':details or {},'status':'open','last_seen_at':now_iso()},return_representation=False)

def load_payload(db,job):
    cal=first_row(db.get('social_content_calendar',f"id=eq.{job['calendar_item_id']}&select=*&limit=1"))
    if not cal:raise RuntimeError('calendar_item_missing')
    variant=first_row(db.get('social_post_variants',f"id=eq.{cal['variant_id']}&select=*&limit=1"))
    asset=first_row(db.get('creative_assets',f"id=eq.{cal.get('creative_asset_id')}&select=*&limit=1"))
    if not variant or not asset:raise RuntimeError('variant_or_asset_missing')
    return cal,variant,asset

def process_job(db,router,job):
    cal,variant,asset=load_payload(db,job)
    if cal.get('status') not in {'approved','scheduled'}:raise RuntimeError(f"calendar_not_publishable:{cal.get('status')}")
    result=router.schedule(job['platform'],cal['scheduled_at'],variant.get('caption') or '',asset['storage_path'],job.get('preferred_provider') or 'auto')
    provider=result['provider'];external=result.get('external_post_id')
    db.patch('social_publish_jobs',f"id=eq.{job['id']}",{'status':'scheduled','actual_provider':provider,'external_post_id':external,'provider_payload':result.get('payload') or {},'provider_response':result.get('response') or {},'finished_at':now_iso(),'updated_at':now_iso(),'error':None})
    db.patch('social_content_calendar',f"id=eq.{cal['id']}",{'status':'scheduled','updated_at':now_iso(),'metadata':{**(cal.get('metadata') or {}),'publisher':provider,'external_post_id':external,'media_url':result.get('media_url')}})
    db.patch('social_post_variants',f"id=eq.{variant['id']}",{'status':'scheduled'})
    return {'job_id':job['id'],'provider':provider,'external_post_id':external}

def sync_health(db,router):
    for platform in ['facebook','instagram','tiktok','linkedin']:
        for name,provider in [('postiz',router.postiz),('buffer',router.buffer)]:
            try:status=provider.health(platform)
            except Exception as exc:status={'configured':False,'healthy':False,'reason':str(exc)[:500]}
            db.post('social_provider_health?on_conflict=provider,platform',{'provider':name,'platform':platform,'configured':bool(status.get('configured')),'healthy':bool(status.get('healthy')),'details':status,'checked_at':now_iso()},upsert=True,return_representation=False)

def main(limit=30):
    db=SupabaseREST();router=PublisherRouter();worker=os.getenv('PUBLISH_WORKER_ID') or f"publisher-{socket.gethostname()}";sync_health(db,router)
    jobs=db.rpc('claim_social_publish_jobs',{'p_worker_id':worker,'p_limit':max(1,min(limit,100))}) or [];results=[]
    for job in jobs:
        try:results.append(process_job(db,router,job))
        except Exception as exc:
            trace=traceback.format_exc(limit=6);retry=datetime.now(timezone.utc)+timedelta(minutes=min(120,5*(2**max(0,int(job.get('attempt_count') or 1)-1))))
            try:
                db.patch('social_publish_jobs',f"id=eq.{job['id']}",{'status':'failed','error':f'{exc}\n{trace}'[:3500],'next_attempt_at':retry.isoformat(),'finished_at':now_iso(),'updated_at':now_iso()});add_incident(db,job,str(exc),{'trace':trace[:1800]})
            except Exception:pass
            results.append({'job_id':job.get('id'),'error':str(exc)})
    print(json.dumps({'ok':True,'worker_id':worker,'processed':len(results),'results':results},ensure_ascii=False));return 0

if __name__=='__main__':raise SystemExit(main(int(os.getenv('PUBLISH_MAX_JOBS','30'))))
