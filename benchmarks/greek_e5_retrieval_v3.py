#!/usr/bin/env python3
"""Real multilingual embedding evaluation — Greek consumer-pain/product retrieval.

Requires network once to fetch the MIT-licensed Hugging Face model, then runs
entirely on CPU without API tokens. Hard negatives are deliberately unrelated.
This does NOT claim Greek demand/supply or trained recommendation quality.
"""
from __future__ import annotations
import json,time
import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_ID="intfloat/multilingual-e5-small"
QUERY=[
 "ανίχνευση κρυφής διαρροής νερού σε τοίχο",
 "ειδοποίηση πτώσης ηλικιωμένου όταν μένει μόνος",
 "έλεγχος θερμοκρασίας ψυγείου εξ αποστάσεως",
 "αισθητήρας υγρασίας για πρόληψη μούχλας",
 "ανίχνευση εισροής νερού σε σκάφος",
]
DOCUMENTS=[
 "Έξυπνος ανιχνευτής διαρροής νερού τοίχου με ειδοποίηση",
 "Αισθητήρας πτώσης ηλικιωμένων και ειδοποίηση κινητού",
 "WiFi θερμόμετρο ψυγείου και συναγερμός θερμοκρασίας",
 "Αισθητήρας σχετικής υγρασίας για εσωτερικούς χώρους",
 "Συναγερμός υδάτων σεντίνας για σκάφος",
 "Χρυσά σκουλαρίκια με ζιργκόν",
 "Καναπές με βελούδινη ταπετσαρία",
 "Φθηνή πτήση από Αθήνα για Ρώμη",
 "Ρουστίκ ξύλινο κρεβάτι πεύκου",
 "Μακρυμάνικη μπλούζα γυναικεία"
]
# Each query has one known relevant synthetic description: ground truth for
# retrieval only, not proof of product efficacy or Greek commercial demand.
GROUND_TRUTH=[0,1,2,3,4]

def evaluate():
 start=time.monotonic()
 model=SentenceTransformer(MODEL_ID,device="cpu",trust_remote_code=False)
 queries=model.encode(["query: "+q for q in QUERY],normalize_embeddings=True,batch_size=8)
 passages=model.encode(["passage: "+d for d in DOCUMENTS],normalize_embeddings=True,batch_size=8)
 if queries.shape != (len(QUERY),384) or passages.shape != (len(DOCUMENTS),384):
  raise AssertionError("wrong_dimension_or_model")
 ranking=np.argsort(-(queries @ passages.T),axis=1)
 rr=[];top1=0;top3=0
 for i,target in enumerate(GROUND_TRUTH):
  rank=int(np.flatnonzero(ranking[i]==target)[0])+1
  rr.append(1/rank)
  top1+=int(rank<=1);top3+=int(rank<=3)
 metrics={"model":MODEL_ID,"synthetic_queries":len(QUERY),
  "hard_negatives":len(DOCUMENTS)-len(QUERY),
  "top1_recall":round(top1/len(QUERY),4),
  "recall_at_3":round(top3/len(QUERY),4),
  "mrr_at_10":round(sum(rr)/len(rr),4),
  "wall_seconds":round(time.monotonic()-start,2),
  "embedding_dim":int(queries.shape[1]),"api_token_cost":0,
  "status":"benchmark_only_not_ready_for_production"}
 print(json.dumps(metrics,ensure_ascii=False))
 assert all(np.isfinite(queries.ravel()))
 assert metrics["recall_at_3"]>=0.6, "Embedding model below minimum synthetic smoke quality"
 return metrics

if __name__=="__main__": evaluate()
