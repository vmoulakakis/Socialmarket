"""Demand Intelligence V3.1 temporal model laboratory.

Complex models are challengers, not defaults. All forecasts model the persisted
EVIDENCE-DERIVED demand index; none is relabelled as search volume, sales or market size.
"""
from __future__ import annotations
import json
import math
import statistics
from datetime import datetime
from typing import Any

MIN_POINTS = 90
MIN_SPAN_DAYS = 30
MIN_WINDOWS = 3
STAT_MIN_DAILY_POINTS = 14
CHANGEPOINT_MIN_DAILY_POINTS = 14
NEURAL_MIN_DAILY_POINTS = 60
NEURAL_MIN_SPAN_DAYS = 45


def _finite(v: Any) -> bool:
    try:
        return math.isfinite(float(v))
    except (TypeError, ValueError):
        return False


def _mae(y,p):
    pairs=[(float(a),float(b)) for a,b in zip(y,p) if _finite(a) and _finite(b)]
    return sum(abs(a-b) for a,b in pairs)/len(pairs) if pairs else None


def _rmse(y,p):
    pairs=[(float(a),float(b)) for a,b in zip(y,p) if _finite(a) and _finite(b)]
    return math.sqrt(sum((a-b)**2 for a,b in pairs)/len(pairs)) if pairs else None


def _smape(y,p):
    vals=[]
    for a,b in zip(y,p):
        if not (_finite(a) and _finite(b)): continue
        a,b=float(a),float(b); den=abs(a)+abs(b)
        vals.append(0.0 if den==0 else 2*abs(a-b)/den)
    return sum(vals)/len(vals)*100 if vals else None


def _daily(rows: list[dict]) -> list[dict]:
    buckets={}
    for r in rows:
        if not r.get('observed_at') or not _finite(r.get('demand_score')): continue
        day=str(r['observed_at'])[:10]
        buckets.setdefault(day,[]).append(float(r['demand_score']))
    return [{'ds':day,'y':statistics.fmean(values)} for day,values in sorted(buckets.items())]


def history_gate(rows: list[dict]) -> dict:
    clean=sorted([r for r in rows if r.get('observed_at') and _finite(r.get('demand_score'))], key=lambda r:r['observed_at'])
    daily=_daily(clean)
    if clean:
        start=datetime.fromisoformat(str(clean[0]['observed_at']).replace('Z','+00:00'))
        end=datetime.fromisoformat(str(clean[-1]['observed_at']).replace('Z','+00:00'))
        span=(end-start).total_seconds()/86400
    else: span=0
    reasons=[]
    if len(clean)<MIN_POINTS: reasons.append(f'needs_{MIN_POINTS}_raw_points')
    if span<MIN_SPAN_DAYS: reasons.append(f'needs_{MIN_SPAN_DAYS}_day_span')
    return {
        'eligible':not reasons,
        'status':'SHADOW_BACKTEST_ELIGIBLE' if not reasons else 'WITHHELD',
        'points':len(clean),'daily_points':len(daily),'span_days':round(span,2),'reasons':reasons,
        'statistical_ready':len(daily)>=STAT_MIN_DAILY_POINTS,
        'change_point_ready':len(daily)>=CHANGEPOINT_MIN_DAILY_POINTS,
        'neural_ready':len(daily)>=NEURAL_MIN_DAILY_POINTS and span>=NEURAL_MIN_SPAN_DAYS,
        'semantics':'readiness only; passing a gate does not promote a forecast to production'
    }


def _baseline_predictions(values:list[float]):
    y=values[1:]
    naive=values[:-1]
    drift=[]; rolling=[]
    for i in range(1,len(values)):
        drift.append(values[i-1] if i<2 else values[i-1]+(values[i-1]-values[0])/max(1,i-1))
        rolling.append(statistics.fmean(values[max(0,i-7):i]))
    return y,{'naive':naive,'drift':drift,'rolling_mean_7':rolling}


