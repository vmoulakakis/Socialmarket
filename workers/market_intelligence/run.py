import os,json,datetime,requests,math,re,time,hashlib
from urllib.parse import urlparse
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
from statsforecast import StatsForecast
from statsforecast.models import AutoARIMA,AutoETS,Theta
from trendspy import Trends

SUPABASE_URL=os.environ.get('SUPABASE_URL','https://prrehmcvpyhupvlhtbzg.supabase.co').rstrip('/')
SERVICE_KEY=os.environ.get('SUPABASE_SERVICE_ROLE_KEY','')
SEARXNG=os.getenv('SEARXNG_BASE_URL','').rstrip('/')
MAX_CATEGORIES=int(os.getenv('MAX_CATEGORIES','40'))
MAX_PRODUCTS_PER_CATEGORY=int(os.getenv('MAX_PRODUCTS_PER_CATEGORY','60'))
HORIZON_WEEKS=int(os.getenv('FORECAST_WEEKS','8'))
MIN_VALIDITY_DAYS=int(os.getenv('MIN_VALIDITY_DAYS','20'))
SELLER_KILL=float(os.getenv('SELLER_COMPETITION_KILL','82'))
AD_PROXY_KILL=float(os.getenv('AD_PRESSURE_PROXY_KILL','92'))
AD_PROXY_MIN_CONF=float(os.getenv('AD_PRESSURE_MIN_CONFIDENCE','.65'))
ATHENS=ZoneInfo('Europe/Athens')
HEADERS={'apikey':SERVICE_KEY,'Authorization':f'Bearer {SERVICE_KEY}','Content-Type':'application/json'} if SERVICE_KEY else {}
COMMERCIAL_HINTS=('skroutz','bestprice','shop','store','public.gr','kotsovolos','plaisio','e-shop','market','price','αγορά','τιμή','προσφορά','€')
PRICE_COMPARE_HINTS=('skroutz','bestprice','price comparison','σύγκριση τιμών','συγκριση τιμων','shopping')
HIGH_FRICTION=('παπου','shoe','ρούχ','ρουχ','dress','φόρε','φορε','jean','jacket','κοστού','κοστου','δαχτυλ','ring','κόσμη','κοσμη','γυαλ','sunglass','άρωμα','αρωμα','perfume')
MEDIUM_FRICTION=('στρώμα','στρωμα','mattress','καναπ','sofa','πολυθρό','πολυθρο','armchair','καρέκ','καρεκ','chair','κράνος','κρανος','helmet','ποδήλα','ποδηλα','bike')

def clamp(v,lo=0,hi=100):return max(lo,min(hi,float(v)))
def now_iso():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def athens_today():return datetime.datetime.now(ATHENS).date()
def validity_cutoff_iso():return datetime.datetime.combine(athens_today()+datetime.timedelta(days=MIN_VALIDITY_DAYS),datetime.time.min,tzinfo=ATHENS).isoformat()
def api(method,path,params=None,data=None,prefer=None):
    if not SERVICE_KEY:raise RuntimeError('SUPABASE_SERVICE_ROLE_KEY is required')
    h=dict(HEADERS)
    if prefer:h['Prefer']=prefer
    r=requests.request(method,f'{SUPABASE_URL}/rest/v1/{path}',headers=h,params=params,json=data,timeout=120)
    r.raise_for_status()
    if not r.text:return None
    try:return r.json()
    except:return r.text

def rpc(name,payload):return api('POST',f'rpc/{name}',data=payload)

def slug_for(name):return 'raw-'+hashlib.sha1(name.encode('utf-8')).hexdigest()[:16]
def ensure_taxonomy(name):
    slug=slug_for(name)
    rows=api('GET','taxonomy',params={'slug':f'eq.{slug}','select':'id,name'}) or []
    if rows:return rows[0]['id']
    rows=api('POST','taxonomy',data={'level':1,'name':name,'slug':slug,'taxonomy_type':'raw_category','country_code':'GR'},prefer='return=representation')
    return rows[0]['id']

