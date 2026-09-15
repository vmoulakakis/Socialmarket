alter table public.commerce_semantic_documents
  add column if not exists embedding_claimed_at timestamptz,
  add column if not exists embedding_worker text,
  add column if not exists embedding_error text,
  add column if not exists embedding_attempts integer not null default 0;

alter table public.commerce_semantic_documents
  drop constraint if exists commerce_semantic_documents_embedding_status_check;

alter table public.commerce_semantic_documents
  add constraint commerce_semantic_documents_embedding_status_check
  check (embedding_status = any (array['pending'::text,'processing'::text,'ready'::text,'failed'::text,'stale'::text,'skipped'::text]));

create index if not exists commerce_semantic_embedding_queue_idx
  on public.commerce_semantic_documents (market_code, embedding_status, updated_at)
  where embedding_status in ('pending','processing');

create or replace function public.vmdb_refresh_semantic_memory(p_market_code text default 'GR')
returns jsonb
language plpgsql
security invoker
set search_path = public, extensions, pg_temp
as $$
declare
  v_merchants bigint := 0;
  v_problems bigint := 0;
  v_products bigint := 0;
  v_presentations bigint := 0;
  v_staled bigint := 0;
  v_current bigint := 0;
begin
  if nullif(trim(p_market_code),'') is null then
    raise exception 'market code is required';
  end if;

  with src as (
    select
      v.id as entity_id,
      coalesce(v.merchant_name,'Merchant') as title,
      concat_ws(E'\n',
        'Merchant: ' || coalesce(v.merchant_name,''),
        'Category: ' || coalesce(v.primary_category,'') || case when nullif(v.primary_subcategory,'') is not null then ' / ' || v.primary_subcategory else '' end,
        'Expected commission EUR: ' || coalesce(v.expected_commission_eur::text,'unknown'),
        'Demand score: ' || coalesce(v.demand_score::text,'unknown'),
        'Commercial intent: ' || coalesce(v.commercial_intent_score::text,'unknown'),
        'Supply gap: ' || coalesce(v.supply_gap_score::text,'unknown'),
        'Greek scarcity: ' || coalesce(v.greek_scarcity_score::text,'unknown'),
        'Problem solving: ' || coalesce(v.problem_solving_score::text,'unknown'),
        'Trust: ' || coalesce(v.trust_score::text,'unknown'),
        'Conversion potential: ' || coalesce(v.conversion_potential_score::text,'unknown'),
        '360 score: ' || coalesce(v.confidence_adjusted_score::text,'unknown'),
        'AI verdict: ' || coalesce(v.ai_verdict,'unassessed'),
        'Affiliate program approved: ' || coalesce(v.program_approved::text,'false'),
        'Tracking verified: ' || coalesce(v.tracking_verified::text,'false')
      ) as content,
      jsonb_build_object(
        'legacy_merchant_id',v.legacy_merchant_id,
        'category',v.primary_category,
        'subcategory',v.primary_subcategory,
        'hard_gate_pass',v.hard_gate_pass,
        'eligible_for_product_discovery',v.eligible_for_product_discovery,
        'grade',v.grade,
        'expected_commission_eur',v.expected_commission_eur
      ) as metadata,
      greatest(coalesce(v.ranked_at,v.updated_at),v.updated_at) as observed_at,
      least(1::numeric,greatest(0::numeric,coalesce(v.ranking_confidence,v.assessment_confidence,0))) as evidence_confidence
    from public.merchant_latest_360 v
  )
  insert into public.commerce_semantic_documents
    (entity_type,entity_id,market_code,document_type,title,content,content_hash,metadata,embedding_status,evidence_confidence,observed_at,updated_at)
  select
    'merchant',entity_id,upper(p_market_code),'semantic_profile',title,content,md5(content),metadata,'pending',evidence_confidence,observed_at,now()
  from src
  on conflict (entity_type,entity_id,document_type,content_hash)
  do update set
    metadata=excluded.metadata,
    evidence_confidence=excluded.evidence_confidence,
    observed_at=excluded.observed_at,
    updated_at=now();
  get diagnostics v_merchants = row_count;

  with latest_problem as (
    select distinct on (pda.problem_cluster_id)
      pda.*
    from public.problem_demand_assessments pda
    order by pda.problem_cluster_id,pda.assessed_at desc
  ), src as (
    select
      p.id as entity_id,
      p.problem_title as title,
      concat_ws(E'\n',
        'Problem: ' || coalesce(p.problem_title,''),
        'Description: ' || coalesce(p.problem_description,''),
        'Target customer: ' || coalesce(p.target_customer,''),
        'Category: ' || coalesce(p.category,'') || case when nullif(p.subcategory,'') is not null then ' / ' || p.subcategory else '' end,
        'Pain severity: ' || coalesce(p.pain_severity_score::text,'unknown'),
        'Purchase urgency: ' || coalesce(p.purchase_urgency_score::text,'unknown'),
        'Solution clarity: ' || coalesce(p.solution_clarity_score::text,'unknown'),
        'Willingness to pay: ' || coalesce(p.willingness_to_pay_score::text,'unknown'),
        'Demand score: ' || coalesce(a.demand_score::text,'unknown'),
        'Buyer intent: ' || coalesce(a.buyer_intent_score::text,'unknown'),
        'Supply gap: ' || coalesce(a.supply_gap_score::text,'unknown'),
        'Competition: ' || coalesce(a.competition_score::text,'unknown'),
        'Trend momentum: ' || coalesce(a.trend_momentum_score::text,'unknown')
      ) as content,
      jsonb_build_object(
        'problem_key',p.problem_key,
        'category',p.category,
        'subcategory',p.subcategory,
        'status',p.status,
        'demand_assessment_id',a.id
      ) as metadata,
      greatest(coalesce(a.assessed_at,p.updated_at),p.updated_at) as observed_at,
      least(1::numeric,greatest(0::numeric,coalesce(a.confidence,p.confidence,0))) as evidence_confidence
    from public.market_problem_clusters p
    left join latest_problem a on a.problem_cluster_id=p.id
    where p.market_code=upper(p_market_code)
  )
  insert into public.commerce_semantic_documents
    (entity_type,entity_id,market_code,document_type,title,content,content_hash,metadata,embedding_status,evidence_confidence,observed_at,updated_at)
  select
    'problem_cluster',entity_id,upper(p_market_code),'semantic_profile',title,content,md5(content),metadata,'pending',evidence_confidence,observed_at,now()
  from src
  on conflict (entity_type,entity_id,document_type,content_hash)
  do update set
    metadata=excluded.metadata,
    evidence_confidence=excluded.evidence_confidence,
    observed_at=excluded.observed_at,
    updated_at=now();
  get diagnostics v_problems = row_count;

  with src as (
    select
      p.id as entity_id,
      p.product_name as title,
      concat_ws(E'\n',
        'Product: ' || coalesce(p.product_name,''),
        'Brand: ' || coalesce(p.brand,''),
        'Category: ' || coalesce(p.category,''),
        'Price EUR: ' || coalesce(p.price_eur::text,'unknown'),
        'Demand: ' || coalesce(p.demand_score::text,'unknown'),
        'Pain fit: ' || coalesce(p.pain_fit_score::text,'unknown'),
        'Supply gap: ' || coalesce(p.supply_gap_score::text,'unknown'),
        'Greek scarcity: ' || coalesce(p.greek_scarcity_score::text,'unknown'),
        'Merchant fit: ' || coalesce(p.merchant_fit_score::text,'unknown'),
        'Price value: ' || coalesce(p.price_value_score::text,'unknown'),
        'Trust: ' || coalesce(p.trust_score::text,'unknown'),
        'Conversion: ' || coalesce(p.conversion_score::text,'unknown'),
        'Final score: ' || coalesce(p.final_score::text,'unknown')
      ) as content,
      jsonb_build_object(
        'source_key',p.source_key,
        'source_product_id',p.source_product_id,
        'merchant_profile_id',p.merchant_profile_id,
        'problem_cluster_id',p.problem_cluster_id,
        'selection_status',p.selection_status,
        'critic_status',p.critic_status
      ) as metadata,
      coalesce(p.observed_at,p.updated_at) as observed_at,
      least(1::numeric,greatest(0::numeric,coalesce(p.confidence,0))) as evidence_confidence
    from public.product_selection_1000 p
  )
  insert into public.commerce_semantic_documents
    (entity_type,entity_id,market_code,document_type,title,content,content_hash,metadata,embedding_status,evidence_confidence,observed_at,updated_at)
  select
    'product_candidate',entity_id,upper(p_market_code),'semantic_profile',title,content,md5(content),metadata,'pending',evidence_confidence,observed_at,now()
  from src
  on conflict (entity_type,entity_id,document_type,content_hash)
  do update set
    metadata=excluded.metadata,
    evidence_confidence=excluded.evidence_confidence,
    observed_at=excluded.observed_at,
    updated_at=now();
  get diagnostics v_products = row_count;

  with src as (
    select
      s.id as entity_id,
      coalesce(nullif(s.hook,''),'Social presentation') as title,
      concat_ws(E'\n',
        'Platform: ' || coalesce(s.platform,''),
        'Audience: ' || coalesce(s.audience_key,''),
        'Angle: ' || coalesce(s.angle_key,''),
        'Hook: ' || coalesce(s.hook,''),
        'Pain: ' || coalesce(s.pain_statement,''),
        'Solution: ' || coalesce(s.solution_statement,''),
        'Value: ' || coalesce(s.value_statement,''),
        'CTA: ' || coalesce(s.cta,'')
      ) as content,
      jsonb_build_object(
        'product_candidate_id',s.product_candidate_id,
        'merchant_id',s.merchant_id,
        'problem_cluster_id',s.problem_cluster_id,
        'platform',s.platform,
        'critic_status',s.critic_status,
        'predicted_conversion_score',s.predicted_conversion_score,
        'predicted_engagement_score',s.predicted_engagement_score
      ) as metadata,
      s.updated_at as observed_at,
      least(1::numeric,greatest(0::numeric,coalesce(s.confidence,0))) as evidence_confidence
    from public.social_presentation_intelligence s
    where lower(coalesce(s.critic_status,'')) in ('approved','pass','ready')
  )
  insert into public.commerce_semantic_documents
    (entity_type,entity_id,market_code,document_type,title,content,content_hash,metadata,embedding_status,evidence_confidence,observed_at,updated_at)
  select
    'social_presentation',entity_id,upper(p_market_code),'semantic_profile',title,content,md5(content),metadata,'pending',evidence_confidence,observed_at,now()
  from src
  on conflict (entity_type,entity_id,document_type,content_hash)
  do update set
    metadata=excluded.metadata,
    evidence_confidence=excluded.evidence_confidence,
    observed_at=excluded.observed_at,
    updated_at=now();
  get diagnostics v_presentations = row_count;

  with ranked as (
    select id,
           row_number() over (
             partition by entity_type,entity_id,document_type
             order by observed_at desc nulls last,updated_at desc,id desc
           ) as rn
    from public.commerce_semantic_documents
    where market_code=upper(p_market_code)
  )
  update public.commerce_semantic_documents d
     set embedding_status='stale',
         expires_at=coalesce(d.expires_at,now()),
         embedding_worker=null,
         embedding_claimed_at=null,
         updated_at=now()
    from ranked r
   where d.id=r.id and r.rn>1 and d.embedding_status<>'stale';
  get diagnostics v_staled = row_count;

  select count(*) into v_current
  from public.commerce_semantic_documents
  where market_code=upper(p_market_code) and embedding_status<>'stale';

  return jsonb_build_object(
    'ok',true,
    'database','vmdb',
    'contract','semantic-memory-v1',
    'market_code',upper(p_market_code),
    'merchant_documents_upserted',v_merchants,
    'problem_documents_upserted',v_problems,
    'product_documents_upserted',v_products,
    'presentation_documents_upserted',v_presentations,
    'old_versions_staled',v_staled,
    'current_documents',v_current
  );
