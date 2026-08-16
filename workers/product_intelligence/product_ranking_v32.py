"""Ranking V3.2: preserve V3.1 scoring semantics but compute expensive RAG only after a high-recall cheap shortlist."""
import collections
import heapq
import os
import sys

import product_intelligence_v1 as v1
import product_ranking_v3 as v3

RAG_PRESELECT=max(v3.PRESELECT,int(os.getenv('PRODUCT_RANK_RAG_PRESELECT','16000')))


def _cheap_item(product,decision_index):
    item={
        'product':{},
        'merchant':product.get('merchant_context') or {},
        '_raw':product,
        '_pains':[],
        '_themes':[],
    }
    item['_deep_demand']=v3.match_deep_demand(item,decision_index)
    item['_rank_metrics']=v3.deterministic_metrics(item)
    return item


def preselect_v32(products,context,decision_index):
    # Stage 1: scan every deterministic eligible best offer with only O(1) signals.
    # No pain/theme RAG is computed here. Keep a deliberately large high-recall pool.
    cheap_heap=[];seq=0;considered=0;deep_matched=0
    for product in products:
        considered+=1
        item=_cheap_item(product,decision_index)
        deep_matched+=int(bool(item['_deep_demand'].get('matched')))
        seq+=1
        entry=(item['_rank_metrics']['deterministic_rank_score'],seq,product)
        if len(cheap_heap)<RAG_PRESELECT:
            heapq.heappush(cheap_heap,entry)
        elif entry[0]>cheap_heap[0][0]:
            heapq.heapreplace(cheap_heap,entry)

    # Stage 2: only the strongest high-recall pool receives semantic pain/theme RAG.
    full_heap=[];rag_evaluated=0
    for _,seq,product in sorted(cheap_heap,key=lambda x:(x[0],x[1]),reverse=True):
        item=v1.build_ai_item(product,context)
        item['_deep_demand']=v3.match_deep_demand(item,decision_index)
        item['_rank_metrics']=v3.deterministic_metrics(item)
        rag_evaluated+=1
        entry=(item['_rank_metrics']['deterministic_rank_score'],seq,item)
        if len(full_heap)<v3.PRESELECT:
            heapq.heappush(full_heap,entry)
        elif entry[0]>full_heap[0][0]:
            heapq.heapreplace(full_heap,entry)

    ordered=sorted(full_heap,key=lambda x:(x[0],x[1]),reverse=True)
    selected=[];merchant_counts=collections.Counter();category_counts=collections.Counter()
    for _,_,item in ordered:
        merchant=str((item.get('merchant') or {}).get('merchant_id') or 'unknown')
        category=str((item.get('_raw') or {}).get('category_raw') or 'unknown').lower()
        if merchant_counts[merchant]>=v3.MAX_PER_MERCHANT or category_counts[category]>=v3.MAX_PER_CATEGORY:
            continue
        selected.append(item);merchant_counts[merchant]+=1;category_counts[category]+=1
        if len(selected)>=v3.AI_MAX:break

    if len(selected)<v3.AI_MAX:
        chosen={str(x['product']['source_record_hash']) for x in selected}
        for _,_,item in ordered:
            h=str(item['product']['source_record_hash'])
            if h in chosen:continue
            selected.append(item);chosen.add(h)
            if len(selected)>=v3.AI_MAX:break

    return selected,{
        'eligible_candidates_considered':considered,
        'cheap_preselected':len(cheap_heap),
        'rag_evaluated':rag_evaluated,
        'preselected':len(ordered),
        'ai_shortlist':len(selected),
        'deep_demand_matched_candidates':deep_matched,
        'deep_demand_markets':decision_index['market_count'],
        'deep_demand_model_markets':decision_index['model_count'],
        'unique_merchants':len({str((x.get('merchant') or {}).get('merchant_id')) for x in selected}),
        'unique_categories':len({str((x.get('_raw') or {}).get('category_raw')) for x in selected}),
        'preselection_policy':'all eligible -> O(1) deterministic heap -> high-recall RAG pool -> full deterministic score -> diversified AI shortlist',
    }


def main(feed):
    v3.ENGINE_VERSION='ranking_v3.2'
    v3.preselect=preselect_v32
    return v3.main(feed)


if __name__=='__main__':
    main(sys.argv[1] if len(sys.argv)>1 else v1.SOURCE_FEED)
