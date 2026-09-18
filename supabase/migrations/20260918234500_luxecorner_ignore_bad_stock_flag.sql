create or replace view public.luxecorner_top100_public_v as
with offers as (
  select
    o.source_product_id,o.product_name,o.price_eur,o.tracking_url,o.image_url,o.category_raw,
    substring(o.tracking_url from '/z/([0-9]+)-0/CD104/') as program_id
  from public.commerce_feed_eligible_offers o
  where o.is_active=true
    and o.price_eur is not null
    and o.price_eur>0
    and o.tracking_url is not null
),
calc as (
  select o.*,c.program_name,
    greatest(
      coalesce(c.flat_commission_eur,0),
      coalesce(c.flat_commission_min_eur,0),
      coalesce(c.flat_commission_max_eur,0),
      coalesce(o.price_eur*c.percent_commission/100.0,0),
      coalesce(o.price_eur*c.percent_commission_min/100.0,0),
      coalesce(o.price_eur*c.percent_commission_max/100.0,0)
    )::numeric(14,2) as calculated_commission_eur
  from offers o
  join public.linkwise_program_commissions c on c.linkwise_program_id=o.program_id
),
dedup as (
  select distinct on (program_id,source_product_id) *
  from calc
  where calculated_commission_eur>0
  order by program_id,source_product_id,calculated_commission_eur desc,price_eur desc
),
ranked as (
  select row_number() over(order by calculated_commission_eur desc,price_eur desc,source_product_id) as rank,* from dedup
)
select rank,source_product_id,product_name,price_eur,calculated_commission_eur,
       tracking_url,image_url,category_raw,program_id,program_name
from ranked where rank<=100;

grant select on public.luxecorner_top100_public_v to anon, authenticated;
