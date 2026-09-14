import json, os, re, subprocess, sys, time, urllib.parse, urllib.request
from pathlib import Path

GATEWAY=os.getenv('SUPABASE_WORKER_GATEWAY','https://gqpbskssrvpfjtujwezc.supabase.co/functions/v1/github-worker-gateway')
REPO=os.getenv('GITHUB_REPOSITORY','vmoulakakis/Socialmarket')
GH_TOKEN=os.getenv('GITHUB_TOKEN','')
WORKER_ID=f"github:{os.getenv('GITHUB_RUN_ID','local')}"
MODEL=os.getenv('GITHUB_MODELS_MODEL','openai/gpt-4.1')
MAX_TASKS=max(1,min(int(os.getenv('AGENT_MAX_TASKS_PER_RUN','2')),2))
_token=None
_token_at=0.0

class TaskError(RuntimeError):
    def __init__(self,message,retry=False): super().__init__(message); self.retry=retry

def sh(args,timeout=600,check=True):
    p=subprocess.run(args,text=True,capture_output=True,timeout=timeout)
    if check and p.returncode:
        raise TaskError(f"command failed ({' '.join(args)}):\n{p.stdout[-2000:]}\n{p.stderr[-3000:]}")
    return p

def http_json(url,method='GET',headers=None,body=None,timeout=60):
    data=None if body is None else json.dumps(body).encode()
    req=urllib.request.Request(url,data=data,method=method,headers=headers or {})
    try:
        with urllib.request.urlopen(req,timeout=timeout) as r:
            raw=r.read().decode(); return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw=e.read().decode(errors='replace')
        raise TaskError(f'HTTP {e.code} {url}: {raw[:2000]}',retry=e.code in (408,409,425,429,500,502,503,504))

def oidc_token(force=False):
    global _token,_token_at
    if _token and not force and time.time()-_token_at<180:return _token
    url=os.getenv('ACTIONS_ID_TOKEN_REQUEST_URL');rt=os.getenv('ACTIONS_ID_TOKEN_REQUEST_TOKEN')
    if not url or not rt: raise TaskError('GitHub OIDC unavailable; workflow needs id-token: write')
    sep='&' if '?' in url else '?'
    res=http_json(f"{url}{sep}audience={urllib.parse.quote('socialmarket-supabase-worker')}",headers={'Authorization':f'Bearer {rt}'})
    _token=res['value'];_token_at=time.time();return _token

def db(method,resource,data=None,params=None,prefer=None):
    payload={'method':method,'resource':resource}
    if data is not None:payload['data']=data
    if params:payload['params']=params
    if prefer:payload['prefer']=prefer
    for attempt in range(2):
        try:
            out=http_json(GATEWAY,'POST',{'Authorization':f'Bearer {oidc_token(force=attempt>0)}','Content-Type':'application/json'},payload,180)
            if not out.get('ok'):raise TaskError(str(out),retry=True)
            return out.get('result')
        except TaskError as e:
            if attempt==0 and '401' in str(e):continue
            raise

def reserve(metric,qty,run_id,metadata=None,provider=None,model=None):
    out=db('POST',f'rpc/reserve_agent_budget',data={'p_metric':metric,'p_quantity':qty,'p_run_id':run_id,'p_actor':'github-agent-executor','p_provider':provider,'p_model':model,'p_metadata':metadata or {}})
    if not out or not out.get('allowed'):raise TaskError(f'budget denied: {metric}: {out}')
    return out.get('reservation_id')

def finalize(rid,qty,metadata=None):
    if rid:db('POST','rpc/finalize_agent_budget',data={'p_reservation_id':rid,'p_actual_quantity':qty,'p_metadata':metadata or {}})

def release(rid):
    if rid:
        try:db('POST','rpc/release_agent_budget',data={'p_reservation_id':rid})
        except Exception:pass

def claim():return db('POST','rpc/claim_agent_tool_task',data={'p_worker_id':WORKER_ID})
def finish(task_id,output):return db('POST','rpc/finish_agent_tool_task',data={'p_task_id':task_id,'p_output':output})
def fail(task_id,error,retry=False):return db('POST','rpc/fail_agent_tool_task',data={'p_task_id':task_id,'p_error':str(error)[:4000],'p_retry':bool(retry)})

def safe_slug(v):return re.sub(r'[^a-z0-9-]+','-',str(v).lower()).strip('-')[:45] or 'task'
def safe_path(path):
    p=str(path).replace('\\','/').lstrip('/')
    denied=('.github/','.env','supabase/','node_modules/','package-lock.json','pnpm-lock.yaml','yarn.lock','.git/')
    if '..' in p.split('/') or any(p==d.rstrip('/') or p.startswith(d) for d in denied):return None
    if not any(p.startswith(x) for x in ('app/','components/','lib/','data/','config/','public/','tests/')):return None
    return p

