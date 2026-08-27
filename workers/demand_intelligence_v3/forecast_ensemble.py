"""Demand Intelligence V3.1 temporal model laboratory.
Models the persisted evidence-derived demand index. Forecasts are never sales/search-volume facts.
"""
from __future__ import annotations
import math,statistics
from datetime import datetime
from typing import Any
MIN_POINTS=90;MIN_SPAN_DAYS=30;STAT_MIN_DAILY_POINTS=14;CHANGEPOINT_MIN_DAILY_POINTS=14;NEURAL_MIN_DAILY_POINTS=60;NEURAL_MIN_SPAN_DAYS=45

def _finite(v:Any)->bool:
    try:return math.isfinite(float(v))
    except (TypeError,ValueError):return False

def _mae(y,p):
    z=[(float(a),float(b)) for a,b in zip(y,p) if _finite(a) and _finite(b)];return sum(abs(a-b) for a,b in z)/len(z) if z else None

def _smape(y,p):
    vals=[]
    for a,b in zip(y,p):
        if not(_finite(a) and _finite(b)):continue
        a,b=float(a),float(b);d=abs(a)+abs(b);vals.append(0 if d==0 else 2*abs(a-b)/d)
    return sum(vals)/len(vals)*100 if vals else None

def _daily(rows):
    buckets={}
    for r in rows:
        if not r.get('observed_at') or not _finite(r.get('demand_score')):continue
        buckets.setdefault(str(r['observed_at'])[:10],[]).append(float(r['demand_score']))
    return [{'ds':d,'y':statistics.fmean(v)} for d,v in sorted(buckets.items())]

def history_gate(rows):
    clean=sorted([r for r in rows if r.get('observed_at') and _finite(r.get('demand_score'))],key=lambda r:r['observed_at']);daily=_daily(clean)
    if clean:
        start=datetime.fromisoformat(str(clean[0]['observed_at']).replace('Z','+00:00'));end=datetime.fromisoformat(str(clean[-1]['observed_at']).replace('Z','+00:00'));span=(end-start).total_seconds()/86400
    else:span=0
    reasons=[]
    if len(clean)<MIN_POINTS:reasons.append(f'needs_{MIN_POINTS}_raw_points')
    if span<MIN_SPAN_DAYS:reasons.append(f'needs_{MIN_SPAN_DAYS}_day_span')
    return {'eligible':not reasons,'status':'SHADOW_BACKTEST_ELIGIBLE' if not reasons else 'WITHHELD','points':len(clean),'daily_points':len(daily),'span_days':round(span,2),'reasons':reasons,'statistical_ready':len(daily)>=STAT_MIN_DAILY_POINTS,'change_point_ready':len(daily)>=CHANGEPOINT_MIN_DAILY_POINTS,'neural_ready':len(daily)>=NEURAL_MIN_DAILY_POINTS and span>=NEURAL_MIN_SPAN_DAYS}

def baseline_backtest(rows):
    values=[r['y'] for r in _daily(rows)]
    if len(values)<8:return {'status':'WITHHELD','reason':'insufficient_daily_baseline_history','daily_points':len(values)}
    y=values[1:];preds={'naive':values[:-1],'rolling_mean_7':[statistics.fmean(values[max(0,i-7):i]) for i in range(1,len(values))]};models={k:{'mae':_mae(y,p),'smape':_smape(y,p)} for k,p in preds.items()};winner=min(models,key=lambda k:models[k]['mae'] if models[k]['mae'] is not None else float('inf'))
    return {'status':'BASELINE_READY','models':models,'winner':winner,'daily_points':len(values)}
def rolling_origin(rows,windows=3,horizon=7):
    values=[r['y'] for r in _daily(rows)]
    if len(values)<max(21,windows*horizon+8):return {'status':'WITHHELD','reason':'insufficient_history_for_rolling_origin','daily_points':len(values)}
    results=[]
    for w in range(windows,0,-1):
        cut=len(values)-w*horizon;train=values[:cut];actual=values[cut:cut+horizon];pred={'naive':[train[-1]]*len(actual),'rolling_mean_7':[statistics.fmean(train[-7:])]*len(actual)};results.append({'window':windows-w+1,'models':{k:{'mae':_mae(actual,p),'smape':_smape(actual,p)} for k,p in pred.items()}})
    aggregate={m:statistics.fmean(r['models'][m]['mae'] for r in results) for m in ('naive','rolling_mean_7')};return {'status':'ROLLING_BACKTEST_READY','windows':results,'winner':min(aggregate,key=aggregate.get),'mean_mae':aggregate}
def change_points(rows):
    daily=_daily(rows)
    if len(daily)<CHANGEPOINT_MIN_DAILY_POINTS:return {'status':'WITHHELD','reason':f'needs_{CHANGEPOINT_MIN_DAILY_POINTS}_daily_points'}
    try:
        import numpy as np,ruptures as rpt
        signal=np.array([x['y'] for x in daily],dtype=float);bkps=[i for i in rpt.Pelt(model='rbf',min_size=3).fit(signal).predict(pen=max(2,math.log(len(signal))*2)) if i<len(signal)];return {'status':'DERIVED','method':'ruptures.PELT-rbf','breakpoints':[{'index':i,'date':daily[i]['ds'],'value':daily[i]['y']} for i in bkps]}
    except Exception as exc:return {'status':'UNAVAILABLE','reason':f'ruptures_runtime:{type(exc).__name__}'}
