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
    and p.valid_to::date > (((now() at time zone 'Europe/Athens')::date) + 20)
    and p.category_raw is not null
  group by p.category_raw
  having count(*) >= min_products
  order by total_times_bought desc, product_count desc
  limit result_limit;
$$;
revoke all on function public.category_universe(numeric,integer,integer) from public, anon;
grant execute on function public.category_universe(numeric,integer,integer) to authenticated, service_role;