end;
$$;

create or replace function public.vmdb_semantic_embedding_claim(
  p_worker text,
  p_limit integer default 20,
  p_lease_minutes integer default 15,
  p_market_code text default 'GR'
)
returns table (
  id uuid,
  entity_type text,
  entity_id uuid,
  document_type text,
  title text,
  content text,
  content_hash text,
  evidence_confidence numeric,
  metadata jsonb
)
language plpgsql
security invoker
set search_path = public, extensions, pg_temp
as $$
begin
  if nullif(trim(p_worker),'') is null then
    raise exception 'worker is required';
  end if;

  update public.commerce_semantic_documents
     set embedding_status='pending',
         embedding_worker=null,
         embedding_claimed_at=null,
         embedding_error='lease_expired',
         updated_at=now()
   where embedding_status='processing'
     and embedding_claimed_at < now() - make_interval(mins => greatest(1,least(coalesce(p_lease_minutes,15),120)));

  return query
  with picked as (
    select d.id
      from public.commerce_semantic_documents d
     where d.market_code=upper(coalesce(nullif(trim(p_market_code),''),'GR'))
       and d.embedding_status='pending'
     order by d.evidence_confidence desc,d.updated_at asc
     for update skip locked
     limit greatest(1,least(coalesce(p_limit,20),100))
  ), claimed as (
    update public.commerce_semantic_documents d
       set embedding_status='processing',
           embedding_worker=p_worker,
           embedding_claimed_at=now(),
           embedding_attempts=d.embedding_attempts+1,
           embedding_error=null,
           updated_at=now()
      from picked p
     where d.id=p.id
    returning d.*
  )
  select c.id,c.entity_type,c.entity_id,c.document_type,c.title,c.content,c.content_hash,c.evidence_confidence,c.metadata
  from claimed c;
