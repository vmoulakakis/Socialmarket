"""Small GitHub-OIDC lifecycle helper for Product Ranking workflow observability."""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

AUDIENCE='socialmarket-supabase-worker'
RANKING_GATEWAY=os.getenv('PRODUCT_RANKING_GATEWAY','https://rpfadpdnnxequgvdcfoq.supabase.co/functions/v1/product-ranking-gateway')
OBS_GATEWAY=os.getenv('PRODUCT_RUN_OBSERVABILITY_GATEWAY','https://rpfadpdnnxequgvdcfoq.supabase.co/functions/v1/product-run-observability-gateway')
ENGINE_VERSION='ranking_v3.6.3'


def oidc_token():
    url=os.getenv('ACTIONS_ID_TOKEN_REQUEST_URL'); token=os.getenv('ACTIONS_ID_TOKEN_REQUEST_TOKEN')
    if not url or not token: raise RuntimeError('GitHub OIDC environment is unavailable')
    sep='&' if '?' in url else '?'
    req=urllib.request.Request(url+sep+'audience='+urllib.parse.quote(AUDIENCE),headers={'Authorization':'Bearer '+token})
    with urllib.request.urlopen(req,timeout=20) as r:return json.loads(r.read().decode())['value']


def call(url,action,**payload):
    body=json.dumps({'action':action,**payload},ensure_ascii=False).encode()
    last=None
    for attempt in (1,2):
        req=urllib.request.Request(url,data=body,headers={'authorization':'Bearer '+oidc_token(),'content-type':'application/json'},method='POST')
        try:
            with urllib.request.urlopen(req,timeout=45) as r:return json.loads(r.read().decode())
        except urllib.error.HTTPError as exc:
            msg=exc.read().decode(errors='replace');last=RuntimeError(f'{action} failed: {exc.code} {msg[:1200]}')
            if exc.code==401 and attempt==1:continue
            raise last
    raise last or RuntimeError(f'{action} failed')


def start():
    run_key=f"{os.environ.get('GITHUB_RUN_ID','local')}-{os.environ.get('GITHUB_RUN_ATTEMPT','1')}"
    result=call(RANKING_GATEWAY,'ranking_start',run_key=run_key,engine_version=ENGINE_VERSION,metadata={
        'github_run_id':os.environ.get('GITHUB_RUN_ID'),
        'github_run_attempt':os.environ.get('GITHUB_RUN_ATTEMPT','1'),
        'github_head_sha':os.environ.get('GITHUB_SHA'),
        'stage':'workflow_start',
        'orchestrator':'product_ranking_v363_production',
        'policy':'durable before feed probe/download/scan',
    })
    run_id=str(result['run_id'])
    output=os.environ.get('GITHUB_OUTPUT'); env=os.environ.get('GITHUB_ENV')
    if output:
        with open(output,'a',encoding='utf-8') as f:f.write(f'run_id={run_id}\n')
    if env:
        with open(env,'a',encoding='utf-8') as f:f.write(f'PRODUCT_RANK_RUN_ID={run_id}\n')
    print(json.dumps({'ok':True,'run_id':run_id,'run_key':run_key,'status':'running'}))


def fail(stage='workflow_pre_final'):
    run_id=os.environ.get('PRODUCT_RANK_RUN_ID','').strip()
    if not run_id:
        print(json.dumps({'warning':'no_product_run_id_to_mark_failed'}));return
    call(OBS_GATEWAY,'ranking_fail',run_id=run_id,stage=stage,error='GitHub workflow failed before Product V3.6.3 final orchestrator could complete',metadata={
        'github_run_id':os.environ.get('GITHUB_RUN_ID'),
        'github_run_attempt':os.environ.get('GITHUB_RUN_ATTEMPT','1'),
        'github_head_sha':os.environ.get('GITHUB_SHA'),
    })
    print(json.dumps({'ok':True,'run_id':run_id,'status':'failed','stage':stage}))


if __name__=='__main__':
    cmd=sys.argv[1] if len(sys.argv)>1 else 'start'
    if cmd=='start':start()
    elif cmd=='fail':fail(sys.argv[2] if len(sys.argv)>2 else 'workflow_pre_final')
    else:raise SystemExit(f'unknown command: {cmd}')
