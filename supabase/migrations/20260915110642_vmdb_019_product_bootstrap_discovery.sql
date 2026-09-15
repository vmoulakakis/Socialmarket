-- VMDB 019: canonical, fail-closed bootstrap layer for Linkwise product discovery.
-- Staging is intentionally separate from the strict Merchant360 publication gate.

update public.merchant_profiles m
set canonical_domain = v.domain,
    updated_at = now()
from (values
  ('m_3b5f7e49dfc3','24home.gr'),
  ('m_a8a177039642','aegeanair.com'),
  ('m_e5b214f957ed','agnotis.com'),
  ('m_51e6ed24305d','aliexpress.com'),
  ('m_c2254ec0cc2a','all4home.com.gr'),
  ('m_a7a95650ebb4','cilek.gr'),
  ('m_66e4ead8d529','desknet.gr'),
  ('m_cdf28d4b16cd','efdeco.gr'),
  ('m_78b7ed2044c2','ekdromi.gr'),
  ('m_b63a532577f6','hionidis.com'),
  ('m_abb7afb3146c','laredoute.gr'),
  ('m_8b24a450b907','samsonite.gr'),
  ('m_7a92a299081e','starkstores.gr'),
  ('m_c3b9dfc1dfeb','top.host'),
  ('m_77f5e59fa7ac','xenodoxeio.gr'),
  ('m_fa05dfd31b45','yolenis.com')
) as v(legacy_merchant_id,domain)
where m.legacy_merchant_id=v.legacy_merchant_id
  and (m.canonical_domain is null or btrim(m.canonical_domain)='');

insert into public.merchant_selection_policies(
  policy_key,enabled,market_code,min_expected_commission_eur,min_demand_score,
  max_competition_score,min_supply_gap_score,min_problem_solving_score,min_trust_score,
  min_price_value_score,min_greek_fulfilment_score,min_confidence,
  min_confidence_adjusted_score,max_merchants_per_subcategory,weights,notes,
  max_merchants_per_category,min_commercial_intent_score,min_greek_scarcity_score,
  min_evidence_sources,updated_at
) values (
  'linkwise_bootstrap_v1',true,'GR',10,0,100,0,0,0,0,0,0,0,10,
  '{"purpose":"staging_only","hard_gates":["programs_joined","tracking_url","in_stock","commission_eur>=10","max_30_per_merchant"],"paid_ai":false}'::jsonb,
  'Bootstrap discovery only. Does not imply Merchant360 approval or permission to publish. Joined-feed products remain pending until downstream demand/trust/product critic gates pass.',
  10,0,0,0,now()
)
on conflict (policy_key) do update set
  enabled=excluded.enabled,
  min_expected_commission_eur=excluded.min_expected_commission_eur,
  max_merchants_per_subcategory=excluded.max_merchants_per_subcategory,
  max_merchants_per_category=excluded.max_merchants_per_category,
  weights=excluded.weights,
  notes=excluded.notes,
  updated_at=now();

alter table public.commerce_feed_eligible_offers
  add column if not exists merchant_profile_id uuid references public.merchant_profiles(id) on delete cascade,
  add column if not exists merchant_domain text,
  add column if not exists linkwise_route text,
  add column if not exists bootstrap_score numeric;

do $$
begin
  if not exists (
    select 1 from pg_constraint
    where conrelid='public.commerce_feed_eligible_offers'::regclass
      and conname='commerce_feed_bootstrap_score_check'
  ) then
    alter table public.commerce_feed_eligible_offers
      add constraint commerce_feed_bootstrap_score_check
      check (bootstrap_score is null or (bootstrap_score>=0 and bootstrap_score<=100));
  end if;
end $$;

create index if not exists commerce_eligible_merchant_profile_idx
  on public.commerce_feed_eligible_offers(merchant_profile_id,is_active,bootstrap_score desc nulls last);

create unique index if not exists commerce_eligible_merchant_product_uq
  on public.commerce_feed_eligible_offers(source_key,merchant_profile_id,source_product_id)
  where merchant_profile_id is not null;

create or replace view public.merchant_product_bootstrap_eligible
with (security_invoker=true) as
select
  m.id,
  m.legacy_merchant_id,
  m.merchant_name,
  lower(regexp_replace(m.canonical_domain,'^www\\.','','i')) as canonical_domain,
  m.flat_commission_min_eur,
  m.flat_commission_max_eur,
  m.percent_commission_min,
  m.percent_commission_max,
  m.expected_commission_eur,
  m.metadata,
  m.program_approved,
  m.tracking_verified
from public.merchant_profiles m
where m.active
  and nullif(btrim(m.canonical_domain),'') is not null
  and (
    coalesce(m.flat_commission_min_eur,0)>0
    or coalesce(m.percent_commission_min,0)>0
    or coalesce(m.expected_commission_eur,0)>=10
  );

revoke all on public.merchant_product_bootstrap_eligible from public,anon,authenticated;
grant select on public.merchant_product_bootstrap_eligible to service_role;

create or replace function public.vmdb_product_bootstrap_health()
returns jsonb
language sql
stable
security invoker
set search_path=public
as $$
with per_merchant as (
  select merchant_profile_id,count(*) filter (where is_active) as active_count
  from public.commerce_feed_eligible_offers
  where merchant_profile_id is not null
  group by merchant_profile_id
), totals as (
  select
    (select count(*) from public.merchant_product_bootstrap_eligible) as bootstrap_merchants,
    (select count(*) from public.commerce_feed_eligible_offers where is_active) as active_offers,
    (select count(*) from public.merchant_product_candidates where admission_status='pending') as pending_candidates,
    coalesce((select max(active_count) from per_merchant),0) as max_active_per_merchant,
    (select count(*) from per_merchant where active_count>30) as cap_violations
)
select jsonb_build_object(
  'ok',cap_violations=0,
  'database','vmdb',
  'contract','linkwise-bootstrap-v1',
  'min_commission_eur',10,
  'max_active_products_per_merchant',30,
  'bootstrap_merchants',bootstrap_merchants,
  'active_offers',active_offers,
  'pending_candidates',pending_candidates,
  'max_active_per_merchant',max_active_per_merchant,
  'cap_violations',cap_violations,
  'publish_ready',false
) from totals;
$$;

revoke all on function public.vmdb_product_bootstrap_health() from public,anon,authenticated;
grant execute on function public.vmdb_product_bootstrap_health() to service_role;
