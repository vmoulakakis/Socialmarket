import os,json,gzip,glob,requests,time

SUPABASE_URL=os.environ['SUPABASE_URL'].rstrip('/')
SERVICE_KEY=os.environ['SUPABASE_SERVICE_ROLE_KEY']
SOURCE_NAME=os.getenv('SOURCE_NAME','linkwise-products.json')
HEADERS={'apikey':SERVICE_KEY,'Authorization':f'Bearer {SERVICE_KEY}','Content-Type':'application/json','Prefer':'resolution=merge-duplicates,return=minimal'}

def ensure_source():
    h={**HEADERS,'Prefer':'resolution=merge-duplicates,return=representation'}
    r=requests.post(f'{SUPABASE_URL}/rest/v1/sources?on_conflict=name',headers=h,json={'name':SOURCE_NAME,'source_type':'json_feed','is_active':True},timeout=30)
    r.raise_for_status();data=r.json()
    if data:return data[0]['id']
    r=requests.get(f'{SUPABASE_URL}/rest/v1/sources',headers=HEADERS,params={'name':f'eq.{SOURCE_NAME}','select':'id'},timeout=30);r.raise_for_status();return r.json()[0]['id']

def post_batch(rows,source_id):
    payload=[]
    for x in rows:
        x['source_id']=source_id
        if not x.get('external_product_id'):continue
        payload.append(x)
    if not payload:return
    r=requests.post(f'{SUPABASE_URL}/rest/v1/products?on_conflict=source_id,external_product_id',headers=HEADERS,json=payload,timeout=120)
    r.raise_for_status()

def main(pattern='shards/*.jsonl.gz',batch_size=500):
    source_id=ensure_source();total=0
    for path in sorted(glob.glob(pattern)):
        batch=[]
        with gzip.open(path,'rt',encoding='utf-8') as f:
            for line in f:
                batch.append(json.loads(line))
                if len(batch)>=batch_size:post_batch(batch,source_id);total+=len(batch);batch=[]
            if batch:post_batch(batch,source_id);total+=len(batch)
        print(json.dumps({'imported':total,'last_shard':path}),flush=True)
    print(json.dumps({'done':True,'records':total,'source_id':source_id}))

if __name__=='__main__':main()
