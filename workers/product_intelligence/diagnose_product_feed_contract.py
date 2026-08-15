import json, sys
from pathlib import Path
import duckdb

src=sys.argv[1] if len(sys.argv)>1 else 'part_0000.parquet'
out=Path(sys.argv[2] if len(sys.argv)>2 else 'product-feed-contract.json')
con=duckdb.connect()

def ident(name):
    return '"'+str(name).replace('"','""')+'"'

cols=con.execute("describe select * from read_parquet(?)",[src]).fetchall()
column_names=[r[0] for r in cols]
possible=[c for c in column_names if any(k in c.lower() for k in ('merchant','program','shop','store','advertiser','partner','network','campaign','site','url'))]

sample_rows=con.execute("select * from read_parquet(?) limit 5",[src]).fetchall()
sample=[dict(zip(column_names,row)) for row in sample_rows]
profiles={}
for c in possible:
    ci=ident(c)
    q=f'''select count(*) total,count({ci}) non_null,count(distinct {ci}) distinct_count from read_parquet(?)'''
    total,non_null,distinct_count=con.execute(q,[src]).fetchone()
    vals=con.execute(f'''select cast({ci} as varchar) value,count(*) n
                         from read_parquet(?) where {ci} is not null
                         group by 1 order by n desc limit 30''',[src]).fetchall()
    profiles[c]={'total':total,'non_null':non_null,'distinct':distinct_count,'top_values':[{'value':v,'count':n} for v,n in vals]}

result={
  'source':src,
  'columns':[{'name':r[0],'type':r[1],'null':r[2]} for r in cols],
  'possible_merchant_identifier_columns':possible,
  'identifier_profiles':profiles,
  'sample_records':sample,
  'row_count':con.execute("select count(*) from read_parquet(?)",[src]).fetchone()[0],
}
out.write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
print(json.dumps({k:result[k] for k in ('row_count','possible_merchant_identifier_columns')},ensure_ascii=False))
