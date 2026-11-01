-- SocialMarket AI 3.0: externally observed, dated CANDIDATE facts.
-- Original sources must be independently audited before they become verified market signals.
-- Re-run safely: inserts only missing source-specific observations.
insert into sm_intel.market_signals_v3 (
 problem_cluster_id,signal_type,metric_name,metric_value,metric_unit,
 qualitative_finding,source_family,source_record_id,source_url,
 independent_source_key,observed_at,expires_at,raw_payload,evidence_status)
values
('0a81d523-73be-4bfd-9ef4-f59dff387a39','supply','search_result_listing_count',
 143,'listed_products','Skroutz lists 143 water leak detectors. Does not imply they suit Airbnb needs.',
 'skroutz','water_leak_detectors_20261101',
 'https://www.skroutz.gr/c/5523/water-leak-detectors.html','skroutz.gr',
 '2026-11-01T20:40:00+00','2026-11-08T20:40:00+00',
 '{"not_product_demand":true,"product_suitability_not_reviewed":true}'::jsonb,'candidate'),
('0a81d523-73be-4bfd-9ef4-f59dff387a39','supply','specific_query_result_count',
 6,'search_results','BestPrice query returns six home automation products; distinct search/filter from Skroutz; do not add the counts.',
 'bestprice','water_sensor_home_automation_20261101',
 'https://www.bestprice.gr/cat/702/home-automation.html?q=%CE%B1%CE%B9%CF%83%CE%B8%CE%B7%CF%84%CE%B7%CF%81%CE%B1%CF%82+%CE%BD%CE%B5%CF%81%CE%BF%CF%85',
 'bestprice.gr','2026-11-01T20:40:00+00','2026-11-08T20:40:00+00',
 '{"not_product_demand":true,"search_filter_differs":true}'::jsonb,'candidate'),
('4d830d64-fa92-4913-bdac-c612311096ce','demand',
 'housing_leak_damp_rot_prevalence_2023',13.5,'percent_population',
 'Greek 2023 housing damp/leak/rot prevalence proxy, not purchase demand for sensors.',
 'eurostat','ilc_mdho01_GR_2023',
 'https://ec.europa.eu/eurostat/databrowser/view/ilc_mdho01%24defaultview/default/table?lang=en',
 'eurostat:ilc_mdho01','2023-12-31T00:00:00+00','2025-01-01T00:00:00+00',
 '{"reference_year":2023,"stale":true,"not_product_demand":true}'::jsonb,'candidate')
on conflict(source_family,source_record_id,signal_type,problem_cluster_id) do nothing;

-- Verified relationship status from connected official Awin account.
-- An active advertiser and online link is NOT a joined/approved publisher.
insert into sm_intel.affiliate_network_programs_v3(
 network,publisher_key,network_program_id,program_name,country_code,relationship,
 network_status,link_status,program_url,active_for_publisher,
 source_metadata,verified_by_network,observed_at)
values('awin','3060863','30859','Back Market GR','GR','pending',
 'Active','online','https://www.backmarket.gr',false,
 '{"source":"Awin publisher programmes","relationship":"pending","not_approved_for_affiliate":true}'::jsonb,
 true,'2026-11-01T20:36:36+00')
on conflict(network,publisher_key,network_program_id) do nothing;
