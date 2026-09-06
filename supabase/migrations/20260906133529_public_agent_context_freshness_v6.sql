-- Add explicit source freshness to the public SocialScheduler agent context.
-- Applied to production as migration 20260906133529.

alter table public.socialscheduler_public_agent_context
  add column if not exists orchestration_decisions_total integer not null default 0,
  add column if not exists source_freshness jsonb not null default '{}'::jsonb,
  add column if not exists stale_sources text[] not null default '{}'::text[],
  add column if not exists is_stale boolean not null default true,
  add column if not exists freshness_policy text not null default 'agent-context-freshness-v6';

create or replace function public.socialscheduler_refresh_public_snapshots_v5()
returns jsonb
language plpgsql
security definer
set search_path = ''
as $function$
declare
  v_assets int:=0;
  v_ready int:=0;
  v_feedback int:=0;
  v_measured int:=0;
  v_decisions int:=0;
  v_decisions_total int:=0;
  v_rankings int:=0;
  v_weights jsonb;
  v_pipeline jsonb;
  v_provider_feedback jsonb;
  v_decisions_latest timestamptz;
  v_runtime_latest timestamptz;
  v_feedback_latest timestamptz;
  v_ranking_latest timestamptz;
  v_outbox_latest timestamptz;
  v_freshness jsonb;
  v_stale_sources text[] := '{}'::text[];
  v_is_stale boolean := false;
