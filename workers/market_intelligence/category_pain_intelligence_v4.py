from __future__ import annotations

import concurrent.futures
import json

import category_pain_intelligence as base
from authoritative_context_v3 import authoritative_context_rows
from consumer_evidence_v4 import collect_consumer_evidence, host

MAJOR_COMMERCE_DOMAINS=(
    'skroutz.gr','bestprice.gr','public.gr','plaisio.gr','kotsovolos.gr','e-shop.gr','shopflix.gr',
    'amazon.de','amazon.com','ikea.gr','jysk.gr','intersport.gr','cosmossport.gr','notino.gr','sephora.gr',
)
CHANNEL_BUDGETS={
    'pain_candidate':80,
    'demand':60,
    'competition':60,
    'official_context':8,
    'industry_context':8,
    'consumer_discovery':20,
}


def _is_major(domain:str)->bool:
    return any(domain==x or domain.endswith('.'+x) for x in MAJOR_COMMERCE_DOMAINS)


def _dedup_key(e):
    return (e.get('source_kind'),e.get('source_url'),e.get('content_hash') or e.get('title'),e.get('body'))


def _budget_channel(rows,kind,limit):
    out=[];seen=set()
    for e in rows:
        if e.get('source_kind')!=kind:continue
        k=_dedup_key(e)
        if k in seen:continue
        seen.add(k);out.append(e)
        if len(out)>=limit:break
    return out


def collect_v4(job):
    p=job.get('payload') or {}
    category=str(p.get('category') or p.get('name') or '').strip()
    subcategory=(str(p.get('subcategory')).strip() if p.get('subcategory') else None)
    aliases=base.market_query_terms(category,subcategory)
    keys=base.keyword_set(category,subcategory,aliases)

    market_raw=[]
    planned_demand_queries=[]
    for term in aliases[:3]:
        demand_queries=[
            f'{term} αγορά Ελλάδα',f'{term} κριτικές Ελλάδα',f'{term} τι να προσέξω',
            f'{term} καλύτερη επιλογή',f'{term} σύγκριση τιμών Ελλάδα',
        ]
        competition_queries=[f'{term} αγορά shop Ελλάδα',f'{term} τιμές eshop Ελλάδα',f'{term} καταστήματα Ελλάδα']
        planned_demand_queries.extend(demand_queries)
        for q in demand_queries:market_raw.extend(base.useful_rows(q,keys,term,'demand',7))
        for q in competition_queries:market_raw.extend(base.useful_rows(q,keys,term,'competition',10))

    # Consumer and context channels are collected separately so broad SERP market
    # coverage can never crowd real consumer pain evidence out of the persisted/audited bundle.
    consumer_raw=collect_consumer_evidence(category,subcategory,aliases,keys,max_rows=100)
    context_raw=authoritative_context_rows(category,subcategory,aliases,keys)

    pain_rows=_budget_channel(consumer_raw,'pain_candidate',CHANNEL_BUDGETS['pain_candidate'])
    discovery_rows=_budget_channel(consumer_raw,'consumer_discovery',CHANNEL_BUDGETS['consumer_discovery'])
    demand_rows=_budget_channel(market_raw,'demand',CHANNEL_BUDGETS['demand'])
    comp_rows=_budget_channel(market_raw,'competition',CHANNEL_BUDGETS['competition'])
    official_rows=_budget_channel(context_raw,'official_context',CHANNEL_BUDGETS['official_context'])
    industry_rows=_budget_channel(context_raw,'industry_context',CHANNEL_BUDGETS['industry_context'])
    context_rows=official_rows+industry_rows

    # Pain comes first intentionally: the gateway's bounded persistence and AI payload
    # must preserve the evidence that can create validated consumer-need clusters.
    evidence=pain_rows+demand_rows+comp_rows+context_rows+discovery_rows

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
            'channel_budget_policy':'independent_v4_budgets_consumer_pain_first',
            'channel_counts':{
                'pain_candidate_raw':sum(1 for e in consumer_raw if e.get('source_kind')=='pain_candidate'),
                'pain_candidate_retained':len(pain_rows),
                'consumer_discovery_raw':sum(1 for e in consumer_raw if e.get('source_kind')=='consumer_discovery'),
                'consumer_discovery_retained':len(discovery_rows),
                'demand_raw':sum(1 for e in market_raw if e.get('source_kind')=='demand'),
                'demand_retained':len(demand_rows),
                'competition_raw':sum(1 for e in market_raw if e.get('source_kind')=='competition'),
                'competition_retained':len(comp_rows),
                'context_raw':len(context_raw),'context_retained':len(context_rows),
            },
        },
        'metric_semantics':{
            'demand':'derived evidence-coverage index from relevant Greek purchase-intent query breadth + domain diversity + commercial-source coverage; not search volume, sales or market size',
            'competition':'derived proxy from distinct relevant commercial domains plus observed major-commerce presence; null when fewer than 3 commercial domains',
            'pain':'only extracted public consumer/reviewer/forum statements can enter the skeptic pain audit; SERP snippets are discovery-only',
            'context':'direct ELSTAT/Eurostat/GR.EC.A/marketplace-industry context; context_only and excluded from demand/pain score arithmetic',
        }
    }
    return {'job_id':job['id'],'entity_id':job['entity_id'],'category':category,'subcategory':subcategory,'evidence':evidence,'market':market}


