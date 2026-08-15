create table if not exists intel.product_ranking_runs (
  id uuid primary key default gen_random_uuid(),
  run_key text not null unique,
  engine_version text not null default 'ranking_v3',
  status text not null default 'running' check (status in ('running','completed','failed')),
  started_at timestamptz not null default now(),
  completed_at timestamptz,
  records_seen bigint,
  eligible_candidates bigint,
  ai_ranked integer,
  saved_count integer,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists intel.product_rankings (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references intel.product_ranking_runs(id) on delete cascade,
  source_record_hash text not null,
  canonical_key text not null,
  external_product_id text,
  merchant_id uuid not null references catalog.merchants(id),
  merchant_program_id uuid references catalog.merchant_programs(id),
  merchant_name text not null,
  product_name text not null,
  brand_name text,
  model_name text,
  category text,
  subcategory text,
  effective_price numeric,
  full_price numeric,
  discount_pct numeric,
  expected_commission_eur numeric,
  tracking_url text,
  image_url text,
  in_stock boolean,
  times_bought bigint,
  merchant_demand_score numeric,
  competition_score numeric,
  merchant_whitespace_score numeric,
  merchant_trust_score numeric,
  pain_signal_score numeric,
  seasonal_score numeric,
  commercial_score numeric,
  purchase_signal_score numeric,
  ai_product_fit_score numeric,
  ai_creative_score numeric,
  ai_value_score numeric,
  ai_confidence numeric,
  ai_risk_score numeric,
  rank_score numeric not null,
  rank_band text not null check (rank_band in ('PROMOTE_NOW','HIGH_POTENTIAL','TEST','WATCHLIST')),
  promotion_angle text,
  promotion_reason text,
  audience text,
  recommended_channels jsonb not null default '[]'::jsonb,
  risk_flags jsonb not null default '[]'::jsonb,
  evidence_summary jsonb not null default '{}'::jsonb,
  ai_summary text,
  ranked_at timestamptz not null default now(),
  unique(run_id, source_record_hash)
);

create index if not exists product_rankings_run_score_idx on intel.product_rankings(run_id, rank_score desc);
create index if not exists product_rankings_merchant_idx on intel.product_rankings(merchant_id, rank_score desc);
create index if not exists product_rankings_category_idx on intel.product_rankings(category, rank_score desc);

alter table intel.product_ranking_runs enable row level security;
alter table intel.product_rankings enable row level security;
revoke all on intel.product_ranking_runs from anon, authenticated;
revoke all on intel.product_rankings from anon, authenticated;

drop view if exists api.product_rankings;
create view api.product_rankings as
with latest as (
  select id, run_key, completed_at
  from intel.product_ranking_runs
  where status='completed'
  order by completed_at desc nulls last, started_at desc
  limit 1
)
select r.*, l.run_key,
       row_number() over(order by r.rank_score desc, r.ai_confidence desc nulls last, r.expected_commission_eur desc nulls last) as global_rank
from intel.product_rankings r
join latest l on l.id=r.run_id;
revoke all on api.product_rankings from anon, authenticated;

create or replace function public.admin_top_ranked_products(p_limit integer default 100, p_band text default null)
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
    select * from api.product_rankings
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
    'generated_at', now(),
    'latest_run', (select to_jsonb(x) from (select * from intel.product_ranking_runs order by started_at desc limit 1) x),
    'product_counts', jsonb_build_object(
      'ranked', (select count(*) from api.product_rankings),
      'promote_now', (select count(*) from api.product_rankings where rank_band='PROMOTE_NOW'),
      'high_potential', (select count(*) from api.product_rankings where rank_band='HIGH_POTENTIAL'),
      'test', (select count(*) from api.product_rankings where rank_band='TEST')
    ),
    'top_products', coalesce((select jsonb_agg(to_jsonb(x) order by x.global_rank) from (select * from api.product_rankings order by global_rank limit 20) x),'[]'::jsonb),
    'top_merchants', coalesce((select jsonb_agg(to_jsonb(x) order by x.global_rank) from (select merchant_id,canonical_name,primary_category,overall_opportunity_score,trust_score,commercial_rank_score,global_rank from api.merchant_rankings order by global_rank limit 10) x),'[]'::jsonb),
    'demand_summary', jsonb_build_object(
      'analysis_runs', (select count(*) from intel.demand_analysis_runs),
      'latest_observed_at', (select max(observed_at) from api.semantic_category_market_v2),
      'active_themes', (select count(*) from intel.demand_themes where status='active')
    )
  ) into result;
  return result;
end $$;

grant execute on function public.admin_top_ranked_products(integer,text) to authenticated;
grant execute on function public.admin_ranking_dashboard() to authenticated;
