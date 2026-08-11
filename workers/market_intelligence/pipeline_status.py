import os,sys,json,time
from gateway import db_call
SOURCE_NAME=os.getenv('SOURCE_NAME','Linkwise Products')
SOURCE_URL=os.getenv('SOURCE_URL','https://drive.google.com/file/d/1oGnQr4uz3dxfHhydEYkYsrXeZJjR65HT/view?usp=drive_link')

def ensure_source():
    rows=db_call('GET','sources',params={'name':f'eq.{SOURCE_NAME}','select':'id','limit':'1'}) or []
    if rows:return rows[0]['id']
    return (db_call('POST','sources',data={'name':SOURCE_NAME,'source_type':'json_feed','source_url':SOURCE_URL,'country_code':'GR','active':True},prefer='return=representation') or [])[0]['id']
def get_job(sid):
    rows=db_call('GET','import_jobs',params={'source_id':f'eq.{sid}','status':'in.(queued,running)','select':'id,status','order':'created_at.desc','limit':'1'}) or []
    if rows:return rows[0]['id']
    return (db_call('POST','import_jobs',data={'source_id':sid,'status':'queued','file_name':'linkwise-products.json'},prefer='return=representation') or [])[0]['id']
def main():
    stage=sys.argv[1] if len(sys.argv)>1 else 'unknown';sid=ensure_source();jid=get_job(sid);payload={'status':'running','checkpoint':{'stage':stage,'policy':'selection-v5-smart-stream','min_price_eur':100,'min_validity_days':20,'target_max':1000},'error_summary':None}
    if stage=='pipeline_start':payload['started_at']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
    if len(sys.argv)>2:
        try:payload['checkpoint'].update(json.loads(sys.argv[2]))
        except:pass
    db_call('PATCH','import_jobs',params={'id':f'eq.{jid}'},data=payload);print(json.dumps({'job_id':jid,'stage':stage}))
if __name__=='__main__':main()
