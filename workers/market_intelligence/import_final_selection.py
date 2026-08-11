import os,json,time
from gateway import db_call

SOURCE_NAME=os.getenv('SOURCE_NAME','Linkwise Products')
SOURCE_URL=os.getenv('SOURCE_URL','https://drive.google.com/file/d/1oGnQr4uz3dxfHhydEYkYsrXeZJjR65HT/view?usp=drive_link')
ALLOWED={'external_product_id','product_name','model_name','description','brand_name','program_name','merchant_name','category_raw','price','full_price','discount_pct','currency','in_stock','availability','valid_from','valid_to','validity_days_remaining','validity_runway_score','times_bought','tracking_url','image_url','thumb_url','extra_images','colour','size','city','longitude','latitude','address','on_sale','is_active','hard_gate_pass','travel_related','market_eligible','market_exclusion_reason','eligibility_reason','canonical_group_key','merchant_trust_score','is_preferred_offer','duplicate_group_size','offer_selection_reason'}

def ensure_source():
    rows=db_call('GET','sources',params={'name':f'eq.{SOURCE_NAME}','select':'id','limit':'1'}) or []
    if rows:return rows[0]['id']
    return (db_call('POST','sources',data={'name':SOURCE_NAME,'source_type':'json_feed','source_url':SOURCE_URL,'country_code':'GR','active':True},prefer='return=representation') or [])[0]['id']
def job(source_id):
    rows=db_call('GET','import_jobs',params={'source_id':f'eq.{source_id}','status':'eq.queued','select':'id','order':'created_at.desc','limit':'1'}) or []
    if rows:return rows[0]['id']
    return (db_call('POST','import_jobs',data={'source_id':source_id,'status':'queued','file_name':'linkwise-products.json'},prefer='return=representation') or [])[0]['id']
def patch(jid,data):db_call('PATCH','import_jobs',params={'id':f'eq.{jid}'},data=data)
def main():
    sid=ensure_source();jid=job(sid);rows=[]
    with open('final-selection.jsonl',encoding='utf-8') as f:
        for line in f:
            p=json.loads(line);q={k:p.get(k) for k in ALLOWED if k in p};q['source_id']=sid;q['hard_gate_pass']=True;q['market_eligible']=True;q['travel_related']=False;q['is_preferred_offer']=True;q['extra_images']=(q.get('extra_images') or [])[:4];q['description']=(q.get('description') or '')[:1800] or None;rows.append(q)
    if len(rows)>1000:raise RuntimeError(f'Final selection exceeds 1000: {len(rows)}')
    patch(jid,{'status':'running','started_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'records_seen':len(rows),'checkpoint':{'stage':'smart_final_import','policy':'selection-v5-smart-stream','target_max':1000}})
    try:
        # Previous catalog rows are made inactive before this generation; current winners are reactivated by upsert.
        db_call('PATCH','products',data={'market_eligible':False,'is_preferred_offer':False,'market_exclusion_reason':'superseded_by_new_selection'})
        inserted=0
        for i in range(0,len(rows),200):
            batch=rows[i:i+200];db_call('POST','products',params={'on_conflict':'source_id,external_product_id'},data=batch,prefer='resolution=merge-duplicates,return=minimal');inserted+=len(batch);patch(jid,{'records_inserted':inserted,'checkpoint':{'stage':'smart_final_import','inserted':inserted,'target':len(rows)}})
        patch(jid,{'status':'completed','records_seen':len(rows),'records_inserted':inserted,'records_skipped':0,'checkpoint':{'stage':'completed_smart_top1000','policy':'selection-v5-smart-stream','selected':inserted},'finished_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())});print(json.dumps({'done':True,'selected_imported':inserted,'job_id':jid}))
    except Exception as e:
        patch(jid,{'status':'failed','error_summary':str(e)[:1200],'checkpoint':{'stage':'failed_smart_final_import'},'finished_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())});raise
if __name__=='__main__':main()