def _fail_job(job,error,stage):
    message=f'{stage}:{type(error).__name__}:{error}'[:1000]
    try:
        base.gateway('fail',job_id=job['id'],error=message)
    except Exception:
        pass
    p=job.get('payload') or {}
    return {'ok':False,'category':p.get('category') or p.get('name'),'subcategory':p.get('subcategory'),'stage':stage,'error':message[:300]}


def process_batch_v4(jobs):
    """Isolate collection/audit/save failures so one category never strands a whole lease batch."""
    items=[];results=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(base.WORKERS,len(jobs))) as executor:
        future_to_job={executor.submit(collect_v4,job):job for job in jobs}
        for future in concurrent.futures.as_completed(future_to_job):
            job=future_to_job[future]
            try:
                items.append(future.result())
            except Exception as exc:
                results.append(_fail_job(job,exc,'collect'))
    if not items:
        return results

    try:
        audit=base.gateway('audit_batch',items=items)
    except Exception as exc:
        for item in items:
            job={'id':item['job_id'],'payload':{'category':item['category'],'subcategory':item['subcategory']}}
            results.append(_fail_job(job,exc,'audit_batch'))
        return results

    audits={str(x.get('entity_id')):x for x in (audit.get('items') or [])}
    for item in items:
        audit_item=audits.get(str(item['entity_id']),{})
        item['clusters']=audit_item.get('clusters') or []
        item['market']['ai_audit_summary']=audit_item.get('audit_summary')
        item['market']['rejected_patterns']=audit_item.get('rejected_patterns') or []
        try:
            saved=base.gateway('save',result=item).get('result') or {}
            quality=item['market'].get('evidence_quality') or {}
            results.append({
                'ok':True,'category':item['category'],'subcategory':item['subcategory'],
                'aliases':item['market']['query_aliases'],'evidence':len(item['evidence']),
                'pain_candidates':quality.get('pain_consumer_rows',0),
                'pain_domains':quality.get('pain_domains',0),
                'pain_source_families':quality.get('pain_source_families',[]),
                'channel_counts':quality.get('channel_counts',{}),
                'official_context':len([e for e in item['evidence'] if e['source_kind']=='official_context']),
                'industry_context':len([e for e in item['evidence'] if e['source_kind']=='industry_context']),
                'validated_clusters':saved.get('validated_clusters',0),
                'competition':item['market']['competition_score'],'demand':item['market']['demand_score'],
            })
        except Exception as exc:
            job={'id':item['job_id'],'payload':{'category':item['category'],'subcategory':item['subcategory']}}
            results.append(_fail_job(job,exc,'save'))
    return results


base.collect=collect_v4
base.process_batch=process_batch_v4
base.UA={'User-Agent':'Mozilla/5.0 SocialMarketSemanticPain/4.1'}


def main():
    seeded=base.gateway('seed')
    print(json.dumps({'seed':seeded},ensure_ascii=False),flush=True)
    done=0;failed=0
    while done<base.LIMIT:
        jobs=(base.gateway('claim',limit=min(base.BATCH,base.LIMIT-done),worker='github-semantic-category-pain-v4').get('jobs') or [])
        if not jobs:break
        batch_results=process_batch_v4(jobs)
        for result in batch_results:
            print(json.dumps(result,ensure_ascii=False),flush=True)
            done+=1
            if not result.get('ok'):failed+=1
    summary={'status':'completed' if failed==0 else 'completed_with_failures','processed':done,'failed':failed,'limit':base.LIMIT,'retrieval':'greek_consumer_evidence_v4+direct_authoritative_context_v3','worker_version':'4.1'}
    print(json.dumps(summary,ensure_ascii=False),flush=True)
    if failed:
        raise SystemExit(f'Category Pain V4 had {failed} failed jobs; see structured output and requeued job errors')


if __name__=='__main__':
    main()
