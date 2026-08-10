import os,re,json,math,hashlib,datetime
from collections import defaultdict
import numpy as np
from gateway import db_call

MAX_CATEGORIES=int(os.getenv('NICHE_MAX_CATEGORIES','35'))
MAX_PRODUCTS=int(os.getenv('NICHE_MAX_PRODUCTS_PER_CATEGORY','1200'))
MIN_PRODUCTS=int(os.getenv('NICHE_MIN_PRODUCTS','8'))
EMBEDDING_MODEL=os.getenv('NICHE_EMBEDDING_MODEL','sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')

def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def clamp(v): return max(0.0,min(100.0,float(v)))
def slug(s): return re.sub(r'[^a-z0-9]+','-',str(s).lower()).strip('-')[:55] or hashlib.sha1(str(s).encode()).hexdigest()[:16]
def category_universe(): return db_call('POST','rpc/category_universe',data={'min_price':150,'min_products':MIN_PRODUCTS,'result_limit':MAX_CATEGORIES}) or []
def products_for(category): return db_call('POST','rpc/eligible_products_for_niche_discovery',data={'category_filter':category,'row_limit':MAX_PRODUCTS}) or []
def ensure_taxonomy(name,parent_id=None,level=1,taxonomy_type='category'):
    key=f'{taxonomy_type}-{slug(name)}-{str(parent_id or "root")[:8]}'
    rows=db_call('GET','taxonomy',params={'slug':f'eq.{key}','select':'id','limit':'1'}) or []
    if rows:return rows[0]['id']
    rows=db_call('POST','taxonomy',data={'parent_id':parent_id,'level':level,'name':name,'slug':key,'taxonomy_type':taxonomy_type,'country_code':'GR','active':True},prefer='return=representation') or []
    return rows[0]['id']
def doc(p): return re.sub(r'\s+',' ',' '.join([p.get('product_name') or '',p.get('brand_name') or '',p.get('description') or '']))[:1800]

def fallback_cluster(docs):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.cluster import MiniBatchKMeans
    from sklearn.metrics.pairwise import cosine_similarity
    n=len(docs)
    if n<MIN_PRODUCTS*2:return [0]*n,{0:{'keywords':[],'cohesion':75.0,'confidence':.58}},'tfidf-single'
    vec=TfidfVectorizer(ngram_range=(1,2),min_df=2,max_df=.92,max_features=8000,strip_accents='unicode',lowercase=True);X=vec.fit_transform(docs)
    k=max(2,min(14,round(math.sqrt(n/7))));model=MiniBatchKMeans(n_clusters=k,random_state=42,batch_size=256,n_init='auto').fit(X);terms=np.array(vec.get_feature_names_out());meta={}
    for cid in range(k):
        idx=np.where(model.labels_==cid)[0]
        if len(idx)==0:continue
        center=model.cluster_centers_[cid];top=terms[np.argsort(center)[-10:][::-1]].tolist();sims=cosine_similarity(X[idx],center.reshape(1,-1)).ravel()
        meta[cid]={'keywords':top,'cohesion':float(np.mean(sims)*100),'confidence':.62}
    return model.labels_.tolist(),meta,'tfidf-kmeans'

