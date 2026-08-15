alter table intel.product_rankings add column if not exists deep_demand_score numeric;
alter table intel.product_rankings add column if not exists deep_demand_status text;
alter table intel.product_rankings add column if not exists deep_demand_context jsonb not null default '{}'::jsonb;
