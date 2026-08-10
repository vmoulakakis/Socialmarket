import os,json,datetime,requests
from statsforecast import StatsForecast
from statsforecast.models import AutoARIMA,AutoETS,Theta

SEARXNG=os.getenv('SEARXNG_BASE_URL','').rstrip('/')

def search(query,limit=10):
    if not SEARXNG:return []
    r=requests.get(f'{SEARXNG}/search',params={'q':query,'format':'json','language':'el-GR'},timeout=20);r.raise_for_status();return r.json().get('results',[])[:limit]

def forecast_panel(df,horizon=28,freq='D'):
    models=[AutoARIMA(season_length=7),AutoETS(season_length=7),Theta(season_length=7)]
    return StatsForecast(models=models,freq=freq,n_jobs=-1).forecast(df=df,h=horizon,level=[80,95])

def main():
    queries=['robot lawn mower Ελλάδα','portable power station Ελλάδα','premium cabin luggage Ελλάδα']
    payload={'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'queries':[]}
    for q in queries:
        results=search(q)
        payload['queries'].append({'query':q,'results':[{'title':x.get('title'),'url':x.get('url'),'engine':x.get('engine')} for x in results]})
    print(json.dumps(payload,ensure_ascii=False))

if __name__=='__main__':main()
