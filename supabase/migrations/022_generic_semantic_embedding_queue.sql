alter table evidence.semantic_clusters add column if not exists embedding_gte vector(384);
alter table evidence.semantic_clusters add column if not exists embedding_status text not null default 'pending' check (embedding_status in ('pending','processing','ready','failed','stale'));
alter table evidence.semantic_clusters add column if not exists embedded_at timestamptz;

create index if not exists semantic_clusters_embedding_status_idx on evidence.semantic_clusters(embedding_status, validation_status, updated_at);

create or replace function ops.enqueue_generic_embedding_jobs(p_entity_type text default null, p_limit integer default 500)
returns integer language plpgsql security definer set search_path='' as $$
declare n integer;
begin
  with candidates as (
    select c.id,c.entity_type from evidence.semantic_clusters c
    where c.validation_status='validated'
      and c.embedding_status in ('pending','stale','failed')
      and (p_entity_type is null or c.entity_type=p_entity_type)
    order by c.audit_score desc nulls last,c.updated_at desc
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
end $$;

create or replace function ops.claim_generic_embedding_jobs(p_worker text,p_limit integer default 20,p_lease_minutes integer default 20)
returns table(job_id uuid,cluster_id uuid,entity_type text,entity_id uuid,semantic_text text)
language plpgsql security definer set search_path='' as $$
begin
  return query
  with picked as (
    select j.id from ops.collection_jobs j
    join evidence.semantic_clusters c on c.id=j.entity_id
    where j.status='queued' and j.not_before<=now()
      and j.collection_type='semantic_embedding'
      and c.validation_status='validated'
      and c.embedding_status in ('pending','stale','failed')
    order by j.priority desc,j.requested_at
    for update of j skip locked
    limit greatest(1,least(coalesce(p_limit,20),100))
  ), leased as (
    update ops.collection_jobs j set status='running',lease_owner=p_worker,
      lease_expires_at=now()+make_interval(mins=>greatest(5,least(coalesce(p_lease_minutes,20),60))),attempt_count=j.attempt_count+1
    from picked p where j.id=p.id returning j.*
  ), mark as (
    update evidence.semantic_clusters c set embedding_status='processing',updated_at=now()
    from leased l where c.id=l.entity_id returning c.id
  )
  select l.id,c.id,c.entity_type,c.entity_id,
    concat_ws(' | ',c.cluster_type,c.canonical_text,c.category,c.subcategory,
      case when c.demand_score is not null then 'demand '||c.demand_score end,
      case when c.competition_score is not null then 'competition '||c.competition_score end,
      case when c.pain_severity is not null then 'pain severity '||c.pain_severity end)
  from leased l join evidence.semantic_clusters c on c.id=l.entity_id;
end $$;

create or replace function ops.complete_generic_embedding_job(p_job_id uuid,p_embedding text,p_model text default 'gte-small')
returns boolean language plpgsql security definer set search_path='' as $$
declare cid uuid;
begin
  select entity_id into cid from ops.collection_jobs where id=p_job_id and collection_type='semantic_embedding' and status='running';
  if cid is null then raise exception 'generic_embedding_job_not_running'; end if;
  update evidence.semantic_clusters set embedding_gte=p_embedding::extensions.vector,embedding_model=p_model,
    embedding_status='ready',embedded_at=now(),updated_at=now() where id=cid;
  if not found then raise exception 'semantic_cluster_not_found'; end if;
  update ops.collection_jobs set status='completed',completed_at=now(),lease_owner=null,lease_expires_at=null,last_error=null where id=p_job_id;
  return true;
end $$;

create or replace function ops.fail_generic_embedding_job(p_job_id uuid,p_error text)
returns boolean language plpgsql security definer set search_path='' as $$
declare cid uuid; attempts integer;
begin
  select entity_id,attempt_count into cid,attempts from ops.collection_jobs where id=p_job_id and collection_type='semantic_embedding';
  if cid is null then return false; end if;
  update evidence.semantic_clusters set embedding_status=case when coalesce(attempts,0)>=4 then 'failed' else 'pending' end,updated_at=now() where id=cid;
  update ops.collection_jobs set status=case when coalesce(attempts,0)>=4 then 'failed' else 'queued' end,
    not_before=now()+interval '30 minutes',lease_owner=null,lease_expires_at=null,last_error=left(p_error,1200) where id=p_job_id;
  return true;
end $$;

select ops.enqueue_generic_embedding_jobs(null,1000);