def discover_context(payload):
    requested=payload.get('input',{}).get('context_paths') or payload.get('context_paths') or []
    paths=[]
    for p in requested:
        sp=safe_path(p)
        if sp and Path(sp).is_file():paths.append(sp)
    site=safe_slug(payload.get('targetSiteId',''))
    if not paths and site:
        candidates=sh(['git','ls-files'],timeout=30).stdout.splitlines()
        paths=[p for p in candidates if safe_path(p) and site in p.lower() and Path(p).is_file()][:8]
    if Path('package.json').is_file():paths.append('package.json')
    seen=[];total=0;context=[]
    for p in paths:
        if p in seen:continue
        seen.append(p)
        try:text=Path(p).read_text(errors='replace')
        except Exception:continue
        if len(text)>30000:text=text[:30000]+'\n/* truncated */'
        if total+len(text)>90000:break
        total+=len(text);context.append({'path':p,'content':text})
    return context

def allowed_prefixes(payload):
    site=str(payload.get('targetSiteId') or '').strip()
    explicit=payload.get('input',{}).get('allowed_paths') or []
    prefixes=[]
    for p in explicit:
        sp=safe_path(str(p).rstrip('/')+'/placeholder')
        if sp:prefixes.append(str(p).rstrip('/')+'/')
    route=f"app/{site}/" if site else ''
    if route and Path(route).exists():prefixes.append(route)
    prefixes.extend(['components/agent-generated/','data/agent-generated/','config/agent-generated/'])
    if site=='socialmarket':prefixes.extend(['app/','lib/orchestrator/'])
    return tuple(dict.fromkeys(prefixes))

def github_model_patch(task):
    payload=task.get('payload') or {};context=discover_context(payload);prefixes=allowed_prefixes(payload)
    if not prefixes:raise TaskError('no bounded writable path resolved')
    call_rid=token_rid=None
    try:
        call_rid=reserve('remote_llm_calls',1,task['run_id'],{'source':'github-models','task_id':task['id']},'github-models',MODEL)
        token_rid=reserve('llm_output_tokens',2400,task['run_id'],{'source':'github-models','task_id':task['id']},'github-models',MODEL)
        prompt={
          'task':{'capability':task['capability'],'prompt':payload.get('prompt'),'input':payload.get('input'),'targetSiteId':payload.get('targetSiteId')},
          'prior_outputs':payload.get('prior'),
          'writable_prefixes':prefixes,
          'repository_context':context
        }
        system='''You are a bounded coding agent. Return ONLY JSON {"summary":"...","files":[{"path":"...","content":"complete file text"}]}. Make the smallest production-quality change that satisfies the task. You may only write paths under writable_prefixes. Never modify workflows, secrets, migrations, lockfiles, package manifests, authentication, billing, or infrastructure. Preserve evidence/tracking truth; do not invent commercial facts. For existing files, only replace them if their current content is included in repository_context. Maximum 8 files.'''
        res=http_json('https://models.github.ai/inference/chat/completions','POST',{'Authorization':f'Bearer {GH_TOKEN}','Content-Type':'application/json'},{'model':MODEL,'messages':[{'role':'system','content':system},{'role':'user','content':json.dumps(prompt,ensure_ascii=False)}],'temperature':0.1,'max_tokens':2400,'response_format':{'type':'json_object'}},120)
        content=res.get('choices',[{}])[0].get('message',{}).get('content','{}');parsed=json.loads(content)
        used=int((res.get('usage') or {}).get('completion_tokens') or 0)
        finalize(call_rid,1,{'ok':True});finalize(token_rid,used,{'ok':True})
        return parsed,prefixes,used
    except Exception:
        release(call_rid);release(token_rid);raise

