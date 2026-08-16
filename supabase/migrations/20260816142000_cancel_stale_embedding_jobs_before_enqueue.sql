create or replace function ops.enqueue_generic_embedding_jobs(p_entity_type text default null, p_limit integer default 500)
returns integer
language plpgsql
security definer
set search_path to ''
as $function$
declare n integer;
begin
  update ops.collection_jobs j
     set status='cancelled',
         completed_at=coalesce(j.completed_at,now()),
         last_error='cluster_no_longer_validated'
    from evidence.semantic_clusters c
   where j.collection_type='semantic_embedding'
     and j.status='queued'
     and j.entity_id=c.id
     and c.validation_status is distinct from 'validated';

  with candidates as (
    select c.id, c.entity_type
    from evidence.semantic_clusters c
    where c.validation_status='validated'
      and c.embedding_status in ('pending','stale','failed')
      and (p_entity_type is null or c.entity_type=p_entity_type)
    order by c.audit_score desc nulls last, c.updated_at desc
    limit greatest(1,least(coalesce(p_limit,500),2000))
  ), ins as (
    insert into ops.collection_jobs(entity_type,entity_id,collection_type,status,priority,reason,dedupe_key,payload)
    select entity_type,id,'semantic_embedding','queued',80,'validated_semantic_cluster',
           'semantic_embedding:'||id::text||':'||md5(coalesce((select canonical_text from evidence.semantic_clusters x where x.id=candidates.id),'')),
           jsonb_build_object('cluster_id',id)
    from candidates
    on conflict(dedupe_key) do update set
      status=case when ops.collection_jobs.status in ('completed','cancelled') then 'queued' else ops.collection_jobs.status end,
      requested_at=case when ops.collection_jobs.status in ('completed','cancelled') then now() else ops.collection_jobs.requested_at end,
      not_before=case when ops.collection_jobs.status in ('completed','cancelled') then now() else ops.collection_jobs.not_before end
    returning 1
  ) select count(*) into n from ins;
  return coalesce(n,0);
end $function$;

select ops.enqueue_generic_embedding_jobs(null,500);
