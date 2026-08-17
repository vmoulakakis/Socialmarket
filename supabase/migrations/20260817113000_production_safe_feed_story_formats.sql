create or replace function publish.native_format_for_slot_v1(p_platform text,p_slot_no integer)
returns text
language sql
immutable
set search_path=''
as $$
  select case
    -- Current ranked 9:16 assets are static images, so they are valid Stories,
    -- not Reels. Reels remain executor-supported for explicit real-video jobs.
    when lower(coalesce(p_platform,''))='instagram' and mod(greatest(coalesce(p_slot_no,1),1),5)=0 then 'story'
    when lower(coalesce(p_platform,''))='tiktok' then 'photo'
    else 'post'
  end
$$;
