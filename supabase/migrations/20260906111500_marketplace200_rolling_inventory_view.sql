create or replace view public.socialmarket_marketplace200_admin_v as
with versions as (
  select i.*, r.run_date, r.completed_at as run_completed_at,
    coalesce(p.passed_to_socialscheduler,false) as passed_to_socialscheduler,
    coalesce(p.claimed_by_socialscheduler,false) as claimed_by_socialscheduler,
    coalesce(p.scheduled_in_provider,false) as scheduled_in_provider,
    coalesce(p.published,false) as published,
    coalesce(p.published_platforms,array[]::text[]) as published_platforms,
    coalesce(p.provider_post_ids,array[]::text[]) as provider_post_ids,
    p.last_claimed_at,p.last_published_at,
    row_number() over(partition by i.source_record_hash order by r.completed_at desc nulls last,i.created_at desc,i.id desc) as version_rn
  from intel.marketplace200_items i
  join intel.marketplace200_runs r on r.id=i.run_id and r.status in ('completed','partial')
  left join public.socialmarket_top100_publication_state_v p on p.source_record_hash=i.source_record_hash
  where i.quality_decision='SELECTED' and i.skeptic_verdict='validated'
), latest as (
  select * from versions where version_rn=1 and not published
), merchant_capped as (
  select l.*,
    row_number() over(
      partition by l.portfolio,coalesce(l.merchant_id::text,l.merchant_name,'unknown')
      order by l.affinity_score desc nulls last,l.product_quality_score desc nulls last,l.demand_score desc nulls last,l.created_at desc
    ) as merchant_slot
  from latest l
), portfolio_capped as (
  select m.*,
    row_number() over(
      partition by m.portfolio
      order by m.affinity_score desc nulls last,m.product_quality_score desc nulls last,m.demand_score desc nulls last,m.created_at desc
    ) as portfolio_slot
  from merchant_capped m
  where m.merchant_slot<=3
)
select
  i.id,i.run_id,i.portfolio,i.source_record_hash,i.source_product_id,i.source_network,
  i.semantic_cluster_key,i.niche,i.subniche,i.job_to_be_done,i.pain_statement,i.gap_statement,i.solution_statement,
  i.merchant_id,i.merchant_name,i.merchant_global_rank,i.merchant_trust_score,i.merchant_research_confidence,i.seller_quality_score,
  i.product_name,i.brand_name,i.image_url,i.tracking_url,i.detail_url,i.sale_price_eur,i.expected_commission_eur,
  i.demand_score,i.pain_score,i.whitespace_score,i.scarcity_score,i.semantic_fit_score,i.product_quality_score,
  i.organic_score,i.ads_score,i.viral_score,i.affinity_score,i.greek_availability,i.quality_decision,i.skeptic_verdict,
  i.evidence_summary,i.semantic_tags,i.social_copy,i.landing_candidate,i.handed_off_at,i.created_at,
  i.run_date,i.run_completed_at,i.passed_to_socialscheduler,i.claimed_by_socialscheduler,i.scheduled_in_provider,i.published,
  i.published_platforms,i.provider_post_ids,i.last_claimed_at,i.last_published_at,
  case when i.published then 'PUBLISHED'
       when i.scheduled_in_provider then 'PROVIDER_SCHEDULED'
       when i.claimed_by_socialscheduler then 'CLAIMED'
       when i.passed_to_socialscheduler then 'SOCIALSCHEDULER'
       when i.handed_off_at is not null then 'CONTENT_READY'
       else 'SELECTED' end as lifecycle_state
from portfolio_capped i
where i.portfolio_slot<=100;
