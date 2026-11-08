#!/usr/bin/env python3
"""Streaming CD104 discovery over the entire Linkwise catalog; EUR15 only gate.

The input can contain millions of items. RAM use is bounded by one item,
a small per-pain heap, program terms, and the existing problem metadata.
No model sees the bulk feed. Output is RESEARCH CANDIDATES ONLY.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime,timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import time
from urllib.parse import parse_qs,urlparse,quote
import uuid
import requests
import ijson

HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path:sys.path.insert(0,str(HERE))
from commission15_opportunity_engine import (
 FLOOR_EUR,BoundedPortfolio,best_problem,build_pain_index,
 estimate_commission,finite,passes_initial_gate,score_candidate
)

GATEWAY="https://gqpbskssrvpfjtujwezc.supabase.co/functions/v1/socialmarket-opportunity-gateway"
AUDIENCE="socialmarket-commission15-discovery"
SOURCE_KEY="linkwise"
ALLOWED_HOST="affiliate.linkwi.se"
def now():return datetime.now(timezone.utc).isoformat()

def oidc_token()->str:
 endpoint=os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"]
 req_token=os.environ["ACTIONS_ID_TOKEN_REQUEST_TOKEN"]
 sep="&" if "?" in endpoint else "?"
 r=requests.get(endpoint+sep+"audience="+quote(AUDIENCE),headers={"Authorization":"Bearer "+req_token},timeout=20)
 r.raise_for_status()
 return r.json()["value"]

def call_gateway(action:str,payload:dict)->dict:
 for attempt in range(3):
  r=requests.post(GATEWAY,headers={"Authorization":"Bearer "+oidc_token(),"Content-Type":"application/json"},
   json={"action":action,**payload},timeout=(15,70))
  if r.status_code in (401,403):raise RuntimeError("OIDC authorization denied")
  if r.status_code in (429,500,502,503,504) and attempt<2:
   time.sleep(3*(attempt+1));continue
  r.raise_for_status()
  result=r.json()
  if not result.get("ok"):raise RuntimeError("gateway declined "+action)
  return result
 raise RuntimeError("gateway unavailable")

def parse_route(link:str)->tuple[str|None,str|None]:
 """Never follow or rewrite affiliate URLs; extract source program and host."""
 try:
  u=urlparse(link)
  if u.scheme!="https" or u.hostname!="go.linkwi.se" or u.username or u.password:return None,None
  m=re.fullmatch(r"/z/([1-9][0-9]*)-0/CD104/?",u.path)
  if not m:return None,None
  landing=parse_qs(u.query).get("lnkurl",[])
  if not landing:return None,None
  dest=urlparse(landing[0])
  if dest.scheme not in ("https","http") or not dest.hostname:return None,None
  return m.group(1),dest.hostname.lower().removeprefix("www.")
 except Exception:return None,None

def parse_record(r:dict)->dict|None:
 if not isinstance(r,dict):return None
 price=finite(r.get("price") if "price" in r else r.get("price_eur"))
 if price is None or price<=0:return None
 # EUR is the scope. Non-EUR requires an authoritative FX quote before EUR15 calculation.
 if str(r.get("currency") or "EUR").upper()!="EUR":return None
 link=str(r.get("tracking_url") or "")
 program,domain=parse_route(link)
 if not program:return None
 if r.get("program_id") not in (None,"",program):return None
 name=str(r.get("product_name") or r.get("product_title") or r.get("title") or "")
 sku=str(r.get("product_id") or r.get("source_product_id") or "")
 if not sku or not name.strip():return None
 stock=r.get("in_stock")
 if stock is None:stock=None
 elif isinstance(stock,bool):pass
 elif str(stock).lower() in ("1","true","yes"):stock=True
 elif str(stock).lower() in ("0","false","no"):stock=False
 else:stock=None
 observed=str(r.get("valid_from") or "") or None
 valid_to=str(r.get("valid_to") or "") or None
 expire=False
 if valid_to:
  try:
   parsed=datetime.fromisoformat(valid_to.replace("Z","+00:00"))
   if parsed.tzinfo is None:parsed=parsed.replace(tzinfo=timezone.utc)
   expire=parsed<datetime.now(timezone.utc)
  except (ValueError,TypeError):pass
 return {"source_key":SOURCE_KEY,"source_product_id":sku,"product_name":name[:250],
   "description":str(r.get("description") or "")[:600],
   "category":str(r.get("category") or r.get("category_raw") or "")[:350],
   "price":price,"currency":"EUR","program_id":program,"merchant_domain":domain,
   "tracking_url":link,"image_url":str(r.get("image_url") or r.get("thumb_url") or "") or None,
   "in_stock":stock,"valid_from":observed,"valid_to":valid_to,
   "expired":expire,"times_bought":finite(r.get("times_bought"))}

def pool_candidates(feed,terms,problems,index,per_problem=32,max_records=0):
 pool=BoundedPortfolio(limit_per_problem=per_problem)
 counts=Counter()
 by_program=Counter()
 for raw in feed:
  if max_records and counts["scanned"]>=max_records:break
  counts["scanned"]+=1
  p=parse_record(raw)
  if p is None:
   counts["not_evaluable_missing_product_url_price_or_eur"]+=1
   continue
  rate=terms.get(p["program_id"])
  commission,basis=estimate_commission(p["price"],rate)
  if commission is None:
   counts["missing_program_terms_not_evaluable"]+=1
   by_program["no_rate:"+p["program_id"]]+=1
   continue
  if not passes_initial_gate(commission):
   counts["below_15_eur"]+=1
   continue
  counts["commission15_eligible"]+=1
  by_program[p["program_id"]]+=1
  selected,fit=best_problem(p["product_name"],p["description"],p["category"],index)
  problem_key=str(selected.get("problem_key") or selected.get("id")) if selected and fit>0 else "unmatched"
  scores=score_candidate(p,selected if fit else None,fit)
  record={"source_key":SOURCE_KEY,
   "source_product_id":p["source_product_id"],"program_id":p["program_id"],
   "merchant_domain":p["merchant_domain"],
   "product_title":p["product_name"],"category_text":p["category"],
   "price_eur":round(p["price"],4),"calculated_commission_eur":commission,
   "commission_basis":basis,
   "commission_provenance":{"program_source":str((rate or {}).get("source") or "historical_catalog"),
                            "program_imported_at":(rate or {}).get("imported_at"),
                            "calculation":"lower_observed_rate_or_flat_for_exploration",
                            "unverified_publisher_approval":True},
   "original_tracking_url":p["tracking_url"],
   "image_url":p["image_url"],"stock_state":"unknown" if p["in_stock"] is None else "in_stock" if p["in_stock"] else "out_of_stock",
   "valid_to":p["valid_to"],"problem_key":problem_key,
   "problem_cluster_id":selected.get("id") if selected and fit else None,
   **{k:scores[k] for k in ("pain_fit_score","demand_score","competition_score",
                          "conversion_proxy_score","opportunity_score","evidence_level","evidence_refs")},
   "stage":"research_candidate",
   "feed_observed_at":now(),"research_gaps":scores["unknowns"]}
  pool.consider(record)
 return pool.result(),counts,by_program

def stream_remote(url:str):
 u=urlparse(url)
 if(u.scheme!="https" or u.hostname!=ALLOWED_HOST or
    not u.path.startswith("/feeds/1.2/CD104/programs-") or
    not u.path.endswith("/feed.json") or u.username or u.password):
  raise ValueError("source URL must be official Linkwise CD104 HTTPS catalog feed")
 with requests.get(url,stream=True,timeout=(45,1500),
   headers={"User-Agent":"SocialMarketAI-CD104-Commission15/2","Accept-Encoding":"gzip, deflate"}) as res:
  res.raise_for_status()
  res.raw.decode_content=True
  yield from ijson.items(res.raw,"item")

def stream_local(path):
 with open(path,"rb") as stream:
  yield from ijson.items(stream,"item")

def chunks(items,n):
 for i in range(0,len(items),n):yield items[i:i+n]

def main():
 ap=argparse.ArgumentParser()
 source=ap.add_mutually_exclusive_group(required=True)
 source.add_argument("--input",type=Path)
 source.add_argument("--feed-url",default=None)
 ap.add_argument("--context",type=Path,help="JSON context for deterministic offline tests; normal runs use OIDC.")
 ap.add_argument("--max-records",type=int,default=0,help="0 means full streaming scan; positive means bounded pilot.")
 ap.add_argument("--per-problem",type=int,default=32)
 ap.add_argument("--upload",action="store_true",help="write only research candidates through OIDC gateway")
 ap.add_argument("--output",type=Path,default=Path("commission15-discovery-summary.json"))
 args=ap.parse_args()
 if args.max_records<0 or not 1<=args.per_problem<=100:raise SystemExit("invalid limits")
 if args.feed_url:
  u=urlparse(args.feed_url)
  if u.scheme!="https" or u.hostname!=ALLOWED_HOST or not u.path.startswith("/feeds/1.2/CD104/"):
   raise SystemExit("source must be official CD104 feed")
 context=json.loads(args.context.read_text(encoding="utf-8")) if args.context else call_gateway("context",{})
 terms={str(p["linkwise_program_id"]):p for p in context.get("programs",[])
        if p.get("linkwise_program_id") and str(p.get("linkwise_program_id")).isdigit()}
 index,problems=build_pain_index(context.get("problems",[]))
 if not terms:raise SystemExit("no numeric program-specific rates; cannot calculate EUR15 floor")
 stream=stream_local(args.input) if args.input else stream_remote(args.feed_url)
 run_key=str(uuid.uuid4())
 start=time.time()
 selected,counts,by_program=pool_candidates(stream,terms,problems,index,args.per_problem,args.max_records)
 if args.max_records:
  scope="bounded_pilot_not_full_catalog"
 else:
  scope="all_records_from_supplied_feed"
 snapshot={"ok":True,"run_key":run_key,"source":SOURCE_KEY,
  "scope":scope,"hard_commercial_filter":{"calculated_commission_eur_gte":15.0},
  "program_rate_count":len(terms),"market_pain_topics":len(problems),
  "counts":dict(counts),"by_program":dict(by_program),
  "ranked_research_candidates":len(selected),"elapsed_seconds":round(time.time()-start,2),
  "verified_demand_signal_count":sum(1 for p in problems if p.get("verified_demand_score") is not None),
  "verified_competition_signal_count":sum(1 for p in problems if p.get("verified_competition_score") is not None),
  "no_guaranteed_conversion_rate":True,"publisher_approval_verified":False,
  "published":False,
  "sample": [
   {"title":v["product_title"],"program_id":v["program_id"],
    "commission_estimate_eur":v["calculated_commission_eur"],
    "problem_key":v["problem_key"],"score":v["opportunity_score"],
    "demand_measured":v["demand_score"] is not None,
    "competition_measured":v["competition_score"] is not None}
   for v in selected[:20]]}
 if args.upload:
  header={k:snapshot[k] for k in ("run_key","source","scope","counts","ranked_research_candidates")}
  call_gateway("begin",header)
  for batch in chunks(selected,40):
   call_gateway("save",{"run_key":run_key,"candidates":batch})
  call_gateway("finish",{"run_key":run_key,"counts":snapshot["counts"],
   "ranked_research_candidates":len(selected),"scope":scope,
   "program_rate_count":len(terms)})
 args.output.write_text(json.dumps(snapshot,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps({k:snapshot[k] for k in ("ok","scope","program_rate_count","counts",
  "ranked_research_candidates","elapsed_seconds","no_guaranteed_conversion_rate")},ensure_ascii=False))
if __name__=="__main__":main()
