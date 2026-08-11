def semantic_group_pains(core, evidence_rows, agent_runtime, run_id, fallback_group=None):
    """Use one bounded local/free agent call to group evidence across sources.

    Final validation still uses deterministic DB thresholds; the model only
    proposes semantic grouping/labels from supplied evidence IDs.
    """
    if not evidence_rows:
        return []
    compact=[]
    for i,ev in enumerate(evidence_rows[:80]):
        compact.append({
            'index':i,
            'statement':str(ev.get('statement') or '')[:360],
            'source':ev.get('source_independence_key'),
            'severity':ev.get('severity_score'),
        })
    payload={
        'evidence':compact,
        'task':(
            'Group only semantically equivalent customer problems into specific pain clusters. '
            'Do not group merely because items are about the same product category. Prefer concrete pains such as '
            'fit/slipping, scratches, coating failure, durability, comfort, price/value, missing functionality, etc. '
            'Use each evidence index at most once. Return groups:[{label,pain_type,target_segment,indices}]. '
            'Labels must describe the problem, not repeat article headings. Maximum 12 groups.'
        )
    }
    parsed,telemetry=agent_runtime.run_json(
        'Pain Mining Agent',
        'You normalize and cluster supplied evidence. You cannot create facts and cannot change numerical scores.',
        payload,
    )
    core.log_model_usage(run_id,telemetry,'pain_semantic_grouping')
    if not parsed or not isinstance(parsed.get('groups'),list):
        if fallback_group:
            return fallback_group(evidence_rows,agent_runtime,run_id)
        return []

    used=set(); groups=[]
    for g in parsed['groups'][:12]:
        idxs=[]
        for raw in g.get('indices') or []:
            try:i=int(raw)
            except Exception:continue
            if 0<=i<len(evidence_rows) and i not in used:
                idxs.append(i); used.add(i)
        if not idxs:continue
        items=[evidence_rows[i] for i in idxs]
        label=str(g.get('label') or '').strip()[:220]
        if not label:
            label=(items[0].get('normalized_statement') or items[0].get('statement') or '')[:180]
        groups.append({
            'representative':str(items[0].get('normalized_statement') or items[0].get('statement') or '')[:700],
            'items':items,
            'label':label,
            'pain_type':str(g.get('pain_type') or 'friction')[:80],
            'target_segment':str(g.get('target_segment') or '')[:200] or None,
        })
    leftovers=[evidence_rows[i] for i in range(len(evidence_rows)) if i not in used]
    for ev in leftovers[:max(0,12-len(groups))]:
        rep=str(ev.get('normalized_statement') or ev.get('statement') or '')[:700]
        groups.append({'representative':rep,'items':[ev],'label':rep[:180],'pain_type':'friction','target_segment':None})
    groups.sort(key=lambda g:len(g['items']),reverse=True)
    return groups[:12]
