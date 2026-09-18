from __future__ import annotations
import heapq, json, os, time
from pathlib import Path
import requests, ijson

from workers.market_intelligence.gateway import db_call

CLIENT="CD104"
CATEGORY_IDS=["3","67","25","27","29","33","63","147","87","89","99","103","109","117","119"]
COLUMNS=[
    "product_id","program_id","program_name","product_name","category","price",
    "tracking_url","image_url","thumb_url","in_stock","valid_from","valid_to",
    "discount","times_bought","sku","model_name"
]
BASE="https://affiliate.linkwi.se/feeds/1.2/{client}/programs-joined/columns-{columns}/catinc-{category}/catex-0/proginc-0/progex-0/feed.json"
MAX_PRODUCTS=max(1,min(100,int(os.getenv("MAX_PRODUCTS","100"))))
HEAP_SIZE=max(MAX_PRODUCTS*5,300)

def n(v):
    try:
        if v is None or v=="": return None
        return float(str(v).replace(",","."))
    except Exception:
        return None

def b(v):
    return v in (True,1,"1","true","True","yes","Y","y")

def load_commissions():
    rows=db_call("GET","linkwise_program_commissions",params={
        "select":"linkwise_program_id,program_name,flat_commission_eur,flat_commission_min_eur,flat_commission_max_eur,percent_commission,percent_commission_min,percent_commission_max"
    }) or []
    out={}
    for r in rows:
        pid=str(r.get("linkwise_program_id") or "").strip()
        if not pid: continue
        flats=[n(r.get(k)) for k in ("flat_commission_eur","flat_commission_min_eur","flat_commission_max_eur")]
        pcts=[n(r.get(k)) for k in ("percent_commission","percent_commission_min","percent_commission_max")]
        out[pid]={
            "program_name":r.get("program_name"),
            "flat":max([x for x in flats if x is not None], default=None),
            "pct":max([x for x in pcts if x is not None], default=None),
        }
    return out

def expected(price, rule):
    vals=[]
    if rule.get("flat") is not None:
        vals.append((float(rule["flat"]),"flat"))
    if rule.get("pct") is not None and price is not None:
        vals.append((price*float(rule["pct"])/100.0,f"percent:{rule['pct']}"))
    return max(vals,key=lambda x:x[0]) if vals else (None,"unknown")

def feed_url(category):
    return BASE.format(client=CLIENT,columns=",".join(COLUMNS),category=category)

def scan():
    commissions=load_commissions()
    heap=[]
    scanned=eligible=invalid=outstock=no_rule=0
    session=requests.Session()
    session.headers.update({"User-Agent":"SocialMarketAI/commission-top100","Accept-Encoding":"gzip, deflate"})

    for category in CATEGORY_IDS:
        url=feed_url(category)
        with session.get(url,stream=True,timeout=(30,900),allow_redirects=True) as r:
            r.raise_for_status()
            for p in ijson.items(r.raw,"item"):
                scanned+=1
                pid=str(p.get("program_id") or "").strip()
                rule=commissions.get(pid)
                if not rule:
                    no_rule+=1; continue
                price=n(p.get("price"))
                if not p.get("product_id") or not p.get("product_name") or not p.get("tracking_url") or price is None or price<=0:
                    invalid+=1; continue
                if p.get("in_stock") is not None and not b(p.get("in_stock")):
                    outstock+=1; continue
                commission,basis=expected(price,rule)
                if commission is None or commission<=0:
                    continue
                eligible+=1
                row={
                    "source_key":"linkwise_top100_calculated_commission",
                    "source_product_id":str(p.get("product_id")),
                    "program_id":pid,
                    "program_name":p.get("program_name") or rule.get("program_name"),
                    "sku":str(p.get("sku")) if p.get("sku") is not None else None,
                    "model_name":p.get("model_name"),
                    "product_name":str(p.get("product_name")),
                    "category_raw":p.get("category"),
                    "price_eur":round(price,4),
                    "expected_commission_eur":round(commission,4),
                    "commission_basis":basis,
                    "tracking_url":p.get("tracking_url"),
                    "image_url":p.get("image_url") or p.get("thumb_url"),
                    "in_stock":True,
                    "valid_from":p.get("valid_from"),
                    "valid_to":p.get("valid_to"),
                    "discount":n(p.get("discount")),
                    "times_bought":int(n(p.get("times_bought")) or 0),
                    "last_seen_at":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
                    "is_active":True,
                    "intelligence_status":"top100_calculated_commission_candidate",
                    "linkwise_route":"top100_calculated_commission"
                }
                key=(row["program_id"],row["source_product_id"])
                item=(commission, key, row)
                if len(heap)<HEAP_SIZE:
                    heapq.heappush(heap,item)
                elif commission>heap[0][0]:
                    heapq.heapreplace(heap,item)
        print(json.dumps({"category":category,"scanned":scanned,"commission_calculated":eligible}),flush=True)

    best={}
    for commission,key,row in sorted(heap,reverse=True):
        if key not in best or commission>best[key][0]:
            best[key]=(commission,row)
    selected=[x[1] for x in sorted(best.values(),key=lambda x:x[0],reverse=True)[:MAX_PRODUCTS]]

    if selected:
        db_call("POST","commerce_feed_eligible_offers",
            params={"on_conflict":"source_key,program_id,source_product_id"},
            data=selected,
            prefer="resolution=merge-duplicates,return=representation")
    return {
        "ok":True,
        "policy":"global top100 by calculated expected commission EUR",
        "max_products":MAX_PRODUCTS,
        "scanned":scanned,
        "commission_calculated":eligible,
        "selected":len(selected),
        "invalid":invalid,
        "out_of_stock":outstock,
        "no_commission_rule":no_rule,
        "top":[{"program":r["program_name"],"product":r["product_name"],"commission":r["expected_commission_eur"],"price":r["price_eur"]} for r in selected[:10]]
    }

if __name__=="__main__":
    result=scan()
    Path("linkwise-top100-commission-result.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False),flush=True)