def baseline_backtest(rows: list[dict]) -> dict:
    values=[r['y'] for r in _daily(rows)]
    if len(values)<8:
        return {'status':'WITHHELD','reason':'insufficient_daily_baseline_history','daily_points':len(values)}
    y,preds=_baseline_predictions(values)
    models={k:{'mae':_mae(y,p),'rmse':_rmse(y,p),'smape':_smape(y,p)} for k,p in preds.items()}
    winner=min(models,key=lambda k:models[k]['mae'] if models[k]['mae'] is not None else float('inf'))
    return {'status':'BASELINE_READY','models':models,'winner':winner,'daily_points':len(values),'semantics':'chronological one-step baseline; no production promotion'}


def rolling_origin_baseline(rows:list[dict],windows:int=3,horizon:int=7)->dict:
    values=[r['y'] for r in _daily(rows)]
    if len(values)<max(21,windows*horizon+8):
        return {'status':'WITHHELD','reason':'insufficient_history_for_rolling_origin','daily_points':len(values)}
    results=[]
    for w in range(windows,0,-1):
        cut=len(values)-w*horizon
        train=values[:cut]; actual=values[cut:cut+horizon]
        naive=[train[-1]]*len(actual)
        slope=(train[-1]-train[0])/max(1,len(train)-1)
        drift=[train[-1]+slope*(i+1) for i in range(len(actual))]
        mean7=[statistics.fmean(train[-7:])]*len(actual)
        models={'naive':naive,'drift':drift,'rolling_mean_7':mean7}
        results.append({'window':windows-w+1,'train_points':len(train),'models':{k:{'mae':_mae(actual,p),'smape':_smape(actual,p)} for k,p in models.items()}})
    aggregate={}
    for model in ('naive','drift','rolling_mean_7'):
        aggregate[model]={
            'mean_mae':statistics.fmean(r['models'][model]['mae'] for r in results),
            'mean_smape':statistics.fmean(r['models'][model]['smape'] for r in results),
        }
    winner=min(aggregate,key=lambda k:aggregate[k]['mean_mae'])
    return {'status':'ROLLING_BACKTEST_READY','windows':results,'aggregate':aggregate,'winner':winner}


def change_points(rows:list[dict])->dict:
    daily=_daily(rows)
    if len(daily)<CHANGEPOINT_MIN_DAILY_POINTS:
        return {'status':'WITHHELD','reason':f'needs_{CHANGEPOINT_MIN_DAILY_POINTS}_daily_points','daily_points':len(daily)}
    try:
        import numpy as np
        import ruptures as rpt
        signal=np.array([x['y'] for x in daily],dtype=float)
        algo=rpt.Pelt(model='rbf',min_size=3).fit(signal)
        bkps=[i for i in algo.predict(pen=max(2.0,math.log(len(signal))*2.0)) if i<len(signal)]
        return {'status':'DERIVED','method':'ruptures.PELT-rbf','breakpoints':[{'index':i,'date':daily[i]['ds'],'value':daily[i]['y']} for i in bkps]}
    except Exception as exc:
        return {'status':'UNAVAILABLE','reason':f'ruptures_runtime:{type(exc).__name__}'}


def statsforecast_challengers(rows:list[dict],horizon:int=14)->dict:
    daily=_daily(rows)
    if len(daily)<STAT_MIN_DAILY_POINTS:
        return {'status':'WITHHELD','reason':f'needs_{STAT_MIN_DAILY_POINTS}_daily_points','daily_points':len(daily)}
    try:
        import pandas as pd
        from statsforecast import StatsForecast
        from statsforecast.models import AutoETS, Theta, AutoARIMA
        df=pd.DataFrame({'unique_id':'demand','ds':pd.to_datetime([x['ds'] for x in daily]),'y':[x['y'] for x in daily]})
        sf=StatsForecast(models=[AutoETS(season_length=7),Theta(season_length=7),AutoARIMA(season_length=7)],freq='D',n_jobs=1)
        fc=sf.forecast(df=df,h=horizon,level=[80,95]).reset_index()
        cols=[c for c in fc.columns if c not in {'unique_id','ds'}]
        point_cols=[c for c in cols if '-lo-' not in c and '-hi-' not in c]
        return {
            'status':'SHADOW_FORECAST',
            'models':point_cols,
            'dates':[str(x.date()) for x in fc['ds']],
            'series':{c:[round(float(v),3) for v in fc[c]] for c in cols},
            'production_promoted':False,
            'semantics':'shadow forecasts of the evidence-derived demand index'
        }
    except Exception as exc:
        return {'status':'UNAVAILABLE','reason':f'statsforecast_runtime:{type(exc).__name__}'}


