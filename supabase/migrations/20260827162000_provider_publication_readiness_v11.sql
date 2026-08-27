-- Provider connectivity is necessary but not sufficient for production routing.
-- A provider becomes assignment-ready only after recent, reconciled publication
-- evidence exists in the canonical delivery ledger. This prevents scheduled
-- acknowledgements from being treated as successful publication.

create or replace function public.socialscheduler_provider_assignment_ready(
  p_provider text,
  p_platform text
) returns boolean
language sql
stable
set search_path = ''
as $function$
  select public.socialscheduler_provider_available(lower(p_provider), lower(p_platform))
     and exists (
       select 1
       from publish.delivery_history h
       where lower(h.platform) = lower(p_platform)
         and h.delivery_status in ('published', 'sent')
         and h.published_at >= now() - interval '14 days'
         and coalesce(
               h.executor_metadata #>> '{orchestrator,provider_key}',
               h.executor_metadata ->> 'publisher',
               h.executor_metadata ->> 'publisher_executor'
             ) = lower(p_provider)
         and nullif(h.buffer_post_id, '') is not null
     )
$function$;

create or replace function public.socialscheduler_choose_provider(p_platform text)
returns text
language plpgsql
set search_path = ''
as $function$
declare
  v text := lower(p_platform);
  last_provider text;
begin
  -- Buffer is the only provider with observed publication evidence on the
  -- three production commerce channels, so reliability wins over rotation.
  if v in ('facebook', 'instagram', 'tiktok') then
    if public.socialscheduler_provider_assignment_ready('buffer', v) then
      return 'buffer';
    end if;
  elsif v = 'linkedin' then
    select coalesce(
             h.executor_metadata #>> '{orchestrator,provider_key}',
             h.executor_metadata ->> 'publisher',
             h.executor_metadata ->> 'publisher_executor'
           )
      into last_provider
    from publish.delivery_history h
    where lower(h.platform) = 'linkedin'
      and h.delivery_status in ('published', 'sent')
      and h.published_at >= now() - interval '14 days'
    order by h.published_at desc
    limit 1;

    if last_provider = 'postzen'
       and public.socialscheduler_provider_assignment_ready('brightbean', v) then
      return 'brightbean';
    end if;
    if last_provider = 'brightbean'
       and public.socialscheduler_provider_assignment_ready('postzen', v) then
      return 'postzen';
    end if;
    if public.socialscheduler_provider_assignment_ready('brightbean', v) then
      return 'brightbean';
    end if;
    if public.socialscheduler_provider_assignment_ready('postzen', v) then
      return 'postzen';
    end if;
  end if;
  return null;
end
$function$;

create or replace function public.socialscheduler_rebalance_approved_jobs()
returns jsonb
language plpgsql
security definer
set search_path = ''
as $function$
declare n integer := 0;
begin
  with candidates as (
    select o.id, public.socialscheduler_choose_provider(o.platform) provider_key
    from publish.outbox o
    where o.status = 'approved'
  ), updated as (
    update publish.outbox o
       set executor_metadata = coalesce(o.executor_metadata, '{}'::jsonb)
           || jsonb_build_object(
                'orchestrator',
                coalesce(o.executor_metadata->'orchestrator', '{}'::jsonb)
                || jsonb_build_object(
                     'provider_key', coalesce(c.provider_key, 'hold'),
                     'assigned_at', now(),
                     'policy', 'verified-publication-readiness-v11',
                     'hold_reason', case when c.provider_key is null
                                         then 'no_recent_verified_publication'
                                         else null end
                   )
              ),
           updated_at = now()
      from candidates c
     where o.id = c.id
       and coalesce(o.executor_metadata #>> '{orchestrator,provider_key}', '')
           is distinct from coalesce(c.provider_key, 'hold')
    returning o.id
  )
  select count(*) into n from updated;
  return jsonb_build_object(
    'rebalanced', n,
    'policy', 'verified-publication-readiness-v11',
    'at', now()
  );
end
$function$;

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
  where h.delivery_status = 'scheduled'
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
  if h.delivery_status <> 'scheduled' then
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
                'policy', 'verified-provider-readback-v11'
              )),
         updated_at = now()
   where id = h.id;

  return jsonb_build_object('ok', true, 'history_id', h.id, 'status', v_status);
end
$function$;

revoke all on function public.socialscheduler_provider_assignment_ready(text,text) from public;
revoke all on function public.socialscheduler_provider_reconcile_candidates(text,integer) from public;
revoke all on function public.worker_v11_delivery_reconcile(jsonb) from public;
revoke execute on function public.socialscheduler_provider_reconcile_candidates(text,integer) from anon, authenticated;
revoke execute on function public.worker_v11_delivery_reconcile(jsonb) from anon, authenticated;
grant execute on function public.socialscheduler_provider_assignment_ready(text,text) to service_role;
grant execute on function public.socialscheduler_provider_reconcile_candidates(text,integer) to service_role;
grant execute on function public.worker_v11_delivery_reconcile(jsonb) to service_role;

