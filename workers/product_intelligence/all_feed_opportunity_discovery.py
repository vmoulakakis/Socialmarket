"""Full-feed research discovery: only >= EUR15 calculated commission is an economic hard gate.

Usage:
 python workers/product_intelligence/all_feed_opportunity_discovery.py \
   --feed linkwise-products.json --commission-rules commission_rules.json \
   --signals independent_market_signals.json --output affiliate-opportunities.json

Streaming JSON input (ijson), O(merchant count + shortlist size) RAM. No seller or
stock exclusion in the research universe. No paid AI or automatic publishing.
A missing commission rule is UNKNOWN, never zero or a guessed rate. Outputs are
research candidates, never verified high demand/low competition or actual CVR.
"""
from __future__ import annotations
import argparse
import heapq
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path:sys.path.insert(0,str(HERE))
from stream_feed import iter_records, normalize, linkwise_route
from vmdb_merchant_admission import _gateway_get

FLOOR=15.0
SHAPE=re.compile(r"^([1-9][0-9]*)-0/CD104$")
DEF_TOP=500
WEIGHTS={"pain_fit":0.35,"demand":0.25,"low_competition":0.20,"conversion":0.20}

def n(x):
    try:
        if x is None or isinstance(x,bool):return None
        value=float(str(x).strip().replace(",","."));return value if math.isfinite(value) else None
    except (TypeError,ValueError):return None

def clamp(x):
    return max(0.,min(100.,float(x)))

def valid_rule(pid,rules):
    r=rules.get(str(pid))
    return r if isinstance(r,dict) else None

def amount(price,rule):
    """Source-specified plan: min independent positive rate as conservative estimate.

    Explicit NULL is unknown. A mixed flat/percent program can have
    complex category exceptions: this is research estimate, not guaranteed payout.
    """
    if rule is None:return None,None
    flat=[n(rule.get(x)) for x in ("flat_commission_min_eur","flat_commission_eur")]
    pct=[n(rule.get(x)) for x in ("percent_commission_min","percent_commission")]
    alternatives=[(v,"flat_min") for v in flat if v is not None and v>0]
    alternatives +=[(price*v/100.,"percent_min") for v in pct if v is not None and v>0]
    if not alternatives:return None,None
    return min(alternatives,key=lambda x:x[0])

def normalize_signals(payload):
    """Market signals require explicit evidence and may be missing without rejection."""
    if not isinstance(payload,dict):return {}
    out={}
    for key,v in payload.items():
        if not isinstance(v,dict):continue
        record={}
        for label in ("pain_fit","demand","competition","conversion"):
            value=n(v.get(label))
            record[label]=clamp(value) if value is not None else None
        refs=v.get("evidence_refs")
        record["evidence_refs"]=[str(x)[:400] for x in refs[:12] if isinstance(x,str)] if isinstance(refs,list) else []
        record["source_kind"]=v.get("source_kind") if v.get("source_kind") in ("independent_observation","first_party_conversion","hypothesis") else "hypothesis"
        out[str(key).lower()]=record
    return out

def score_product(product,signals):
    """Evidence-aware opportunity score. Never claim a null as measured 0."""
    category=str(product.get("category_raw") or "").lower()
    title=str(product.get("product_name") or "").lower()
    best_key=None;best=None;strength=0
    for label,signal in signals.items():
        # Keys should describe a real product use-case, not generic fashion ranking.
        words=[w for w in re.findall(r"[a-z0-9α-ωάέήίόύώ]{4,}",label) if w not in {"item","products","tools"}]
        matches=sum(2 if w in title else 1 if w in category else 0 for w in words)
        if matches>strength:strength=matches;best_key=label;best=signal
    components={"pain_fit":None,"demand":None,"low_competition":None,"conversion":None}
    refs=[]
    kind="hypothesis_only"
    if best is not None and strength>0:
        components["pain_fit"]=best.get("pain_fit")
        components["demand"]=best.get("demand")
        components["low_competition"]=100.-best["competition"] if best.get("competition") is not None else None
        components["conversion"]=best.get("conversion")
        refs=best.get("evidence_refs",[])
        kind="source_observed" if best.get("source_kind")=="independent_observation" and refs else "hypothesis_only"
    # times_bought is feed-provided marketplace traction, NOT our affiliate CVR.
    observed=n(product.get("times_bought"))
    if components["conversion"] is None and observed is not None and observed>0:
        components["conversion"]=min(70.,10.*math.log1p(observed))
        refs.append("feed:times_bought_proxy_not_CVR")
    valid={k:v for k,v in components.items() if v is not None}
    # Missing evidence has neutral provisional score, not a fake demand estimate.
    mean=sum(WEIGHTS[k]*(components[k] if k in valid else 50.) for k in WEIGHTS)
    coverage=sum(WEIGHTS[k] for k in valid)
    confidence=round(coverage*(0.9 if kind=="source_observed" else 0.35),3)
    # Ranking usefulness with uncertainty penalty; none of these are exclusion filters.
    final=round(clamp(mean*(0.65+0.35*confidence)),3)
    return {"opportunity_score":final,"evidence_coverage":round(coverage,3),
            "evidence_confidence":confidence,"evidence_level":kind,
            "components":components,"problem_key":best_key,
            "evidence_refs":refs[:12],
            "interpretation":"research_hypothesis_not_verified_market_demand_or_CVR"}