begin
  delete from public.socialscheduler_public_asset_feed;
  insert into public.socialscheduler_public_asset_feed(content_item_id,brand_name,brand_slug,title,core_copy,cta,tracking_url,hashtags,created_at,opportunity_score,expected_media_url,snapshot_at)
  select ci.id,
         coalesce(bs.name,'Aurevia AI'),
         coalesce(bs.slug,'socialscheduler'),
         ci.title,
         ci.core_copy,
         ci.cta,
         ci.tracking_url,
         coalesce(ci.metadata->'hashtags','[]'::jsonb),
         ci.created_at,
         public.socialscheduler_opportunity_score_v5(ci.id,'facebook',now()+interval '12 hours',70::smallint),
         'https://raw.githubusercontent.com/vmoulakakis/socialscheduler/main/assets/generated/'||ci.id::text||'.png',
         now()
  from content.items ci
  left join content.brand_sites bs on bs.id=ci.brand_site_id
  where ci.status in('approved','queued')
    and ci.media_url is null
    and ci.tracking_url like 'http%'
    and coalesce(trim(ci.title),'')<>''
  order by 10 desc,ci.created_at desc;
  get diagnostics v_assets=row_count;

  select count(*)::int into v_ready from content.items where status in('approved','queued');
  select count(*)::int,count(*) filter(where weighted_score>0)::int,max(updated_at)
    into v_feedback,v_measured,v_feedback_latest
    from public.socialscheduler_post_feedback;

  select count(*)::int,max(updated_at)
    into v_decisions_total,v_decisions_latest
    from public.socialscheduler_orchestration_decisions;
  select count(*)::int into v_decisions
    from public.socialscheduler_orchestration_decisions
    where updated_at >= now()-interval '24 hours'
      and status in ('queued','leased','running','scheduled','selected');

  select count(*)::int into v_rankings from intel.product_rankings;
  select max(coalesce(completed_at,started_at,created_at)) into v_ranking_latest
    from intel.product_ranking_runs where status in ('completed','success','succeeded');
  select max(observed_at) into v_runtime_latest from public.socialscheduler_runtime_snapshots;
  select max(updated_at) into v_outbox_latest from publish.outbox;

  select to_jsonb(w) into v_weights from public.socialscheduler_opportunity_weights w where id=1;
  select jsonb_object_agg(platform,pipeline_jobs) into v_pipeline from (
    select p.platform,
      (select count(*) from publish.outbox o where o.platform=p.platform and o.status in('approved','leased','scheduled') and o.scheduled_for>=now()-interval '10 minutes' and o.scheduled_for<=now()+interval '7 days')+
      (select count(*) from publish.delivery_history h where h.platform=p.platform and h.delivery_status='scheduled' and h.scheduled_for>=now()-interval '10 minutes' and h.scheduled_for<=now()+interval '7 days') pipeline_jobs
    from (values('facebook'::text),('instagram'),('tiktok'),('linkedin')) p(platform)
  ) x;
  select coalesce(jsonb_agg(x order by avg_score desc),'[]'::jsonb) into v_provider_feedback from (
    select platform,provider_key,count(*) posts,round(avg(weighted_score),3) avg_score,sum(clicks) clicks,sum(shares) shares,sum(saves) saves
    from public.socialscheduler_post_feedback where scheduled_for>=now()-interval '30 days'
    group by platform,provider_key
  ) x;

  if v_runtime_latest is null or v_runtime_latest < now()-interval '15 minutes' then
    v_stale_sources := array_append(v_stale_sources,'provider_runtime_snapshots');
  end if;
  if v_decisions_latest is null or v_decisions_latest < now()-interval '24 hours' then
    v_stale_sources := array_append(v_stale_sources,'orchestration_decisions');
  end if;
  if v_feedback_latest is null or v_feedback_latest < now()-interval '6 hours' then
    v_stale_sources := array_append(v_stale_sources,'provider_feedback');
  end if;
  if v_ranking_latest is null or v_ranking_latest < now()-interval '36 hours' then
    v_stale_sources := array_append(v_stale_sources,'product_rankings');
  end if;
  if v_outbox_latest is null or v_outbox_latest < now()-interval '2 hours' then
    v_stale_sources := array_append(v_stale_sources,'publishing_outbox');
  end if;
  v_is_stale := cardinality(v_stale_sources) > 0;

  v_freshness := jsonb_build_object(
    'policy','agent-context-freshness-v6',
    'checked_at',now(),
    'provider_runtime_snapshots',jsonb_build_object('latest_at',v_runtime_latest,'max_age_seconds',900,'stale',v_runtime_latest is null or v_runtime_latest < now()-interval '15 minutes'),
    'orchestration_decisions',jsonb_build_object('latest_at',v_decisions_latest,'max_age_seconds',86400,'stale',v_decisions_latest is null or v_decisions_latest < now()-interval '24 hours','fresh_active_count',v_decisions,'total_count',v_decisions_total),
    'provider_feedback',jsonb_build_object('latest_at',v_feedback_latest,'max_age_seconds',21600,'stale',v_feedback_latest is null or v_feedback_latest < now()-interval '6 hours'),
    'product_rankings',jsonb_build_object('latest_at',v_ranking_latest,'max_age_seconds',129600,'stale',v_ranking_latest is null or v_ranking_latest < now()-interval '36 hours'),
    'publishing_outbox',jsonb_build_object('latest_at',v_outbox_latest,'max_age_seconds',7200,'stale',v_outbox_latest is null or v_outbox_latest < now()-interval '2 hours')
  );

  insert into public.socialscheduler_public_agent_context(
    id,generated_at,opportunity_weights,content_ready,missing_assets,feedback_rows,measured_feedback_rows,
    orchestration_decisions,orchestration_decisions_total,durable_product_rankings,pipeline_by_platform,provider_feedback_30d,
    source_freshness,stale_sources,is_stale,freshness_policy
  )
  values(
    1,now(),coalesce(v_weights,'{}'::jsonb),v_ready,v_assets,v_feedback,v_measured,
    v_decisions,v_decisions_total,v_rankings,coalesce(v_pipeline,'{}'::jsonb),coalesce(v_provider_feedback,'[]'::jsonb),
    v_freshness,v_stale_sources,v_is_stale,'agent-context-freshness-v6'
  )
  on conflict(id) do update set
    generated_at=excluded.generated_at,
    opportunity_weights=excluded.opportunity_weights,
    content_ready=excluded.content_ready,
    missing_assets=excluded.missing_assets,
    feedback_rows=excluded.feedback_rows,
    measured_feedback_rows=excluded.measured_feedback_rows,
    orchestration_decisions=excluded.orchestration_decisions,
    orchestration_decisions_total=excluded.orchestration_decisions_total,
    durable_product_rankings=excluded.durable_product_rankings,
    pipeline_by_platform=excluded.pipeline_by_platform,
    provider_feedback_30d=excluded.provider_feedback_30d,
    source_freshness=excluded.source_freshness,
    stale_sources=excluded.stale_sources,
    is_stale=excluded.is_stale,
    freshness_policy=excluded.freshness_policy;

  return jsonb_build_object(
    'ok',true,'asset_rows',v_assets,'content_ready',v_ready,'feedback_rows',v_feedback,
    'measured_feedback_rows',v_measured,'fresh_decisions',v_decisions,'decision_rows_total',v_decisions_total,
    'rankings',v_rankings,'stale_sources',v_stale_sources,'is_stale',v_is_stale,'refreshed_at',now()
  );
end
$function$;
