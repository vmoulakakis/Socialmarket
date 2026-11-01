-- Live operator diagnostic for full Linkwise CD104 import readiness; no inventing terms.
create or replace view sm_intel.linkwise_program_readiness_v4 with (security_invoker=true) as
with source as (
 select r.program_id, count(*)::integer historical_product_count,
 count(*) filter(where r.valid_to>now())::integer currently_unexpired_with_valid_to,
 count(*) filter(where r.valid_to is null)::integer no_valid_to,
 count(*) filter(where r.valid_to is not null and r.valid_to<=now())::integer expired
 from sm_intel.raw_products r where r.source_key='linkwise_cd104'
 group by r.program_id
)
select s.program_id,s.historical_product_count,s.currently_unexpired_with_valid_to,
 s.no_valid_to,s.expired,
 c.program_name,c.review_status as commission_review_status,
 c.rate_type,c.rate_value,c.effective_until,
 (c.id is not null) has_verified_current_terms,
 case when c.id is null then 'blocked_missing_current_verified_terms'
      when s.currently_unexpired_with_valid_to=0 then 'no_current_dated_offers'
      else 'eligible_for_product_level_evaluation' end pipeline_state
from source s
left join lateral (
 select t.id,t.program_name,t.review_status,t.rate_type,t.rate_value,t.effective_until
 from sm_intel.commission_terms t
 where t.program_id=s.program_id and t.publisher_key='CD104'
 and t.review_status='verified' and t.currency='EUR' and t.effective_from<=now()
 and (t.effective_until>now() or (t.effective_until is null and t.evidence->>'explicit_open_ended_verified'='true'))
 order by t.effective_from desc,t.id desc limit 1
) c on true;
revoke all on sm_intel.linkwise_program_readiness_v4 from public,anon,authenticated;
grant select on sm_intel.linkwise_program_readiness_v4 to service_role;
