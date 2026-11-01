#!/usr/bin/env python3
"""SocialMarket neural search benchmark v3: Greek / Greeklish smoke, no production writes.

Optional local CPU execution: pip install sentence-transformers==5.1.2;
python workers/product_intelligence/neural_retrieval_eval_v3.py --run-model

The built-in labeled pairs are SYNTHETIC CONTRACT FIXTURES, not evidence that
the model works on the real SocialMarket catalog. Production launch requires a
separately reviewed, human-labeled catalog holdout and negative pairs.
"""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass

MODEL = "intfloat/multilingual-e5-small"
DIMENSIONS = 384
# Synthetic examples have independently authored query/positive/negative forms.
FIXTURES = [
 ("αισθητήρας για διαρροή νερού σε διαμέρισμα",
  "έξυπνος αισθητήρας ανίχνευσης διαρροής νερού με ειδοποίηση",
  "ανδρικό παπούτσι τρεξίματος"),
 ("γραμμές υπερβολικής κατανάλωσης ρεύματος",
  "μετρητής ηλεκτρικής ενέργειας ανά κύκλωμα",
  "χρυσό βραχιόλι με πέτρες"),
 ("pos na metrao ygrasia xwrafiou",
  "ασύρματος μετρητής υγρασίας εδάφους για αρδευτικό σύστημα",
  "ξενοδοχείο για διακοπές στην Αθήνα"),
 ("how do I detect a leaking pipe",
  "συσκευή εντοπισμού διαρροής σωληνώσεων",
  "διακόσμηση εσωτερικού χώρου"),
 ("ασφαλής παράδοση κλειδιών σε επισκέπτες",
  "έξυπνη κλειδοθήκη πρόσβασης με προσωρινό κωδικό",
  "καναπές κρεβάτι"),
]

def dot(a, b):
    if len(a) != len(b) or not a or any(not math.isfinite(float(x)) for x in a+b):
        raise ValueError("invalid_vector")
    return sum(float(x)*float(y) for x,y in zip(a,b))

def evaluate(encoder, cases=FIXTURES):
    if not cases:
        raise ValueError("human_labeled_eval_required")
    queries=["query: "+q for q,_,_ in cases]
    passages=["passage: "+p for _,p,_ in cases]+["passage: "+n for _,_,n in cases]
    vectors=encoder.encode(queries+passages,normalize_embeddings=True)
    if len(vectors)!=3*len(cases):
        raise ValueError("embedding_count_mismatch")
    rows=[]; recall1=0; margin_total=0.
    n=len(cases)
    for i,(query,positive,negative) in enumerate(cases):
        q=list(vectors[i]); p=list(vectors[n+i]); bad=list(vectors[2*n+i])
        if any(len(z)!=DIMENSIONS for z in (q,p,bad)):
            raise ValueError("wrong_model_dimension")
        good_score=dot(q,p); bad_score=dot(q,bad)
        correct=good_score>bad_score
        recall1+=int(correct);margin_total+=good_score-bad_score
        rows.append({"case":i,"query":query,"pair_margin":round(good_score-bad_score,5),
                     "correct":correct})
    return {"model":MODEL,"evaluation_type":"synthetic_smoke_only",
            "not_production_quality_proof":True,"cases":n,
            "pair_recall_at_1":round(recall1/n,3),"average_positive_margin":round(margin_total/n,4),
            "details":rows}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--run-model",action="store_true",help="Explicit CPU model inference (no DB writes)")
    args=parser.parse_args()
    if not args.run_model:
        print(json.dumps({"model":MODEL,"status":"not_run",
            "reason":"pass --run-model to download and benchmark the local CPU model",
            "evaluation_type":"synthetic_smoke_only"}))
        return 0
    from sentence_transformers import SentenceTransformer
    model=SentenceTransformer(MODEL,device="cpu",trust_remote_code=False)
    print(json.dumps(evaluate(model),ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