def semantic_cluster(docs):
    try:
        from bertopic import BERTopic
        from sentence_transformers import SentenceTransformer
        model=SentenceTransformer(EMBEDDING_MODEL);emb=model.encode(docs,show_progress_bar=False,batch_size=32,normalize_embeddings=True)
        min_topic=max(MIN_PRODUCTS,min(30,len(docs)//18 or MIN_PRODUCTS));tm=BERTopic(embedding_model=None,min_topic_size=min_topic,calculate_probabilities=False,verbose=False,language='multilingual')
        topics,_=tm.fit_transform(docs,emb);meta={}
        for tid in sorted(set(topics)):
            if tid==-1:continue
            words=[w for w,_ in (tm.get_topic(tid) or [])[:10]];idx=[i for i,t in enumerate(topics) if t==tid];cent=np.mean(emb[idx],axis=0);cohesion=float(np.mean(np.dot(emb[idx],cent)/(np.linalg.norm(cent)+1e-9))*100)
            meta[tid]={'keywords':words,'cohesion':cohesion,'confidence':.82}
        if -1 in topics:
            fb,fbmeta,_=fallback_cluster(docs);next_id=(max(meta.keys())+1) if meta else 0;remap={}
            for i,t in enumerate(topics):
                if t!=-1:continue
                f=fb[i]
                if f not in remap:remap[f]=next_id;meta[next_id]=fbmeta.get(f,{'keywords':[],'cohesion':55,'confidence':.52});next_id+=1
                topics[i]=remap[f]
        return list(topics),meta,'bertopic-multilingual'
    except Exception as e:
        labels,meta,engine=fallback_cluster(docs);return labels,meta,f'{engine};fallback={type(e).__name__}'

def label_for(category,keywords,products):
    clean=[x for x in keywords if len(x)>2 and not x.isdigit()][:4]
    return ' · '.join(clean) if clean else ((products[0].get('product_name') or category)[:90])
def score_cluster(rows,meta,category_total,category_merchants):
    count=len(rows);merchants=len(set(x.get('merchant_name') for x in rows if x.get('merchant_name')));brands=len(set(x.get('brand_name') for x in rows if x.get('brand_name')));times=sum(int(x.get('times_bought') or 0) for x in rows);median=float(np.median([float(x.get('price') or 0) for x in rows])) if rows else 0
    demand=clamp(22*math.log1p(times)+18*math.log1p(count));seller=clamp(50*(merchants/max(1,category_merchants))+50*(count/max(1,category_total)));cohesion=clamp(meta.get('cohesion',50));gap=clamp(demand*.62+(100-seller)*.38);discovery=clamp(gap*.55+cohesion*.20+min(100,median/5)*.10+meta.get('confidence',.5)*100*.15)
    return {'product_count':count,'merchant_count':merchants,'brand_count':brands,'median_price':median,'total_times_bought':times,'demand_proxy':demand,'seller_saturation_proxy':seller,'cluster_cohesion':cohesion,'discovery_score':discovery,'confidence':meta.get('confidence',.5)}

def main():
    cats=category_universe();run=(db_call('POST','niche_runs',data={'status':'running','engine':'bertopic+fallback','embedding_model':EMBEDDING_MODEL,'config':{'max_categories':MAX_CATEGORIES,'max_products_per_category':MAX_PRODUCTS,'min_products':MIN_PRODUCTS},'started_at':now()},prefer='return=representation') or [])[0];run_id=run['id'];total_products=0;niches=0;engines=defaultdict(int)
    try:
        for ci,c in enumerate(cats,1):
            category=c['category_raw'];rows=products_for(category)
            if len(rows)<MIN_PRODUCTS:continue
            total_products+=len(rows);labels,meta,engine=semantic_cluster([doc(p) for p in rows]);engines[engine]+=1;parent=ensure_taxonomy(category,None,1,'category');groups=defaultdict(list)
            for i,l in enumerate(labels):groups[int(l)].append(rows[i])
            for cluster_id,cluster_rows in groups.items():
                if len(cluster_rows)<max(3,MIN_PRODUCTS//2):continue
                m=meta.get(cluster_id,{'keywords':[],'cohesion':50,'confidence':.5});label=label_for(category,m.get('keywords',[]),cluster_rows);niche_key=f'{slug(category)}--{slug(label)}--{cluster_id}';tax=ensure_taxonomy(label,parent,2,'micro_niche');metrics=score_cluster(cluster_rows,m,len(rows),max(1,int(c.get('merchant_count') or 1)));representatives=sorted(cluster_rows,key=lambda p:(int(p.get('times_bought') or 0),float(p.get('discount_pct') or 0)),reverse=True)[:5]
                rec=(db_call('POST','niche_candidates',data={'run_id':run_id,'taxonomy_id':tax,'parent_taxonomy_id':parent,'category_raw':category,'niche_key':niche_key,'label':label,'keywords':m.get('keywords',[])[:10],'representative_products':[{'id':p['id'],'name':p.get('product_name'),'price':p.get('price'),'times_bought':p.get('times_bought')} for p in representatives],**metrics},prefer='return=representation') or [])[0];niche_id=rec['id'];rep_ids={p['id'] for p in representatives};members=[{'run_id':run_id,'niche_id':niche_id,'product_id':p['id'],'membership_score':round(float(m.get('confidence',.5)),4),'is_representative':p['id'] in rep_ids} for p in cluster_rows]
                for start in range(0,len(members),200):db_call('POST','niche_product_memberships',data=members[start:start+200],prefer='return=minimal')
                niches+=1
            db_call('PATCH','niche_runs',params={'id':f'eq.{run_id}'},data={'categories_seen':ci,'products_seen':total_products,'niches_created':niches});print(json.dumps({'category':category,'products':len(rows),'niches_total':niches,'engine':engine},ensure_ascii=False),flush=True)
        db_call('PATCH','niche_runs',params={'id':f'eq.{run_id}'},data={'status':'completed','categories_seen':len(cats),'products_seen':total_products,'niches_created':niches,'config':{'engines':dict(engines),'max_categories':MAX_CATEGORIES,'max_products_per_category':MAX_PRODUCTS},'finished_at':now()});print(json.dumps({'status':'completed','run_id':run_id,'products_seen':total_products,'niches_created':niches,'engines':dict(engines)},ensure_ascii=False))
    except Exception as e:
        db_call('PATCH','niche_runs',params={'id':f'eq.{run_id}'},data={'status':'failed','error':str(e)[:1500],'finished_at':now()});raise
if __name__=='__main__':main()
