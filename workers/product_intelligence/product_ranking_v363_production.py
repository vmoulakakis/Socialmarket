"""Authoritative zero-paid Product Ranking orchestration.

The multi-million-record Linkwise universe is streamed and filtered deterministically.
Only the bounded diversified frontier reaches the provider-neutral local AI router.
Normal production has no paid LLM dependency and fails closed with SAFE_HOLD/errors.
"""
import collections
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import product_intelligence_v1 as v1
import product_ranking_v3 as v3
import product_ranking_v32 as v32
import product_local_autopilot as local_ai
from runtime_config import apply_runtime_config, load_runtime_config

ENGINE_VERSION='ranking_v4.0_local_autopilot'
RUN_GATEWAY=os.getenv('PRODUCT_RUN_OBSERVABILITY_GATEWAY','https://rpfadpdnnxequgvdcfoq.supabase.co/functions/v1/product-run-observability-gateway')


def run_observability(action,**payload):
    body=json.dumps({'action':action,**payload},ensure_ascii=False).encode();last=None
    for attempt in (1,2):
        token=v1.oidc_token();req=urllib.request.Request(RUN_GATEWAY,data=body,headers={'authorization':'Bearer '+token,'content-type':'application/json'},method='POST')
        try:
            with urllib.request.urlopen(req,timeout=45) as r:return json.loads(r.read().decode())
        except urllib.error.HTTPError as exc:
            message=exc.read().decode(errors='replace');last=f'run observability {action} failed: {exc.code} {message[:1000]}'
            if exc.code==401 and attempt==1:continue
            raise RuntimeError(last)
    raise RuntimeError(last or f'run observability {action} failed')


def production_gateway(action,**payload):
    """Persistence/finalization boundary only; no model inference is performed here."""
    if action=='ranking_complete':
        base=v32.BASE_RANK_GATEWAY('ranking_complete',**payload)
        creative=v32.creative_gateway('finalize',minimum_ranked=v32.FINAL_MIN_RANKED,minimum_creatives=v32.CREATIVE_LIMIT,minimum_content_packs=v32.CREATIVE_LIMIT,**payload)
        return {'ok':True,'ranking':base,'creative':creative}
    return v32.rank_gateway_final(action,**payload)


def _profile(rows,run_key,stream_stats,shortlist_stats,ai_stats,content_stats,saved):
    bands=collections.Counter(x['rank_band'] for x in rows)
    return {
        'engine_version':ENGINE_VERSION,'run_key':run_key,**stream_stats,**shortlist_stats,**ai_stats,**content_stats,
        'saved_rankings':saved,'bands':dict(bands),'owner_min_expected_commission_eur':float(v1.MIN_COMMISSION),
        'paid_llm_required':False,'bulk_feed_to_llm':False,
        'top_20':[
            {k:x.get(k) for k in ('product_name','merchant_name','rank_score','rank_band','expected_commission_eur','network_performance_score','promotion_angle','recommended_channels')}
            | {'kpis':x.get('kpi_snapshot'),'seo_title':(x.get('seo_content') or {}).get('title')}
            for x in rows[:20]
        ],
        'ranking_policy':'All eligible products compete deterministically; only a bounded frontier reaches local open-weight AI. Missing pain/forecast gives no bonus but is not fabricated. Only independent-skeptic VALIDATED products may enter the final Top 100.',
    }


def _assert_local_health():
    ranking=production_gateway('health')
    if not ranking.get('ok'):raise RuntimeError('ranking persistence gateway unhealthy')
    creative=v32.creative_gateway('health')
    if not creative.get('ok'):raise RuntimeError('creative persistence gateway unhealthy')
    executor=local_ai.OllamaExecutor(name='preflight',tier=2,model=local_ai.LOCAL_MODEL,timeout_seconds=20,max_output_tokens=32)
    probe=local_ai.AITask(task_type='local_model_health',role='Health probe',instructions='Return strict JSON.',payload={'health':True},required_keys=(),max_tier=2,cacheable=False)
    if not executor.available(probe):raise RuntimeError(f'qualified local model unavailable: {local_ai.LOCAL_MODEL}')
    return {'ranking_gateway':True,'creative_gateway':True,'local_model':local_ai.LOCAL_MODEL,'paid_provider_required':False}


