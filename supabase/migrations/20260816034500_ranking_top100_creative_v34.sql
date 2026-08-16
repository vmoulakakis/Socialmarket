alter table intel.product_rankings
  add column if not exists creative_pack jsonb not null default '{}'::jsonb,
  add column if not exists creative_audit jsonb not null default '{}'::jsonb,
  add column if not exists creative_status text not null default 'not_targeted',
  add column if not exists creative_generated_at timestamptz;

do $$ begin
  alter table intel.product_rankings
    add constraint product_rankings_creative_status_check
    check (creative_status in ('not_targeted','ready','needs_review','failed'));
exception when duplicate_object then null; end $$;

do $$ begin
  alter table intel.product_rankings
    add constraint product_rankings_creative_pack_three_variants_check
    check (
      creative_pack='{}'::jsonb or (
        jsonb_typeof(creative_pack->'variants')='array'
        and jsonb_array_length(creative_pack->'variants')=3
      )
    );
exception when duplicate_object then null; end $$;

create index if not exists product_rankings_creative_status_idx
  on intel.product_rankings(run_id, creative_status, rank_score desc);

create or replace function public.admin_top20_creative_products()
returns jsonb
language plpgsql
security definer
set search_path=''
as $$
declare result jsonb;
begin
  if not public.socialmarket_is_admin() then raise exception 'admin_only'; end if;
  with latest as (
    select id,run_key,completed_at
    from intel.product_ranking_runs
    where status='completed'
    order by completed_at desc nulls last,started_at desc
    limit 1
  ), ranked as (
    select r.*,l.run_key,
      row_number() over(order by r.rank_score desc,r.ai_confidence desc nulls last,r.expected_commission_eur desc nulls last) global_rank
    from intel.product_rankings r
    join latest l on l.id=r.run_id
  )
  select coalesce(jsonb_agg(to_jsonb(x) order by x.global_rank),'[]'::jsonb)
  into result
  from (select * from ranked order by global_rank limit 20) x;
  return result;
end $$;

revoke all on function public.admin_top20_creative_products() from public;
grant execute on function public.admin_top20_creative_products() to authenticated;
