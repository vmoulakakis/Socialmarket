-- SocialMarket AI 3.0: keep network identity separate from merchant identity and approval.
create table if not exists sm_intel.affiliate_network_programs_v3 (
 id uuid primary key default gen_random_uuid(),
 network text not null check(network in ('awin','linkwise')),
 publisher_key text not null,
 network_program_id text not null,
 program_name text not null,
 country_code text not null default 'GR',
 relationship text not null check(relationship in ('joined','pending','rejected','notjoined','suspended','unknown')),
 network_status text,
 link_status text,
 program_url text,
 active_for_publisher boolean not null default false,
 terms_evidence jsonb not null default '{}'::jsonb,
 source_metadata jsonb not null default '{}'::jsonb,
 observed_at timestamptz not null default now(),
 verified_by_network boolean not null default false,
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now(),
 unique(network,publisher_key,network_program_id),
 check (active_for_publisher is false or (relationship='joined' and verified_by_network is true))
);
create index if not exists sm_v3_affiliate_network_approval
  on sm_intel.affiliate_network_programs_v3(network,relationship,observed_at desc);

create or replace view sm_intel.affiliate_network_coverage_v3
 with (security_invoker=true) as
select network,publisher_key,count(*) program_records,
 count(*) filter(where relationship='joined') joined_programs,
 count(*) filter(where relationship='pending') pending_programs,
 count(*) filter(where active_for_publisher) active_and_verified,
 max(observed_at) last_observed
from sm_intel.affiliate_network_programs_v3
group by network,publisher_key;

alter table sm_intel.affiliate_network_programs_v3 enable row level security;
revoke all on sm_intel.affiliate_network_programs_v3 from public,anon,authenticated;
revoke all on sm_intel.affiliate_network_coverage_v3 from public,anon,authenticated;
grant select,insert,update on sm_intel.affiliate_network_programs_v3 to service_role;
grant select on sm_intel.affiliate_network_coverage_v3 to service_role;