def query_term(category):
    parts=[x.strip() for x in re.split(r'[>|/\\]+',category or '') if x.strip()]
    s=(parts[-1] if parts else category or '').strip()
    s=re.sub(r'\s+',' ',re.sub(r'[_]+',' ',s))
    return s[:90] or 'online shopping'

def search(query,limit=20):
    if not SEARXNG:return []
    try:
        r=requests.get(f'{SEARXNG}/search',params={'q':query,'format':'json','language':'el-GR','safesearch':1},timeout=25)
        r.raise_for_status();return r.json().get('results',[])[:limit]
    except Exception:return []

def serp_density(results):
    if not results:return None
    commercial=0;price_compare=0;domains=set();evidence=[]
    for x in results:
        title=(x.get('title') or '').lower();url=x.get('url') or '';host=urlparse(url).netloc.lower();domains.add(host)
        text=f'{title} {url.lower()}'
        is_commercial=any(h in text for h in COMMERCIAL_HINTS)
        is_compare=any(h in text for h in PRICE_COMPARE_HINTS)
        commercial+=1 if is_commercial else 0;price_compare+=1 if is_compare else 0
        if len(evidence)<10:evidence.append({'title':x.get('title'),'url':url,'commercial':is_commercial,'price_compare':is_compare})
    n=max(1,len(results));density=100*commercial/n;diversity=100*len(domains)/n;compare_share=100*price_compare/n
    organic_saturation=clamp(density*.65+diversity*.35)
    # This is intentionally a proxy, not a claim of observed paid ad impressions.
    ad_pressure_proxy=clamp(density*.70+compare_share*.20+diversity*.10)
    confidence=clamp(len(results)/20,0,1)*.70
    return {'score':organic_saturation,'commercial_density':density,'domain_diversity':diversity,'price_compare_share':compare_share,'ad_pressure_proxy':ad_pressure_proxy,'ad_proxy_confidence':confidence,'evidence':evidence}

def seller_pressure(category_row,serp=None):
    merchants=float(category_row.get('merchant_count') or 0);products=float(category_row.get('product_count') or 0);brands=float(category_row.get('brand_count') or 0)
    merchant_score=100*(1-math.exp(-merchants/7.0));product_score=100*(1-math.exp(-products/45.0));brand_score=100*(1-math.exp(-brands/12.0))
    feed_score=clamp(merchant_score*.50+product_score*.30+brand_score*.20)
    external_score=(serp['commercial_density']*.60+serp['domain_diversity']*.40) if serp else None
    final=clamp(feed_score*.70+external_score*.30) if external_score is not None else feed_score
    return {'score':final,'feed_score':feed_score,'external_score':external_score,'merchants':merchants,'products':products,'brands':brands}

def trend_weekly(term):
    tr=Trends()
    df=tr.interest_over_time(term,timeframe='today 12-m',geo='GR')
    if df is None or len(df)==0:return None
    numeric=[]
    for c in df.columns:
        try:
            s=pd.to_numeric(df[c],errors='coerce')
            if s.notna().sum()>3:numeric.append((c,s))
        except Exception:pass
    if not numeric:return None
    col,series=numeric[0]
    series.index=pd.to_datetime(df.index)
    weekly=series.resample('W').mean().dropna().astype(float)
    if len(weekly)<12:return None
    return weekly

def trend_metrics(series):
    current=float(series.tail(4).mean())
    prev=float(series.iloc[-12:-4].mean()) if len(series)>=12 else float(series.iloc[:-4].mean())
    growth=100*(current-prev)/max(1,prev)
    slope=np.polyfit(np.arange(min(12,len(series))),series.tail(12).values,1)[0] if len(series)>=4 else 0
    return {'demand':clamp(current),'growth_pct':float(growth),'slope':float(slope),'latest':float(series.iloc[-1]),'last_12':[round(float(x),2) for x in series.tail(12).tolist()]}

