import json
from vectorize_local_fast import fast_embed_products
import vectorize_local as v

if __name__ == '__main__':
    embedded, seen, needed = fast_embed_products(limit=500, batch_size=8)
    print(json.dumps({
        'status':'completed',
        'model':v.EMBED_DB_NAME,
        'dimensions':1024,
        'products_seen':seen,
        'products_needing_embedding':needed,
        'products_embedded':embedded,
        'paid_llm_calls':0,
        'paid_llm_cost_usd':0,
    },ensure_ascii=False,indent=2))
