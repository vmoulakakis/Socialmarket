-- Deep Demand Intelligence V3
-- Additive admin-only analytical contract. Does not alter existing demand scoring.

create table if not exists intel.deep_demand_snapshots (
  id uuid primary key default gen_random_uuid(),
  taxonomy_id uuid not null references catalog.taxonomy_nodes(id) on delete cascade,
  geography text not null default 'GR',
  generated_at timestamptz not null default now(),
  source_max_observed_at timestamptz,
  engine_version text not null default 'deep_demand_v3',
  history_points integer not null default 0,
  history_span_days numeric,
  forecast_tier text,
  analysis jsonb not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists deep_demand_snapshots_taxonomy_generated_idx
  on intel.deep_demand_snapshots(taxonomy_id, generated_at desc);

alter table intel.deep_demand_snapshots enable row level security;
revoke all on table intel.deep_demand_snapshots from anon, authenticated;

create or replace function public.admin_deep_demand_intelligence_v3(p_days integer default 90)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_days integer := greatest(7, least(coalesce(p_days, 90), 365));
  v_current jsonb;
  v_history jsonb;
  v_supply jsonb;
  v_pains jsonb;
  v_models jsonb;
  v_quality jsonb;
begin
  if not public.socialmarket_is_admin() then
    raise exception 'admin_only';
  end if;

  select coalesce(jsonb_agg(to_jsonb(x) order by x.opportunity_score desc nulls last, x.demand_score desc nulls last), '[]'::jsonb)
    into v_current
  from api.semantic_category_market_v2 x;

  select coalesce(jsonb_agg(to_jsonb(h) order by h.observed_at asc), '[]'::jsonb)
    into v_history
  from (
    select
      s.taxonomy_id,
      n.name as taxonomy_name,
      n.node_type,
      p.name as parent_name,
      s.observed_at,
      s.demand_score,
      s.competition_score,
      s.pain_gap_score,
      s.satisfaction_score,
      s.opportunity_score,
      s.confidence,
      s.methodology_version
    from intel.category_market_snapshots s
    join catalog.taxonomy_nodes n on n.id = s.taxonomy_id
    left join catalog.taxonomy_nodes p on p.id = n.parent_id
    where s.geography = 'GR'
      and s.observed_at >= now() - make_interval(days => v_days)
      and n.semantic_status in ('validated','mapped')
  ) h;

  select coalesce(jsonb_agg(to_jsonb(s) order by s.trusted_merchant_count desc, s.avg_trust_score desc nulls last), '[]'::jsonb)
    into v_supply
  from (
    select
      v.taxonomy_id,
      max(v.taxonomy_name) as taxonomy_name,
      max(v.primary_category) as primary_category,
      max(v.primary_subcategory) as primary_subcategory,
      count(distinct v.merchant_id)::int as trusted_merchant_count,
      count(*)::int as trusted_opportunity_rows,
      avg(v.trust_score)::numeric(8,3) as avg_trust_score,
      avg(v.saturation_penalty)::numeric(8,3) as avg_saturation_penalty,
      avg(v.merchant_scale_score)::numeric(8,3) as avg_merchant_scale_score,
      avg(v.opportunity_after_audit)::numeric(8,3) as avg_audited_opportunity,
      min(v.observed_at) as oldest_observed_at,
      max(v.observed_at) as latest_observed_at
    from api.validated_merchant_opportunities v
    where v.taxonomy_id is not null
    group by v.taxonomy_id
  ) s;

  select coalesce(jsonb_agg(to_jsonb(p) order by p.pain_severity desc nulls last, p.mention_count desc nulls last), '[]'::jsonb)
    into v_pains
  from (
    select
      c.id,
      c.taxonomy_id,
      c.cluster_label,
      c.representative_pain,
      c.mention_count,
      c.platforms,
      c.weighted_engagement,
      c.sentiment_score,
      c.pain_severity,
      c.unmet_need_score,
      c.competition_context_score,
      c.solution_whitespace_score,
      c.confidence,
      c.evidence,
      c.updated_at
    from ai.social_pain_clusters c
    where c.validated is true
      and c.taxonomy_id is not null
  ) p;

  select coalesce(jsonb_agg(to_jsonb(m) order by m.generated_at desc), '[]'::jsonb)
    into v_models
  from (
    select distinct on (d.taxonomy_id)
      d.taxonomy_id,
      d.generated_at,
      d.source_max_observed_at,
      d.engine_version,
      d.history_points,
      d.history_span_days,
      d.forecast_tier,
      d.analysis,
      d.metadata
    from intel.deep_demand_snapshots d
    where d.geography='GR'
    order by d.taxonomy_id, d.generated_at desc
  ) m;

  select jsonb_build_object(
    'history_days_requested', v_days,
    'history_rows', count(*),
    'history_taxonomies', count(distinct taxonomy_id),
    'earliest_observed_at', min(observed_at),
    'latest_observed_at', max(observed_at),
    'history_span_days', coalesce(extract(epoch from (max(observed_at)-min(observed_at))) / 86400.0, 0),
    'neural_min_daily_points', 30,
    'statistical_min_daily_points', 8,
    'change_point_min_daily_points', 12
  )
    into v_quality
  from intel.category_market_snapshots
  where geography='GR'
    and observed_at >= now() - make_interval(days => v_days);

  return jsonb_build_object(
    'version', 'deep_demand_v3',
    'generated_at', now(),
    'geography', 'GR',
    'current_market', v_current,
    'history', v_history,
    'trusted_supply', v_supply,
    'validated_social_pains', v_pains,
    'model_snapshots', v_models,
    'data_quality', v_quality,
    'semantics', jsonb_build_object(
      'observed_demand', 'existing semantic_category_market_v2 demand index; never overwritten',
      'supply', 'trusted merchant solution coverage; separate from observed demand',
      'whitespace', 'derived/inferred demand-supply opportunity; never a replacement demand score',
      'forecast', 'future estimate of the evidence-derived demand index, not search volume',
      'causality', 'disabled until explicit identification and refutation pass'
    )
  );
end
$$;

revoke all on function public.admin_deep_demand_intelligence_v3(integer) from public;
grant execute on function public.admin_deep_demand_intelligence_v3(integer) to authenticated;
