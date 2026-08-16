"""Production orchestration for Ranking V3.6.4.

Keeps the proven ranking/SEO/creative logic, makes run-state durable before expensive
work, and strictly recovers missing partial AI batch results instead of accepting an
incomplete promotion list.
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
from runtime_config import apply_runtime_config, load_runtime_config

ENGINE_VERSION='ranking_v3.6.4'
RUN_GATEWAY=os.getenv('PRODUCT_RUN_OBSERVABILITY_GATEWAY','https://rpfadpdnnxequgvdcfoq.supabase.co/functions/v1/product-run-observability-gateway')


def run_observability(action,**payload):
    body=json.dumps({'action':action,**payload},ensure_ascii=False).encode()
    last=None
    for attempt in (1,2):
        token=v1.oidc_token()
        req=urllib.request.Request(RUN_GATEWAY,data=body,headers={'authorization':'Bearer '+token,'content-type':'application/json'},method='POST')
        try:
            with urllib.request.urlopen(req,timeout=45) as r:return json.loads(r.read().decode())
        except urllib.error.HTTPError as exc:
            message=exc.read().decode(errors='replace');last=f'run observability {action} failed: {exc.code} {message[:1000]}'
            if exc.code==401 and attempt==1:continue
            raise RuntimeError(last)
    raise RuntimeError(last or f'run observability {action} failed')


def production_gateway(action,**payload):
    if action=='ranking_complete':
        base=v32.BASE_RANK_GATEWAY('ranking_complete',**payload)
        creative=v32.creative_gateway(
            'finalize',
            minimum_ranked=v32.FINAL_MIN_RANKED,
            minimum_creatives=v32.CREATIVE_LIMIT,
            minimum_content_packs=v32.CREATIVE_LIMIT,
            **payload,
        )
        return {'ok':True,'ranking':base,'creative':creative}
    return v32.rank_gateway_final(action,**payload)


def _profile(rows,run_key,stream_stats,shortlist_stats,ai_stats,content_stats,saved):
    bands=collections.Counter(x['rank_band'] for x in rows)
    return {
        'engine_version':ENGINE_VERSION,'run_key':run_key,
        **stream_stats,**shortlist_stats,**ai_stats,**content_stats,
        'saved_rankings':saved,'bands':dict(bands),
        'top_20':[
            {k:x.get(k) for k in ('product_name','merchant_name','rank_score','rank_band','expected_commission_eur','network_performance_score','promotion_angle','recommended_channels')}
            | {'kpis':x.get('kpi_snapshot'),'seo_title':(x.get('seo_content') or {}).get('title')}
            for x in rows[:20]
        ],
        'ranking_policy':'Every deterministic eligible product can compete. Network commercial performance is an evidence-backed conversion signal. Deep Demand is additive modeled context; missing pain/forecast never automatically excludes.',
    }


def _item_hash(item):
    return str((item.get('product') or {}).get('source_record_hash') or item.get('source_record_hash') or '')


def strict_rank_with_ai(items):
    """Recover partial DeepSeek batch output without substituting non-AI rankings.

    The gateway can return syntactically valid JSON containing fewer items than were
    requested. V3.6.3 treated that as success. V3.6.4 retries only missing hashes in
    progressively smaller batches until the production Top-100 contract is satisfied.
    """
    outputs,stats=v32.rank_with_ai_v32(items)
    stats=dict(stats)
    minimum=v32.FINAL_MIN_RANKED
    target=max(minimum,min(v3.SAVE_LIMIT,160))
    attempted=0;recovered=0;rounds=0
    missing=[x for x in items if _item_hash(x) not in outputs]
    while len(outputs)<target and missing and rounds<3:
        rounds+=1;before=len(outputs);batch_size=2 if rounds<3 else 1
        for i in range(0,len(missing),batch_size):
            if len(outputs)>=target:break
            batch=missing[i:i+batch_size];attempted+=len(batch)
            result,failed,splits=v32._run_ai_batch_resilient(batch)
            outputs.update(result)
            stats['ai_rank_failures']=int(stats.get('ai_rank_failures') or 0)+int(failed or 0)
            stats['ai_split_retries']=int(stats.get('ai_split_retries') or 0)+int(splits or 0)
        recovered+=len(outputs)-before
        missing=[x for x in items if _item_hash(x) not in outputs]
        if len(outputs)==before:break
    stats.update({
        'ai_ranked':len(outputs),
        'ai_recovery_target':target,
        'ai_recovery_rounds':rounds,
        'ai_recovery_attempted':attempted,
        'ai_recovered_missing':recovered,
        'ai_missing_after_recovery':len(missing),
        'ai_completeness_policy':'partial batch output is retried on missing hashes; no deterministic substitute',
    })
    if len(outputs)<minimum:
        raise RuntimeError(f'AI completeness contract requires at least {minimum} fully ranked products; got {len(outputs)} after {rounds} recovery rounds')
    return outputs,stats


def main(feed):
    cfg=load_runtime_config(v1);apply_runtime_config(v1,cfg)
    v3.ENGINE_VERSION=ENGINE_VERSION
    v3.preselect=v32.preselect_v32
    v3.rank_with_ai=strict_rank_with_ai
    v3.enrich_final_rows=v32.enrich_final_rows_v34
    v3.rank_gateway=production_gateway

    health=production_gateway('health')
    if not health.get('deepseek_configured'):
        raise SystemExit('Ranking V3.6.4 requires AI for the final promotion list; DeepSeek is not configured.')
    creative_health=v32.creative_gateway('health')
    if not creative_health.get('deepseek_configured'):
        raise SystemExit('Ranking V3.6.4 requires the creative AI gateway; DeepSeek is not configured.')

    run_key=f"{os.getenv('GITHUB_RUN_ID') or datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{os.getenv('GITHUB_RUN_ATTEMPT','1')}"
    run_id=os.getenv('PRODUCT_RANK_RUN_ID','').strip()
    if not run_id:
        run=production_gateway('ranking_start',run_key=run_key,engine_version=ENGINE_VERSION,metadata={
            'runtime_config_version':cfg.get('_version'),
            'orchestrator':'product_ranking_v364_production',
            'stage':'starting',
            'policy':'ranking-first; pain optional; partial AI output is retried by missing hash; no deterministic fallback',
        })
        run_id=str(run['run_id'])
    stage='context';db=None

    try:
        context=v1.gateway('context')
        decision_payload=production_gateway('decision_context')
        decision_index=v3.prepare_decision_context(decision_payload)

        stage='stage_feed';reused=False
        if v1.REUSE_STAGE and Path(v1.STAGE_DB).exists():
            try:
                db=v1.init_stage(v1.STAGE_DB,reset=False)
                staged=db.execute('select count(*) from candidates').fetchone()[0]
                reused=staged>0
            except Exception:
                reused=False
        if reused:
            stream_stats={'stage_reused_from_phase_a':True,'commission_eligible_records':staged}
        else:
            db,stream_stats=v1.stage_feed(feed,context);stream_stats=dict(stream_stats)

        stage='preselect'
        shortlist,shortlist_stats=v32.preselect_v32(v1.iter_best_offers(db,v1.AI_OFFERS_PER_PRODUCT),context,decision_index)

        stage='ai_ranking'
        ai_outputs,ai_stats=strict_rank_with_ai(shortlist)
        rows=[v3.final_row(item,ai_outputs[str(item['product']['source_record_hash'])]) for item in shortlist if str(item['product']['source_record_hash']) in ai_outputs]
        rows.sort(key=lambda x:(x['rank_score'],x['ai_confidence'],v3.num(x['expected_commission_eur'])),reverse=True)
        rows=rows[:v3.SAVE_LIMIT]

        stage='seo_creatives_assets'
        rows,content_stats=v32.enrich_final_rows_v34(rows)

        stage='canonical_persistence';saved=0
        for i in range(0,len(rows),40):
            saved+=int(production_gateway('save_rankings',run_id=run_id,items=rows[i:i+40]).get('saved') or 0)
        if saved<len(rows):
            raise RuntimeError(f'canonical product ranking persistence incomplete: {saved}/{len(rows)}')

        stage='finalize'
        production_gateway(
            'ranking_complete',run_id=run_id,
            records_seen=int(stream_stats.get('records_seen') or 0),
            eligible_candidates=int(stream_stats.get('commission_eligible_records') or 0),
            ai_ranked=int(ai_stats.get('ai_ranked') or 0),
            saved_count=saved,
            metadata={'shortlist':shortlist_stats,'ai':ai_stats,'content':content_stats,'orchestrator':'product_ranking_v364_production'},
        )

        profile=_profile(rows,run_key,stream_stats,shortlist_stats,ai_stats,content_stats,saved)
        v3.PROFILE.write_text(json.dumps(profile,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
        print(json.dumps({'product_ranking_v364':profile},ensure_ascii=False,default=str),flush=True)
        return profile
    except BaseException as exc:
        if isinstance(exc,KeyboardInterrupt):raise
        failure={'stage':stage,'error':str(exc)[:4000],'engine_version':ENGINE_VERSION,'run_key':run_key}
        try:
            run_observability('ranking_fail',run_id=run_id,stage=stage,error=str(exc),metadata=failure)
        except Exception as mark_exc:
            print(json.dumps({'warning':'ranking_failure_observability_failed','run_id':run_id,'stage':stage,'error':str(mark_exc)[:1200]}),flush=True)
        raise
    finally:
        if db is not None:
            try:db.close()
            except Exception:pass


if __name__=='__main__':main(sys.argv[1] if len(sys.argv)>1 else v1.SOURCE_FEED)
