-- SocialMarket AI: READ-ONLY Linkwise program reconciliation diagnostic
-- Change: CHG-SM-BUYER-20261106
-- NEVER run on a write connection to repair data automatically.
-- A route code proves ONLY the tracking path; it does NOT prove merchant approval.
with offers as (
  select o.source_key,o.source_product_id,o.program_id,o.program_name,
         substring(o.tracking_url from '^https://go[.]linkwi[.]se/z/([0-9]+)-[0-9]+/CD104/') as route_program,
         o.in_stock,o.is_active,o.expected_commission_eur,o.valid_to,o.last_seen_at,
         o.raw_snapshot->>'availability' as availability_text
  from public.commerce_feed_eligible_offers o
  where o.source_key='linkwise'
),
rollup as (
  select coalesce(route_program,'INVALID') as route_program,
         count(*) as source_rows,
         count(*) filter (where program_id='unknown') as unmapped_program_rows,
         count(*) filter (where program_id <> 'unknown' and program_id <> route_program) as conflicting_program_rows,
         count(*) filter (where in_stock=true) as feed_in_stock_true,
         count(*) filter (where in_stock=false) as feed_out_of_stock,
         count(*) filter (where in_stock is null) as feed_stock_unknown,
         count(*) filter (where availability_text is not null) as availability_text_present,
         count(*) filter (where expected_commission_eur>=10) as estimated_commission_at_least_10,
         max(last_seen_at) as latest_import
  from offers group by 1
)
select r.*,c.program_name as commission_program_name,c.imported_at as commission_source_imported_at,
       case when c.linkwise_program_id is null then 'PROGRAM_REFERENCE_MISSING'
            else 'PROGRAM_REFERENCE_PRESENT_NOT_APPROVAL_PROOF' end as program_status
from rollup r
left join public.linkwise_program_commissions c on c.linkwise_program_id=r.route_program
order by source_rows desc;

-- Approval snapshot (do not promote until verified by official program source):
select count(*) as merchant_profiles,
       count(*) filter (where active=true) active_profiles,
       count(*) filter (where program_approved=true) program_approved,
       count(*) filter (where tracking_verified=true) tracking_verified
from public.merchant_profiles;

-- Truthfulness: counts are NOT conversion counts, affiliate approvals, or live inventory.
