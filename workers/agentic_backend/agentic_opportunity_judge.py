#!/usr/bin/env python3
"""Agentic commercial reasoning: hypotheses, forecasts, and product judge."""
from __future__ import annotations
import json, os, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import requests

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"workers"/"market_intelligence"))
from gateway import db_call  # noqa:E402

ENDPOINT="https://models.github.ai/inference/chat/completions"
TOKEN=os.getenv("GITHUB_TOKEN","")
FAST_MODEL=os.getenv("HYPOTHESIS_MODEL","openai/gpt-4.1-mini")
JUDGE_MODEL=os.getenv("OPPORTUNITY_JUDGE_MODEL","openai/gpt-4.1")
TOPICS=int(os.getenv("AGENTIC_TOPIC_LIMIT","20"))
PRODUCTS=int(os.getenv("AGENTIC_PRODUCT_LIMIT","60"))

def ask(model:str,system:str,payload:Any)->dict[str,Any]:
    if not TOKEN: raise RuntimeError("GITHUB_TOKEN_missing")
    r=requests.post(ENDPOINT,headers={"Authorization":f"Bearer {TOKEN}","Content-Type":"application/json"},
      json={"model":model,"temperature":0.12,"response_format":{"type":"json_object"},
            "messages":[{"role":"system","content":system},{"role":"user","content":json.dumps(payload,ensure_ascii=False)}]},
      timeout=120)
    r.raise_for_status()
    return json.loads(r.json()["choices"][0]["message"]["content"])

def load_topics():
    return list(db_call("GET","market_problem_clusters",params={
      "select":"id,problem_key,problem_title,problem_description,target_customer,category,subcategory",
      "market_code":"eq.GR","order":"updated_at.desc","limit":str(TOPICS)}) or [])

def build_queries(topic):
    system="""You are the Product Hunter in an agentic Greek commerce team.
Given one Greek problem, generate 4-8 concise AliExpress search queries for distinct solution mechanisms.
Do not optimize for cheapness. Do not impose seller, warehouse, shipping, scarcity or trust thresholds.
EU fulfillment is useful evidence, not a hard gate. Return JSON {queries:[{query,hypothesis,reason}]}."""
    out=ask(FAST_MODEL,system,topic)
    for i,x in enumerate(out.get("queries") or []):
      q=str(x.get("query") or "").strip()
      if not q:continue
      db_call("POST","ai_source_queries",params={"on_conflict":"market_code,source_key,query_text"},
        data={"market_code":"GR","source_key":"aliexpress","query_text":q,"problem_cluster_id":topic["id"],
              "hypothesis":x,"priority":100-i,"status":"active",
              "updated_at":datetime.now(timezone.utc).isoformat()},
        prefer="resolution=merge-duplicates,return=minimal")

def forecast(topic):
    signals=list(db_call("GET","ai_demand_signals",params={
      "select":"id,source_family,source_name,signal_type,observed_value,evidence_url,evidence_text,observed_at,ai_relevance,ai_purchase_intent,ai_confidence,metadata",
      "problem_cluster_id":f"eq.{topic['id']}","order":"observed_at.desc","limit":"120"}) or [])
    if not signals:return
    system="""You are the Forecast Agent for Greece. Use only supplied evidence.
Estimate directional demand for 30, 60 and 90 days. Never invent search volume or sales.
Return JSON {horizon_30:{direction,score_0_100,reason},horizon_60:{...},horizon_90:{...},
expected_peak:{window,reason},drivers:[...],risks:[...],confidence_0_100}.
Score is an AI directional index, not measured demand."""
    out=ask(JUDGE_MODEL,system,{"topic":topic,"signals":signals})
    db_call("POST","ai_demand_forecasts",data={
      "market_code":"GR","topic_key":str(topic.get("problem_key") or topic["id"]),
      "problem_cluster_id":topic["id"],"model_name":JUDGE_MODEL,
      "horizon_30":out.get("horizon_30") or {},"horizon_60":out.get("horizon_60") or {},
      "horizon_90":out.get("horizon_90") or {},"expected_peak":out.get("expected_peak") or {},
      "drivers":out.get("drivers") or [],"risks":out.get("risks") or [],
      "confidence":float(out.get("confidence_0_100") or 0)/100,
      "evidence_ids":[x["id"] for x in signals if x.get("id")],
      "raw_output":out},prefer="return=minimal")

def judge_products():
    rows=list(db_call("GET","ai_promotion_candidates_v",params={
      "select":"*","order":"observed_at.desc","limit":str(PRODUCTS)}) or [])
    for p in rows:
      recent=list(db_call("GET","ai_product_evaluations",params={
        "select":"id","product_candidate_id":f"eq.{p['product_candidate_id']}",
        "offer_id":f"eq.{p['offer_id']}","evaluator_role":"eq.final_judge","limit":"1"}) or [])
      if recent:continue
      system="""You are the final Commercial Judge in an agentic Greek commerce team.
The ONLY deterministic gate has already been applied: expected commission is at least EUR 10.
You MUST NOT create new hard thresholds for seller rating, EU warehouse, shipping, reviews,
scarcity, trust, demand, or price gap. Evaluate them holistically as evidence and trade-offs.
EU warehouse is a strong preference but not mandatory. Non-EU can win if overall economics and
conversion case justify it. Return strict JSON:
{verdict:'PROMOTE'|'WATCH'|'IGNORE',confidence_0_100,opportunity_thesis,risk_thesis,
demand_analysis,greek_market_analysis,seller_analysis,fulfillment_analysis,economics_analysis,
conversion_analysis,evidence_used:[...],next_evidence:[...]}."""
      out=ask(JUDGE_MODEL,system,{"candidate":p})
      db_call("POST","ai_product_evaluations",data={
        "product_candidate_id":p["product_candidate_id"],"offer_id":p["offer_id"],
        "evaluator_role":"final_judge","model_name":JUDGE_MODEL,"verdict":out.get("verdict"),
        "confidence":float(out.get("confidence_0_100") or 0)/100,
        "opportunity_thesis":out.get("opportunity_thesis"),"risk_thesis":out.get("risk_thesis"),
        "demand_analysis":out.get("demand_analysis") or {},
        "greek_market_analysis":out.get("greek_market_analysis") or {},
        "seller_analysis":out.get("seller_analysis") or {},
        "fulfillment_analysis":out.get("fulfillment_analysis") or {},
        "economics_analysis":out.get("economics_analysis") or {},
        "conversion_analysis":out.get("conversion_analysis") or {},
        "evidence":out.get("evidence_used") or [],"raw_output":out},
        prefer="return=minimal")

def main():
    topics=load_topics()
    for t in topics:
      try: build_queries(t)
      except Exception as e: print(json.dumps({"event":"query_agent_error","topic":t["id"],"error":str(e)[:300]}))
      try: forecast(t)
      except Exception as e: print(json.dumps({"event":"forecast_agent_error","topic":t["id"],"error":str(e)[:300]}))
    judge_products()
    print(json.dumps({"event":"agentic_backend_complete","topics":len(topics)}))
if __name__=="__main__": main()
