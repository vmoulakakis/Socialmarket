import requests
from urllib.parse import urlparse
from urllib import robotparser

import run_pipeline as core
from research_v2 import discover_market_queries, relevant_searx
from local_agent_runtime import LocalFirstAgentRuntime
from pain_grouping_v2 import semantic_group_pains

_original_searx = core.searx
_original_log_model_usage = core.log_model_usage
core.discover_market_queries = discover_market_queries
core.searx = lambda query, limit=8: relevant_searx(_original_searx, query, limit)
core.FreeAgentRuntime = LocalFirstAgentRuntime


def fast_robots_allowed(url: str):
    d = core.domain(url)
    if not d:
        return False
    if any(d == b or d.endswith('.' + b) for b in core.BLOCKED_DOMAINS):
        return False
    try:
        p = urlparse(url)
        rr = requests.get(f"{p.scheme}://{p.netloc}/robots.txt", headers={'User-Agent': core.UA}, timeout=3, allow_redirects=True)
        if rr.status_code == 200 and rr.text:
            rp = robotparser.RobotFileParser(); rp.set_url(str(rr.url)); rp.parse(rr.text.splitlines())
            return rp.can_fetch(core.UA, url)
        if rr.status_code in (401, 403):
            return False
        return True
    except Exception:
        return True


core.robots_allowed = fast_robots_allowed


def corrected_log_model_usage(run_id, telemetry, task_type):
    if telemetry and telemetry.get('route') == 'local_llm':
        core.post_one('model_usage_events', {
            'route':'local_llm',
            'provider':telemetry.get('provider') or 'ollama',
            'model_name':telemetry.get('model'),
            'input_tokens':int(telemetry.get('input_tokens') or 0),
            'output_tokens':int(telemetry.get('output_tokens') or 0),
            'cost_usd':0,
        })
        core.audit(run_id,'free_model_call',{'task_type':task_type,**telemetry},actor='model-router')
        return
    _original_log_model_usage(run_id,telemetry,task_type)


core.log_model_usage = corrected_log_model_usage
_original_group = core.group_pains
core.group_pains = lambda evidence_rows, agent_runtime, run_id: semantic_group_pains(core, evidence_rows, agent_runtime, run_id, _original_group)

if __name__ == '__main__':
    core.main()
