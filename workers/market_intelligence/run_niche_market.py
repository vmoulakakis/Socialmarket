import os,json,datetime,math,time
from gateway import db_call
import run as core

SELLER_KILL=float(os.getenv('SELLER_COMPETITION_KILL','82'))
AD_KILL=float(os.getenv('AD_PRESSURE_PROXY_KILL','92'))
AD_CONF=float(os.getenv('AD_PRESSURE_MIN_CONFIDENCE','.65'))
MAX_NICHES=int(os.getenv('MAX_NICHES','120'))

def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def clamp(v):return max(0.0,min(100.0,float(v)))
def latest_run():
    rows=db_call('GET','niche_runs',params={'status':'eq.completed','select':'id','order':'created_at.desc','limit':'1'}) or []
    return rows[0]['id'] if rows else None

def main():
    run_id=latest_run()
    if not run_id:
        print(json.dumps({'status':'no_niche_run'}));return
    niches=db_call('GET','niche_candidates',params={'run_id':f'eq.{run_id}','select':'id,taxonomy_id,category_raw,label,keywords,product_count,merchant_count,brand_count,median_price,total_times_bought,demand_proxy,seller_saturation_proxy,discovery_score,confidence','order':'discovery_score.desc.nullslast','limit':str(MAX_NICHES)}) or []
    if not niches:
        print(json.dumps({'status':'no_niches'}));return
    rr=(db_call('POST','market_research_runs',data={'scope_type':'micro_niche','scope_key':'GR','country_code':'GR','status':'running','query_plan':{'niche_run_id':run_id,'niches':len(niches),'providers':['google_trends','feed','searxng_optional'],'forecast':'statsforecast'},'started_at':now()},prefer='return=representation') or [])[0]
    fr=(db_call('POST','forecast_runs',data={'model_name':'StatsForecast niche ensemble','horizon_days':56,'training_window_days':365,'parameters':{'freq':'W','scope':'micro_niche'},'status':'running','started_at':now()},prefer='return=representation') or [])[0]
    out=[]
    try:
        for i,n in enumerate(niches,1):
            term=(n.get('label') or '').split('·')[0].strip() or n.get('category_raw') or ''
            tm={'demand':0,'growth_pct':0};fc={'growth_pct':0,'direction':'flat','dates':[],'points':[]};trend_ok=False
            try:
                series=core.trend_weekly(term)
                if series is not None:tm=core.trend_metrics(series);fc=core.forecast_series(series,8);trend_ok=True
            except Exception:pass
            serp=core.serp_density(core.search(f'{term} Ελλάδα αγορά τιμή προσφορά',20));serp_ok=serp is not None
            internal_demand=float(n.get('demand_proxy') or 0);combined=clamp(tm['demand']*.65+internal_demand*.35) if trend_ok else internal_demand
            seller_internal=float(n.get('seller_saturation_proxy') or 0);seller=clamp(seller_internal*.70+(serp['score'] if serp else seller_internal)*.30)
            ad=float(serp.get('ad_pressure_proxy') or 0) if serp else 0;ad_conf=float(serp.get('ad_proxy_confidence') or 0) if serp else 0
            kill=seller>=SELLER_KILL or (ad>=AD_KILL and ad_conf>=AD_CONF);reason='seller_competition_kill' if seller>=SELLER_KILL else 'ad_pressure_proxy_kill' if kill else None
            forecast_score=clamp(50+float(fc.get('growth_pct') or 0)*1.5);gap=clamp(combined*.65+(100-seller)*.35);discovery=float(n.get('discovery_score') or 0)
            score=0 if kill else clamp(combined*.35+forecast_score*.20+gap*.30+discovery*.15)
            conf=.82 if trend_ok and serp_ok else .68 if trend_ok or serp_ok else .52
            db_call('PATCH','niche_candidates',params={'id':f"eq.{n['id']}"},data={'trend_demand':round(combined,2),'forecast_growth':round(float(fc.get('growth_pct') or 0),2),'seller_competition':round(seller,2),'ad_pressure_proxy':round(ad,2),'market_score':round(score,2),'market_confidence':conf,'competition_kill':kill,'kill_reason':reason,'status':'market_scored'})
            for signal_type,val,confidence,evidence in [
                ('niche_combined_demand',combined,.82 if trend_ok else .58,{'term':term,'trend_available':trend_ok,'internal_demand':internal_demand,'trend_growth':tm.get('growth_pct')}),
                ('niche_seller_competition',seller,.78 if serp_ok else .65,{'merchant_count':n.get('merchant_count'),'product_count':n.get('product_count'),'serp_available':serp_ok}),
                ('niche_ad_pressure_proxy',ad,ad_conf,{'proxy_only':True,'serp':serp or {}})]:
                db_call('POST','market_signals',data={'research_run_id':rr['id'],'taxonomy_id':n.get('taxonomy_id'),'signal_type':signal_type,'source_name':'SocialMarket niche intelligence','normalized_score':round(val,2),'confidence':round(confidence,4),'evidence':evidence,'direction':'flat'})
            if trend_ok:
                for d,p in zip(fc.get('dates',[]),fc.get('points',[])):
                    db_call('POST','forecasts',data={'forecast_run_id':fr['id'],'scope_type':'micro_niche','scope_key':str(n['id']),'taxonomy_id':n.get('taxonomy_id'),'forecast_date':d,'point_forecast':p,'growth_pct':round(float(fc.get('growth_pct') or 0),2),'direction':fc.get('direction'),'confidence':.78})
            out.append({'niche':n.get('label'),'score':score,'competition_kill':kill,'forecast_growth':fc.get('growth_pct',0)});print(json.dumps({'progress':f'{i}/{len(niches)}','niche':n.get('label'),'score':round(score,1),'kill':kill},ensure_ascii=False),flush=True);time.sleep(.4)
        db_call('PATCH','market_research_runs',params={'id':f"eq.{rr['id']}"},data={'status':'completed','finished_at':now()});db_call('PATCH','forecast_runs',params={'id':f"eq.{fr['id']}"},data={'status':'completed','finished_at':now()})
    except Exception as e:
        db_call('PATCH','market_research_runs',params={'id':f"eq.{rr['id']}"},data={'status':'failed','error':str(e)[:1000],'finished_at':now()});db_call('PATCH','forecast_runs',params={'id':f"eq.{fr['id']}"},data={'status':'failed','finished_at':now()});raise
    print(json.dumps({'status':'completed','niches_scored':len(out),'top':sorted(out,key=lambda x:x['score'],reverse=True)[:20]},ensure_ascii=False))
if __name__=='__main__':main()
