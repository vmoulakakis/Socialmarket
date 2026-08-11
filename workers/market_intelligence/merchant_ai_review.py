import os,json,requests,datetime
from gateway import db_call

KEY=os.getenv('DEEPSEEK_API_KEY','').strip()
MODEL=os.getenv('DEEPSEEK_MERCHANT_MODEL','deepseek-v4-flash')
LIMIT=min(int(os.getenv('MERCHANT_AI_REVIEW_LIMIT','100')),100)
ENABLE_PAID=os.getenv('ENABLE_PAID_REMOTE','0')=='1'

def clamp(v,lo=0,hi=100):return max(lo,min(hi,float(v)))
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def reserve():
    # Every legacy DeepSeek call must consume one slot from the SAME database
    # hard cap used by the new agentic engine. The RPC rejects the 101st
    # DeepSeek/OpenAI request in the current month.
    return db_call('POST','rpc/reserve_remote_model_request',data={
        'p_task_id':None,
        'p_provider':'deepseek',
        'p_model_name':MODEL,
        'p_complexity_score':0.97,
        'p_escalation_reason':'Legacy merchant evidence review explicitly enabled after deterministic evidence collection'
    })
def complete(payload):
    reserve()
    r=requests.post('https://api.deepseek.com/chat/completions',headers={'Authorization':f'Bearer {KEY}','Content-Type':'application/json'},json={'model':MODEL,'thinking':{'type':'disabled'},'temperature':0.0,'response_format':{'type':'json_object'},'messages':[{'role':'system','content':'You are an evidence auditor. Never invent facts. Judge only supplied snippets and source metadata. Treat uncorroborated complaints as weak evidence. Return JSON only.'},{'role':'user','content':json.dumps(payload,ensure_ascii=False)}]},timeout=90)
    r.raise_for_status();return json.loads(r.json()['choices'][0]['message']['content'])
def evidence(profile_id):
    return db_call('GET','merchant_reputation_evidence',params={'merchant_profile_id':f'eq.{profile_id}','select':'evidence_type,source_domain,title,snippet,credibility_tier,signal_score,confidence,review_rating,review_count','order':'credibility_tier.asc,observed_at.desc','limit':'35'}) or []
def main():
    if not ENABLE_PAID:
        print(json.dumps({'status':'skipped','reason':'paid remote inference disabled; set ENABLE_PAID_REMOTE=1 explicitly'}));return
    if not KEY:
        print(json.dumps({'status':'skipped','reason':'DEEPSEEK_API_KEY not configured'}));return
    merchants=db_call('GET','merchant_profiles',params={'select':'id,merchant_name,internal_trust_score,trust_score,external_reputation_score,external_reputation_confidence,complaint_risk_score,external_risk_flag,evidence_count','evidence_count':'gte.3','order':'active_offer_count.desc','limit':str(LIMIT)}) or []
    reviewed=0
    for m in merchants:
        ev=evidence(m['id'])
        if len(ev)<3:continue
        prompt={'merchant':m['merchant_name'],'current_external_score':m.get('external_reputation_score'),'current_complaint_risk':m.get('complaint_risk_score'),'rules':{'reputation_adjustment_range':[-15,15],'complaint_risk_adjustment_range':[-20,20],'severe_risk_requires':'at least two independent credible sources supporting a serious merchant-risk claim'},'evidence':ev}
        try:a=complete(prompt)
        except Exception as e:
            print(json.dumps({'merchant':m['merchant_name'],'ai_error':str(e)[:200]},ensure_ascii=False));continue
        rep_adj=max(-15,min(15,float(a.get('reputation_adjustment',0))));risk_adj=max(-20,min(20,float(a.get('complaint_risk_adjustment',0))));ai_conf=max(0,min(1,float(a.get('confidence',0))));base_ext=float(m.get('external_reputation_score') or 50);base_risk=float(m.get('complaint_risk_score') or 0)
        external=clamp(base_ext+rep_adj*ai_conf);risk=clamp(base_risk+risk_adj*ai_conf);internal=float(m.get('internal_trust_score') or m.get('trust_score') or 50);existing_conf=float(m.get('external_reputation_confidence') or 0);effective_conf=max(existing_conf,ai_conf*.85);effective_external=50+(external-50)*effective_conf;final=clamp(internal*.65+effective_external*.35)
        severe=bool(a.get('severe_risk')) and ai_conf>=.75 and risk>=80
        db_call('PATCH','merchant_profiles',params={'id':f"eq.{m['id']}"},data={'external_reputation_score':round(external,2),'external_reputation_confidence':round(effective_conf,4),'complaint_risk_score':round(risk,2),'external_risk_flag':bool(m.get('external_risk_flag')) or severe,'external_risk_reason':'deepseek_corroborated_external_risk' if severe else None,'trust_score':round(final,2),'evidence':{'deterministic_external_score':base_ext,'ai_reputation_adjustment':rep_adj,'ai_risk_adjustment':risk_adj,'ai_confidence':ai_conf,'ai_summary':str(a.get('summary') or '')[:1000],'model':MODEL,'final_trust':final},'last_researched_at':now()})
        db_call('POST','merchant_reputation_evidence',data={'merchant_profile_id':m['id'],'merchant_name':m['merchant_name'],'evidence_type':'ai_evidence_audit','source_name':'DeepSeek evidence auditor','source_domain':'api.deepseek.com','title':'Structured review of collected evidence','snippet':str(a.get('summary') or '')[:1800],'credibility_tier':4,'signal_score':round(rep_adj*ai_conf,2),'confidence':round(ai_conf,4),'metadata':{'model':MODEL,'risk_adjustment':risk_adj,'severe_risk':severe,'note':'AI interpretation only; underlying web evidence remains source of truth'}},prefer='return=minimal')
        reviewed+=1;print(json.dumps({'merchant':m['merchant_name'],'ai_confidence':ai_conf,'external':round(external,1),'risk':round(risk,1),'final_trust':round(final,1),'severe':severe},ensure_ascii=False),flush=True)
    print(json.dumps({'status':'completed','reviewed':reviewed,'model':MODEL,'shared_remote_cap':100}))
if __name__=='__main__':main()