def statsforecast_challengers(rows,horizon=14):
    daily=_daily(rows)
    if len(daily)<STAT_MIN_DAILY_POINTS:return {'status':'WITHHELD','reason':f'needs_{STAT_MIN_DAILY_POINTS}_daily_points'}
    try:
        import pandas as pd
        from statsforecast import StatsForecast
        from statsforecast.models import AutoETS,Theta,AutoARIMA
        df=pd.DataFrame({'unique_id':'demand','ds':pd.to_datetime([x['ds'] for x in daily]),'y':[x['y'] for x in daily]});sf=StatsForecast(models=[AutoETS(season_length=7),Theta(season_length=7),AutoARIMA(season_length=7)],freq='D',n_jobs=1);fc=sf.forecast(df=df,h=horizon,level=[80]).reset_index();cols=[c for c in fc.columns if c not in {'unique_id','ds'}]
        return {'status':'SHADOW_FORECAST','dates':[str(x.date()) for x in fc['ds']],'series':{c:[round(float(v),3) for v in fc[c]] for c in cols},'production_promoted':False}
    except Exception as exc:return {'status':'UNAVAILABLE','reason':f'statsforecast_runtime:{type(exc).__name__}'}
def neural_challenger(rows,horizon=14):
    gate=history_gate(rows);daily=_daily(rows)
    if not gate['neural_ready']:return {'status':'WITHHELD','reason':'neural_history_gate','daily_points':len(daily),'span_days':gate['span_days']}
    try:
        import pandas as pd
        from neuralforecast import NeuralForecast
        from neuralforecast.models import NHITS
        df=pd.DataFrame({'unique_id':'demand','ds':pd.to_datetime([x['ds'] for x in daily]),'y':[x['y'] for x in daily]});nf=NeuralForecast(models=[NHITS(h=horizon,input_size=min(42,max(14,len(df)-horizon)),max_steps=300)],freq='D');nf.fit(df=df);fc=nf.predict().reset_index();col=next(c for c in fc.columns if c not in {'unique_id','ds'});return {'status':'SHADOW_FORECAST','model':'NHITS','forecast':[round(float(v),3) for v in fc[col]],'production_promoted':False,'promotion_rule':'must beat chronological statistical baselines'}
    except Exception as exc:return {'status':'UNAVAILABLE','reason':f'neuralforecast_runtime:{type(exc).__name__}'}
def optional_challengers():
    available={}
    for name in ('statsforecast','neuralforecast','ruptures','dowhy'):
        try:__import__(name);available[name]=True
        except Exception:available[name]=False
    return {'available':available,'strategy':['AutoETS','Theta','AutoARIMA','NHITS gated','change-point PELT','rolling-origin backtest','DoWhy only after causal readiness']}

def directional_scenarios(rows,horizon=14):
    """Transparent conservative/base/upside paths for the 0-100 demand index.

    This is a decision aid, not a volume or revenue forecast. It stays withheld
    until the same temporal history gate used by the model lab is satisfied.
    """
    gate=history_gate(rows);daily=_daily(rows)
    if not gate['eligible'] or len(daily)<14:
        return {'status':'WITHHELD','reasons':gate['reasons'] or ['needs_14_daily_points'],'truth_label':'WITHHELD'}
    values=[float(x['y']) for x in daily]
    recent=values[-14:];base_level=statistics.fmean(recent[-7:])
    prior=statistics.fmean(recent[:7]);raw_daily_trend=(base_level-prior)/7
    # Cap extrapolation so a short-lived spike cannot dominate the horizon.
    daily_trend=max(-1.5,min(1.5,raw_daily_trend))
    baseline=baseline_backtest(rows);winner=baseline.get('winner')
    mae=float(((baseline.get('models') or {}).get(winner) or {}).get('mae') or 0)
    dispersion=statistics.pstdev(recent) if len(recent)>1 else 0
    band=max(3.0,mae,dispersion*.8)
    clamp_index=lambda x:round(max(0.0,min(100.0,x)),3)
    base=[clamp_index(base_level+daily_trend*(i+1)) for i in range(horizon)]
    return {
        'status':'MODELED_SCENARIOS','horizon_days':horizon,
        'conservative':[clamp_index(x-band) for x in base],
        'base':base,
        'upside':[clamp_index(x+band) for x in base],
        'uncertainty_band':round(band,3),'baseline_winner':winner,
        'truth_label':'MODELED demand-index scenarios; not sales, search volume, market size or revenue',
        'assumptions':{'trend_cap_index_points_per_day':1.5,'history_points':gate['points'],'span_days':gate['span_days']},
    }

def run_lab(rows):
    gate=history_gate(rows);result={'version':'temporal_lab_v31','gate':gate,'baseline':baseline_backtest(rows),'rolling_origin':rolling_origin(rows),'change_points':change_points(rows),'directional_scenarios':directional_scenarios(rows),'statistical_challengers':statsforecast_challengers(rows),'neural_challenger':neural_challenger(rows),'challengers':optional_challengers(),'production_forecast':None,'truth_label':'FORECASTED outputs are never OBSERVED demand'}
    if not gate['eligible']:result['decision']='WITHHOLD_PRODUCTION_FORECAST';result['reason']='Complex models cannot compensate for insufficient temporal history.'
    else:result['decision']='RUN_SHADOW_ENSEMBLE';result['reason']='History gate passed; no model promoted until chronological backtests win.'
    return result
