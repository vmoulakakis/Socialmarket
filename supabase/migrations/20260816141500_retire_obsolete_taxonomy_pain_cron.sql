do $$
declare j record;
begin
  for j in select jobid from cron.job where active=true and command like '%enqueue_daily_taxonomy_pain_refresh%' loop
    perform cron.unschedule(j.jobid);
  end loop;
end $$;

update ops.collection_jobs
   set status='cancelled',
       completed_at=coalesce(completed_at,now()),
       last_error='superseded_by_semantic_category_pain_v4'
 where status='queued'
   and collection_type in ('pain_discovery','semantic_category_pain','semantic_category_pain_v2');