def main(feed):
    cfg=load_runtime_config(v1);apply_runtime_config(v1,cfg)
    v3.ENGINE_VERSION=ENGINE_VERSION
    v3.preselect=v32.preselect_v32
    v3.rank_with_ai=local_ai.rank_with_local_ai
    v3.enrich_final_rows=local_ai.enrich_final_rows_local
    v3.rank_gateway=production_gateway

    if float(v1.MIN_COMMISSION)<15.0:raise SystemExit(f'First authoritative Autopilot run requires owner commission floor >= €15; got €{v1.MIN_COMMISSION:.2f}')
    health=_assert_local_health()
    run_key=f"{os.getenv('GITHUB_RUN_ID') or datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{os.getenv('GITHUB_RUN_ATTEMPT','1')}"
    run_id=os.getenv('PRODUCT_RANK_RUN_ID','').strip()
    if not run_id:
        run=production_gateway('ranking_start',run_key=run_key,engine_version=ENGINE_VERSION,metadata={
            'runtime_config_version':cfg.get('_version'),'orchestrator':'product_ranking_v4_local_autopilot','stage':'starting','model_route':'provider_neutral_local_router',
            'local_model':local_ai.LOCAL_MODEL,'paid_llm_required':False,'bulk_feed_to_llm':False,'owner_min_expected_commission_eur':float(v1.MIN_COMMISSION),
            'policy':'deterministic bulk filters -> bounded RAG frontier -> local rank -> independent local skeptic -> VALIDATED only -> deterministic SEO -> local Top20 creative + skeptic',
        });run_id=str(run['run_id'])
    stage='context';db=None

    try:
        context=v1.gateway('context');decision_payload=production_gateway('decision_context');decision_index=v3.prepare_decision_context(decision_payload)
        stage='stage_feed';reused=False
        if v1.REUSE_STAGE and Path(v1.STAGE_DB).exists():
            try:db=v1.init_stage(v1.STAGE_DB,reset=False);staged=db.execute('select count(*) from candidates').fetchone()[0];reused=staged>0
            except Exception:reused=False
        if reused:stream_stats={'stage_reused_from_phase_a':True,'commission_eligible_records':staged}
        else:db,stream_stats=v1.stage_feed(feed,context);stream_stats=dict(stream_stats)

        stage='preselect';shortlist,shortlist_stats=v32.preselect_v32(v1.iter_best_offers(db,v1.AI_OFFERS_PER_PRODUCT),context,decision_index)
        if len(shortlist)<v32.FINAL_MIN_RANKED:raise RuntimeError(f'bounded frontier too small for Top100 contract: {len(shortlist)}')

        stage='local_ai_ranking';ai_outputs,ai_stats=local_ai.rank_with_local_ai(shortlist)
        held=sum(1 for x in ai_outputs.values() if str((x.get('audit') or {}).get('verdict') or '').upper()!='VALIDATED')
        ai_outputs={h:x for h,x in ai_outputs.items() if str((x.get('audit') or {}).get('verdict') or '').upper()=='VALIDATED'}
        ai_stats=dict(ai_stats);ai_stats['local_validated']=len(ai_outputs);ai_stats['local_nonvalidated_held']=held
        if len(ai_outputs)<v32.FINAL_MIN_RANKED:raise RuntimeError(f'VALIDATED-only Top100 contract requires {v32.FINAL_MIN_RANKED}; got {len(ai_outputs)}')
        rows=[v3.final_row(item,ai_outputs[str(item['product']['source_record_hash'])]) for item in shortlist if str(item['product']['source_record_hash']) in ai_outputs]
        rows.sort(key=lambda x:(x['rank_score'],x['ai_confidence'],v3.num(x['expected_commission_eur'])),reverse=True);rows=rows[:v3.SAVE_LIMIT]
        v32.assert_final_contract(rows)
        if any(v3.num(x.get('expected_commission_eur'))+1e-9<float(v1.MIN_COMMISSION) for x in rows):raise RuntimeError('owner commission hard gate violation detected after local ranking')

        stage='deterministic_seo_local_top20_creatives';rows,content_stats=local_ai.enrich_final_rows_local(rows)
        stage='canonical_persistence';saved=0
        for i in range(0,len(rows),40):saved+=int(production_gateway('save_rankings',run_id=run_id,items=rows[i:i+40]).get('saved') or 0)
        if saved<len(rows):raise RuntimeError(f'canonical product ranking persistence incomplete: {saved}/{len(rows)}')

        stage='finalize';production_gateway('ranking_complete',run_id=run_id,records_seen=int(stream_stats.get('records_seen') or 0),eligible_candidates=int(stream_stats.get('commission_eligible_records') or 0),ai_ranked=int(ai_stats.get('local_validated') or 0),saved_count=saved,metadata={
            'shortlist':shortlist_stats,'ai':ai_stats,'content':content_stats,'health':health,'orchestrator':'product_ranking_v4_local_autopilot','paid_llm_required':False,'bulk_feed_to_llm':False,
        })
        profile=_profile(rows,run_key,stream_stats,shortlist_stats,ai_stats,content_stats,saved);v3.PROFILE.write_text(json.dumps(profile,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
        print(json.dumps({'product_ranking_v4_local_autopilot':profile},ensure_ascii=False,default=str),flush=True);return profile
    except BaseException as exc:
        if isinstance(exc,KeyboardInterrupt):raise
        failure={'stage':stage,'error':str(exc)[:4000],'engine_version':ENGINE_VERSION,'run_key':run_key,'local_model':local_ai.LOCAL_MODEL,'paid_llm_required':False}
        try:run_observability('ranking_fail',run_id=run_id,stage=stage,error=str(exc),metadata=failure)
        except Exception as mark_exc:print(json.dumps({'warning':'ranking_failure_observability_failed','run_id':run_id,'stage':stage,'error':str(mark_exc)[:1200]}),flush=True)
        raise
    finally:
        if db is not None:
            try:db.close()
            except Exception:pass


if __name__=='__main__':main(sys.argv[1] if len(sys.argv)>1 else v1.SOURCE_FEED)
