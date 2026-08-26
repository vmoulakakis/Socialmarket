-- Keep the internal publication ledger private and make v10 refill automation
-- fail closed without turning an expected quality-gate hold into a failed cron.

alter table publish.outbox enable row level security;
alter table publish.delivery_history enable row level security;

comment on table publish.outbox is
  'Internal publishing queue. RLS enabled; accessed only by privileged backend workers.';
comment on table publish.delivery_history is
  'Internal publication history. RLS enabled; accessed only by privileged backend workers.';

create or replace function public.worker_v10_poster_outbox_refill_safe(
  p_hours integer default 72,
  p_dry_run boolean default false
) returns jsonb
language plpgsql
security definer
set search_path = ''
as $function$
begin
  return public.worker_v10_poster_outbox_refill(p_hours, p_dry_run);
exception
  when raise_exception then
    if sqlerrm = 'v10_no_completed_batch'
       or sqlerrm like 'v10_hard_gate_closed:%' then
      return jsonb_build_object(
        'ok', true,
        'skipped', true,
        'reason', split_part(sqlerrm, ':', 1),
        'checked_at', clock_timestamp()
      );
    end if;
    raise;
end
$function$;

revoke all on function public.worker_v10_poster_outbox_refill_safe(integer, boolean) from public;
grant execute on function public.worker_v10_poster_outbox_refill_safe(integer, boolean) to service_role;

do $migration$
declare
  v_job_id bigint;
begin
  select jobid into v_job_id
  from cron.job
  where jobname = 'socialscheduler-outbox-refill';

  if v_job_id is not null then
    perform cron.alter_job(
      job_id := v_job_id,
      command := 'select public.worker_v10_poster_outbox_refill_safe(72,false);',
      active := true
    );
  end if;

  select jobid into v_job_id
  from cron.job
  where jobname = 'socialscheduler-morning-horizon-refill';

  if v_job_id is not null then
    perform cron.alter_job(
      job_id := v_job_id,
      command := 'select public.worker_v10_poster_outbox_refill_safe(168,false); select public.socialscheduler_rebalance_frequency_v6(168);',
      active := true
    );
  end if;
end
$migration$;
