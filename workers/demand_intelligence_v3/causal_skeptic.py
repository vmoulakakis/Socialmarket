"""Conservative causal skeptic: correlation is never promoted to causation automatically."""
from __future__ import annotations
from typing import Any
MIN_OBSERVATIONS=60;MIN_EXOGENOUS=2

def readiness(history:list[dict],exogenous:dict[str,list[Any]]|None=None,dag:str|None=None,treatment:str|None=None,outcome:str='demand_score')->dict:
    rows=[r for r in history if r.get('observed_at') and r.get('demand_score') is not None];exogenous=exogenous or {};usable={k:v for k,v in exogenous.items() if isinstance(v,list) and len(v)>=MIN_OBSERVATIONS};reasons=[]
    if len(rows)<MIN_OBSERVATIONS:reasons.append(f'needs_{MIN_OBSERVATIONS}_observations')
    if len(usable)<MIN_EXOGENOUS:reasons.append(f'needs_{MIN_EXOGENOUS}_aligned_exogenous_series')
    if not dag:reasons.append('causal_dag_required')
    if not treatment:reasons.append('treatment_required')
    return {'status':'READY_FOR_CAUSAL_REFUTATION' if not reasons else 'WITHHELD','eligible':not reasons,'observations':len(rows),'usable_exogenous':sorted(usable),'reasons':reasons,'treatment':treatment,'outcome':outcome,'can_claim_causality':False,'semantics':'Causal language remains forbidden until identification, estimation and refutation succeed.'}

def alternative_explanations(context:dict)->list[dict]:
    evidence=context.get('retrieved_evidence') or [];supply=context.get('supply_context') or [];history=context.get('history') or [];domains={e.get('source_domain') for e in evidence if e.get('source_domain')};a=[]
    if len(domains)<=2 and evidence:a.append({'hypothesis':'source_concentration','why':'Most evidence may come from too few independent domains.','test':'Expand independent source types and compare demand.'})
    if supply:a.append({'hypothesis':'supply_visibility_bias','why':'More merchant pages may create more searchable evidence without higher underlying demand.','test':'Compare demand after controlling for supply/page count.'})
    if len(history)<30:a.append({'hypothesis':'short_history_regime','why':'Movement may be a research-cycle artifact.','test':'Accumulate longer history before trend claims.'})
    a.append({'hypothesis':'seasonality_or_event_confounder','why':'Holiday, school cycle, weather, event or promotion may affect evidence and supply.','test':'Add sourced exogenous event/season series.'})
    a.append({'hypothesis':'collector_or_query_change','why':'Collector coverage or taxonomy aliases can alter evidence density.','test':'Audit collector version, aliases and source mix.'})
    return a

def run_dowhy(data,dag:str,treatment:str,outcome:str,common_causes:list[str]|None=None)->dict:
    try:
        from dowhy import CausalModel
        model=CausalModel(data=data,treatment=treatment,outcome=outcome,graph=dag,common_causes=common_causes);estimand=model.identify_effect(proceed_when_unidentifiable=False);estimate=model.estimate_effect(estimand,method_name='backdoor.linear_regression');placebo=model.refute_estimate(estimand,estimate,method_name='placebo_treatment_refuter');subset=model.refute_estimate(estimand,estimate,method_name='data_subset_refuter')
        return {'status':'CAUSAL_CANDIDATE_REFUTED','estimate':float(estimate.value),'estimand':str(estimand),'placebo':str(placebo),'subset_refutation':str(subset),'can_claim_causality':False,'next':'Review assumptions and refutation statistics before causal wording.'}
    except Exception as exc:return {'status':'UNAVAILABLE','reason':f'dowhy_runtime:{type(exc).__name__}','can_claim_causality':False}

def audit(context:dict,exogenous:dict|None=None,dag:str|None=None,treatment:str|None=None)->dict:
    return {'readiness':readiness(context.get('history') or [],exogenous,dag,treatment),'alternative_explanations':alternative_explanations(context),'claim_policy':{'correlation_is_causation':False,'forecast_is_observation':False,'supply_may_modify_observed_demand':False}}
