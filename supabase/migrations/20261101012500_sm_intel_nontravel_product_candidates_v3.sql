-- SocialMarket candidate curation: user selected TravelAI separately; avoid travel contaminating SocialMarket solutions.
create or replace function sm_intel.refresh_opportunity_research_v3(p_limit int default 100)
returns jsonb language plpgsql volatile security invoker set search_path='' as $$
declare researched int := 0; matches int := 0;
begin
 if p_limit is null or p_limit<1 or p_limit>100 then raise exception 'limit_out_of_range'; end if;
 with problems as (
  select id,problem_title,category from public.market_problem_clusters
  where market_code='GR' order by id limit p_limit
 ),
 signals as (
  select p.id as problem_id,
  count(e.id) filter(where e.signal_kind='demand' and e.observed_at>now()-interval '90 days' and
       (e.expires_at is null or e.expires_at>now()))::integer as demand_n,
  count(e.id) filter(where e.signal_kind='supply' and e.observed_at>now()-interval '90 days' and
       (e.expires_at is null or e.expires_at>now()))::integer as supply_n,
  count(e.id) filter(where e.signal_kind in ('counter_evidence','competition') and
       e.observed_at>now()-interval '90 days' and (e.expires_at is null or e.expires_at>now()))::integer as counters_n,
  count(e.id) filter(where e.signal_kind='demand' and e.audit_status='verified' and
       e.observed_at>now()-interval '90 days' and (e.expires_at is null or e.expires_at>now()))::integer as verified_d_n,
  count(e.id) filter(where e.signal_kind='supply' and e.audit_status='verified' and
       e.observed_at>now()-interval '90 days' and (e.expires_at is null or e.expires_at>now()))::integer as verified_s_n,
  count(distinct nullif(lower(split_part(e.source_url,'/',3)),'')) filter(
       where e.signal_kind='demand' and e.audit_status='verified' and
       e.observed_at>now()-interval '90 days' and (e.expires_at is null or e.expires_at>now()))::integer as verified_d_domains,
  count(distinct nullif(lower(split_part(e.source_url,'/',3)),'')) filter(
       where e.signal_kind='supply' and e.audit_status='verified' and
       e.observed_at>now()-interval '90 days' and (e.expires_at is null or e.expires_at>now()))::integer as verified_s_domains,
  coalesce(jsonb_agg(jsonb_build_object('id',e.id,'kind',e.signal_kind,
     'status',e.audit_status,'source_url',e.source_url,'observed_at',e.observed_at,
     'confidence',e.confidence) order by e.observed_at desc)
     filter(where e.id is not null),'[]'::jsonb) as audit_snapshot
  from problems p left join sm_intel.research_evidence e on e.problem_cluster_id=p.id
       and e.market_code='GR' and e.region_code='GR'
  group by p.id
 ), proposed as (
 select s.*,
  case when s.verified_d_domains>=2 and s.verified_s_domains>=2
        then 'ready_for_independent_review'
       when s.demand_n>0 or s.supply_n>0 or s.counters_n>0 then 'partial_evidence'
       else 'research_needed' end as next_status,
  (case when s.verified_d_domains<2 then jsonb_build_array('need_two_verified_demand_source_domains')
     else '[]'::jsonb end) ||
  (case when s.verified_s_domains<2 then jsonb_build_array('need_two_verified_supply_source_domains')
     else '[]'::jsonb end) ||
  (case when s.counters_n=0 then jsonb_build_array('need_counterevidence_or_competitor_research')
     else '[]'::jsonb end) as gaps
 from signals s
 ), written as (
  insert into sm_intel.opportunity_research_v3 (
    problem_cluster_id,demand_sources,supply_sources,counter_sources,
    verified_demand_sources,verified_supply_sources,distinct_verified_demand_domains,
    distinct_verified_supply_domains,evidence_status,research_gaps,source_snapshot,assessed_at
  ) select problem_id,demand_n,supply_n,counters_n,verified_d_n,verified_s_n,
           verified_d_domains,verified_s_domains,next_status,gaps,
           jsonb_build_object('observed_90_day_signals',audit_snapshot,
            'review_note','Distinct domains are not proof of source independence',
            'source_policy','Only verified source evidence can unlock independent review'),
           now()
    from proposed
  on conflict(problem_cluster_id,region_code,methodology_version)
  do update set demand_sources=excluded.demand_sources,
    supply_sources=excluded.supply_sources,counter_sources=excluded.counter_sources,
    verified_demand_sources=excluded.verified_demand_sources,
    verified_supply_sources=excluded.verified_supply_sources,
    distinct_verified_demand_domains=excluded.distinct_verified_demand_domains,
    distinct_verified_supply_domains=excluded.distinct_verified_supply_domains,
    evidence_status=excluded.evidence_status,
    research_gaps=excluded.research_gaps,source_snapshot=excluded.source_snapshot,
    assessed_at=now()
  returning id
 )
 select count(*) into researched from written;
 -- Search returns *candidate* product relevance only. Never creates promotion-ready offers.
 with problems as (
  select id,problem_title from public.market_problem_clusters
  where market_code='GR' order by id limit p_limit
 ), retrieved as (
  select p.id problem_id,h.doc_id,h.rrf_score,
   row_number() over(partition by p.id order by h.rrf_score desc,h.doc_id) as rank
  from problems p cross join lateral sm_intel.hybrid_retrieve(
       p.problem_title,null,8,array['product']::text[],true) h
  join sm_intel.search_documents d on d.id=h.doc_id and d.source_table='sm_intel.raw_products'
  join sm_intel.raw_products rp on rp.id=d.entity_pk::uuid
  where h.entity_type='product'
    and coalesce(rp.category_raw,'') !~* '(xenodoxeia|ξενοδοχ|ταξιδ|travel|flight|πτήσ|εκδρομ|holiday|hotel)'
    and coalesce(rp.product_title,'') !~* '(ταξιδ|εκδρομ|πτήσ|διαμονή|holiday|hotel)'
 ), ins as (
  insert into sm_intel.opportunity_product_candidates_v3
     (problem_cluster_id,document_id,retrieval_rank,rrf_score)
  select problem_id,doc_id,rank::integer,rrf_score from retrieved
  on conflict(problem_cluster_id,document_id,retrieval_version)
  do update set retrieval_rank=excluded.retrieval_rank,rrf_score=excluded.rrf_score,
                evaluated_at=now()
  returning 1
 )
 select count(*) into matches from ins;
 return jsonb_build_object('problems_assessed',researched,
    'candidate_matches_scored',matches,
    'promotions_created',0,'market_demand_estimates_created',0,
    'mode','evidence_gated_and_unverified_match_only');
end $$;
update sm_intel.opportunity_product_candidates_v3 c
set relevance_review='rejected',
 evidence_statement='Excluded from SocialMarket scope: travel/hotel/flight product; retained as auditable rejected candidate'
from sm_intel.search_documents d
join sm_intel.raw_products rp on rp.id=d.entity_pk::uuid
where c.document_id=d.id and d.source_table='sm_intel.raw_products'
 and (
  coalesce(rp.category_raw,'') ~* '(xenodoxeia|ξενοδοχ|ταξιδ|travel|flight|πτήσ|εκδρομ|holiday|hotel)'
  or coalesce(rp.product_title,'') ~* '(ταξιδ|εκδρομ|πτήσ|διαμονή|holiday|hotel)'
 );