import os


def install_scope_context(core):
    scope_key=os.getenv('MARKET_SCOPE_KEY','').strip()
    if not scope_key or scope_key.lower() in ('all','portfolio'):
        return

    original_load=core.load_products
    original_post_one=core.post_one

    def scoped_load_products(max_products):
        scopes=core.get('market_scopes',{
            'scope_key':f'eq.{scope_key}','select':'id,scope_key,name,country_code,config','limit':'1'
        })
        if not scopes:
            raise RuntimeError(f'unknown market scope: {scope_key}')
        scope=scopes[0]
        members=core.get('product_market_scopes',{
            'market_scope_id':f"eq.{scope['id']}",'is_primary':'eq.true','select':'product_id,confidence',
            'order':'confidence.desc','limit':str(max(200,max_products*5))
        })
        ids=[x['product_id'] for x in members[:max_products]]
        if not ids:
            return []
        id_filter='in.('+','.join(ids)+')'
        rows=core.get('products',{
            'select':'id,product_name,description,category_raw,brand_name,merchant_name,price,full_price,times_bought,tracking_url,availability,in_stock,merchant_trust_score',
            'id':id_filter,'is_active':'eq.true','market_eligible':'eq.true','order':'times_bought.desc.nullslast,price.desc.nullslast','limit':str(max_products)
        })
        if not rows:
            rows=core.get('products',{
                'select':'id,product_name,description,category_raw,brand_name,merchant_name,price,full_price,times_bought,tracking_url,availability,in_stock,merchant_trust_score',
                'id':id_filter,'is_active':'eq.true','order':'times_bought.desc.nullslast','limit':str(max_products)
            })
        return rows

    def scoped_post_one(table,data):
        if table=='intelligence_runs':
            data=dict(data)
            data['scope_type']='market_scope'
            data['scope_key']=scope_key
            data['country_code']='GR'
            cfg=dict(data.get('config') or {})
            cfg['market_scope_key']=scope_key
            data['config']=cfg
        return original_post_one(table,data)

    core.load_products=scoped_load_products
    core.post_one=scoped_post_one