end;
$$;

create or replace function public.vmdb_semantic_embedding_ack(
  p_id uuid,
  p_worker text,
  p_embedding_text text default null,
  p_model text default null,
  p_error text default null
)
returns jsonb
language plpgsql
security invoker
set search_path = public, extensions, pg_temp
as $$
declare
  v_status text;
begin
  if p_error is not null then
    update public.commerce_semantic_documents
       set embedding_status='failed',
           embedding_error=left(p_error,2000),
           embedding_worker=null,
           embedding_claimed_at=null,
           updated_at=now()
     where id=p_id
       and embedding_status='processing'
       and embedding_worker=p_worker;
  else
    if nullif(trim(p_embedding_text),'') is null then
      raise exception 'embedding is required when p_error is null';
    end if;
    update public.commerce_semantic_documents
       set embedding=p_embedding_text::extensions.vector(1536),
           embedding_model=coalesce(nullif(trim(p_model),''),'unknown'),
           embedding_status='ready',
           embedding_error=null,
           embedding_worker=null,
           embedding_claimed_at=null,
           updated_at=now()
     where id=p_id
       and embedding_status='processing'
       and embedding_worker=p_worker;
  end if;

  select embedding_status into v_status
  from public.commerce_semantic_documents
  where id=p_id;

  if v_status is null then
    raise exception 'semantic document not found';
  end if;

  return jsonb_build_object('ok',true,'id',p_id,'embedding_status',v_status);
