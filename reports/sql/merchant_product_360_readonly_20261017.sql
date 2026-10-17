-- SocialMarket / Merchant + Product 360 read-only baseline
-- Verified against public VMDB schema on 2026-10-17.
-- SELECT ONLY: No DDL, writes, cron, link clicks or changes to merchant approval.
-- DATA READINESS = observed field completeness, NOT affiliate network approval,
-- AI merit, purchase likelihood, verified EPC or approved commission.
-- Query 1: all 334 program records, sorted by auditable readiness signals.
WITH inventory AS (
 SELECT program_id,
        COUNT(*) AS offer_count,
        COUNT(*) FILTER (WHERE expected_commission_eur>=20) AS nominal_20_count,
        COUNT(*) FILTER (WHERE in_stock=true) AS in_stock_count,
        MAX(last_seen_at) AS last_feed
 FROM public.commerce_feed_eligible_offers
 WHERE program_id<>'unknown' GROUP BY 1
), profiles AS (
 SELECT lower(trim(merchant_name)) as normalized_name,
        bool_or(program_approved) as approval_flag,
        bool_or(tracking_verified) as tracking_flag
 FROM public.merchant_profiles GROUP BY 1
), merchant360 AS (
 SELECT c.program_name,c.linkwise_program_id,c.actual_http_site,c.percent_commission_min,c.flat_commission_min_eur,
    COALESCE(i.offer_count,0) AS offer_count,
    COALESCE(i.nominal_20_count,0) AS nominal_20_count,
    COALESCE(i.in_stock_count,0) AS in_stock_count,
    i.last_feed,
    COALESCE(p.approval_flag,false) AS approved_recorded,
    COALESCE(p.tracking_flag,false) AS tracking_recorded,
    (CASE WHEN c.linkwise_program_id IS NOT NULL THEN 25 ELSE 0 END
     +CASE WHEN NULLIF(c.actual_http_site,'') IS NOT NULL THEN 10 ELSE 0 END
     +CASE WHEN c.percent_commission_min IS NOT NULL OR c.flat_commission_min_eur IS NOT NULL THEN 10 ELSE 0 END
     +CASE WHEN COALESCE(i.offer_count,0)>0 THEN 20 ELSE 0 END
     +CASE WHEN COALESCE(i.nominal_20_count,0)>0 THEN 10 ELSE 0 END
     +CASE WHEN COALESCE(i.in_stock_count,0)>0 THEN 15 ELSE 0 END
     +CASE WHEN COALESCE(p.approval_flag,false) AND COALESCE(p.tracking_flag,false) THEN 10 ELSE 0 END
    )::int AS data_readiness_100
 FROM public.linkwise_program_commissions c
 LEFT JOIN inventory i ON i.program_id=c.linkwise_program_id
 LEFT JOIN profiles p ON p.normalized_name=lower(trim(c.program_name))
)
SELECT *,
  CASE
    WHEN NOT approved_recorded OR NOT tracking_recorded THEN 'HOLD_APPROVAL_UNCONFIRMED'
    WHEN linkwise_program_id IS NULL THEN 'HOLD_ID_MISSING'
    WHEN in_stock_count=0 THEN 'HOLD_STOCK_UNCONFIRMED'
    WHEN last_feed<now()-interval '7 days' THEN 'HOLD_STALE_FEED'
    ELSE 'NEEDS_OFFICIAL_TERMS_AND_DEEPLINK_VERIFICATION'
  END AS merchant_commercial_status
FROM merchant360
ORDER BY data_readiness_100 DESC, offer_count DESC, program_name;

-- Query 2: ALL imported offers (3,921 at 2026-10-17) with reasons.
-- NO public-approval or commission acceptance can be inferred from this view.
SELECT
  id,source_key,source_product_id,program_id,program_name,sku,model_name,
  product_name,category_raw,price_eur,image_url,tracking_url,
  expected_commission_eur,commission_basis,in_stock,last_seen_at,
  ARRAY_REMOVE(ARRAY[
   CASE WHEN program_id='unknown' THEN 'UNRESOLVED_PROGRAM' END,
   CASE WHEN in_stock IS DISTINCT FROM TRUE THEN 'STOCK_UNCONFIRMED' END,
   CASE WHEN last_seen_at IS NULL OR last_seen_at<now()-interval '7 days' THEN 'STALE_OFFER' END,
   CASE WHEN image_url IS NULL OR image_url NOT LIKE 'https://%' THEN 'IMAGE_HTTPS_REVIEW' END,
   CASE WHEN tracking_url !~ '^https://go[.]linkwi[.]se/z/' THEN 'TRACKING_FORMAT_REVIEW' END,
   CASE WHEN expected_commission_eur<20 OR expected_commission_eur IS NULL THEN 'MODELED_PAYOUT_BELOW_20_OR_UNKNOWN' END,
   'OFFICIAL_LINKWISE_PUBLISHER_APPROVAL_UNVERIFIED',
   'COMMISSION_TERMS_NOT_OFFICIALLY_RECONCILED'
  ],NULL)::text[] AS blocked_reasons,
  (CASE WHEN NULLIF(sku,'') IS NOT NULL THEN 20 ELSE 0 END
   +CASE WHEN program_id<>'unknown' THEN 20 ELSE 0 END
   +CASE WHEN image_url LIKE 'https://%' THEN 10 ELSE 0 END
   +CASE WHEN NULLIF(category_raw,'') IS NOT NULL THEN 10 ELSE 0 END
   +CASE WHEN price_eur>0 THEN 10 ELSE 0 END
   +CASE WHEN last_seen_at>=now()-interval '7 days' THEN 15 ELSE 0 END
   +CASE WHEN in_stock=true THEN 15 ELSE 0 END)::int AS data_readiness_100,
  'HOLD_FOR_VERIFICATION' AS publication_status
FROM public.commerce_feed_eligible_offers
ORDER BY data_readiness_100 DESC,price_eur DESC NULLS LAST;

-- Query 3: Data quality by program, never confuse modeled commission with paid commission.
SELECT
 program_id,COALESCE(program_name,'UNKNOWN') AS program_name,
 COUNT(*) AS offers,
 COUNT(*) FILTER(WHERE in_stock=true) AS stock_verified,
 COUNT(*) FILTER(WHERE in_stock IS NULL) AS stock_unknown,
 COUNT(*) FILTER(WHERE last_seen_at>=now()-interval '7 days') AS refreshed_last_7_days,
 COUNT(*) FILTER(WHERE expected_commission_eur>=20) AS nominal_payout_20,
 COUNT(*) FILTER(WHERE image_url LIKE 'https://%') AS https_images,
 MAX(last_seen_at) AS latest_seen
FROM public.commerce_feed_eligible_offers
GROUP BY program_id,program_name ORDER BY offers DESC;
