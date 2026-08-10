create schema if not exists extensions;
alter extension vector set schema extensions;

create or replace function public.match_products(
  query_embedding extensions.vector(1024),
  match_count integer default 20,
  min_price numeric default 150,
  min_similarity double precision default 0.35
)
returns table(product_id uuid, similarity double precision)
language sql stable
set search_path = public, extensions
as $$
  select pe.product_id, 1 - (pe.embedding <=> query_embedding) as similarity
  from public.product_embeddings pe
  join public.products p on p.id = pe.product_id
  where p.is_active = true
    and p.hard_gate_pass = true
    and coalesce(p.price,0) >= min_price
    and 1 - (pe.embedding <=> query_embedding) >= min_similarity
  order by pe.embedding <=> query_embedding
  limit match_count;
$$;
