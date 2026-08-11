from deep_validation import deepen_pain


def iterative_deepen_then_contradict(core, original_contradiction_check, run_id, pain, max_pages=2):
    """Expand evidence autonomously until the pain is validated or new evidence stalls.

    This never lowers the validation threshold. It spends more deterministic
    search/crawl + local embedding work on promising pains instead of asking a
    paid LLM to "decide" whether the market pain is real.
    """
    current = pain
    max_attempts = 3
    for _ in range(max_attempts):
        before_score = float(current.get('pain_score') or 0)
        before_count = int(current.get('evidence_count') or 0)
        before_sources = int(current.get('independent_source_count') or 0)
        current = deepen_pain(core, run_id, current, max_pages=8)
        after_score = float(current.get('pain_score') or 0)
        after_count = int(current.get('evidence_count') or 0)
        after_sources = int(current.get('independent_source_count') or 0)
        if current.get('status') in ('validated','strong_validated'):
            break
        if after_count <= before_count and after_sources <= before_sources:
            break
        if (after_score - before_score) < 0.5 and (after_count - before_count) <= 1:
            break

    fresh, contradictions = original_contradiction_check(run_id, current, max_pages=max_pages)
    try:
        core.db_call('POST','rpc/recompute_pain_metrics',data={'p_pain_id':current['id']})
        rows=core.get('pain_candidates',{'id':f"eq.{current['id']}",'select':'*','limit':'1'})
        if rows:
            fresh=rows[0]
    except Exception:
        pass
    core.audit(run_id,'iterative_pain_validation_complete',{
        'pain_id':current['id'],
        'label':current.get('label'),
        'final_score':fresh.get('pain_score'),
        'final_status':fresh.get('status'),
        'final_evidence_count':fresh.get('evidence_count'),
        'final_independent_sources':fresh.get('independent_source_count'),
        'contradictions':len(contradictions),
    },actor='evidence-validator')
    return fresh, contradictions
