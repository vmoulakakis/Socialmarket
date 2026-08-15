"""Demand Intelligence V3.1 fuzzy analytical engine.
Canonical market metrics are immutable inputs. Fuzzy logic describes market state and solution whitespace; it never rewrites Demand, Competition, Pain or Confidence.
"""
from __future__ import annotations
from dataclasses import dataclass,asdict
from math import exp
from typing import Optional

def _clamp(v:float,lo:float=0.0,hi:float=1.0)->float:return max(lo,min(hi,float(v)))
def trap(x:Optional[float],a:float,b:float,c:float,d:float)->Optional[float]:
    if x is None:return None
    x=float(x)
    if x<=a:return 1.0 if a==b and x==a else 0.0
    if x>=d:return 1.0 if c==d and x==d else 0.0
    if b<=x<=c:return 1.0
    if a<x<b:return _clamp((x-a)/(b-a))
    return _clamp((d-x)/(d-c))
def tri(x:Optional[float],a:float,b:float,c:float)->Optional[float]:
    if x is None:return None
    x=float(x)
    if x==b:return 1.0
    if x<=a or x>=c:return 0.0
    return _clamp((x-a)/(b-a) if x<b else (c-x)/(c-b))
def _and(*values:Optional[float])->Optional[float]:
    if any(v is None for v in values):return None
    return min(float(v) for v in values if v is not None)
def _or(*values:Optional[float])->float:return max([float(v) for v in values if v is not None] or [0.0])
@dataclass(frozen=True)
class FuzzyState:
    state:str;membership:dict[str,float];semantics:str='DERIVED fuzzy state; canonical metrics are immutable.'
def supply_strength(merchant_count:int,trust:Optional[float],commercial:Optional[float],research_confidence:Optional[float],fragmentation:Optional[float]=None)->Optional[float]:
    count_component=1-exp(-max(0,merchant_count)/8);parts=[count_component]
    if trust is not None:parts.append(_clamp(float(trust)/100))
    if commercial is not None:parts.append(_clamp(float(commercial)/100))
    if research_confidence is not None:
        rc=float(research_confidence);parts.append(_clamp(rc if rc<=1 else rc/100))
    quality=sum(parts)/len(parts) if parts else None
    if quality is None:return None
    if fragmentation is not None:quality*=1-.28*_clamp(float(fragmentation)/100)
    return round(quality*100,1)
def classify(demand:Optional[float],competition:Optional[float],pain:Optional[float],confidence:Optional[float],supply_strength:Optional[float],evidence_count:int=0)->FuzzyState:
    conf=None if confidence is None else float(confidence)*(100 if float(confidence)<=1 else 1)
    d_high=trap(demand,55,72,100,100);d_mid=tri(demand,25,55,82);c_low=trap(competition,0,0,30,55);c_high=trap(competition,50,72,100,100);p_high=trap(pain,48,68,100,100);cf_high=trap(conf,55,72,100,100);cf_low=trap(conf,0,0,45,65);s_low=trap(supply_strength,0,0,30,58);s_high=trap(supply_strength,48,70,100,100)
    raw={'validated_unmet_need':_and(d_high,p_high,cf_high),'whitespace':_and(d_high,s_low,c_low,cf_high),'emerging':_and(_or(d_mid,d_high),s_low,cf_high),'crowded_demand':_and(d_high,_or(c_high,s_high),cf_high),'balanced':_and(_or(d_mid,d_high),_or(s_high,tri(supply_strength,25,55,80)),cf_high),'uncertain':_or(cf_low,1.0 if competition is None else 0.0,.75 if pain is None else 0.0,.85 if evidence_count<3 else 0.0)}
    membership={k:round(float(v or 0.0),3) for k,v in raw.items()};return FuzzyState(state=max(membership,key=membership.get),membership=membership)
def whitespace_inference(demand:Optional[float],pain:Optional[float],competition:Optional[float],supply:Optional[float],confidence:Optional[float])->dict:
    if demand is None or pain is None:return {'status':'UNAVAILABLE','score':None,'reason':'demand_and_pain_required','rules':[],'canonical_demand_unchanged':demand}
    conf=float(confidence or 0);conf=conf*100 if conf<=1 else conf;d_hi=trap(demand,50,72,100,100) or 0;d_mid=tri(demand,25,55,82) or 0;p_hi=trap(pain,45,68,100,100) or 0;s_low=trap(supply,0,0,28,58) if supply is not None else None;s_hi=trap(supply,48,72,100,100) if supply is not None else None;c_low=trap(competition,0,0,30,58) if competition is not None else None;c_hi=trap(competition,48,72,100,100) if competition is not None else None;rules=[]
    def add(name,activation,target):
        if activation is not None and activation>0:rules.append({'rule':name,'activation':round(float(activation),3),'target':float(target)})
    if s_low is not None:add('high demand + high pain + low supply',min(d_hi,p_hi,s_low),94);add('medium/high demand + high pain + low supply',min(max(d_mid,d_hi),p_hi,s_low),80)
    if c_low is not None:add('high demand + high pain + low competition',min(d_hi,p_hi,c_low),90)
    if s_hi is not None:add('high demand + strong supply',min(d_hi,s_hi),46)
    if c_hi is not None:add('high demand + strong competition',min(d_hi,c_hi),42)
    add('high demand + high pain',min(d_hi,p_hi),72);add('medium demand + pain',min(max(d_mid,.05),max(p_hi,.05)),56)
    if not rules:return {'status':'UNAVAILABLE','score':None,'reason':'no_active_rules','rules':[],'canonical_demand_unchanged':demand}
    raw=sum(r['activation']*r['target'] for r in rules)/sum(r['activation'] for r in rules);certainty=.55+.45*_clamp(conf/100);score=max(0,min(100,raw*certainty))
    return {'status':'INFERRED','score':round(score,2),'raw_rule_score':round(raw,2),'certainty_multiplier':round(certainty,3),'rules':sorted(rules,key=lambda r:r['activation'],reverse=True),'canonical_demand_unchanged':demand,'semantics':'INFERRED solution whitespace; supply/competition affect exploitability, never observed demand.'}
def market_structure(demand:Optional[float],competition:Optional[float],pain:Optional[float],confidence:Optional[float],merchant_count:int,trust:Optional[float],commercial:Optional[float],research_confidence:Optional[float],evidence_count:int=0,fragmentation:Optional[float]=None)->dict:
    supply=supply_strength(merchant_count,trust,commercial,research_confidence,fragmentation);state=classify(demand,competition,pain,confidence,supply,evidence_count);whitespace=whitespace_inference(demand,pain,competition,supply,confidence)
    return {'supply_strength':supply,'state':asdict(state),'whitespace':whitespace,'contract':{'canonical_demand':demand,'canonical_demand_modified':False,'supply_is_separate_dimension':True}}
