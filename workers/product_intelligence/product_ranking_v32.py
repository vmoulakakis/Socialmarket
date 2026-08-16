"""Ranking V3.2: preserve V3.1 semantics while reducing preselection and AI wall-clock latency."""
import collections
import heapq
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import product_intelligence_v1 as v1
import product_ranking_v3 as v3

RAG_PRESELECT=max(v3.PRESELECT,int(os.getenv('PRODUCT_RANK_RAG_PRESELECT','16000')))
AI_WORKERS=max(1,min(3,int(os.getenv('PRODUCT_RANK_AI_WORKERS','3'))))


def _cheap_item(product,decision_index):
    item={'product':{},'merchant':product.get('merchant_context') or {},'_raw':product,'_pains':[],'_themes':[]}
    item['_deep_demand']=v3.match_deep_demand(item,decision_index)
    item['_rank_metrics']=v3.deterministic_metrics(item)
    return item


def preselect_v32(products,context,decision_index):
    cheap_heap=[];seq=0;considered=0;deep_matched=0
    for product in products:
        considered+=1
        item=_cheap_item(product,decision_index)
        deep_matched+=int(bool(item['_deep_demand'].get('matched')))
        seq+=1;entry=(item['_rank_metrics']['deterministic_rank_score'],seq,product)
        if len(cheap_heap)<RAG_PRESELECT:heapq.heappush(cheap_heap,entry)
        elif entry[0]>cheap_heap[0][0]:heapq.heapreplace(cheap_heap,entry)

    full_heap=[];rag_evaluated=0
    for _,seq,product in sorted(cheap_heap,key=lambda x:(x[0],x[1]),reverse=True):
        item=v1.build_ai_item(product,context)
        item['_deep_demand']=v3.match_deep_demand(item,decision_index)
        item['_rank_metrics']=v3.deterministic_metrics(item)
        rag_evaluated+=1;entry=(item['_rank_metrics']['deterministic_rank_score'],seq,item)
        if len(full_heap)<v3.PRESELECT:heapq.heappush(full_heap,entry)
        elif entry[0]>full_heap[0][0]:heapq.heapreplace(full_heap,entry)

    ordered=sorted(full_heap,key=lambda x:(x[0],x[1]),reverse=True)
    selected=[];merchant_counts=collections.Counter();category_counts=collections.Counter()
    for _,_,item in ordered:
        merchant=str((item.get('merchant') or {}).get('merchant_id') or 'unknown')
        category=str((item.get('_raw') or {}).get('category_raw') or 'unknown').lower()
        if merchant_counts[merchant]>=v3.MAX_PER_MERCHANT or category_counts[category]>=v3.MAX_PER_CATEGORY:continue
        selected.append(item);merchant_counts[merchant]+=1;category_counts[category]+=1
        if len(selected)>=v3.AI_MAX:break
    if len(selected)<v3.AI_MAX:
        chosen={str(x['product']['source_record_hash']) for x in selected}
        for _,_,item in ordered:
            h=str(item['product']['source_record_hash'])
            if h in chosen:continue
            selected.append(item);chosen.add(h)
            if len(selected)>=v3.AI_MAX:break

    return selected,{'eligible_candidates_considered':considered,'cheap_preselected':len(cheap_heap),'rag_evaluated':rag_evaluated,'preselected':len(ordered),'ai_shortlist':len(selected),'ai_workers':AI_WORKERS,'deep_demand_matched_candidates':deep_matched,'deep_demand_markets':decision_index['market_count'],'deep_demand_model_markets':decision_index['model_count'],'unique_merchants':len({str((x.get('merchant') or {}).get('merchant_id')) for x in selected}),'unique_categories':len({str((x.get('_raw') or {}).get('category_raw')) for x in selected}),'preselection_policy':'all eligible -> O(1) deterministic heap -> high-recall RAG pool -> full deterministic score -> diversified AI shortlist'}


def _run_ai_batch_once(batch):
    wire=[v3.wire_item(x) for x in batch]
    ranked=v3.rank_gateway('rank',items=wire,thinking='auto').get('items',[])
    by_hash={str(x.get('source_record_hash')):x for x in ranked}
    audit_wire=[{**x,'ranking':by_hash[str(x['product']['source_record_hash'])]} for x in wire if str(x['product']['source_record_hash']) in by_hash]
    audited=v3.rank_gateway('rank_audit',items=audit_wire,thinking='auto').get('items',[]) if audit_wire else []
    audit_by={str(x.get('source_record_hash')):x for x in audited}
    return {h:{'ranking':result,'audit':audit_by.get(h,{})} for h,result in by_hash.items()}


def _run_ai_batch_resilient(batch):
    """No synthetic fallback: retry failed model work by splitting only.

    A large structured-output failure must not discard the whole batch. One failure
    gets recursively split 8->4->2; single-item failures remain failed and are counted.
    """
    try:
        return _run_ai_batch_once(batch),0,0
    except Exception:
        if len(batch)<=1:return {},len(batch),1
        mid=max(1,len(batch)//2);outputs={};failed=0;splits=1
        for part in (batch[:mid],batch[mid:]):
            result,part_failed,part_splits=_run_ai_batch_resilient(part)
            outputs.update(result);failed+=part_failed;splits+=part_splits
        return outputs,failed,splits


def rank_with_ai_v32(items):
    batches=[items[i:i+v3.AI_BATCH] for i in range(0,len(items),v3.AI_BATCH)]
    outputs={};stats=collections.Counter({'ai_rank_batches':len(batches),'ai_workers':AI_WORKERS})
    with ThreadPoolExecutor(max_workers=AI_WORKERS) as pool:
        futures={pool.submit(_run_ai_batch_resilient,batch):len(batch) for batch in batches}
        for future in as_completed(futures):
            size=futures[future]
            try:
                result,failed,splits=future.result();outputs.update(result);stats['ai_ranked']+=len(result);stats['ai_rank_failures']+=failed;stats['ai_split_retries']+=splits
            except Exception:
                stats['ai_rank_failures']+=size
    return outputs,dict(stats)


def main(feed):
    v3.ENGINE_VERSION='ranking_v3.2.1'
    v3.preselect=preselect_v32
    v3.rank_with_ai=rank_with_ai_v32
    return v3.main(feed)


if __name__=='__main__':main(sys.argv[1] if len(sys.argv)>1 else v1.SOURCE_FEED)
