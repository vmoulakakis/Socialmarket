-- Preserve truth when provider ACK exists but terminal publication evidence is missing.
-- Applied to production as migration 20260906133324.

create or replace function public.socialscheduler_provider_reconcile_candidates(
  p_provider text,
  p_limit integer default 100
) returns table(
  history_id uuid,
  original_outbox_id uuid,
  platform text,
  scheduled_for timestamptz,
  external_post_id text,
  provider_key text
)
language sql
security definer
set search_path = ''
as $function$
  select h.id, h.original_outbox_id, h.platform, h.scheduled_for,
         h.buffer_post_id,
         coalesce(
           h.executor_metadata #>> '{orchestrator,provider_key}',
           h.executor_metadata ->> 'publisher',
           h.executor_metadata ->> 'publisher_executor'
         )
  from publish.delivery_history h
  where h.delivery_status in ('scheduled','unknown_provider_state')
    and h.scheduled_for < now() - interval '5 minutes'
    and nullif(h.buffer_post_id, '') is not null
    and coalesce(
          h.executor_metadata #>> '{orchestrator,provider_key}',
          h.executor_metadata ->> 'publisher',
          h.executor_metadata ->> 'publisher_executor'
        ) = lower(p_provider)
  order by h.scheduled_for
  limit greatest(1, least(coalesce(p_limit, 100), 500))
$function$;

create or replace function public.worker_v11_delivery_reconcile(p_payload jsonb)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $function$
declare
  h publish.delivery_history%rowtype;
  v_provider text := lower(coalesce(p_payload->>'provider_key', ''));
  v_status text := lower(coalesce(p_payload->>'status', ''));
  v_provider_status text := lower(coalesce(p_payload->>'provider_status', ''));
  v_external_id text := nullif(p_payload->>'external_post_id', '');
  v_published_at timestamptz := nullif(p_payload->>'published_at', '')::timestamptz;
begin
  if v_provider not in ('buffer', 'postzen', 'brightbean') then
    raise exception 'invalid_provider';
  end if;
  if v_status not in ('published', 'failed') then
    raise exception 'invalid_reconciliation_status';
  end if;

  select * into h
  from publish.delivery_history
  where id = (p_payload->>'history_id')::uuid
  for update;
  if not found then raise exception 'delivery_history_not_found'; end if;
  if h.delivery_status not in ('scheduled','unknown_provider_state') then
    return jsonb_build_object('ok', true, 'unchanged', true, 'current_status', h.delivery_status);
  end if;
  if h.buffer_post_id is distinct from v_external_id then
    raise exception 'provider_external_id_mismatch';
  end if;
  if coalesce(
       h.executor_metadata #>> '{orchestrator,provider_key}',
       h.executor_metadata ->> 'publisher',
       h.executor_metadata ->> 'publisher_executor'
     ) is distinct from v_provider then
    raise exception 'provider_identity_mismatch';
  end if;
  if v_status = 'published' then
    if v_provider_status not in ('published', 'sent') or v_published_at is null then
      raise exception 'verified_provider_publication_evidence_required';
    end if;
  end if;

  update publish.delivery_history
     set delivery_status = v_status,
         published_at = case when v_status = 'published' then v_published_at else published_at end,
         external_permalink = coalesce(nullif(p_payload->>'external_permalink', ''), external_permalink),
         executor_metadata = coalesce(executor_metadata, '{}'::jsonb)
           || jsonb_build_object('provider_reconciliation', jsonb_build_object(
                'provider_key', v_provider,
                'provider_status', v_provider_status,
                'external_platform_post_id', nullif(p_payload->>'external_platform_post_id', ''),
                'error', nullif(p_payload->>'error', ''),
                'reconciled_at', now(),
                'policy', 'verified-provider-readback-v12'
              )),
         updated_at = now()
   where id = h.id;

  return jsonb_build_object('ok', true, 'history_id', h.id, 'status', v_status);
end
$function$;

create or replace function public.socialscheduler_mark_overdue_delivery_unknown(
  p_grace_minutes integer default 10,
  p_limit integer default 1000
) returns jsonb
language plpgsql
security definer
set search_path = ''
as $function$
declare
  n integer := 0;
begin
  with picked as (
    select h.id
    from publish.delivery_history h
    where h.delivery_status = 'scheduled'
      and h.scheduled_for < now() - make_interval(mins => greatest(5, least(coalesce(p_grace_minutes,10), 1440)))
    order by h.scheduled_for
    limit greatest(1, least(coalesce(p_limit,1000),5000))
    for update skip locked
  ), changed as (
    update publish.delivery_history h
       set delivery_status = 'unknown_provider_state',
           executor_metadata = coalesce(h.executor_metadata,'{}'::jsonb)
             || jsonb_build_object(
                  'provider_reconciliation',
                  coalesce(h.executor_metadata->'provider_reconciliation','{}'::jsonb)
                  || jsonb_build_object(
                       'provider_status','unconfirmed_overdue',
                       'reconciled_at',now(),
                       'policy','overdue-without-terminal-evidence-v12'
                     )
                ),
           updated_at = now()
      from picked p
     where h.id = p.id
    returning h.id
  )
  select count(*) into n from changed;
  return jsonb_build_object('ok',true,'marked_unknown',n,'grace_minutes',p_grace_minutes,'at',now());
end
$function$;

revoke all on function public.socialscheduler_mark_overdue_delivery_unknown(integer,integer) from public;
grant execute on function public.socialscheduler_mark_overdue_delivery_unknown(integer,integer) to service_role;
