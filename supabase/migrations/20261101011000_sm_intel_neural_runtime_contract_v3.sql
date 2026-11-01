-- SocialMarket AI 3.0 P1 neural execution contract. No model compute is started by this migration.
create table if not exists sm_intel.neural_model_registry_v3(
 model_id text primary key,
 task_kind text not null check(task_kind in ('embedding','reranking','classification','forecasting')),
 vector_dimensions integer,
 runtime text not null default 'cpu',
 model_revision text,
 status text not null default 'needs_benchmark'
   check(status in ('needs_benchmark','benchmarked','approved','retired')),
 benchmark_results jsonb not null default '{}'::jsonb,
 reviewed_by text,
 reviewed_at timestamptz,
 created_at timestamptz not null default now(),
 check(status<>'approved' or (reviewed_by is not null and reviewed_at is not null
  and benchmark_results ? 'evaluation_dataset_version'))
);
alter table sm_intel.neural_model_registry_v3 enable row level security;
revoke all on sm_intel.neural_model_registry_v3 from public,anon,authenticated;
grant select,insert,update on sm_intel.neural_model_registry_v3 to service_role;
insert into sm_intel.neural_model_registry_v3(model_id,task_kind,vector_dimensions,runtime)
values
 ('intfloat/multilingual-e5-small','embedding',384,'cpu'),
 ('BAAI/bge-m3','embedding',1024,'benchmark_only'),
 ('BAAI/bge-reranker-v2-m3','reranking',null,'benchmark_only')
on conflict(model_id) do nothing;

-- Avoid infinite failure loops: no more than 3 automatic attempts per document.
-- Real worker must use this lease/ACK contract and must not silently set ready on errors.
create or replace function sm_intel.claim_embeddings(p_worker text,p_limit integer default 16)
returns table(doc_id uuid,doc_text text,doc_hash text)
language sql volatile security invoker set search_path='' as $$
with picked as (
 select id from sm_intel.search_documents
 where embedding_attempts < 3
   and (embedding_status in ('pending','failed','stale')
        or (embedding_status='processing' and claimed_at<now()-interval '20 minutes'))
 order by case when entity_type='problem' then 0 when entity_type='product' then 1 else 2 end,
          synced_at asc,id
 for update skip locked
 limit greatest(1,least(coalesce(p_limit,16),32))
), updated as (
 update sm_intel.search_documents d
 set embedding_status='processing',embedding_attempts=d.embedding_attempts+1,
 claimed_by=left(p_worker,120),claimed_at=now(),embedding_error=null
 from picked where d.id=picked.id
 returning d.id,d.title,d.content,d.content_sha256
)
select id,left(concat_ws(' ',title,content),1200),content_sha256 from updated;
$$;
revoke all on function sm_intel.claim_embeddings(text,integer) from public,anon,authenticated;
grant execute on function sm_intel.claim_embeddings(text,integer) to service_role;

create or replace function sm_intel.embedding_health_v3()
returns jsonb language sql stable security invoker set search_path='' as $$
select jsonb_build_object(
 'model','intfloat/multilingual-e5-small','expected_dimensions',384,
 'total_docs',count(*),
 'pending',count(*) filter(where embedding_status='pending'),
 'processing',count(*) filter(where embedding_status='processing'),
 'ready',count(*) filter(where embedding_status='ready' and embedding is not null),
 'failed',count(*) filter(where embedding_status='failed'),
 'needs_manual_review',count(*) filter(where embedding_status='failed' and embedding_attempts>=3),
 'stale_claims',count(*) filter(where embedding_status='processing' and claimed_at<now()-interval '20 minutes'),
 'local_worker_required',true,
 'production_neural_available',(count(*) filter(where embedding_status='ready')>0),
 'provider_cost_policy','no_paid_model_calls_without_explicit_budget'
)
from sm_intel.search_documents;
$$;
revoke all on function sm_intel.embedding_health_v3() from public,anon,authenticated;
grant execute on function sm_intel.embedding_health_v3() to service_role;