def forecast_series(series,h=8):
    panel=pd.DataFrame({'unique_id':'trend','ds':series.index,'y':series.values.astype(float)})
    models=[AutoARIMA(season_length=4),AutoETS(season_length=4),Theta(season_length=4)]
    try:
        out=StatsForecast(models=models,freq='W',n_jobs=1).forecast(df=panel,h=h,level=[80])
        model_cols=[c for c in out.columns if c not in ('unique_id','ds') and '-lo-' not in c and '-hi-' not in c]
        values=out[model_cols].mean(axis=1).clip(0,100) if model_cols else pd.Series([series.tail(4).mean()]*h)
        current=max(1,float(series.tail(4).mean()));growth=100*(float(values.mean())-current)/current
        return {'dates':[pd.Timestamp(x).date().isoformat() for x in out['ds']], 'points':[round(float(x),2) for x in values], 'growth_pct':float(growth), 'direction':'up' if growth>3 else 'down' if growth<-3 else 'flat'}
    except Exception:
        current=float(series.tail(4).mean());return {'dates':[(series.index[-1]+pd.Timedelta(weeks=i+1)).date().isoformat() for i in range(h)],'points':[round(current,2)]*h,'growth_pct':0.0,'direction':'flat'}

def purchase_friction(category):
    s=(category or '').lower()
    if any(k in s for k in HIGH_FRICTION):return 0.85,'High fit/touch/sensory dependence'
    if any(k in s for k in MEDIUM_FRICTION):return 0.62,'Meaningful physical-fit or comfort dependence'
    return 0.28,'Primarily specification/value-led online purchase'

def friction_allowed(friction,discount):
    limit=.75 if discount>=45 else .60 if discount>=30 else .40
    return friction<=limit,limit

def relative(v,maxv):return clamp(100*math.log1p(max(0,float(v or 0)))/max(1e-9,math.log1p(max(0,float(maxv or 0))))) if maxv else 0

def product_validity_days(p):
    s=p.get('valid_to')
    if not s:return None
    try:
        dt=datetime.datetime.fromisoformat(str(s).replace('Z','+00:00'))
        d=dt.astimezone(ATHENS).date() if dt.tzinfo else dt.date()
        return (d-athens_today()).days
    except:return p.get('validity_days_remaining')

def validity_runway_score(days):
    if days is None or days<=MIN_VALIDITY_DAYS:return 0.0
    if days<=30:return 40.0
    if days<=60:return 65.0
    if days<=90:return 85.0
    return 100.0

def create_research_run(category_count):
    rows=api('POST','market_research_runs',data={'scope_type':'daily_market','scope_key':'GR','country_code':'GR','status':'running','query_plan':{'categories':category_count,'providers':['feed','google_trends','searxng_optional'],'forecast':'statsforecast','selection_policy':'v2-validity-travel-competition'},'started_at':now_iso()},prefer='return=representation')
    return rows[0]['id']

def create_forecast_run():
    rows=api('POST','forecast_runs',data={'model_name':'StatsForecast ensemble AutoARIMA+AutoETS+Theta','horizon_days':HORIZON_WEEKS*7,'training_window_days':365,'parameters':{'freq':'W','season_length':4},'status':'running','started_at':now_iso()},prefer='return=representation')
    return rows[0]['id']

def save_signal(run_id,taxonomy_id,signal_type,source_name,score,confidence,evidence,direction=None,raw=None):
    api('POST','market_signals',data={'research_run_id':run_id,'taxonomy_id':taxonomy_id,'signal_type':signal_type,'source_name':source_name,'normalized_score':round(clamp(score),2),'confidence':round(clamp(confidence,0,1),4),'evidence':evidence,'direction':direction,'raw_value':raw})

