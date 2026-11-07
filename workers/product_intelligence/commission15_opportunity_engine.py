"""SocialMarket opportunity discovery: exactly one commercial admission gate (EUR15).

This module ranks research CANDIDATES, never certifies merchant approval, market
demand, true competition, paid conversion probability or publication readiness.
It deliberately distinguishes unknown evidence from a low observed score.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import heapq
import html
import math
import re
import unicodedata
from typing import Any

FLOOR_EUR = 15.0
WEIGHTS = {"pain": .35, "demand": .25, "competition": .20, "conversion": .15, "quality": .05}
STOP = set("και της των στην στον για απο που ειναι στο την των ενος ενα μιας με μια οταν το αυτη που δεν να this that from into product best shop item greek purchase buy use cost home products problem better value price market".split())
# Bilingual hints are search-expansion hints, not evidence of demand or efficacy.
ALIASES = {
 "leak": ["διαρροη", "διαρροες", "leak", "water"],
 "water": ["νερο", "υγρασια", "water"],
 "mold": ["μουχλα", "mold", "humidity"],
 "humidity": ["υγρασια", "humid", "mold"],
 "solar": ["φωτοβολταικ", "solar", "panel", "pv"],
 "power": ["ρευμα", "ηλεκτρ", "power", "energy"],
 "hvac": ["κλιματισ", "hvac", "aircondition", "ac"],
 "key": ["κλειδι", "κλειδαρ", "lock", "key"],
 "noise": ["θορυβ", "noise", "decibel"],
 "storage": ["αποθηκευσ", "ντουλαπ", "storage", "cabinet"],
 "organize": ["οργανωσ", "αποθηκευσ", "organizer", "shelf"],
 "car": ["αυτοκιν", "car", "vehicle", "obd"],
 "thermal": ["θερμο", "thermal", "infrared"],
 "diagnostic": ["διαγνωσ", "diagnostic", "scanner"],
 "airbnb": ["airbnb", "rental", "επισκεπτ"],
 "cleaning": ["καθαρισ", "σκουπα", "clean", "vacuum"],
 "ergonomic": ["εργονομ", "ergonomic", "office"],
 "camera": ["καμερα", "camera", "visual"],
}
def norm(s:Any)->str:
 s=html.unescape(str(s or "")).casefold()
 s="".join(c for c in unicodedata.normalize("NFKD",s) if not unicodedata.combining(c))
 return re.sub(r"[^a-z0-9\u0370-\u03ff\u1f00-\u1fff]+"," ",s).strip()

def tokens(s:Any)->set[str]:
 return {w for w in norm(s).split() if len(w)>3 and w not in STOP}

def finite(v:Any)->float|None:
 try:
  x=float(str(v).replace(",",".")) if v not in (None,"") else None
  return x if x is not None and math.isfinite(x) else None
 except (TypeError,ValueError):return None

def estimate_commission(price:Any, program:dict|None)->tuple[float|None,str]:
 """Only numeric, source-attributed terms; never invent a general rate."""
 x=finite(price)
 if x is None or x<=0 or not isinstance(program,dict):return None,"missing_price_or_program_terms"
 options=[]
 flat=finite(program.get("flat_commission_min_eur"))
 if flat is None:flat=finite(program.get("flat_commission_eur"))
 rate=finite(program.get("percent_commission_min"))
 if rate is None:rate=finite(program.get("percent_commission"))
 if flat is not None and flat>0:options.append((flat,"flat_observed_or_min"))
 if rate is not None and rate>0:options.append((x*rate/100,"percentage_observed_or_min"))
 if not options:return None,"commission_terms_unknown"
 value,basis=min(options,key=lambda z:z[0])
 return round(value,4),basis

def passes_initial_gate(commission:Any)->bool:
 c=finite(commission)
 return c is not None and c>=FLOOR_EUR

def build_pain_index(problems:list[dict])->tuple[dict[str,list[dict]],list[dict]]:
 inverted=defaultdict(list)
 prepared=[]
 for original in problems:
  p=dict(original)
  words=tokens(str(p.get("problem_title") or "")+" "+str(p.get("problem_description") or ""))
  # Only specific tokens carry matching weight. Category labels alone don't.
  words.difference_update({"σπιτι","προιοντα","καλυτερη","καλυτερο","διαφορα","χρηση","χωρις","πρακτικες","λυσεις","προβλημα","τιμη"})
  for alias,alternates in ALIASES.items():
   if any(any(w.startswith(v) or v in w for v in alternates) for w in words):
    words.add(alias)
  p["_words"]=words
  prepared.append(p)
  for w in words:inverted[w].append(p)
 return dict(inverted),prepared

def product_terms(name:Any,description:Any,category:Any)->set[str]:
 result=tokens(str(name or "")+" "+str(description or "")+" "+str(category or ""))
 for alias,terms in ALIASES.items():
  if any(any(w.startswith(t) or t in w for t in terms) for w in result):
   result.add(alias)
 return result

def best_problem(name:Any,description:Any,category:Any,index:dict[str,list[dict]])->tuple[dict|None,float]:
 words=product_terms(name,description,category)
 hits=Counter()
 original={}
 for w in words:
  for p in index.get(w,[]):
   k=str(p.get("problem_key") or p.get("id"))
   hits[k]+=1;original[k]=p
 if not hits:return None,0.
 best=max(hits,key=lambda k:(hits[k]/max(2,min(6,len(original[k]["_words"]))),hits[k]))
 p=original[best]
 count=hits[best]
 score=round(min(100.,100.*count/max(2,min(6,len(p["_words"])))),3)
 # A single ambiguous token is just a weak hypothesis. Never call it "pain solved".
 if count==1:score=min(score,25.)
 return p,score

def conversion_proxy(product:dict)->float:
 """Listing-quality/friction proxy, NOT measured conversion or expected CVR."""
 price=finite(product.get("price")) or 0
 stock=product.get("in_stock")
 quality=35. if stock is True else 4. if stock is False else 18.
 if product.get("image_url"):quality+=15.
 if len(str(product.get("product_name") or ""))>=20:quality+=10.
 # Expensive offers may convert more slowly. No universal hard price gate.
 if price>0:quality+=max(0.,20.-max(0.,math.log10(max(1.,price/80.)))*13.)
 bought=finite(product.get("times_bought"))
 if bought and bought>0:quality+=min(15.,math.log10(bought+1)*5.)
 if product.get("valid_to") and product.get("expired") is True:quality-=30.
 return round(min(100.,max(0.,quality)),3)

def score_candidate(product:dict,pain:dict|None,fit:float)->dict:
 """Explicit missingness: neither demand nor competition appears without data."""
 demand=finite(pain.get("verified_demand_score")) if pain else None
 competition=finite(pain.get("verified_competition_score")) if pain else None
 # Null means not observed. Do not substitute AI-generated numbers as actual data.
 cv=conversion_proxy(product)
 quality=(100. if product.get("in_stock") is True else 25. if product.get("in_stock") is None else 0.)
 if not product.get("image_url"):quality*=.6
 # The unobserved demand/competition components contribute 0, and are listed as gaps.
 rank=fit*WEIGHTS["pain"]+cv*WEIGHTS["conversion"]+quality*WEIGHTS["quality"]
 if demand is not None:rank+=demand*WEIGHTS["demand"]
 if competition is not None:rank+=(100.-competition)*WEIGHTS["competition"]
 observed=sum([demand is not None,competition is not None])
 provenance=[]
 if pain and fit>0:provenance.append("hypothesis_pain_text_match")
 if demand is not None:provenance.append("independent_demand_observation")
 if competition is not None:provenance.append("independent_competition_observation")
 if finite(product.get("times_bought")) is not None:provenance.append("merchant_feed_times_bought_unverified")
 unknowns=[]
 if demand is None:unknowns.append("unmeasured_greek_demand")
 if competition is None:unknowns.append("unmeasured_competition")
 unknowns.extend(["no_observed_affiliate_cvr","no_verified_publisher_commission_terms","stock_unconfirmed"] if product.get("in_stock") is None else ["no_observed_affiliate_cvr","no_verified_publisher_commission_terms"])
 return {"opportunity_score":round(min(100.,max(0.,rank)),3),
   "pain_fit_score":fit,"demand_score":demand,"competition_score":competition,
   "conversion_proxy_score":cv,
   "evidence_level":"source_observed" if observed==2 else "hypothesis_only",
   "unknowns":unknowns,"evidence_refs":provenance}

@dataclass(order=True)
class Ranked:
 score:float
 serial:int
 item:dict

class BoundedPortfolio:
 def __init__(self,limit_per_problem:int=32):
  self.limit=limit_per_problem
  self.heaps:dict[str,list[Ranked]]=defaultdict(list)
  self.serial=0
 def consider(self,record:dict):
  key=str(record.get("problem_key") or "unmatched")
  h=self.heaps[key]
  self.serial+=1
  it=Ranked(float(record.get("opportunity_score") or 0),self.serial,record)
  if len(h)<self.limit:heapq.heappush(h,it)
  elif it.score>h[0].score:heapq.heapreplace(h,it)
 def result(self)->list[dict]:
  # Deduplicate repeated SKU across overlapping source categories.
  rows=[i.item for h in self.heaps.values() for i in h]
  dedup={}
  for item in rows:
   k=(item["source_key"],item["source_product_id"],item["problem_key"])
   old=dedup.get(k)
   if old is None or float(item["opportunity_score"])>float(old["opportunity_score"]):dedup[k]=item
  return sorted(dedup.values(),key=lambda x:(-float(x["opportunity_score"]),x["source_product_id"]))
