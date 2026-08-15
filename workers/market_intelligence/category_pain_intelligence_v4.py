from __future__ import annotations

import json

import category_pain_intelligence as base
from authoritative_context_v3 import authoritative_context_rows
from consumer_evidence_v4 import collect_consumer_evidence, host

MAJOR_COMMERCE_DOMAINS=(
    'skroutz.gr','bestprice.gr','public.gr','plaisio.gr','kotsovolos.gr','e-shop.gr','shopflix.gr',
    'amazon.de','amazon.com','ikea.gr','jysk.gr','intersport.gr','cosmossport.gr','notino.gr','sephora.gr',
)


def _is_major(domain:str)->bool:
    return any(domain==x or domain.endswith('.'+x) for x in MAJOR_COMMERCE_DOMAINS)


def collect_v4(job):
    p=job.get('payload') or {}
    category=str(p.get('category') or p.get('name') or '').strip()
    subcategory=(str(p.get('subcategory')).strip() if p.get('subcategory') else None)
    aliases=base.market_query_terms(category,subcategory)
    keys=base.keyword_set(category,subcategory,aliases)

    evidence=[]
    planned_demand_queries=[]
    for term in aliases[:3]:
        demand_queries=[
            f'{term} αγορά Ελλάδα',f'{term} κριτικές Ελλάδα',f'{term} τι να προσέξω',
            f'{term} καλύτερη επιλογή',f'{term} σύγκριση τιμών Ελλάδα',
        ]
        competition_queries=[f'{term} αγορά shop Ελλάδα',f'{term} τιμές eshop Ελλάδα',f'{term} καταστήματα Ελλάδα']
        planned_demand_queries.extend(demand_queries)
        for q in demand_queries:evidence.extend(base.useful_rows(q,keys,term,'demand',7))
        for q in competition_queries:evidence.extend(base.useful_rows(q,keys,term,'competition',10))

    # V4 pain evidence is extracted from real public consumer/review/forum pages.
    # Raw search-result snippets are discovery only and never eligible for pain audit.
    consumer=collect_consumer_evidence(category,subcategory,aliases,keys,max_rows=90)
    evidence.extend(consumer)
    evidence.extend(authoritative_context_rows(category,subcategory,aliases,keys))

    dedup=[];seen=set()
    for e in evidence:
        k=(e.get('source_kind'),e.get('source_url'),e.get('content_hash') or e.get('title'),e.get('body'))
        if k in seen:continue
        seen.add(k);dedup.append(e)
    evidence=dedup[:240]

    demand_rows=[e for e in evidence if e.get('source_kind')=='demand']
    pain_rows=[e for e in evidence if e.get('source_kind')=='pain_candidate']
    comp_rows=[e for e in evidence if e.get('source_kind')=='competition']
    context_rows=[e for e in evidence if e.get('source_kind') in ('official_context','industry_context')]

    demand_domains={host(e.get('source_url','')) for e in demand_rows if host(e.get('source_url',''))}
    pain_domains={host(e.get('source_url','')) for e in pain_rows if host(e.get('source_url',''))}
    pain_families={str((e.get('metadata') or {}).get('source_family') or 'public_web') for e in pain_rows}
    comp_domains=sorted({d for e in comp_rows if (d:=base.commercial_domain(e))})
    matched_queries={str((e.get('metadata') or {}).get('query') or '') for e in demand_rows if (e.get('metadata') or {}).get('query')}

    # Demand is an evidence-coverage index, never search volume. This prevents the
    # old row-count formula from saturating at 100 simply because many near-duplicate
    # SERP snippets were returned.
    query_coverage=(len(matched_queries)/len(set(planned_demand_queries))) if planned_demand_queries else 0.0
    domain_strength=min(1.0,len(demand_domains)/12.0)
    commerce_domains={d for d in comp_domains}
    for e in demand_rows:
        if d:=base.commercial_domain(e):commerce_domains.add(d)
    commercial_coverage=min(1.0,len(commerce_domains)/10.0)
    demand_score=round(100*(query_coverage*.45+domain_strength*.35+commercial_coverage*.20),2) if demand_rows else None

    major_count=sum(1 for d in comp_domains if _is_major(d))
    competition_score=min(100,round(10+len(comp_domains)*6+major_count*8,2)) if len(comp_domains)>=3 else None

    pain_domain_strength=min(1.0,len(pain_domains)/6.0)
    pain_family_strength=min(1.0,len(pain_families)/3.0)
    context_authority=max([float((e.get('metadata') or {}).get('authority_weight') or 0) for e in context_rows] or [0])
    confidence=min(.95,.28+query_coverage*.18+domain_strength*.12+pain_domain_strength*.16+pain_family_strength*.10+(.07 if competition_score is not None else 0)+context_authority*.04)

    market={
        'demand_score':demand_score,'competition_score':competition_score,'confidence':round(confidence,3),
        'query_aliases':aliases,
        'demand_evidence':[{'source_url':e['source_url'],'title':e['title'],'query':(e.get('metadata') or {}).get('query')} for e in demand_rows[:30]],
        'competition_evidence':{'domains':comp_domains,'major_domains':[d for d in comp_domains if _is_major(d)],'results':[{'source_url':e['source_url'],'title':e['title']} for e in comp_rows[:36]]},
        'pain_evidence':[{'source_url':e['source_url'],'title':e['title'],'body':e.get('body'),'source_family':(e.get('metadata') or {}).get('source_family'),'consumer_language_score':(e.get('metadata') or {}).get('consumer_language_score')} for e in pain_rows[:60]],
        'context_evidence':[{'source_kind':e['source_kind'],'source_url':e['source_url'],'title':e['title'],'source_class':(e.get('metadata') or {}).get('source_class'),'authority_weight':(e.get('metadata') or {}).get('authority_weight'),'taxonomy_direct':(e.get('metadata') or {}).get('taxonomy_direct')} for e in context_rows[:16]],
        'evidence_quality':{
            'planned_demand_queries':len(set(planned_demand_queries)),'matched_demand_queries':len(matched_queries),'query_coverage':round(query_coverage,3),
            'demand_domains':len(demand_domains),'pain_consumer_rows':len(pain_rows),'pain_domains':len(pain_domains),'pain_source_families':sorted(pain_families),
            'competition_domains':len(comp_domains),'major_commerce_domains':major_count,'context_rows':len(context_rows),
        },
        'metric_semantics':{
            'demand':'derived evidence-coverage index from relevant Greek purchase-intent query breadth + domain diversity + commercial-source coverage; not search volume, sales or market size',
            'competition':'derived proxy from distinct relevant commercial domains plus observed major-commerce presence; null when fewer than 3 commercial domains',
            'pain':'only extracted public consumer/reviewer/forum statements can enter the skeptic pain audit; SERP snippets are discovery-only',
            'context':'direct ELSTAT/Eurostat/GR.EC.A/marketplace-industry context; context_only and excluded from demand/pain score arithmetic',
        }
    }
    return {'job_id':job['id'],'entity_id':job['entity_id'],'category':category,'subcategory':subcategory,'evidence':evidence,'market':market}


base.collect=collect_v4
base.UA={'User-Agent':'Mozilla/5.0 SocialMarketSemanticPain/4.0'}


def main():
    seeded=base.gateway('seed')
    print(json.dumps({'seed':seeded},ensure_ascii=False),flush=True)
    done=0
    while done<base.LIMIT:
        jobs=(base.gateway('claim',limit=min(base.BATCH,base.LIMIT-done),worker='github-semantic-category-pain-v4').get('jobs') or [])
        if not jobs:break
        for result in base.process_batch(jobs):
            print(json.dumps(result,ensure_ascii=False),flush=True)
            done+=1
    print(json.dumps({'status':'completed','processed':done,'limit':base.LIMIT,'retrieval':'greek_consumer_evidence_v4+direct_authoritative_context_v3'},ensure_ascii=False),flush=True)


if __name__=='__main__':
    main()
