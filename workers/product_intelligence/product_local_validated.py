"""VALIDATED-only local Product Ranking frontier.

This wrapper reuses the bounded local ranking tasks but counts only independent
Skeptic VALIDATED decisions toward the authoritative Top-100 contract.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Mapping

import product_local_autopilot as local
import product_ranking_v3 as v3


def rank_with_validated_local_ai(items:list[Mapping[str,Any]])->tuple[dict[str,dict[str,Any]],dict[str,Any]]:
    rank_router=local._router(local.LOCAL_RANK_OUTPUT_TOKENS)
    ranked={};rank_stats=[]
    with ThreadPoolExecutor(max_workers=local.LOCAL_AI_WORKERS) as pool:
        futures={pool.submit(local._rank_one,item,rank_router):item for item in items}
        for future in as_completed(futures):
            h,data,stats=future.result();rank_stats.append(stats)
            if data is not None:ranked[h]=(futures[future],data)
    if len(ranked)<local.LOCAL_MIN_FINAL:
        raise RuntimeError(f'local ranking completeness requires at least {local.LOCAL_MIN_FINAL} ranked candidates; got {len(ranked)}')

    priority=[]
    for h,(item,ranking) in ranked.items():
        proxy=v3.final_row(item,{'ranking':ranking,'audit':{'risk_score':0}})
        priority.append((proxy['rank_score'],h,item,ranking))
    priority.sort(reverse=True,key=lambda x:x[0])

    audit_router=local._router(local.LOCAL_AUDIT_OUTPUT_TOKENS)
    outputs={};audited=0;rejected=0;needs_review=0;audit_stats=[]
    for start in range(0,len(priority),local.LOCAL_AI_WORKERS):
        if len(outputs)>=local.LOCAL_MIN_FINAL:break
        chunk=priority[start:start+local.LOCAL_AI_WORKERS]
        with ThreadPoolExecutor(max_workers=local.LOCAL_AI_WORKERS) as pool:
            futures={pool.submit(local._audit_one,item,ranking,audit_router):(h,item,ranking) for _,h,item,ranking in chunk}
            for future in as_completed(futures):
                h,item,ranking=futures[future];_,audit,stats=future.result();audited+=1;audit_stats.append(stats)
                if audit is None:continue
                verdict=str(audit.get('verdict') or '').upper()
                if verdict=='REJECTED':rejected+=1;continue
                if verdict=='NEEDS_REVIEW':needs_review+=1;continue
                if verdict!='VALIDATED':continue
                outputs[h]={'ranking':ranking,'audit':audit}

    if len(outputs)<local.LOCAL_MIN_FINAL:
        raise RuntimeError(f'VALIDATED-only local skeptic contract requires {local.LOCAL_MIN_FINAL}; got {len(outputs)} after auditing {audited} of {len(priority)} candidates')

    all_stats=rank_stats+audit_stats
    calls=sum(1 for x in all_stats if not x.get('from_cache') and x.get('status')=='ok')
    cache_hits=sum(1 for x in all_stats if x.get('from_cache'))
    cost=sum(float(x.get('cost_usd') or 0) for x in all_stats)
    return outputs,{
        'ai_ranked':len(outputs),'local_validated':len(outputs),'local_rank_candidates':len(ranked),'local_audited':audited,
        'local_rejected':rejected,'local_needs_review':needs_review,'local_model':local.LOCAL_MODEL,'local_ai_workers':local.LOCAL_AI_WORKERS,
        'local_model_calls':calls,'local_cache_hits':cache_hits,'paid_inference_cost_usd':round(cost,6),
        'ai_route':'provider_neutral_local_router','bulk_feed_to_llm':False,
        'audit_policy':'only independent-skeptic VALIDATED products count toward Top100; NEEDS_REVIEW is held; audit continues until 100 validated or frontier exhausted',
    }