def category_products(category,limit):
    return api('GET','products',params={'category_raw':f'eq.{category}','hard_gate_pass':'eq.true','is_active':'eq.true','travel_related':'eq.false','valid_to':f'gt.{validity_cutoff_iso()}','select':'id,product_name,price,full_price,discount_pct,times_bought,tracking_url,image_url,thumb_url,extra_images,in_stock,valid_to,validity_days_remaining,validity_runway_score,program_name,merchant_name,category_raw','order':'times_bought.desc.nullslast,discount_pct.desc.nullslast','limit':str(limit)}) or []

def score_product(p,cm):
    friction,friction_reason=purchase_friction(p.get('category_raw'));discount=float(p.get('discount_pct') or 0);allowed,friction_limit=friction_allowed(friction,discount)
    days=product_validity_days(p);runway=validity_runway_score(days);validity_ok=days is not None and days>MIN_VALIDITY_DAYS
    purchase_ease=clamp((1-friction)*100);times=relative(p.get('times_bought'),cm['max_product_times'])
    demand=clamp(cm['combined_demand']*.75+times*.25);forecast_score=clamp(50+cm['forecast_growth']*1.5);attention_gap=clamp(demand*.6+(100-cm['competition'])*.4)
    median=max(1,float(cm['median_price'] or p.get('price') or 1));price=float(p.get('price') or 0);relative_price=clamp(50+(median-price)/median*80);offer=clamp(min(100,discount*2)*.7+relative_price*.3)
    merchant=80 if p.get('tracking_url') and p.get('in_stock') is not False else 50;creative=82 if p.get('image_url') and p.get('extra_images') else 72 if p.get('image_url') or p.get('thumb_url') else 20
    evidence=clamp(35+(25 if cm['trend_ok'] else 0)+(15 if cm['serp_ok'] else 0)+15+(10 if p.get('times_bought') is not None else 0));confidence=clamp(evidence/100*.85+0.10,0,1)
    raw=clamp(demand*.24+forecast_score*.18+attention_gap*.20+purchase_ease*.10+offer*.08+runway*.08+evidence*.05+merchant*.04+creative*.03);adjusted=clamp(raw-(1-confidence)*20)
    risks=[]
    if not validity_ok:risks.append('valid_to_20_days_or_less')
    if not allowed:risks.append(f'purchase_friction>{friction_limit:.2f}')
    if cm['competition_kill']:risks.append(cm['competition_kill_reason'])
    if cm['trend_ok'] and cm['trend_growth']>80 and cm['forecast_growth']<0:risks.append('possible_temporary_spike')
    if evidence<55:risks.append('weak_evidence')
    if not validity_ok or not allowed or cm['competition_kill']:decision='DROP'
    elif raw>=92 and confidence>=.78 and not risks:decision='PRIORITY'
    elif raw>=85 and confidence>=.70 and not any(r in risks for r in ('possible_temporary_spike',)):decision='CREATE_CREATIVE'
    elif raw>=75:decision='WATCHLIST'
    elif raw>=60:decision='MONITOR'
    else:decision='DROP'
    return {'friction':friction,'friction_reason':friction_reason,'validity_days':days,'runway':runway,'demand':demand,'forecast':forecast_score,'gap':attention_gap,'ease':purchase_ease,'offer':offer,'evidence':evidence,'merchant':merchant,'creative':creative,'raw':raw,'confidence':confidence,'adjusted':adjusted,'decision':decision,'risks':risks}

