import os, json, hashlib, datetime, requests

VMDB_URL=os.getenv('SUPABASE_URL','https://gqpbskssrvpfjtujwezc.supabase.co').rstrip('/')
SERVICE_KEY=os.getenv('SUPABASE_SERVICE_ROLE_KEY','')
PIPELINE=os.getenv('COMMERCE_PIPELINE','greece_problem_solver_v1')
CANONICAL='https://gqpbskssrvpfjtujwezc.supabase.co'
if VMDB_URL != CANONICAL:
    raise RuntimeError(f'VMDB v2 blocks non-canonical database: {VMDB_URL}')
if not SERVICE_KEY:
    raise RuntimeError('SUPABASE_SERVICE_ROLE_KEY is required')
HEADERS={'apikey':SERVICE_KEY,'Authorization':f'Bearer {SERVICE_KEY}','Content-Type':'application/json','Prefer':'return=representation'}

def api(method,path,params=None,data=None):
    r=requests.request(method,f'{VMDB_URL}/rest/v1/{path}',headers=HEADERS,params=params,json=data,timeout=90)
    r.raise_for_status()
    return r.json() if r.text else None

def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def h(v): return hashlib.sha256(v.encode('utf-8')).hexdigest()

def evidence_count():
    r=requests.get(f'{VMDB_URL}/rest/v1/commerce_raw_evidence',headers={**HEADERS,'Prefer':'count=exact'},params={'market_code':'eq.GR','select':'id','limit':'1'},timeout=30)
    r.raise_for_status(); cr=r.headers.get('content-range','0-0/0')
    return int(cr.split('/')[-1]) if '/' in cr and cr.split('/')[-1].isdigit() else 0

def queue(stage,agent,entity_type='market',entity_key='GR',snapshot=None):
    # Idempotence is enforced operationally by checking for an unfinished identical job.
    existing=api('GET','commerce_agent_runs',params={'pipeline_key':f'eq.{PIPELINE}','stage_key':f'eq.{stage}','agent_key':f'eq.{agent}','entity_type':f'eq.{entity_type}','entity_key':f'eq.{entity_key}','status':'in.(queued,running)','select':'id','limit':'1'}) or []
    if existing:return existing[0]['id']
    row=api('POST','commerce_agent_runs',data={'pipeline_key':PIPELINE,'stage_key':stage,'agent_key':agent,'entity_type':entity_type,'entity_key':entity_key,'status':'queued','input_snapshot':snapshot or {}})
    return row[0]['id']

def bootstrap():
    n=evidence_count()
    snapshot={'market':'GR','raw_evidence_count':n,'queued_at':now()}
    stages=[
      ('greek_demand_pain','demand_scout'),('greek_demand_pain','pain_miner'),('greek_demand_pain','trend_analyst'),
      ('opportunity_engine','supply_gap_analyst'),('opportunity_engine','evidence_critic'),('opportunity_engine','opportunity_judge'),
      ('merchant_360','merchant_analyst'),('merchant_360','portfolio_scout'),('merchant_360','ranking_judge'),
      ('dynamic_product_discovery','product_scout'),('product_360','product_analyst'),('product_360','price_value_analyst'),('product_360','trust_analyst'),
      ('social_presentation','presentation_strategist'),('performance_learning','performance_learner')]
    ids=[queue(s,a,snapshot=snapshot) for s,a in stages]
    print(json.dumps({'pipeline':PIPELINE,'market':'GR','evidence':n,'queued_jobs':len(ids),'job_ids':ids},ensure_ascii=False))

if __name__=='__main__': bootstrap()
