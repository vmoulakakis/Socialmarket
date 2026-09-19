#!/usr/bin/env python3
"""Multi-source Greek demand harvester.

Collects public evidence from source families via SearXNG, then uses AI to
classify relevance and purchase intent. No product-quality hard filters.
"""
from __future__ import annotations
import json, os, sys, urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import requests

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"workers"/"market_intelligence"))
from gateway import db_call  # noqa:E402

SEARX=os.getenv("SEARXNG_BASE_URL","http://127.0.0.1:8080").rstrip("/")
MODEL_ENDPOINT="https://models.github.ai/inference/chat/completions"
MODEL=os.getenv("DEMAND_AGENT_MODEL","openai/gpt-4.1-mini")
TOKEN=os.getenv("GITHUB_TOKEN","")
MARKET="GR"
LIMIT=int(os.getenv("DEMAND_TOPIC_LIMIT","20"))

SOURCE_PLANS=[
 ("search","google_web",None,["τιμή","αγορά","πού θα βρω","review"]),
 ("greek_marketplace","skroutz","skroutz.gr",["τιμή","κριτικές","αγορά"]),
 ("greek_marketplace","bestprice","bestprice.gr",["τιμή","αγορά"]),
 ("social","reddit","reddit.com",["Greece","Ελλάδα","recommend","buy"]),
 ("social","youtube","youtube.com",["Greece","review","2026"]),
 ("social","tiktok","tiktok.com",["Greece","review","viral"]),
]

def ai_json(system:str,payload:Any)->dict[str,Any]:
    if not TOKEN:return {}
    r=requests.post(MODEL_ENDPOINT,headers={"Authorization":f"Bearer {TOKEN}","Content-Type":"application/json"},
      json={"model":MODEL,"temperature":0.1,"response_format":{"type":"json_object"},
            "messages":[{"role":"system","content":system},{"role":"user","content":json.dumps(payload,ensure_ascii=False)}]},
      timeout=90)
    r.raise_for_status()
    return json.loads(r.json()["choices"][0]["message"]["content"])

def search(q:str)->list[dict[str,Any]]:
    r=requests.get(f"{SEARX}/search",params={"q":q,"format":"json","language":"el-GR"},timeout=45)
    r.raise_for_status()
    return list(r.json().get("results") or [])[:8]

def topics()->list[dict[str,Any]]:
    rows=db_call("GET","market_problem_clusters",params={
      "select":"id,problem_key,problem_title,problem_description,target_customer,category",
      "market_code":"eq.GR","order":"updated_at.desc","limit":str(LIMIT)})
    return list(rows or [])

def classify(topic:dict[str,Any],family:str,name:str,result:dict[str,Any])->dict[str,Any]:
    system="""You are a Greek commerce demand evidence classifier. Use only the supplied web result.
Return strict JSON: {relevance_0_100,purchase_intent_0_100,confidence_0_100,signal_type,
evidence_summary,why_it_matters,noise_risk}. Do not invent search volumes, sales, rankings,
or metrics absent from the result. Viral attention is not automatically purchase demand."""
    return ai_json(system,{"topic":topic,"source_family":family,"source_name":name,
      "result":{"title":result.get("title"),"content":result.get("content"),"url":result.get("url")}})

def main()->int:
    count=0
    now=datetime.now(timezone.utc).isoformat()
    for topic in topics():
      title=topic.get("problem_title") or topic.get("problem_key")
      for family,name,domain,mods in SOURCE_PLANS:
        modifier=" OR ".join(f'"{m}"' for m in mods[:3])
        q=f'"{title}" ({modifier})'
        if domain:q+=f" site:{domain}"
        try: results=search(q)
        except Exception as e:
          print(json.dumps({"event":"source_error","source":name,"error":str(e)[:250]}));continue
        for result in results:
          url=str(result.get("url") or "")
          if not url:continue
          try: cls=classify(topic,family,name,result)
          except Exception as e:
            cls={"confidence_0_100":0,"noise_risk":str(e)[:250]}
          row={
            "market_code":MARKET,
            "topic_key":str(topic.get("problem_key") or topic["id"]),
            "problem_cluster_id":topic["id"],
            "source_family":family,
            "source_name":name,
            "signal_type":str(cls.get("signal_type") or "public_evidence"),
            "observed_value":{"title":result.get("title"),"engine":result.get("engine"),
              "publishedDate":result.get("publishedDate")},
            "evidence_url":url,
            "evidence_text":str(result.get("content") or "")[:4000],
            "observed_at":result.get("publishedDate") or now,
            "ai_relevance":float(cls.get("relevance_0_100") or 0)/100,
            "ai_purchase_intent":float(cls.get("purchase_intent_0_100") or 0)/100,
            "ai_confidence":float(cls.get("confidence_0_100") or 0)/100,
            "metadata":{"classification":cls,"query":q}
          }
          db_call("POST","ai_demand_signals",data=row,prefer="return=minimal")
          count+=1
    print(json.dumps({"event":"demand_harvest_complete","signals":count}))
    return 0
if __name__=="__main__": raise SystemExit(main())