def main():
    categories=rpc('category_universe',{'min_price':150,'min_products':3,'result_limit':MAX_CATEGORIES}) or []
    if not categories:
        print(json.dumps({'generated_at':now_iso(),'status':'no_categories','message':'Import product feed first or no products satisfy rolling validity/travel gates'},ensure_ascii=False));return
    max_times=max(float(c.get('total_times_bought') or 0) for c in categories)
    research_run=create_research_run(len(categories));forecast_run=create_forecast_run();summary=[]
    try:
        for idx,c in enumerate(categories,1):
            category=c['category_raw'];term=query_term(category);taxonomy_id=ensure_taxonomy(category)
            trend_ok=False;series=None;tm={'demand':0,'growth_pct':0,'slope':0,'latest':0,'last_12':[]};fc={'dates':[],'points':[],'growth_pct':0,'direction':'flat'}
            try:
                series=trend_weekly(term)
                if series is not None:tm=trend_metrics(series);fc=forecast_series(series,HORIZON_WEEKS);trend_ok=True
            except Exception as e:tm['error']=str(e)[:300]
            feed_purchase=relative(c.get('total_times_bought'),max_times)
            serp=serp_density(search(f'{term} Ελλάδα αγορά τιμή προσφορά',20));serp_ok=serp is not None
            seller=seller_pressure(c,serp);ad_proxy=(serp.get('ad_pressure_proxy') if serp else 0);ad_conf=(serp.get('ad_proxy_confidence') if serp else 0)
            competition=clamp(seller['score']*.75+(serp['score'] if serp else seller['score'])*.25)
            seller_kill=seller['score']>=SELLER_KILL;ad_kill=bool(serp and ad_proxy>=AD_PROXY_KILL and ad_conf>=AD_PROXY_MIN_CONF)
            competition_kill=seller_kill or ad_kill;kill_reason='seller_competition_kill' if seller_kill else 'ad_pressure_proxy_kill' if ad_kill else None
            combined_demand=clamp((tm['demand']*.7+feed_purchase*.3) if trend_ok else feed_purchase)
            save_signal(research_run,taxonomy_id,'google_trends_demand','Google Trends via trendspy',tm['demand'],.80 if trend_ok else .0,{'term':term,'growth_pct':tm['growth_pct'],'slope':tm['slope'],'last_12':tm['last_12'],'available':trend_ok},'up' if tm['growth_pct']>3 else 'down' if tm['growth_pct']<-3 else 'flat',tm['latest'] if trend_ok else None)
            save_signal(research_run,taxonomy_id,'feed_purchase_demand','Linkwise feed',feed_purchase,.85,{'total_times_bought':c.get('total_times_bought'),'product_count':c.get('product_count')})
            save_signal(research_run,taxonomy_id,'seller_competition','Feed + SERP seller pressure',seller['score'],.82 if serp_ok else .72,seller,'flat')
            if serp:
                save_signal(research_run,taxonomy_id,'serp_saturation','SearXNG',serp['score'],.65,serp,'flat')
                save_signal(research_run,taxonomy_id,'ad_pressure_proxy','Transactional SERP proxy',ad_proxy,ad_conf,{'warning':'Proxy only; not direct paid-ad impression data','commercial_density':serp['commercial_density'],'price_compare_share':serp['price_compare_share'],'domain_diversity':serp['domain_diversity'],'evidence':serp['evidence']},'flat')
            save_signal(research_run,taxonomy_id,'combined_demand','SocialMarket ensemble',combined_demand,.82 if trend_ok else .58,{'trend_demand':tm['demand'],'feed_purchase':feed_purchase})
            if fc['dates']:
                for d,point in zip(fc['dates'],fc['points']):api('POST','forecasts',data={'forecast_run_id':forecast_run,'scope_type':'taxonomy','scope_key':slug_for(category),'taxonomy_id':taxonomy_id,'forecast_date':d,'point_forecast':point,'growth_pct':round(fc['growth_pct'],2),'direction':fc['direction'],'confidence':.78 if trend_ok else .45})
            products=category_products(category,MAX_PRODUCTS_PER_CATEGORY);max_product_times=max([float(p.get('times_bought') or 0) for p in products] or [0])
            cm={'combined_demand':combined_demand,'competition':competition,'seller_competition':seller['score'],'ad_pressure_proxy':ad_proxy,'ad_proxy_confidence':ad_conf,'competition_kill':competition_kill,'competition_kill_reason':kill_reason,'forecast_growth':fc['growth_pct'],'trend_growth':tm['growth_pct'],'trend_ok':trend_ok,'serp_ok':serp_ok,'median_price':c.get('median_price'),'max_product_times':max_product_times}
            promoted=0
            for p in products:
                sc=score_product(p,cm);market_ok=sc['decision']!='DROP' or (not cm['competition_kill'] and sc['validity_days'] is not None and sc['validity_days']>MIN_VALIDITY_DAYS)
                api('PATCH','products',params={'id':f"eq.{p['id']}"},data={'purchase_friction':round(sc['friction'],4),'purchase_friction_reason':sc['friction_reason'],'validity_days_remaining':sc['validity_days'],'validity_runway_score':round(sc['runway'],2),'market_eligible':market_ok and not cm['competition_kill'],'market_exclusion_reason':kill_reason if cm['competition_kill'] else ('validity_or_friction_gate' if sc['decision']=='DROP' else None)})
                rows=api('POST','opportunity_scores',data={'product_id':p['id'],'demand_score':round(sc['demand'],2),'forecast_momentum_score':round(sc['forecast'],2),'attention_gap_score':round(sc['gap'],2),'purchase_ease_score':round(sc['ease'],2),'offer_score':round(sc['offer'],2),'evidence_quality_score':round(sc['evidence'],2),'merchant_reliability_score':round(sc['merchant'],2),'creative_potential_score':round(sc['creative'],2),'seller_competition_score':round(seller['score'],2),'ad_pressure_score':round(ad_proxy,2),'competition_kill':cm['competition_kill'],'validity_runway_score':round(sc['runway'],2),'higo_raw':round(sc['raw'],2),'confidence':round(sc['confidence'],4),'higo_adjusted':round(sc['adjusted'],2),'decision':sc['decision'],'skeptic_status':'passed' if not sc['risks'] else 'risks_found','explanation':{'category':category,'market':cm,'validity_days':sc['validity_days'],'validity_runway_score':sc['runway'],'risks':sc['risks']}},prefer='return=representation')
                oid=rows[0]['id'];api('POST','evidence_audits',data={'opportunity_score_id':oid,'verdict':'pass' if not sc['risks'] else 'review' if sc['decision']!='DROP' else 'fail','risk_score':min(100,len(sc['risks'])*30),'risks':sc['risks'],'counter_evidence':[],'notes':'Deterministic skeptic audit; AI audit can refine later','model_route':'rules-v2'})
                if sc['decision'] in ('PRIORITY','CREATE_CREATIVE'):promoted+=1
            summary.append({'category':category,'term':term,'demand':round(combined_demand,1),'seller_competition':round(seller['score'],1),'ad_pressure_proxy':round(ad_proxy,1),'ad_proxy_confidence':round(ad_conf,2),'competition_kill':competition_kill,'kill_reason':kill_reason,'forecast_growth':round(fc['growth_pct'],1),'trend_available':trend_ok,'serp_available':serp_ok,'scored_products':len(products),'creative_candidates':promoted})
            print(json.dumps({'progress':f'{idx}/{len(categories)}','category':category,'competition_kill':competition_kill,'creative_candidates':promoted},ensure_ascii=False),flush=True);time.sleep(.7)
        api('PATCH','market_research_runs',params={'id':f'eq.{research_run}'},data={'status':'completed','finished_at':now_iso()});api('PATCH','forecast_runs',params={'id':f'eq.{forecast_run}'},data={'status':'completed','finished_at':now_iso()})
    except Exception as e:
        api('PATCH','market_research_runs',params={'id':f'eq.{research_run}'},data={'status':'failed','error':str(e)[:1000],'finished_at':now_iso()});api('PATCH','forecast_runs',params={'id':f'eq.{forecast_run}'},data={'status':'failed','finished_at':now_iso()});raise
    print(json.dumps({'generated_at':now_iso(),'status':'completed','research_run':research_run,'forecast_run':forecast_run,'categories':summary},ensure_ascii=False))

if __name__=='__main__':main()