end;
$$;

create or replace function public.vmdb_semantic_search(
  p_query_embedding_text text,
  p_query_text text default null,
  p_market_code text default 'GR',
  p_limit integer default 20,
  p_entity_types text[] default null
)
returns table (
  id uuid,
  entity_type text,
  entity_id uuid,
  document_type text,
  title text,
  content text,
  metadata jsonb,
  evidence_confidence numeric,
  semantic_score double precision,
  text_score real,
  hybrid_score double precision
)
language sql
stable
security invoker
set search_path = public, extensions, pg_temp
as $$
  with params as (
    select p_query_embedding_text::extensions.vector(1536) as qv
  ), scored as (
    select
      d.id,d.entity_type,d.entity_id,d.document_type,d.title,d.content,d.metadata,d.evidence_confidence,
      greatest(0::double precision,least(1::double precision,1 - (d.embedding <=> params.qv))) as semantic_score,
      case
        when nullif(trim(p_query_text),'') is null then 0::real
        else ts_rank_cd(
          to_tsvector('simple',coalesce(d.title,'') || ' ' || coalesce(d.content,'')),
          plainto_tsquery('simple',p_query_text)
        )
      end as text_score
    from public.commerce_semantic_documents d
    cross join params
    where d.market_code=upper(coalesce(nullif(trim(p_market_code),''),'GR'))
      and d.embedding_status='ready'
      and d.embedding is not null
      and (p_entity_types is null or d.entity_type=any(p_entity_types))
  )
  select
    s.id,s.entity_type,s.entity_id,s.document_type,s.title,s.content,s.metadata,s.evidence_confidence,
    s.semantic_score,s.text_score,
    (s.semantic_score * 0.85 + least(1::double precision,s.text_score::double precision) * 0.15) as hybrid_score
  from scored s
  order by hybrid_score desc,s.evidence_confidence desc
  limit greatest(1,least(coalesce(p_limit,20),100));
