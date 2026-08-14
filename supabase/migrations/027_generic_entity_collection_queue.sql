create or replace function ops.enqueue_daily_taxonomy_pain_refresh(p_day date default current_date)
returns integer
language plpgsql
security definer
set search_path=''
as $$
declare n integer;
begin
  insert into ops.collection_jobs(entity_type,entity_id,collection_type,status,priority,reason,requested_at,not_before,dedupe_key,payload)
  select 'taxonomy',t.id,'pain_discovery','queued',90,'daily_greek_market_pain_discovery',now(),now(),
         'taxonomy-pain:'||t.id::text||':'||p_day::text,
         jsonb_build_object('name',t.name,'node_type',t.node_type,'day',p_day,'geography','GR')
  from catalog.taxonomy_nodes t
  where t.active=true and t.node_type in ('category','subcategory','product_type','micro_niche','service_type')
  on conflict(dedupe_key) do nothing;
  get diagnostics n=row_count;
  return n;
end $$;

select ops.enqueue_daily_taxonomy_pain_refresh(current_date);

select cron.unschedule(jobid) from cron.job where jobname='socialmarket-daily-taxonomy-pain-refresh';
select cron.schedule('socialmarket-daily-taxonomy-pain-refresh','45 0 * * *',
  $$select ops.enqueue_daily_taxonomy_pain_refresh(current_date);$$);
