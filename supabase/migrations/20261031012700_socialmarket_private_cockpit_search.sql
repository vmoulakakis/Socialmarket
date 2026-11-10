-- Add SQL-first read-only GraphRAG explorer for personal cockpit.
create or replace function public.socialmarket_cockpit_search(p_query text,p_limit integer default 12)
returns jsonb language plpgsql stable security definer set search_path='' as $$
declare result jsonb;
begin
 if auth.uid() is null or not private.is_admin() then
  raise exception 'admin_access_required' using errcode='42501';
 end if;
 if p_query is null or length(trim(p_query))<2 or length(p_query)>160 or
    p_limit is null or p_limit<1 or p_limit>20 then
   raise exception 'invalid_search' using errcode='22023';
 end if;
 select coalesce(jsonb_agg(
   jsonb_build_object('type',x.entity_type,'title',x.title,
   'source_state',x.source_state,'score',round(x.rrf_score::numeric,5),
   'lexical_rank',x.lexical_rank,'semantic_rank',x.semantic_rank,
   'entity_pk',x.entity_pk,'graph_node_id',x.graph_node_id,
   'excerpt',left(x.content,220)) order by x.rrf_score desc
 ),'[]'::jsonb) into result
 from sm_intel.hybrid_retrieve(p_query,null,p_limit,null::text[],true) x;
 return jsonb_build_object('query',p_query,'retrieval_mode','fts_plus_sql',
  'results',result,'vector_ready',(select count(*) from sm_intel.search_documents where embedding_status='ready'),
  'note','Unverified candidate results are not approved commercial offers');
end $$;
revoke all on function public.socialmarket_cockpit_search(text,integer) from public,anon,authenticated;
grant execute on function public.socialmarket_cockpit_search(text,integer) to authenticated,service_role;