def scan(feed,rules,signals,top=DEF_TOP):
    counts=Counter()
    heap=[]
    best={}
    for raw in iter_records(feed):
        counts["scanned"]+=1
        try:
            p=normalize(raw)
            route=linkwise_route(p.get("tracking_url"))
            match=SHAPE.fullmatch(route or "")
            pid=match.group(1) if match else None
            price=n(p.get("price"))
            if not pid or price is None or price<=0 or not p.get("external_product_id"):
                counts["missing_required_price_identity"]+=1;continue
            rule=valid_rule(pid,rules)
            commission,basis=amount(price,rule)
            if commission is None:
                counts["commission_unknown"]+=1;continue
            if commission+1e-9<FLOOR:
                counts["below_15"]+=1;continue
            counts["commission_eligible"]+=1
            record={
                "source_key":"linkwise",
                "source_product_id":p["external_product_id"],
                "program_id":pid,
                "merchant_domain":p.get("target_domain"),
                "product_title":p.get("product_name"),
                "category_text":p.get("category_raw"),
                "price_eur":round(price,2),
                "calculated_commission_eur":round(commission,2),
                "commission_basis":basis,
                "commission_provenance":{"network_program_id":pid,"rule_source":rule.get("source"),
                                         "imported_at":rule.get("imported_at"),"estimate_only":True},
                "original_tracking_url":p["tracking_url"],
                "image_url":p.get("image_url") or p.get("thumb_url"),
                "stock_state":"in_stock" if p.get("in_stock") is True else "out_of_stock" if p.get("in_stock") is False else "unknown",
                "valid_to":p.get("valid_to"),
                "feed_observed_at":datetime.now(timezone.utc).isoformat()
            }
            rank=score_product({**record,"product_name":record["product_title"],
                   "category_raw":record["category_text"],"times_bought":p.get("times_bought")},signals)
            record.update(rank)
            key=(pid,record["source_product_id"])
            old=best.get(key)
            if old and old["opportunity_score"]>=record["opportunity_score"]:
                counts["duplicate_encounter"]+=1;continue
            best[key]=record
            # Keep candidate frontier bounded, retain diversity at final selection.
            heapq.heappush(heap,(rank["opportunity_score"],counts["scanned"],key))
            if len(heap)>top*8:
                trim=heapq.nlargest(top*4,heap)
                heap=trim;heapq.heapify(heap)
                live={item[2] for item in heap}
                best={k:v for k,v in best.items() if k in live}
        except Exception:
            counts["malformed_source_row"]+=1
            continue
    shortlisted=sorted(best.values(),key=lambda v:(v["opportunity_score"],v["evidence_confidence"]),reverse=True)
    # Diversification is a ranking preference; no item fails economic eligibility for it.
    buckets=defaultdict(int);selected=[];overflow=[]
    for row in shortlisted:
        key=row.get("problem_key") or row.get("category_text") or "unknown"
        if buckets[key]<max(5,top//8):
            selected.append(row);buckets[key]+=1
        else:overflow.append(row)
        if len(selected)>=top:break
    if len(selected)<top:selected.extend(overflow[:top-len(selected)])
    return {"version":"full_feed_opportunity_v1","hard_filter":{"calculated_commission_eur_gte":FLOOR},
            "ranking_weights":WEIGHTS,"scope":"all_feed_input_records","counts":dict(counts),
            "selected_count":len(selected),"only_research_candidates":True,
            "market_demand_verified":False,"affiliate_conversions_verified":False,
            "products":selected}

def load_rules(path):
    if path == "vmdb":
        # Fetch ALL known network rules, not Merchant-360-approved subset.
        rows=_gateway_get("linkwise_program_commissions",{
          "select":"linkwise_program_id,program_name,flat_commission_eur,flat_commission_min_eur,percent_commission,percent_commission_min,source,imported_at",
          "limit":"1000"})
        return {str(r["linkwise_program_id"]):r for r in rows if r.get("linkwise_program_id")}
    return json.loads(Path(path).read_text(encoding="utf-8"))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--feed",required=True)
    ap.add_argument("--commission-rules",required=True)
    ap.add_argument("--signals",default="")
    ap.add_argument("--top",type=int,default=500)
    ap.add_argument("--output",default="affiliate-opportunities.json")
    args=ap.parse_args()
    if args.top<1 or args.top>2000:raise SystemExit("top must be 1..2000")
    rules=load_rules(args.commission_rules)
    if not isinstance(rules,dict):raise SystemExit("expected program-ID -> commission rule map")
    signals=normalize_signals(json.loads(Path(args.signals).read_text(encoding="utf-8"))) if args.signals else {}
    result=scan(args.feed,rules,signals,args.top)
    path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k!="products"},ensure_ascii=False))
if __name__=="__main__":main()
