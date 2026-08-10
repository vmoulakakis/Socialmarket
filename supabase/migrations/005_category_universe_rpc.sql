create or replace function public.category_universe(
  min_price numeric default 150,
  min_products integer default 3,
  result_limit integer default 100
)
returns table(
  category_raw text,
  product_count bigint,
  merchant_count bigint,
  brand_count bigint,
  avg_price numeric,
  median_price numeric,
  avg_discount numeric,
  total_times_bought numeric
)
language sql
stable
security invoker
set search_path = public
as $$
  select
    coalesce(p.category_raw,'Uncategorized') as category_raw,
    count(*)::bigint as product_count,
    count(distinct coalesce(p.merchant_name,p.program_name))::bigint as merchant_count,
    count(distinct p.brand_name)::bigint as brand_count,
    round(avg(p.price),2) as avg_price,
    percentile_cont(0.5) within group (order by p.price)::numeric as median_price,
    round(avg(coalesce(p.discount_pct,0)),2) as avg_discount,
    sum(coalesce(p.times_bought,0))::numeric as total_times_bought
  from public.products p
  where p.is_active=true and p.hard_gate_pass=true and coalesce(p.price,0)>=min_price
  group by coalesce(p.category_raw,'Uncategorized')
  having count(*) >= min_products
  order by sum(coalesce(p.times_bought,0)) desc, count(*) desc
  limit result_limit;
$$;

grant execute on function public.category_universe(numeric,integer,integer) to authenticated, service_role;
