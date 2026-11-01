#!/usr/bin/env python3
"""SocialMarket 3.0 evidence-first lexical/char-neural candidate retrieval baseline.

A low-cost reproducible baseline; not a trained neural recommender. Its purpose is
to reject obvious false matches before multilingual embeddings / neural reranking
are benchmarked. Outputs are always NEEDS_EVIDENCE and never affiliate offers.

No external network, no API tokens. Database access is opt-in. Importing the full
Linkwise feed is deliberately outside this worker's responsibility.
"""
from __future__ import annotations
import argparse, html, json, os, re, sys, unicodedata
from dataclasses import dataclass
from typing import Iterable

STOP = set("""και από στον στην στο στις τους τους για της του των μια ένα εναν ειναι
πως ποιο ποια ποιος που πως χωρίς χωρις μετα πριν πιο την στο την απο την για
με σε ο η το τα οι τον την του τους αυτές αυτα αυτά μια ενα ενας καλη καλυτερη
καλύτερο καλυτερη καλυτερα τιμή τιμη τιμες προσφορά προσφορα φθηνά φθηνα
δωρεαν εως έξτρα νεα νέο νεο online best buy sale αποθήκη τοπ top xxl
value μερικά λιγότερα καλυτερο καλυτερες χαμηλή χαμηλο χαμηλα
""".split())
TOKEN = re.compile(r"[a-zα-ω0-9]{3,}", re.I)


def normalize(value: str) -> str:
    plain = html.unescape(str(value or "")).casefold()
    plain = unicodedata.normalize("NFD", plain)
    plain = "".join(c for c in plain if unicodedata.category(c)!="Mn")
    return unicodedata.normalize("NFKC",plain)

def keywords(value: str) -> set[str]:
    return {t[:6] for t in TOKEN.findall(normalize(value)) if t not in STOP and len(t)>3}

@dataclass(frozen=True)
class Match:
    problem_id: str
    product_id: str
    title: str
    score: float
    shared_concepts: tuple[str,...]
    status: str = "needs_evidence"


def candidate_gate(problem: dict, product: dict) -> Match | None:
    p=keywords(" ".join([str(problem.get("title") or ""),str(problem.get("description") or "")]))
    # Title only: long marketing descriptions tend to generate accidental overlaps.
    d=keywords(str(product.get("title") or ""))
    shared=tuple(sorted(p & d))
    # One generic match is not evidence of a solution.
    if len(shared)<2 or not p or not d:
        return None
    jaccard=len(shared)/len(p|d)
    balance=2*len(shared)/(len(p)+len(d))
    score=round(.55*balance+.45*jaccard,4)
    if score<.26:
        return None
    return Match(problem_id=str(problem["id"]),product_id=str(product["id"]),
        title=str(product.get("title") or ""),score=score,shared_concepts=shared)


def shortlist(problems: list[dict], products: list[dict], top_k=8) -> list[Match]:
    if not 1<=top_k<=30:
        raise ValueError("invalid_top_k")
    result=[]
    for p in problems:
        matched=[x for product in products if (x:=candidate_gate(p,product)) is not None]
        matched.sort(key=lambda m:(-m.score,m.product_id))
        result.extend(matched[:top_k])
    return result


def run_fixture(path: str, top_k: int) -> dict:
    with open(path,encoding="utf-8") as stream:
        obj=json.load(stream)
    matches=shortlist(obj["problems"],obj["products"],top_k)
    return {"problems":len(obj["problems"]),"products":len(obj["products"]),
        "candidate_pairs":len(matches),"review_status":"needs_evidence",
        "matches":[m.__dict__ for m in matches]}


def run_db(top_k: int, max_products: int, write: bool) -> dict:
    url=os.getenv("SOCIALMARKET_DB_URL")
    if not url: raise RuntimeError("SOCIALMARKET_DB_URL server_secret_required")
    import psycopg
    with psycopg.connect(url,sslmode="require",connect_timeout=10) as conn:
        with conn.cursor() as cur:
            cur.execute("""select id::text,problem_title,problem_description
                from public.market_problem_clusters where market_code='GR'""")
            ps=[dict(id=r[0],title=r[1],description=r[2]) for r in cur.fetchall()]
            cur.execute("""select id::text,product_title from sm_intel.raw_products
                where product_title is not null order by id limit %s""",(max_products,))
            ds=[dict(id=r[0],title=r[1]) for r in cur.fetchall()]
        found=shortlist(ps,ds,top_k)
        if write:
            # Candidate insert ONLY; links do not imply current market demand,
            # product quality, source eligibility, stock, commission or sale readiness.
            with conn.cursor() as cur:
                for match in found:
                    cur.execute("""insert into sm_intel.product_problem_hypotheses_v3
                      (problem_cluster_id,raw_product_id,model_version,retrieval_method,
                       relevance_score,status,reasoning)
                     values (%s,%s,'lexical_baseline_v3','lexical',%s,'needs_evidence',%s::jsonb)
                     on conflict(problem_cluster_id,raw_product_id,model_version) do nothing""",
                     (match.problem_id,match.product_id,match.score,
                      json.dumps({"shared_stems":match.shared_concepts,
                        "not_market_demand":True,"not_verified_product_fit":True})))
            conn.commit()
        return {"products":len(ds),"problems":len(ps),"candidate_pairs":len(found),
                "written_candidates":len(found) if write else 0,
                "commercial_approval":False,"verified_market_demand":False}

def main():
    p=argparse.ArgumentParser()
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument("--fixture")
    g.add_argument("--db",action="store_true")
    p.add_argument("--top-k",type=int,default=8)
    p.add_argument("--max-products",type=int,default=10000)
    p.add_argument("--commit-candidates",action="store_true")
    a=p.parse_args()
    if a.commit_candidates and not a.db:
        p.error("fixture_writes_are_not_supported")
    if not 1<=a.max_products<=20000: p.error("max_products_must_be_bounded")
    out=run_fixture(a.fixture,a.top_k) if a.fixture else run_db(a.top_k,a.max_products,a.commit_candidates)
    print(json.dumps(out,ensure_ascii=False))
    return 0

if __name__=="__main__":
    sys.exit(main())
