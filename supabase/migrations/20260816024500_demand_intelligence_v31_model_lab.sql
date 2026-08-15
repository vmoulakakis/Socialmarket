create table if not exists intel.demand_model_lab_runs (
  id uuid primary key default gen_random_uuid(),
  taxonomy_id uuid not null references catalog.taxonomy_nodes(id) on delete cascade,
  geography text not null default 'GR',
  engine_version text not null default 'deep_demand_v31',
  status text not null default 'completed' check(status in ('completed','withheld','failed')),
  source_market_observed_at timestamptz,
  generated_at timestamptz not null default now(),
  analysis jsonb not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists demand_model_lab_runs_taxonomy_generated_idx on intel.demand_model_lab_runs(taxonomy_id,generated_at desc);
alter table intel.demand_model_lab_runs enable row level security;
revoke all on table intel.demand_model_lab_runs from anon, authenticated;
create or replace function public.admin_latest_demand_model_lab_v31(p_taxonomy_id uuid)
returns jsonb language plpgsql security definer set search_path='' as $$declare out_json jsonb; begin
 if not public.socialmarket_is_admin() then raise exception 'admin_only'; end if;
 select jsonb_build_object('id',x.id,'taxonomy_id',x.taxonomy_id,'engine_version',x.engine_version,'status',x.status,'source_market_observed_at',x.source_market_observed_at,'generated_at',x.generated_at,'analysis',x.analysis,'metadata',x.metadata) into out_json
 from intel.demand_model_lab_runs x where x.taxonomy_id=p_taxonomy_id and x.geography='GR' order by x.generated_at desc limit 1;
 return out_json; end; $$;
revoke all on function public.admin_latest_demand_model_lab_v31(uuid) from public;
grant execute on function public.admin_latest_demand_model_lab_v31(uuid) to authenticated;
create or replace function public.admin_demand_model_lab_status_v31()
returns jsonb language plpgsql security definer set search_path='' as $$begin
 if not public.socialmarket_is_admin() then raise exception 'admin_only'; end if;
 return jsonb_build_object('engine_version','deep_demand_v31','runs',(select count(*) from intel.demand_model_lab_runs where geography='GR'),'taxonomies',(select count(distinct taxonomy_id) from intel.demand_model_lab_runs where geography='GR'),'completed',(select count(*) from intel.demand_model_lab_runs where geography='GR' and status='completed'),'withheld',(select count(*) from intel.demand_model_lab_runs where geography='GR' and status='withheld'),'failed',(select count(*) from intel.demand_model_lab_runs where geography='GR' and status='failed'),'latest_generated_at',(select max(generated_at) from intel.demand_model_lab_runs where geography='GR')); end; $$;
revoke all on function public.admin_demand_model_lab_status_v31() from public;
grant execute on function public.admin_demand_model_lab_status_v31() to authenticated;
