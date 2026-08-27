from collections import Counter, defaultdict

from greek_source_policy import is_demand_beacon

_CURRENT_RUN_ID = None
_CURRENT_META = {}

NON_COMPETITOR_DOMAINS = {
    'forbes.com','wikipedia.org','medium.com','youtube.com','reddit.com','quora.com',
    'allaboutvision.com','aao.org','aoa.org','healthline.com','medicalnewstoday.com',
    'facebook.com','instagram.com','linkedin.com','tiktok.com','x.com','twitter.com',
    'pinterest.com','google.com','bing.com','duckduckgo.com',
}
NON_COMMERCIAL_HINTS = {
    'news','article','guide','blog','wiki','forum','reddit','health','medical','academy','association','foundation'
}
COMMERCIAL_HINTS = {
    'shop','store','buy','price','product','collection','official','brand','sunglasses','eyewear','lighting','furniture','decor'
}


def _blocked(domain: str) -> bool:
    d=(domain or '').lower().removeprefix('www.')
    return is_demand_beacon(d) or any(d==x or d.endswith('.'+x) for x in NON_COMPETITOR_DOMAINS)


def strict_candidates(core, results, products, agent_runtime, run_id):
    global _CURRENT_RUN_ID, _CURRENT_META
    _CURRENT_RUN_ID=run_id
    by_domain=defaultdict(lambda:{'frequency':0,'commercial_hits':0,'alternative_hits':0,'samples':[]})
    for row in results:
        d=str(row.get('domain') or '').lower().removeprefix('www.')
        if not d or _blocked(d) or d in core.DISCOVERY_ONLY_DOMAINS:
            continue
        text=f"{row.get('title','')} {row.get('snippet','')}".lower()
        rec=by_domain[d]
        rec['frequency']+=1
        rec['commercial_hits']+=sum(1 for h in COMMERCIAL_HINTS if h in text)
        rec['alternative_hits']+=1 if any(h in text for h in ('alternative','competitor','similar','shop','store')) else 0
        if len(rec['samples'])<3:
            rec['samples'].append({'title':str(row.get('title') or '')[:240],'snippet':str(row.get('snippet') or '')[:420]})

    candidates=[]
    for d,rec in by_domain.items():
        # Discovery gate: appearing once in a generic result is not enough.
        if rec['frequency']<2 and rec['commercial_hits']<2:
            continue
        candidates.append({'domain':d,**rec})
    candidates.sort(key=lambda x:(x['alternative_hits'],x['commercial_hits'],x['frequency']),reverse=True)
    candidates=candidates[:24]
    if not candidates:
        _CURRENT_META={}
        return []

    payload={
        'market_products':[{'name':p.get('product_name'),'brand':p.get('brand_name'),'category':p.get('category_raw')} for p in products[:12]],
        'candidate_domains':candidates,
        'task':(
            'Classify only businesses that plausibly sell a competing or substitutable product/service in the same customer decision. '
            'Reject publishers, media, medical/information sites, forums, review sites, social networks and generic directories. '
            'Return competitors:[{domain,name,competitor_type,confidence,reason}]. Confidence must be <=0.6 when evidence is weak.'
        ),
    }
    parsed,telemetry=agent_runtime.run_json(
        'Competitor Intelligence Agent',
        'Be conservative. A domain is not a competitor merely because it discusses the market. Use only supplied search metadata.',
        payload,
    )
    core.log_model_usage(run_id,telemetry,'competitor_classification_v2')
    allowed={x['domain']:x for x in candidates}
    selected=[]
    if parsed and isinstance(parsed.get('competitors'),list):
        for item in parsed['competitors']:
            d=str(item.get('domain') or '').lower().removeprefix('www.')
            if d not in allowed or _blocked(d):
                continue
            confidence=float(item.get('confidence') or 0)
            if confidence<0.65:
                continue
            rec=allowed[d]
            # Require at least one deterministic commercial/discovery signal in addition to model classification.
            if rec['commercial_hits']<1 and rec['alternative_hits']<1:
                continue
            selected.append({
                'domain':d,
                'name':str(item.get('name') or d)[:200],
                'confidence':confidence,
                'competitor_type':str(item.get('competitor_type') or 'direct')[:30],
                'reason':str(item.get('reason') or '')[:600],
                'evidence_count':rec['frequency'],
            })
    _CURRENT_META={x['domain']:x for x in selected}
    core.audit(run_id,'competitor_discovery_v2',{
        'domains_considered':len(candidates),'validated_candidates':len(selected),
        'rejected_by_gate':len(candidates)-len(selected),
    },actor='competitor-intelligence')
    return selected[:12]


def strict_get_or_create(core, original_get_or_create, candidate):
    competitor=original_get_or_create(candidate)
    if not competitor or not _CURRENT_RUN_ID:
        return competitor
    meta=_CURRENT_META.get(candidate.get('domain'),candidate)
    try:
        core.post_one('intelligence_run_competitors',{
            'run_id':_CURRENT_RUN_ID,
            'competitor_id':competitor['id'],
            'discovery_method':'search_metadata+local_agent_gate',
            'confidence':float(meta.get('confidence') or 0),
            'evidence_count':int(meta.get('evidence_count') or 0),
            'classification':'validated' if float(meta.get('confidence') or 0)>=0.65 else 'candidate',
            'rationale':{'reason':meta.get('reason'),'domain':meta.get('domain')},
        })
    except Exception:
        pass
    return competitor
