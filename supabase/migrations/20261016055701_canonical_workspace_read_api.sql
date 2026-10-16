-- One bounded, admin-only read contract over the canonical VMDB schema.
-- No grants on business tables and no publication or policy side effects.
create or replace function private.socialmarket_workspace(
  p_section text default 'overview', p_query text default '',
  p_limit integer default 100, p_offset integer default 0, p_id uuid default null
) returns jsonb language plpgsql stable security definer
set search_path = pg_catalog, public, private
as $$
declare
  result jsonb; rows jsonb := '[]'; total bigint := 0;
  lim integer := greatest(1, least(coalesce(p_limit,100),200));
  off integer := greatest(0,least(coalesce(p_offset,0),100000));
  q text := left(trim(coalesce(p_query,'')),200);
  markets jsonb; merchants jsonb; health jsonb;
begin
  if auth.uid() is null or lower(coalesce(auth.jwt()->>'email','')) <> 'vmoulakakis@gmail.com'
     or not private.is_admin() then
    raise exception 'admin_required' using errcode = '42501';
  end if;
  if p_section not in ('overview','products','curation','creatives','outbox','analytics','configuration','optimization','merchants','problems','demand-context') then
    raise exception 'invalid_section' using errcode = '22023';
  end if;
  health := public.vmdb_ai_backend_health();
  select coalesce(jsonb_agg(to_jsonb(x) order by x.confidence_adjusted_score desc nulls last),'[]') into merchants
  from (select id as merchant_id, merchant_name as canonical_name, canonical_domain as official_domain,
    primary_category,primary_subcategory as peer_group, trust_score,
    confidence_adjusted_score as overall_opportunity_score, competition_score as competition_intensity_score,
    greek_fulfilment_score as greek_market_fit_score, null::numeric as deep_research_score,
    assessment_confidence as research_confidence, not coalesce(hard_gate_pass,false) as risk_flag,
    case when not program_approved or not tracking_verified then 'Program or tracking unverified' else ai_verdict end as risk_reason,
    null::bigint as evidence_count,ranked_at as researched_at,diversified_rank as global_rank,
    ai_verdict as score_stage,program_approved,tracking_verified,eligible_for_product_discovery,
    confidence_adjusted_score, expected_commission_eur,median_conversion_rate,median_approval_pct,median_epc_eur
    from public.merchant_latest_360) x;
  select coalesce(jsonb_agg(to_jsonb(x) order by x.demand_score desc nulls last),'[]') into markets
  from (select c.id,c.id as taxonomy_id,c.category as category_name,c.subcategory as subcategory_name,
    c.problem_title as taxonomy_name,'problem_cluster'::text as node_type,
    coalesce(d.assessed_at,c.updated_at) as observed_at,d.demand_score,d.competition_score,
    coalesce(d.pain_score,c.pain_severity_score) as pain_gap_score,null::numeric as satisfaction_score,
    o.opportunity_score,coalesce(d.confidence,c.confidence) as confidence,
    case when c.status in ('validated','approved') then 1 else 0 end as validated_pain_clusters,
    'vmdb_problem_demand_v1'::text as methodology_version,c.problem_description,c.status,
    coalesce(cardinality(d.evidence_ids),0) as evidence_entities
    from public.market_problem_clusters c
    left join lateral (select * from public.problem_demand_assessments a where a.problem_cluster_id=c.id order by a.assessed_at desc limit 1) d on true
    left join lateral (select * from public.market_opportunities a where a.problem_cluster_id=c.id order by a.calculated_at desc limit 1) o on true
    where c.market_code='GR') x;
  result := jsonb_build_object('generated_at',now(),'source','canonical_vmdb','health',health,
    'category_market',markets,'merchants',merchants,'section',p_section);
  if p_section='products' then
    select count(*) into total from public.commerce_feed_eligible_offers x
      where q='' or strpos(lower(concat_ws(' ',product_name,program_name,category_raw)),lower(q))>0;
    select coalesce(jsonb_agg(to_jsonb(x)),'[]') into rows from (
      select id,source_key,source_product_id,program_name,product_name,category_raw,price_eur,expected_commission_eur,
        commission_basis,tracking_url,image_url,in_stock,is_active,intelligence_status,last_seen_at,valid_to
      from public.commerce_feed_eligible_offers
      where q='' or strpos(lower(concat_ws(' ',product_name,program_name,category_raw)),lower(q))>0
      order by last_seen_at desc,id limit lim offset off) x;
  elsif p_section='curation' then
    select count(*) into total from public.product_selection_1000;
    select coalesce(jsonb_agg(to_jsonb(x)),'[]') into rows from (
      select * from public.product_selection_1000 order by final_score desc nulls last,id limit lim offset off) x;
  elsif p_section='creatives' or p_section='outbox' then
    if p_section='outbox' then
      select count(*) into total from public.social_publishing_outbox;
      select coalesce(jsonb_agg(to_jsonb(x)),'[]') into rows from (
        select id,source_key,source_presentation_id,platform,title,brand_slug,brand_name,caption,hashtags,format,media_url,
          tracking_url,scheduled_for,status,external_permalink,created_at,last_error,published_at,claimed_at
        from public.social_publishing_outbox order by created_at desc,id limit lim offset off) x;
    else
      select count(*) into total from public.social_presentation_intelligence;
      select coalesce(jsonb_agg(to_jsonb(x)),'[]') into rows from (
        select * from public.social_presentation_intelligence order by created_at desc,id limit lim offset off) x;
    end if;
  elsif p_section='analytics' then
    select count(*) into total from public.commerce_agent_runs;
    select coalesce(jsonb_agg(to_jsonb(x)),'[]') into rows from (
      select id,pipeline_key,stage_key,agent_key,status,model_provider,model_name,confidence,critic_status,started_at,completed_at,error
      from public.commerce_agent_runs order by created_at desc,id limit lim offset off) x;
    result := result || jsonb_build_object('feed_runs',(select coalesce(jsonb_agg(to_jsonb(x)),'[]') from (
      select id,source_key,status,scanned,eligible,inserted,updated,unchanged,error,started_at,finished_at from public.commerce_feed_runs order by created_at desc limit 20) x));
  elsif p_section='configuration' then
    select count(*) into total from public.product_selection_policies;
    select coalesce(jsonb_agg(to_jsonb(x)),'[]') into rows from public.product_selection_policies x;
    result := result || jsonb_build_object('pipeline_policies',(select coalesce(jsonb_agg(to_jsonb(x)),'[]') from public.commerce_pipeline_policies x));
  elsif p_section='optimization' then
    select count(*) into total from public.commerce_learning_calibrations;
    select coalesce(jsonb_agg(to_jsonb(x)),'[]') into rows from (
      select * from public.commerce_learning_calibrations order by calculated_at desc limit lim offset off) x;
    result := result || jsonb_build_object('feedback_events',(select count(*) from public.commerce_performance_events));
  elsif p_section='merchants' then rows:=merchants; total:=jsonb_array_length(rows);
  elsif p_section='problems' then rows:=markets; total:=jsonb_array_length(rows);
  elsif p_section='demand-context' then
    result := result || jsonb_build_object('context',jsonb_build_object(
      'taxonomy_id',p_id,'market',(select x from jsonb_array_elements(markets) x where x->>'id'=p_id::text),
      'history',(select coalesce(jsonb_agg(jsonb_build_object('observed_at',assessed_at,'demand_score',demand_score,'competition_score',competition_score,'pain_gap_score',pain_score)),'[]') from public.problem_demand_assessments where problem_cluster_id=p_id),
      'retrieved_evidence',(select coalesce(jsonb_agg(to_jsonb(x)),'[]') from (
        select id,source_type as source_kind,source_name as source_domain,source_url,query_or_topic as title,
          raw_evidence::text as body,confidence,observed_at
        from public.market_demand_observations where problem_cluster_id=p_id order by observed_at desc limit lim) x),
      'supply_context','[]'::jsonb,'source_mix','[]'::jsonb,
      'retrieval_method','exact_problem_cluster','semantic_retrieval_available',false));
  end if;
  return result || jsonb_build_object('rows',rows,'total',total,'limit',lim,'offset',off);
end $$;
revoke all on function private.socialmarket_workspace(text,text,integer,integer,uuid) from public,anon;
grant execute on function private.socialmarket_workspace(text,text,integer,integer,uuid) to authenticated;
create or replace function public.socialmarket_workspace(
  p_section text default 'overview',p_query text default '',p_limit integer default 100,p_offset integer default 0,p_id uuid default null
) returns jsonb language sql stable security invoker set search_path=pg_catalog,private
as $$ select private.socialmarket_workspace(p_section,p_query,p_limit,p_offset,p_id) $$;
revoke all on function public.socialmarket_workspace(text,text,integer,integer,uuid) from public,anon;
grant execute on function public.socialmarket_workspace(text,text,integer,integer,uuid) to authenticated;
notify pgrst,'reload schema';
