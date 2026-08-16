alter table intel.product_rankings
  add column if not exists network_performance_score numeric,
  add column if not exists product_attributes jsonb not null default '{}'::jsonb,
  add column if not exists kpi_snapshot jsonb not null default '{}'::jsonb,
  add column if not exists seo_content jsonb not null default '{}'::jsonb,
  add column if not exists seo_generated_at timestamptz;

create or replace view api.product_rankings_enriched as
with latest as (
  select id,run_key,completed_at
  from intel.product_ranking_runs
  where status='completed'
  order by completed_at desc nulls last,started_at desc
  limit 1
)
select r.*,l.run_key,
       row_number() over(order by r.rank_score desc,r.ai_confidence desc nulls last,r.expected_commission_eur desc nulls last) as global_rank
from intel.product_rankings r
join latest l on l.id=r.run_id;
revoke all on api.product_rankings_enriched from anon,authenticated;

create or replace function public.admin_top_ranked_products(p_limit integer default 100,p_band text default null)
returns jsonb
language plpgsql
security definer
set search_path=''
as $$
declare result jsonb;
begin
  if not public.socialmarket_is_admin() then raise exception 'admin_only'; end if;
  select coalesce(jsonb_agg(to_jsonb(x) order by x.global_rank),'[]'::jsonb)
  into result
  from (
    select * from api.product_rankings_enriched
    where p_band is null or rank_band=p_band
    order by global_rank
    limit greatest(1,least(coalesce(p_limit,100),500))
  ) x;
  return result;
end $$;

create or replace function public.admin_ranking_dashboard()
returns jsonb
language plpgsql
security definer
set search_path=''
as $$
declare result jsonb;
begin
  if not public.socialmarket_is_admin() then raise exception 'admin_only'; end if;
  select jsonb_build_object(
    'generated_at',now(),
    'latest_run',(select to_jsonb(x) from (select * from intel.product_ranking_runs order by started_at desc limit 1)x),
    'product_counts',jsonb_build_object(
      'ranked',(select count(*) from api.product_rankings_enriched),
      'promote_now',(select count(*) from api.product_rankings_enriched where rank_band='PROMOTE_NOW'),
      'high_potential',(select count(*) from api.product_rankings_enriched where rank_band='HIGH_POTENTIAL'),
      'test',(select count(*) from api.product_rankings_enriched where rank_band='TEST'),
      'with_seo',(select count(*) from api.product_rankings_enriched where seo_generated_at is not null),
      'with_network_kpi',(select count(*) from api.product_rankings_enriched where (kpi_snapshot->'network_baseline'->>'status')='observed_program_baseline'),
      'with_first_party_30d',(select count(*) from api.product_rankings_enriched where (kpi_snapshot->'first_party_30d'->>'status')='observed')
    ),
    'top_products',coalesce((select jsonb_agg(to_jsonb(x) order by x.global_rank) from (select * from api.product_rankings_enriched order by global_rank limit 20)x),'[]'::jsonb),
    'top_merchants',coalesce((select jsonb_agg(to_jsonb(x) order by x.global_rank) from (select merchant_id,canonical_name,primary_category,overall_opportunity_score,trust_score,commercial_rank_score,global_rank from api.merchant_rankings order by global_rank limit 10)x),'[]'::jsonb),
    'demand_summary',jsonb_build_object(
      'analysis_runs',(select count(*) from intel.demand_analysis_runs),
      'latest_observed_at',(select max(observed_at) from api.semantic_category_market_v2),
      'active_themes',(select count(*) from intel.demand_themes where status='active')
    ),
    'analytics_status',jsonb_build_object(
      'first_party_rows_30d',(select count(*) from ops.affiliate_performance_daily where metric_date>=current_date-29),
      'first_party_clicks_30d',(select coalesce(sum(outbound_clicks),0) from ops.affiliate_performance_daily where metric_date>=current_date-29),
      'first_party_approved_conversions_30d',(select coalesce(sum(conversions_approved),0) from ops.affiliate_performance_daily where metric_date>=current_date-29)
    )
  ) into result;
  return result;
end $$;

revoke all on function public.admin_top_ranked_products(integer,text) from public;
revoke all on function public.admin_ranking_dashboard() from public;
grant execute on function public.admin_top_ranked_products(integer,text) to authenticated;
grant execute on function public.admin_ranking_dashboard() to authenticated;
