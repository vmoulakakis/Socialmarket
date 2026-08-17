create or replace function content.ensure_ranked_creative_native_platforms_v1()
returns trigger
language plpgsql
set search_path=''
as $$
declare
  v_platforms jsonb;
begin
  if new.metadata->>'origin'='ranked_product_creative'
     and new.metadata->>'variant_id' in ('feed_4x5','square_1x1') then
    select coalesce(jsonb_agg(x order by x),'[]'::jsonb)
      into v_platforms
    from (
      select distinct value as x
      from jsonb_array_elements_text(
        coalesce(new.metadata->'platforms','[]'::jsonb) || '["linkedin"]'::jsonb
      )
    ) s;
    new.metadata=jsonb_set(new.metadata,'{platforms}',v_platforms,true);
  end if;
  return new;
end
$$;

drop trigger if exists trg_ranked_creative_native_platforms on content.items;
create trigger trg_ranked_creative_native_platforms
before insert or update of metadata on content.items
for each row execute function content.ensure_ranked_creative_native_platforms_v1();

update content.items ci
set metadata=jsonb_set(
  ci.metadata,
  '{platforms}',
  (
    select coalesce(jsonb_agg(x order by x),'[]'::jsonb)
    from (
      select distinct value as x
      from jsonb_array_elements_text(
        coalesce(ci.metadata->'platforms','[]'::jsonb) || '["linkedin"]'::jsonb
      )
    ) s
  ),
  true
), updated_at=now()
where ci.metadata->>'origin'='ranked_product_creative'
  and ci.metadata->>'variant_id' in ('feed_4x5','square_1x1');
