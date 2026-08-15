import collections, json, sys
from pathlib import Path
import ijson

from stream_feed import iter_records

src=sys.argv[1] if len(sys.argv)>1 else 'linkwise-products.json'
out=Path(sys.argv[2] if len(sys.argv)>2 else 'product-json-feed-contract.json')
limit=int(sys.argv[3]) if len(sys.argv)>3 else 1000

key_counts=collections.Counter()
merchant_like=collections.defaultdict(collections.Counter)
type_counts=collections.defaultdict(collections.Counter)
samples=[]
seen=0
integrity={'truncated':False,'error':None}

try:
    it=iter_records(src)
    while seen<limit:
        try:r=next(it)
        except StopIteration:break
        except ijson.common.IncompleteJSONError as e:
            integrity={'truncated':True,'error':str(e)[:500]};break
        if not isinstance(r,dict):continue
        seen+=1
        key_counts.update(r.keys())
        for k,v in r.items():
            type_counts[k][type(v).__name__]+=1
            lk=k.lower()
            if any(x in lk for x in ('merchant','program','shop','store','advertiser','partner','network','campaign','website','site','url','action')):
                text=str(v)[:500] if v is not None else '<NULL>'
                merchant_like[k][text]+=1
        if len(samples)<8:
            samples.append({k:v for k,v in r.items() if k.lower() not in ('description','extra_images')})
except ijson.common.IncompleteJSONError as e:
    integrity={'truncated':True,'error':str(e)[:500]}

result={
  'source':'linkwise-products.json',
  'records_sampled':seen,
  'integrity_within_sample':integrity,
  'keys_by_frequency':key_counts.most_common(),
  'types_by_key':{k:dict(v) for k,v in type_counts.items()},
  'merchant_like_fields':{
    k:{'distinct_in_sample':len(v),'top_values':[{'value':value,'count':n} for value,n in v.most_common(40)]}
    for k,v in merchant_like.items()
  },
  'sample_records_without_description_or_extra_images':samples,
}
out.write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
print(json.dumps({'records_sampled':seen,'fields':list(key_counts),'merchant_like_fields':list(merchant_like)},ensure_ascii=False))
