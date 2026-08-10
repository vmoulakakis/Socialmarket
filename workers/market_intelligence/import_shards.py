import os,json,gzip,glob,time
from gateway import db_call

SOURCE_NAME=os.getenv('SOURCE_NAME','Linkwise Products')
SOURCE_URL=os.getenv('SOURCE_URL','https://drive.google.com/file/d/1oGnQr4uz3dxfHhydEYkYsrXeZJjR65HT/view?usp=drive_link')

def ensure_source():
    rows=db_call('GET','sources',params={'name':f'eq.{SOURCE_NAME}','select':'id','limit':'1'}) or []
    if rows:return rows[0]['id']
    rows=db_call('POST','sources',data={'name':SOURCE_NAME,'source_type':'json_feed','source_url':SOURCE_URL,'country_code':'GR','active':True},prefer='return=representation') or []
    if not rows:raise RuntimeError('Source could not be created')
    return rows[0]['id']

def find_or_create_job(source_id):
    rows=db_call('GET','import_jobs',params={'source_id':f'eq.{source_id}','status':'eq.queued','select':'id','order':'created_at.desc','limit':'1'}) or []
    if rows:return rows[0]['id']
    rows=db_call('POST','import_jobs',data={'source_id':source_id,'status':'queued','file_name':'linkwise-products.json'},prefer='return=representation') or []
    return rows[0]['id']

def patch_job(job_id,body):
    db_call('PATCH','import_jobs',params={'id':f'eq.{job_id}'},data=body)

def compact_product(x,source_id):
    if not x.get('external_product_id') or not x.get('hard_gate_pass'):
        return None
    x=dict(x)
    x['source_id']=source_id
    if x.get('description') and len(x['description'])>5000:
        x['description']=x['description'][:5000]
    images=x.get('extra_images') or []
    x['extra_images']=images[:10] if isinstance(images,list) else []
    # Unknown raw feed payload is not useful enough to justify database bloat.
    x['extra_json']={}
    return x

def post_batch(rows,source_id):
    payload=[p for p in (compact_product(x,source_id) for x in rows) if p]
    if not payload:return 0
    db_call('POST','products',params={'on_conflict':'source_id,external_product_id'},data=payload,prefer='resolution=merge-duplicates,return=minimal')
    return len(payload)

def main(pattern='shards/*.jsonl.gz',batch_size=500):
    source_id=ensure_source();job_id=find_or_create_job(source_id);total=0;seen=0
    patch_job(job_id,{'status':'running','started_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'checkpoint':{'stage':'importing_eligible_only'}})
    try:
        for path in sorted(glob.glob(pattern)):
            batch=[]
            with gzip.open(path,'rt',encoding='utf-8') as f:
                for line in f:
                    seen+=1;batch.append(json.loads(line))
                    if len(batch)>=batch_size:
                        total+=post_batch(batch,source_id);batch=[]
                if batch:total+=post_batch(batch,source_id)
            patch_job(job_id,{'records_seen':seen,'records_inserted':total,'records_skipped':max(0,seen-total),'checkpoint':{'stage':'importing_eligible_only','last_shard':path}})
            print(json.dumps({'imported_eligible':total,'seen':seen,'skipped':seen-total,'last_shard':path}),flush=True)
        patch_job(job_id,{'status':'completed','records_seen':seen,'records_inserted':total,'records_skipped':max(0,seen-total),'checkpoint':{'stage':'completed_eligible_only'},'finished_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())})
        print(json.dumps({'done':True,'eligible_records':total,'seen':seen,'source_id':source_id,'job_id':job_id}))
    except Exception as e:
        patch_job(job_id,{'status':'failed','records_seen':seen,'records_inserted':total,'records_skipped':max(0,seen-total),'error_summary':str(e),'checkpoint':{'stage':'failed'},'finished_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())})
        raise

if __name__=='__main__':main()
