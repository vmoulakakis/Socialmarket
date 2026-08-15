"""SocialMarket Deep Demand Intelligence V3.1 supervisor.

Consumes a single taxonomy deep-context object and produces an auditable analytical
research object. The output is additive: canonical market values are copied exactly.
"""
from __future__ import annotations
import json
import sys
from statistics import fmean
from typing import Any

from fuzzy_fusion import market_structure
from forecast_ensemble import run_lab
from graph_rag import build as build_graph
from causal_skeptic import audit as causal_audit


def _finite(v:Any)->bool:
    try:
        x=float(v); return x==x and abs(x)!=float('inf')
    except (TypeError,ValueError): return False


def _mean(values):
    vals=[float(v) for v in values if _finite(v)]
    return fmean(vals) if vals else None


def evidence_decomposition(context:dict)->dict:
    rows=context.get('retrieved_evidence') or []
    domains={r.get('source_domain') for r in rows if r.get('source_domain')}
    platforms={r.get('platform') for r in rows if r.get('platform')}
    source_kinds={r.get('source_kind') for r in rows if r.get('source_kind')}
    direct=sum(1 for r in rows if float((r.get('retrieval') or {}).get('direct') or 0)>0)
    validated=sum(1 for r in rows if str(r.get('validation_status') or '').lower()=='validated')
    return {
        'status':'DERIVED','observations':len(rows),'independent_domains':len(domains),
        'source_kinds':sorted(source_kinds),'platforms':sorted(platforms),'direct_taxonomy_rows':direct,
        'validated_rows':validated,'validated_share':round(validated/len(rows),3) if rows else None,
        'avg_confidence':_mean([r.get('confidence') for r in rows]),
        'avg_retrieval_score':_mean([(r.get('retrieval') or {}).get('score') for r in rows]),
        'avg_authority':_mean([(r.get('retrieval') or {}).get('authority') for r in rows]),
        'avg_recency':_mean([(r.get('retrieval') or {}).get('recency') for r in rows]),
        'semantics':'Evidence quality/decomposition, not a new demand score.'
    }


def supply_decomposition(context:dict)->dict:
    rows=context.get('supply_context') or []
    merchants={str(r.get('merchant_id')):r for r in rows if r.get('merchant_id')}
    unique=list(merchants.values())
    risk=sum(1 for r in unique if r.get('risk_flag') is True)
    trust=_mean([r.get('trust_score') for r in unique])
    commercial=_mean([r.get('commercial_score') for r in unique])
    research=_mean([r.get('research_confidence') for r in unique])
    saturation=_mean([r.get('competition_intensity_score') for r in unique])
    return {
        'status':'DERIVED','merchant_count':len(unique),'program_rows':len(rows),'avg_trust':trust,
        'avg_commercial_quality':commercial,'avg_research_confidence':research,
        'avg_competition_intensity':saturation,'risk_rate':round(risk/len(unique),3) if unique else None,
        'semantics':'Exact-taxonomy solution coverage. It is not market share and never changes observed demand.'
    }


def pain_decomposition(context:dict)->dict:
    rows=context.get('validated_pains') or []
    return {
        'status':'OBSERVED' if rows else 'UNAVAILABLE','validated_clusters':len(rows),
        'avg_severity':_mean([r.get('pain_severity') for r in rows]),
        'avg_commercial_intent':_mean([r.get('commercial_intent') for r in rows]),
        'avg_audit_score':_mean([r.get('audit_score') for r in rows]),
        'avg_confidence':_mean([r.get('confidence') for r in rows]),
        'top_pains':[{
            'id':r.get('id'),'text':r.get('canonical_text') or r.get('representative_pain') or r.get('cluster_label'),
            'severity':r.get('pain_severity'),'commercial_intent':r.get('commercial_intent'),
            'evidence_count':r.get('evidence_count') or r.get('mention_count'),'source_diversity':r.get('source_diversity'),
            'confidence':r.get('confidence')
        } for r in rows[:15]],
    }