def neural_challenger(rows:list[dict],horizon:int=14)->dict:
    gate=history_gate(rows)
    daily=_daily(rows)
    if not gate['neural_ready']:
        return {'status':'WITHHELD','reason':'neural_history_gate','daily_points':len(daily),'span_days':gate['span_days']}
    try:
        import pandas as pd
        from neuralforecast import NeuralForecast
        from neuralforecast.models import NHITS
        df=pd.DataFrame({'unique_id':'demand','ds':pd.to_datetime([x['ds'] for x in daily]),'y':[x['y'] for x in daily]})
        input_size=min(42,max(14,len(df)-horizon))
        nf=NeuralForecast(models=[NHITS(h=horizon,input_size=input_size,max_steps=300)],freq='D')
        nf.fit(df=df)
        fc=nf.predict().reset_index()
        value_col=next(c for c in fc.columns if c not in {'unique_id','ds'})
        return {
            'status':'SHADOW_FORECAST','model':'NHITS','dates':[str(pd.Timestamp(x).date()) for x in fc['ds']],
            'forecast':[round(float(v),3) for v in fc[value_col]],'production_promoted':False,
            'promotion_rule':'must beat statistical/naive baselines across chronological rolling windows'
        }
    except Exception as exc:
        return {'status':'UNAVAILABLE','reason':f'neuralforecast_runtime:{type(exc).__name__}'}


def optional_challengers() -> dict:
    available={}
    for name,module in [('statsforecast','statsforecast'),('neuralforecast','neuralforecast'),('ruptures','ruptures'),('dowhy','dowhy'),('darts','darts'),('timesfm','timesfm'),('chronos','chronos')]:
        try: __import__(module); available[name]=True
        except Exception: available[name]=False
    return {
      'available':available,
      'planned':{
        'statistical':['AutoETS','Theta','AutoARIMA'],
        'neuralforecast':['NHITS','NBEATSx','PatchTST','TFT'],
        'foundation':['TimesFM','Chronos2'],
        'reconciliation':['HierarchicalForecast'],
        'validation':['rolling-origin backtest','MAE','sMAPE','interval calibration']
      }
    }


def run_lab(rows: list[dict]) -> dict:
    gate=history_gate(rows)
    result={
        'version':'temporal_lab_v31',
        'gate':gate,
        'baseline':baseline_backtest(rows),
        'rolling_origin':rolling_origin_baseline(rows),
        'change_points':change_points(rows),
        'statistical_challengers':statsforecast_challengers(rows),
        'neural_challenger':neural_challenger(rows),
        'challengers':optional_challengers(),
        'production_forecast':None,
        'truth_label':'FORECASTED outputs are never OBSERVED demand'
    }
    if not gate['eligible']:
        result['decision']='WITHHOLD_PRODUCTION_FORECAST'
        result['reason']='Complex models cannot compensate for insufficient temporal history.'
        return result
    result['decision']='RUN_SHADOW_ENSEMBLE'
    result['reason']='History gate passed. No model is promoted until it wins chronological backtests and uncertainty checks.'
    return result


if __name__=='__main__':
    import sys
    payload=json.load(sys.stdin)
    print(json.dumps(run_lab(payload.get('history') or []),ensure_ascii=False,indent=2))
