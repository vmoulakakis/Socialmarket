"""Lightweight GraphRAG context for Demand Intelligence V3.1.

The graph is built from already-audited SocialMarket relations. It is a retrieval and
explanation structure only: node degree, centrality and edge counts are NEVER demand.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from urllib.parse import urlparse
from typing import Any


def _id(prefix:str,value:Any,fallback:int)->str:
    return f"{prefix}:{value if value not in (None,'') else fallback}"


def build(context:dict[str,Any],max_evidence:int=50,max_supply:int=40,max_pains:int=30)->dict[str,Any]:
    market=context.get('market') or {}
    taxonomy=str(context.get('taxonomy_id') or market.get('taxonomy_id') or '')
    root=_id('taxonomy',taxonomy,0)
    nodes={root:{'id':root,'type':'taxonomy','label':market.get('subcategory_name') or market.get('category_name') or market.get('taxonomy_name') or taxonomy}}
    edges=[]
    source_domains=Counter(); relations=Counter(); evidence_by_domain=defaultdict(list)

    for i,e in enumerate((context.get('retrieved_evidence') or [])[:max_evidence]):
        eid=_id('evidence',e.get('id'),i)
        domain=e.get('source_domain') or (urlparse(str(e.get('source_url') or '')).hostname or 'unknown')
        nodes[eid]={'id':eid,'type':'evidence','label':e.get('title') or domain,'domain':domain,'confidence':e.get('confidence'),'validation_status':e.get('validation_status')}
        edges.append({'source':root,'target':eid,'relation':'SUPPORTED_BY','weight':(e.get('retrieval') or {}).get('score')})
        source_domains[domain]+=1; relations['SUPPORTED_BY']+=1; evidence_by_domain[domain].append(eid)

    for i,p in enumerate((context.get('validated_pains') or [])[:max_pains]):
        pid=_id('pain',p.get('id'),i)
        nodes[pid]={'id':pid,'type':'pain','label':p.get('canonical_text') or p.get('representative_pain') or p.get('cluster_label') or 'validated pain','confidence':p.get('confidence'),'severity':p.get('pain_severity')}
        edges.append({'source':root,'target':pid,'relation':'HAS_VALIDATED_PAIN'}); relations['HAS_VALIDATED_PAIN']+=1

    merchant_seen=set()
    for i,m in enumerate((context.get('supply_context') or [])[:max_supply]):
        mid=_id('merchant',m.get('merchant_id'),i)
        if mid not in nodes:
            nodes[mid]={'id':mid,'type':'merchant','label':m.get('canonical_name') or 'merchant','trust':m.get('trust_score'),'commercial':m.get('commercial_score'),'risk':m.get('risk_flag')}
        edges.append({'source':root,'target':mid,'relation':'HAS_SUPPLY','weight':m.get('research_confidence')}); relations['HAS_SUPPLY']+=1
        merchant_seen.add(mid)
        if m.get('program_id'):
            prid=_id('program',m.get('program_id'),i)
            nodes[prid]={'id':prid,'type':'program','label':m.get('program_name') or 'program','commercial':m.get('commercial_score')}
            edges.append({'source':mid,'target':prid,'relation':'OFFERS_PROGRAM'}); relations['OFFERS_PROGRAM']+=1

    contradictions=[]
    for i,e in enumerate((context.get('retrieved_evidence') or [])[:max_evidence]):
        md=e.get('metadata') or {}
        if md.get('contradiction') is True or md.get('stance')=='contradicting':
            contradictions.append(str(e.get('id') or i))

    domain_concentration=0.0
    total=sum(source_domains.values())
    if total:
        domain_concentration=sum((c/total)**2 for c in source_domains.values())

    return {
        'status':'DERIVED',
        'pattern':'lightweight_graph_rag_v31',
        'nodes':list(nodes.values()),
        'edges':edges,
        'summary':{
            'node_count':len(nodes),'edge_count':len(edges),'merchant_nodes':len(merchant_seen),
            'independent_domains':len(source_domains),'domain_hhi':round(domain_concentration,4),
            'relations':dict(relations),'explicit_contradictions':len(contradictions),
        },
        'source_domains':dict(source_domains.most_common()),
        'contradiction_evidence_ids':contradictions,
        'semantics':'Graph structure supports retrieval, lineage and explanation. Graph density/centrality is never interpreted as demand.',
    }