def jobs_to_be_done(context:dict)->dict:
    """Deterministic JTBD facets from persisted pain fields/text; AI may enrich later."""
    pains=context.get('validated_pains') or []
    facets=[]
    markers={
        'price_constraint':['ακριβ','φθην','οικονομ','τιμή','κόστος'],
        'availability_constraint':['δεν βρίσκ','διαθέσι','εξαντ','availability'],
        'delivery_constraint':['παράδο','μεταφορ','shipping','αποστολ'],
        'trust_constraint':['απάτ','εμπιστ','επιστροφ','εγγύη','refund'],
        'simplicity_desire':['εύκολ','απλ','setup','ρύθμι'],
        'alternative_request':['εναλλακ','χωρίς συνδρομ','alternative'],
        'fit_or_variant':['μέγεθος','χρώμα','μικρ','μεγαλ','variant'],
    }
    for p in pains:
        text=str(p.get('canonical_text') or p.get('representative_pain') or p.get('cluster_label') or '').lower()
        hits=[name for name,terms in markers.items() if any(t in text for t in terms)]
        if hits:
            facets.append({'pain_id':p.get('id'),'text':text[:500],'facets':hits})
    counts={name:sum(1 for f in facets if name in f['facets']) for name in markers}
    return {
        'status':'DERIVED' if pains else 'UNAVAILABLE','facets':facets[:25],
        'facet_counts':counts,'semantics':'Lexical JTBD facets used for research routing; not an LLM-created fact.'
    }


def analyze(context:dict,exogenous:dict|None=None)->dict:
    market=context.get('market') or {}
    evidence=evidence_decomposition(context)
    supply=supply_decomposition(context)
    pain=pain_decomposition(context)
    structure=market_structure(
        market.get('demand_score'),market.get('competition_score'),market.get('pain_gap_score'),market.get('confidence'),
        supply['merchant_count'],supply.get('avg_trust'),supply.get('avg_commercial_quality'),supply.get('avg_research_confidence'),
        evidence_count=evidence['observations']
    )
    graph=build_graph(context)
    temporal=run_lab(context.get('history') or [])
    causal=causal_audit(context,exogenous)
    return {
        'version':'deep_demand_v31',
        'taxonomy_id':context.get('taxonomy_id') or market.get('taxonomy_id'),
        'generated_from_market_observed_at':market.get('observed_at'),
        'truth_contract':{
            'canonical_metrics_read_only':True,'missing_remains_missing':True,
            'demand_supply_separated':True,'correlation_is_not_causation':True,'forecast_is_not_observed':True,
        },
        'observed':{
            'demand_score':market.get('demand_score'),'competition_score':market.get('competition_score'),
            'pain_gap_score':market.get('pain_gap_score'),'opportunity_score':market.get('opportunity_score'),
            'confidence':market.get('confidence'),'observed_at':market.get('observed_at'),
            'methodology_version':market.get('methodology_version')
        },
        'research':{'evidence':evidence,'pains':pain,'jobs_to_be_done':jobs_to_be_done(context)},
        'market_structure':{'supply':supply,'fuzzy':structure},
        'graph_rag':graph,
        'temporal_lab':temporal,
        'causal_skeptic':causal,
        'presentation_hints':{
            'scene_order':['executive_thesis','demand_anatomy','demand_supply_regime','jobs_to_be_done','market_structure','temporal_regime','forecast_lab','evidence_graph','causal_skeptic','decision_board'],
            'truth_labels':['OBSERVED','DERIVED','INFERRED','FORECASTED','CAUSAL_CANDIDATE','WITHHELD'],
        }
    }


if __name__=='__main__':
    payload=json.load(sys.stdin)
    print(json.dumps(analyze(payload.get('context') or payload,payload.get('exogenous')),ensure_ascii=False,indent=2,default=str))
