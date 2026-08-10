alter table public.products add column if not exists validity_days_remaining integer;
alter table public.products add column if not exists validity_runway_score numeric(5,2) not null default 0;
alter table public.products add column if not exists travel_related boolean not null default false;
alter table public.products add column if not exists eligibility_reason jsonb not null default '{}'::jsonb;
alter table public.products add column if not exists market_eligible boolean not null default true;
alter table public.products add column if not exists market_exclusion_reason text;

alter table public.opportunity_scores add column if not exists seller_competition_score numeric(5,2) not null default 0;
alter table public.opportunity_scores add column if not exists ad_pressure_score numeric(5,2) not null default 0;
alter table public.opportunity_scores add column if not exists competition_kill boolean not null default false;
alter table public.opportunity_scores add column if not exists validity_runway_score numeric(5,2) not null default 0;

insert into public.app_settings(key,value) values
 ('selection_policy', jsonb_build_object(
   'min_price_eur',150,
   'min_validity_days',20,
   'exclude_travel',true,
   'seller_competition_kill',82,
   'ad_pressure_proxy_kill',92,
   'ad_pressure_min_confidence',0.65,
   'timezone','Europe/Athens'
 ))
on conflict (key) do update set value=excluded.value, updated_at=now();

drop function if exists public.category_universe(numeric,integer,integer);
create function public.category_universe(
  min_price numeric default 150,
  min_products integer default 3,
  result_limit integer default 40
)
returns table(
  category_raw text,
  product_count bigint,
  merchant_count bigint,
  brand_count bigint,
  total_times_bought numeric,
  median_price numeric
)
language sql
stable
security invoker
set search_path=''
as $$
  select
    p.category_raw,
    count(*)::bigint as product_count,
    count(distinct coalesce(p.merchant_name,p.program_name))::bigint as merchant_count,
    count(distinct p.brand_name)::bigint as brand_count,
    coalesce(sum(p.times_bought),0)::numeric as total_times_bought,
    percentile_cont(0.5) within group (order by p.price)::numeric as median_price
  from public.products p
  where p.hard_gate_pass = true
    and p.is_active = true
    and p.price >= min_price
    and p.travel_related = false
    and p.valid_to is not null
    and p.valid_to::date > (current_date + 20)
    and p.category_raw is not null
  group by p.category_raw
  having count(*) >= min_products
  order by total_times_bought desc, product_count desc
  limit result_limit;
$$;

revoke all on function public.category_universe(numeric,integer,integer) from public, anon;
grant execute on function public.category_universe(numeric,integer,integer) to authenticated, service_role;

create index if not exists idx_products_valid_market_gate on public.products(valid_to, travel_related, hard_gate_pass, is_active, price);
create index if not exists idx_products_market_eligible on public.products(market_eligible) where market_eligible=true;
