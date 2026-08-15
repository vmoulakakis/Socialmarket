from __future__ import annotations
import json, os, sys, time
from urllib.parse import quote
import requests
HERE=os.path.dirname(__file__)
if HERE not in sys.path:sys.path.insert(0,HERE)
from deep_lab import analyze
AUDIENCE='socialmarket-supabase-worker'
GATEWAY=os.getenv('DEMAND_MODEL_LAB_GATEWAY','https://rpfadpdnnxequgvdcfoq.supabase.co/functions/v1/demand-model-lab-gateway')
MAX_TAXONOMIES=max(1,min(int(os.getenv('MAX_TAXONOMIES','120')),160))
_token=None;_token_at=0.0

def oidc(force=False):
    global _token,_token_at
    if _token and not force and time.time()-_token_at<180:return _token
    url=os.environ.get('ACTIONS_ID_TOKEN_REQUEST_URL');request_token=os.environ.get('ACTIONS_ID_TOKEN_REQUEST_TOKEN')
    if not url or not request_token:raise RuntimeError('GitHub OIDC unavailable; workflow needs id-token: write')
    sep='&' if '?' in url else '?';r=requests.get(f'{url}{sep}audience={quote(AUDIENCE)}',headers={'Authorization':f'Bearer {request_token}'},timeout=30);r.raise_for_status();_token=r.json()['value'];_token_at=time.time();return _token

def call(action,**payload):
    for attempt in range(2):
        r=requests.post(GATEWAY,headers={'Authorization':f'Bearer {oidc(force=attempt>0)}','Content-Type':'application/json'},json={'action':action,**payload},timeout=180)
        if r.status_code==401 and attempt==0:continue
        r.raise_for_status();body=r.json()
        if not body.get('ok'):raise RuntimeError(body)
        return body
    raise RuntimeError('OIDC gateway authentication failed')

def main():
    items=(call('taxonomy_list').get('items') or [])[:MAX_TAXONOMIES];stats={'total':len(items),'completed':0,'withheld':0,'failed':0,'errors':[]}
    for i,item in enumerate(items,1):
        tid=str(item.get('taxonomy_id') or '')
        if not tid:continue
        try:
            ctx=call('context',taxonomy_id=tid).get('context') or {};result=analyze(ctx);call('save',taxonomy_id=tid,analysis=result);decision=str(result.get('temporal_lab',{}).get('decision') or '')
            if decision=='WITHHOLD_PRODUCTION_FORECAST':stats['withheld']+=1
            else:stats['completed']+=1
            print(json.dumps({'taxonomy_id':tid,'index':i,'status':decision or 'completed','demand':result.get('observed',{}).get('demand_score'),'whitespace':result.get('market_structure',{}).get('fuzzy',{}).get('whitespace',{}).get('score')},ensure_ascii=False),flush=True)
        except Exception as exc:
            stats['failed']+=1;stats['errors'].append({'taxonomy_id':tid,'error':f'{type(exc).__name__}:{exc}'[:500]});print(json.dumps(stats['errors'][-1],ensure_ascii=False),flush=True)
    print(json.dumps({'summary':stats},ensure_ascii=False))
    if stats['failed'] and stats['completed']+stats['withheld']==0:raise SystemExit(2)

if __name__=='__main__':main()