$$;

create or replace function public.vmdb_ai_backend_health()
returns jsonb
language plpgsql
stable
security invoker
set search_path = public, extensions, pg_temp
as $$
declare
  v_merchants bigint;
  v_assessed bigint;
  v_ranked bigint;
  v_unverified bigint;
  v_eligible bigint;
  v_problems bigint;
  v_problem_assessments bigint;
  v_problem_fits bigint;
  v_offers bigint;
  v_funnel bigint;
  v_selected bigint;
  v_semantic_current bigint;
  v_semantic_pending bigint;
  v_semantic_ready bigint;
  v_presentations bigint;
  v_outbox_open bigint;
  v_feedback bigint;
  v_tool_tasks_open bigint;
  v_next_action text;
  v_pipeline_status text;
begin
  select count(*) into v_merchants from public.merchant_profiles where active;
  select count(distinct merchant_id) into v_assessed from public.merchant_demand_assessments where market_code='GR';
  select count(distinct merchant_id) into v_ranked from public.merchant_rankings;
  select count(*) into v_unverified from public.merchant_profiles where active and (not coalesce(program_approved,false) or not coalesce(tracking_verified,false));
  select count(*) into v_eligible from public.merchant_product_discovery_eligible;
  select count(*) into v_problems from public.market_problem_clusters where market_code='GR';
  select count(distinct problem_cluster_id) into v_problem_assessments from public.problem_demand_assessments;
  select count(*) into v_problem_fits from public.merchant_problem_fits;
  select count(*) into v_offers from public.commerce_feed_eligible_offers;
  select count(*) into v_funnel from public.product_selection_funnel;
  select count(*) into v_selected from public.product_selection_1000;
  select count(*) into v_semantic_current from public.commerce_semantic_documents where market_code='GR' and embedding_status<>'stale';
  select count(*) into v_semantic_pending from public.commerce_semantic_documents where market_code='GR' and embedding_status in ('pending','processing','failed');
  select count(*) into v_semantic_ready from public.commerce_semantic_documents where market_code='GR' and embedding_status='ready';
  select count(*) into v_presentations from public.social_presentation_intelligence where lower(coalesce(critic_status,'')) in ('approved','pass','ready');
  select count(*) into v_outbox_open from public.social_publishing_outbox where status in ('queued','leased','scheduled');
  select count(*) into v_feedback from public.commerce_performance_events;
  select count(*) into v_tool_tasks_open from public.agent_tool_tasks where completed_at is null and lower(state) not in ('completed','done','failed','cancelled');

  if v_merchants=0 then
    v_next_action:='ingest_merchants';
  elsif v_assessed<v_merchants or v_ranked<v_merchants then
    v_next_action:='run_merchant360';
  elsif v_eligible=0 and v_unverified>0 then
    v_next_action:='verify_affiliate_program_and_tracking_then_rerun_merchant360';
  elsif v_eligible=0 then
    v_next_action:='review_merchant360_evidence_without_weakening_gates';
  elsif v_problems=0 then
    v_next_action:='research_problem_demand';
  elsif v_problem_assessments=0 then
    v_next_action:='score_problem_demand';
  elsif v_problem_fits=0 then
    v_next_action:='build_merchant_problem_fit';
  elsif v_offers=0 then
    v_next_action:='ingest_products_for_eligible_merchants';
  elsif v_funnel=0 then
    v_next_action:='evaluate_product_selection_funnel';
  elsif v_selected=0 then
    v_next_action:='run_product_ai_critic';
  elsif v_semantic_current=0 then
    v_next_action:='refresh_semantic_memory';
  elsif v_semantic_pending>0 then
    v_next_action:='embed_semantic_memory';
  elsif v_presentations=0 then
    v_next_action:='generate_social_presentations';
  elsif v_outbox_open=0 then
    v_next_action:='refill_social_publishing_outbox';
  elsif v_feedback=0 then
    v_next_action:='collect_conversion_feedback';
  else
    v_next_action:='operate_and_learn';
  end if;

  v_pipeline_status := case
    when v_merchants=0 then 'empty'
    when v_eligible=0 then 'blocked_by_gate'
    when v_selected=0 then 'building'
    when v_presentations=0 then 'building'
    else 'operational'
  end;

  return jsonb_build_object(
    'ok',true,
    'database','vmdb',
    'backend_version',18,
    'backend_status','operational',
    'pipeline_status',v_pipeline_status,
    'fail_closed',true,
    'next_action',v_next_action,
    'counts',jsonb_build_object(
      'active_merchants',v_merchants,
      'merchant360_assessed',v_assessed,
      'merchant360_ranked',v_ranked,
      'merchant_program_or_tracking_unverified',v_unverified,
      'eligible_merchants',v_eligible,
      'problem_clusters',v_problems,
      'problem_demand_assessed',v_problem_assessments,
      'merchant_problem_fits',v_problem_fits,
      'eligible_product_offers',v_offers,
      'product_funnel_rows',v_funnel,
      'selected_products',v_selected,
      'semantic_documents_current',v_semantic_current,
      'semantic_embeddings_pending',v_semantic_pending,
      'semantic_embeddings_ready',v_semantic_ready,
      'approved_social_presentations',v_presentations,
      'publishing_jobs_open',v_outbox_open,
      'performance_feedback_events',v_feedback,
      'agent_tool_tasks_open',v_tool_tasks_open
    )
  );
end;
$$;

revoke all on function public.vmdb_refresh_semantic_memory(text) from public, anon, authenticated;
revoke all on function public.vmdb_semantic_embedding_claim(text,integer,integer,text) from public, anon, authenticated;
revoke all on function public.vmdb_semantic_embedding_ack(uuid,text,text,text,text) from public, anon, authenticated;
revoke all on function public.vmdb_semantic_search(text,text,text,integer,text[]) from public, anon, authenticated;
revoke all on function public.vmdb_ai_backend_health() from public, anon, authenticated;

grant execute on function public.vmdb_refresh_semantic_memory(text) to service_role;
grant execute on function public.vmdb_semantic_embedding_claim(text,integer,integer,text) to service_role;
grant execute on function public.vmdb_semantic_embedding_ack(uuid,text,text,text,text) to service_role;
grant execute on function public.vmdb_semantic_search(text,text,text,integer,text[]) to service_role;
grant execute on function public.vmdb_ai_backend_health() to service_role;
