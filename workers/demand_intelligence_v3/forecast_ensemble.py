"""Demand Intelligence V3 forecast laboratory.

Neural/foundation models are challengers only. This file is intentionally optional:
the web application does not depend on heavy ML packages. A scheduled research
worker may install them when the history gate is satisfied.
"""
from __future__ import annotations
import json
import math
import statistics
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any

MIN_POINTS = 90
MIN_SPAN_DAYS = 30
MIN_WINDOWS = 3


def _finite(v: Any) -> bool:
    try:
        return math.isfinite(float(v))
    except (TypeError, ValueError):
        return False


def _mae(y, p):
    pairs=[(float(a),float(b)) for a,b in zip(y,p) if _finite(a) and _finite(b)]
    return sum(abs(a-b) for a,b in pairs)/len(pairs) if pairs else None


def _smape(y,p):
    vals=[]
    for a,b in zip(y,p):
        if not (_finite(a) and _finite(b)): continue
        a,b=float(a),float(b); den=abs(a)+abs(b)
        vals.append(0.0 if den==0 else 2*abs(a-b)/den)
    return sum(vals)/len(vals)*100 if vals else None


def history_gate(rows: list[dict]) -> dict:
    clean=sorted([r for r in rows if r.get('observed_at') and _finite(r.get('demand_score'))], key=lambda r:r['observed_at'])
    if clean:
        start=datetime.fromisoformat(str(clean[0]['observed_at']).replace('Z','+00:00'))
        end=datetime.fromisoformat(str(clean[-1]['observed_at']).replace('Z','+00:00'))
        span=(end-start).total_seconds()/86400
    else: span=0
    reasons=[]
    if len(clean)<MIN_POINTS: reasons.append(f'needs_{MIN_POINTS}_points')
    if span<MIN_SPAN_DAYS: reasons.append(f'needs_{MIN_SPAN_DAYS}_day_span')
    return {'eligible':not reasons,'status':'SHADOW_BACKTEST_ELIGIBLE' if not reasons else 'WITHHELD','points':len(clean),'span_days':round(span,2),'reasons':reasons}


def baseline_backtest(rows: list[dict], horizon: int=1) -> dict:
    clean=sorted([r for r in rows if _finite(r.get('demand_score'))], key=lambda r:r.get('observed_at',''))
    values=[float(r['demand_score']) for r in clean]
    if len(values)<8:
        return {'status':'WITHHELD','reason':'insufficient_baseline_history'}
    y=values[1:]
    naive=values[:-1]
    drift=[]
    for i in range(1,len(values)):
        if i<2: drift.append(values[i-1])
        else: drift.append(values[i-1]+(values[i-1]-values[0])/max(1,i-1))
    rolling=[]
    for i in range(1,len(values)):
        rolling.append(statistics.fmean(values[max(0,i-7):i]))
    models={
      'naive':{'mae':_mae(y,naive),'smape':_smape(y,naive)},
      'drift':{'mae':_mae(y,drift),'smape':_smape(y,drift)},
      'rolling_mean_7':{'mae':_mae(y,rolling),'smape':_smape(y,rolling)},
    }
    winner=min(models,key=lambda k:models[k]['mae'] if models[k]['mae'] is not None else float('inf'))
    return {'status':'BASELINE_READY','models':models,'winner':winner,'semantics':'chronological one-step descriptive baseline; no production promotion'}


def optional_challengers() -> dict:
    available={}
    for name,module in [('neuralforecast','neuralforecast'),('darts','darts'),('timesfm','timesfm'),('chronos','chronos')]:
        try:
            __import__(module); available[name]=True
        except Exception:
            available[name]=False
    return {
      'available':available,
      'planned':{
        'neuralforecast':['NHITS','NBEATSx','PatchTST','TFT'],
        'foundation':['TimesFM','Chronos2'],
        'reconciliation':['HierarchicalForecast'],
        'validation':['Darts backtesting/conformal where available']
      }
    }


def run_lab(rows: list[dict]) -> dict:
    gate=history_gate(rows)
    result={'gate':gate,'baseline':baseline_backtest(rows),'challengers':optional_challengers(),'production_forecast':None}
    if not gate['eligible']:
        result['decision']='WITHHOLD_NEURAL_FORECAST'
        result['reason']='Complex models cannot compensate for insufficient temporal history.'
        return result
    result['decision']='RUN_SHADOW_CHALLENGERS'
    result['reason']='History gate passed. Challengers may be backtested but cannot be promoted without beating the baseline across >=3 chronological windows.'
    return result


if __name__=='__main__':
    import sys
    payload=json.load(sys.stdin)
    print(json.dumps(run_lab(payload.get('history') or []),ensure_ascii=False,indent=2))
