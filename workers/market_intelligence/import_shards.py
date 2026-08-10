import os,json,gzip,glob,requests,time

SUPABASE_URL=os.environ['SUPABASE_URL'].rstrip('/')
SERVICE_KEY=os.environ['SUPABASE_SERVICE_ROLE_KEY']
SOURCE_NAME=os.getenv('SOURCE_NAME','Linkwise Products')
SOURCE_URL=os.getenv('SOURCE_URL','https://drive.google.com/file/d/1oGnQr4uz3dxfHhydEYkYsrXeZJjR65HT/view?usp=drive_link')
HEADERS={'apikey':SERVICE_KEY,'Authorization':f'Bearer {SERVICE_KEY}','Content-Type':'application/json','Prefer':'resolution=merge-duplicates,return=minimal'}

def ensure_source():
    h={**HEADERS,'Prefer':'resolution=merge-duplicates,return=representation'}
    payload={'name':SOURCE_NAME,'source_type':'json_feed','source_url':SOURCE_URL,'country_code':'GR','active':True}
    r=requests.post(f'{SUPABASE_URL}/rest/v1/sources?on_conflict=name',headers=h,json=payload,timeout=30)
    if r.status_code in (400,409):
        r=requests.get(f'{SUPABASE_URL}/rest/v1/sources',headers=HEADERS,params={'name':f'eq.{SOURCE_NAME}','select':'id'},timeout=30)
        r.raise_for_status();data=r.json();
        if not data:raise RuntimeError('Source not found and could not be created')
        return data[0]['id']
    r.raise_for_status();data=r.json()
    if data:return data[0]['id']
    r=requests.get(f'{SUPABASE_URL}/rest/v1/sources',headers=HEADERS,params={'name':f'eq.{SOURCE_NAME}','select':'id'},timeout=30);r.raise_for_status();return r.json()[0]['id']

def find_or_create_job(source_id):
    r=requests.get(f'{SUPABASE_URL}/rest/v1/import_jobs',headers=HEADERS,params={'source_id':f'eq.{source_id}','status':'eq.queued','select':'id','order':'created_at.desc','limit':'1'},timeout=30)
    r.raise_for_status();rows=r.json()
    if rows:return rows[0]['id']
    h={**HEADERS,'Prefer':'return=representation'}
    r=requests.post(f'{SUPABASE_URL}/rest/v1/import_jobs',headers=h,json={'source_id':source_id,'status':'queued','file_name':'linkwise-products.json'},timeout=30)
    r.raise_for_status();return r.json()[0]['id']

def patch_job(job_id,body):
    r=requests.patch(f'{SUPABASE_URL}/rest/v1/import_jobs',headers=HEADERS,params={'id':f'eq.{job_id}'},json=body,timeout=30);r.raise_for_status()

def post_batch(rows,source_id):
    payload=[]
    for x in rows:
        x['source_id']=source_id
        if not x.get('external_product_id'):continue
        payload.append(x)
    if not payload:return 0
    r=requests.post(f'{SUPABASE_URL}/rest/v1/products?on_conflict=source_id,external_product_id',headers=HEADERS,json=payload,timeout=120)
    r.raise_for_status();return len(payload)

def main(pattern='shards/*.jsonl.gz',batch_size=500):
    source_id=ensure_source();job_id=find_or_create_job(source_id);total=0;seen=0
    patch_job(job_id,{'status':'running','started_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'checkpoint':{'stage':'importing'}})
    try:
        for path in sorted(glob.glob(pattern)):
            batch=[]
            with gzip.open(path,'rt',encoding='utf-8') as f:
                for line in f:
                    seen+=1;batch.append(json.loads(line))
                    if len(batch)>=batch_size:
                        total+=post_batch(batch,source_id);batch=[]
                if batch:total+=post_batch(batch,source_id)
            patch_job(job_id,{'records_seen':seen,'records_inserted':total,'checkpoint':{'stage':'importing','last_shard':path}})
            print(json.dumps({'imported':total,'seen':seen,'last_shard':path}),flush=True)
        patch_job(job_id,{'status':'completed','records_seen':seen,'records_inserted':total,'checkpoint':{'stage':'completed'},'finished_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())})
        print(json.dumps({'done':True,'records':total,'source_id':source_id,'job_id':job_id}))
    except Exception as e:
        patch_job(job_id,{'status':'failed','records_seen':seen,'records_inserted':total,'error_summary':str(e),'checkpoint':{'stage':'failed'},'finished_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())})
        raise

if __name__=='__main__':main()
