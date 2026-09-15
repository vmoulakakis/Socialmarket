-- VMDB 017: fail-closed security hardening for canonical commerce data plane.
-- These tables are server-side/service-role pipeline state and must not be directly exposed to anon/authenticated roles.

alter table public.commerce_semantic_documents enable row level security;
alter table public.commerce_entity_taxonomy enable row level security;
alter table public.commerce_taxonomy_nodes enable row level security;
alter table public.commerce_problem_product_matches enable row level security;
alter table public.commerce_forecasts enable row level security;
alter table public.commerce_feed_runs enable row level security;
alter table public.commerce_feed_eligible_offers enable row level security;

revoke all privileges on table public.commerce_semantic_documents from anon, authenticated;
revoke all privileges on table public.commerce_entity_taxonomy from anon, authenticated;
revoke all privileges on table public.commerce_taxonomy_nodes from anon, authenticated;
revoke all privileges on table public.commerce_problem_product_matches from anon, authenticated;
revoke all privileges on table public.commerce_forecasts from anon, authenticated;
revoke all privileges on table public.commerce_feed_runs from anon, authenticated;
revoke all privileges on table public.commerce_feed_eligible_offers from anon, authenticated;

-- Canonical merchant admission view must execute with caller privileges.
alter view public.merchant_product_discovery_eligible set (security_invoker = true);
revoke all privileges on table public.merchant_product_discovery_eligible from anon, authenticated;
grant select on table public.merchant_product_discovery_eligible to service_role;

-- Pin function name resolution to trusted schemas.
alter function public.vmdb_v2_opportunity_score(numeric,numeric,numeric,numeric,numeric,numeric,numeric,numeric,numeric,numeric)
  set search_path = pg_catalog, public;