def apply_code_task(task):
    payload=task.get('payload') or {}
    if payload.get('targetRepo')!=REPO:raise TaskError(f"cross-repo write disabled: {payload.get('targetRepo')}")
    generated,prefixes,used=github_model_patch(task);files=generated.get('files') or []
    if not files or len(files)>8:raise TaskError('model returned invalid file count')
    total=0;changed=[]
    for item in files:
        p=safe_path(item.get('path',''));content=item.get('content')
        if not p or not isinstance(content,str) or not any(p.startswith(x) for x in prefixes):raise TaskError(f'unsafe generated path: {item.get("path")}')
        total+=len(content.encode())
        if total>180000:raise TaskError('generated patch exceeds 180KB')
        Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(content);changed.append(p)
    if not sh(['git','status','--porcelain'],timeout=30).stdout.strip():raise TaskError('model produced no repository changes')
    sh(['npm','install','--disable-pip-version-check'],timeout=300)
    sh(['npm','run','build'],timeout=600)
    branch=f"agent/{safe_slug(task['run_id'])}-{safe_slug(task['step_id'])}-{str(task['id'])[:8]}"
    sh(['git','config','user.name','SocialMarket Agent']);sh(['git','config','user.email','actions@users.noreply.github.com']);sh(['git','checkout','-b',branch]);sh(['git','add','--']+changed)
    sh(['git','commit','-m',f"agent: {task['capability']} {task['step_id']}"])
    sh(['git','push','origin',branch],timeout=180)
    title=f"Agent: {task['capability']} — {task['step_id']}"
    body=f"Automated bounded change for run `{task['run_id']}`.\n\nFiles: {', '.join(changed)}\n\nBuild: passed. Production merge remains separately approval-gated."
    pr=sh(['gh','pr','create','--repo',REPO,'--base','main','--head',branch,'--title',title,'--body',body],timeout=90).stdout.strip()
    sha=sh(['git','rev-parse','HEAD']).stdout.strip()
    number=None
    m=re.search(r'/pull/(\d+)',pr or '');number=int(m.group(1)) if m else None
    return {'summary':generated.get('summary'),'branch':branch,'commitSha':sha,'prUrl':pr,'prNumber':number,'files':changed,'build':'passed','model':MODEL,'modelOutputTokens':used}

def recursive_find(obj,key):
    if isinstance(obj,dict):
        if obj.get(key) not in (None,''):return obj[key]
        for v in obj.values():
            hit=recursive_find(v,key)
            if hit not in (None,''):return hit
    elif isinstance(obj,list):
        for v in obj:
            hit=recursive_find(v,key)
            if hit not in (None,''):return hit
    return None

def preview_task(task):
    prior=(task.get('payload') or {}).get('prior') or {}
    sha=recursive_find(prior,'commitSha')
    if not sha:raise TaskError('preview requires prior commitSha')
    status=json.loads(sh(['gh','api',f'repos/{REPO}/commits/{sha}/status'],timeout=60).stdout)
    vercel=[s for s in status.get('statuses',[]) if 'vercel' in str(s.get('context','')).lower()]
    if not vercel:raise TaskError('Vercel preview status not available yet',retry=True)
    best=vercel[0]
    if best.get('state')=='pending':raise TaskError('Vercel preview still pending',retry=True)
    if best.get('state')!='success':raise TaskError(f"Vercel preview failed: {best.get('state')}")
    return {'previewUrl':best.get('target_url'),'commitSha':sha,'provider':'vercel','status':'success'}

def production_task(task):
    payload=task.get('payload') or {}
    if not payload.get('approved'):raise TaskError('production deployment missing explicit approval')
    prior=payload.get('prior') or {};pr=recursive_find(prior,'prNumber')
    if not pr:raise TaskError('production deployment requires prior PR')
    checks=sh(['gh','pr','checks',str(pr),'--repo',REPO],timeout=90,check=False)
    if checks.returncode!=0:raise TaskError('required PR checks are not green',retry=True)
    out=sh(['gh','pr','merge',str(pr),'--repo',REPO,'--squash','--delete-branch'],timeout=120).stdout.strip()
    return {'merged':True,'prNumber':pr,'provider':'github+vercel','message':out[-1000:]}

def execute(task):
    cap=task.get('capability')
    if cap in ('code.change','site.repair','experiment.run'):return apply_code_task(task)
    if cap=='deploy.preview':return preview_task(task)
    if cap=='deploy.production':return production_task(task)
    raise TaskError(f'unsupported capability: {cap}')

def main():
    if not GH_TOKEN:raise SystemExit('GITHUB_TOKEN missing')
    processed=0
    while processed<MAX_TASKS:
        task=claim()
        if not task:break
        rid=None
        try:
            rid=reserve('github_worker_runs',1,task['run_id'],{'task_id':task['id'],'capability':task['capability']})
            output=execute(task);finish(task['id'],output);finalize(rid,1,{'ok':True});print(json.dumps({'task':task['id'],'status':'succeeded','output':output},ensure_ascii=False))
        except TaskError as e:
            release(rid);fail(task['id'],e,e.retry);print(json.dumps({'task':task.get('id'),'status':'failed','retry':e.retry,'error':str(e)},ensure_ascii=False))
        except Exception as e:
            release(rid);fail(task['id'],e,False);print(json.dumps({'task':task.get('id'),'status':'failed','error':str(e)},ensure_ascii=False))
        processed+=1
    print(json.dumps({'processed':processed,'worker':WORKER_ID}))

if __name__=='__main__':main()
