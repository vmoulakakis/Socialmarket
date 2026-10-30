-- SocialMarket GraphRAG v1.1 — real multilingual vector + Greek FTS + SQL RRF, isolated.
-- E5-small multilingual (384 dimensions), model provenance prevents mixing with 1536-dimensional legacy vectors.
create table if not exists sm_intel.search_documents (
 id uuid primary key default gen_random_uuid(),
 tenant_key text not null default 'socialmarket' check (tenant_key='socialmarket'),
 market_code text not null default 'GR' check (market_code='GR'),
 entity_type text not null check (entity_type in ('product','problem','merchant','evidence')),
 entity_pk text not null,
 source_table text not null,
 title text not null,
 content text not null,
 source_state text not null default 'candidate'
  check (source_state in ('candidate','identified','verified','quarantined','removed','stale')),
 metadata jsonb not null default '{}'::jsonb,
 content_sha256 text not null check (length(content_sha256)=64),
 embedding extensions.vector(384),
 embedding_model text,
 embedding_status text not null default 'pending'
  check (embedding_status in ('pending','processing','ready','failed','stale')),
 embedding_attempts integer not null default 0 check (embedding_attempts>=0),
 embedding_error text,
 claimed_by text,
 claimed_at timestamptz,
 embedded_at timestamptz,
 synced_at timestamptz not null default now(),
 fts tsvector generated always as (
  to_tsvector('simple'::regconfig,coalesce(title,'')||' '||coalesce(content,''))
 ) stored,
 unique(tenant_key,source_table,entity_pk),
 check(embedding_status <> 'ready' or (embedding is not null and embedding_model is not null)),
 check(embedding is null or embedding_model='intfloat/multilingual-e5-small')
);
create index if not exists sm_docs_fts_idx on sm_intel.search_documents using gin(fts);
create index if not exists sm_docs_title_trgm_idx on sm_intel.search_documents using gin(lower(title) extensions.gin_trgm_ops);
create index if not exists sm_docs_vec_idx on sm_intel.search_documents using hnsw(embedding extensions.vector_cosine_ops) where embedding is not null and embedding_status='ready';
create index if not exists sm_docs_queue_idx on sm_intel.search_documents(embedding_status,claimed_at,synced_at) where embedding_status in ('pending','processing','failed','stale');
create index if not exists sm_docs_entity_idx on sm_intel.search_documents(entity_type,entity_pk);

create or replace function sm_intel.sync_search_documents()
returns jsonb language plpgsql security invoker set search_path='' as $$
declare products integer:=0; problems integer:=0; merchants integer:=0; evidence integer:=0;
begin
 with input as (
  select r.id::text entity_pk,'sm_intel.raw_products' source_table,'product' entity_type,
   coalesce(nullif(r.product_title,''),r.source_product_id,r.record_key) title,
   left(concat_ws(' ',r.product_title,r.category_raw,
    nullif(r.raw_json->>'description',''),r.raw_json->>'brand_name',
    r.raw_json->>'model_name',r.raw_json->>'size',r.raw_json->>'colour'),1600) content,
   r.source_state source_state,
   jsonb_build_object('program_id',r.program_id,'source_product_id',r.source_product_id,
    'source_key',r.source_key,'stock_available',r.stock_available,
    'price_eur',r.price,'source_updated_at',r.last_seen_at) metadata
  from sm_intel.raw_products r where r.source_key='linkwise_cd104'
 ), upsert as (
  insert into sm_intel.search_documents(entity_pk,source_table,entity_type,title,content,source_state,metadata,content_sha256)
  select entity_pk,source_table,entity_type,title,content,source_state,metadata,
    encode(sha256(convert_to(concat_ws('|',title,content),'UTF8')),'hex')
  from input
  on conflict(tenant_key,source_table,entity_pk) do update
    set title=excluded.title,content=excluded.content,
     source_state=excluded.source_state,metadata=excluded.metadata,
     embedding=case when sm_intel.search_documents.content_sha256<>excluded.content_sha256 then null else sm_intel.search_documents.embedding end,
     embedding_status=case when sm_intel.search_documents.content_sha256<>excluded.content_sha256 then 'pending' else sm_intel.search_documents.embedding_status end,
     embedding_model=case when sm_intel.search_documents.content_sha256<>excluded.content_sha256 then null else sm_intel.search_documents.embedding_model end,
     content_sha256=excluded.content_sha256,synced_at=now()
  returning 1
 ) select count(*) into products from upsert;

 with input as (
  select p.id::text entity_pk,'public.market_problem_clusters' source_table,'problem' entity_type,
    p.problem_title title,
    left(concat_ws(' ',p.problem_title,p.problem_description,p.category,p.subcategory,p.target_customer),1600) content,
    case when p.status='verified' then 'verified' else 'candidate' end source_state,
    jsonb_build_object('problem_key',p.problem_key,'category',p.category,'confidence',p.confidence) metadata
  from public.market_problem_clusters p where p.market_code='GR'
 ), upsert as (
  insert into sm_intel.search_documents(entity_pk,source_table,entity_type,title,content,source_state,metadata,content_sha256)
  select entity_pk,source_table,entity_type,title,content,source_state,metadata,
   encode(sha256(convert_to(concat_ws('|',title,content),'UTF8')),'hex') from input
  on conflict(tenant_key,source_table,entity_pk) do update
   set title=excluded.title,content=excluded.content,source_state=excluded.source_state,
    metadata=excluded.metadata,
    embedding=case when sm_intel.search_documents.content_sha256<>excluded.content_sha256 then null else sm_intel.search_documents.embedding end,
    embedding_status=case when sm_intel.search_documents.content_sha256<>excluded.content_sha256 then 'pending' else sm_intel.search_documents.embedding_status end,
    embedding_model=case when sm_intel.search_documents.content_sha256<>excluded.content_sha256 then null else sm_intel.search_documents.embedding_model end,
    content_sha256=excluded.content_sha256,synced_at=now()
  returning 1
 ) select count(*) into problems from upsert;

 with input as (
  select m.id::text entity_pk,'public.merchant_profiles' source_table,'merchant' entity_type,
   m.merchant_name title,
   left(concat_ws(' ',m.merchant_name,m.primary_category,m.primary_subcategory,m.canonical_domain),1600) content,
   'candidate' source_state,
   jsonb_build_object('merchant_id',m.id,'legacy_approved',m.program_approved,'legacy_tracking_verified',m.tracking_verified) metadata
  from public.merchant_profiles m
 ), upsert as (
  insert into sm_intel.search_documents(entity_pk,source_table,entity_type,title,content,source_state,metadata,content_sha256)
  select entity_pk,source_table,entity_type,title,content,source_state,metadata,
   encode(sha256(convert_to(concat_ws('|',title,content),'UTF8')),'hex') from input
  on conflict(tenant_key,source_table,entity_pk) do update
   set title=excluded.title,content=excluded.content,source_state=excluded.source_state,
    metadata=excluded.metadata,
    embedding=case when sm_intel.search_documents.content_sha256<>excluded.content_sha256 then null else sm_intel.search_documents.embedding end,
    embedding_status=case when sm_intel.search_documents.content_sha256<>excluded.content_sha256 then 'pending' else sm_intel.search_documents.embedding_status end,
    embedding_model=case when sm_intel.search_documents.content_sha256<>excluded.content_sha256 then null else sm_intel.search_documents.embedding_model end,
    content_sha256=excluded.content_sha256,synced_at=now()
  returning 1
 ) select count(*) into merchants from upsert;

 with input as (
  select e.id::text entity_pk,'sm_intel.research_evidence' source_table,'evidence' entity_type,
    e.signal_kind||' — '||e.source_family title,
    left(concat_ws(' ',e.signal_kind,e.source_family,e.signal_value->>'title',e.signal_value->>'snippet'),1600) content,
    case when e.audit_status='verified' then 'verified' else 'candidate' end source_state,
    jsonb_build_object('source_family',e.source_family,'source_url',e.source_url,
     'problem_cluster_id',e.problem_cluster_id,'observed_at',e.observed_at,
     'confidence',e.confidence) metadata
  from sm_intel.research_evidence e
 ), upsert as (
  insert into sm_intel.search_documents(entity_pk,source_table,entity_type,title,content,source_state,metadata,content_sha256)
  select entity_pk,source_table,entity_type,title,content,source_state,metadata,
   encode(sha256(convert_to(concat_ws('|',title,content),'UTF8')),'hex') from input
  on conflict(tenant_key,source_table,entity_pk) do update
   set title=excluded.title,content=excluded.content,source_state=excluded.source_state,
    metadata=excluded.metadata,
    embedding=case when sm_intel.search_documents.content_sha256<>excluded.content_sha256 then null else sm_intel.search_documents.embedding end,
    embedding_status=case when sm_intel.search_documents.content_sha256<>excluded.content_sha256 then 'pending' else sm_intel.search_documents.embedding_status end,
    embedding_model=case when sm_intel.search_documents.content_sha256<>excluded.content_sha256 then null else sm_intel.search_documents.embedding_model end,
    content_sha256=excluded.content_sha256,synced_at=now()
  returning 1
 ) select count(*) into evidence from upsert;

 return jsonb_build_object('products',products,'problems',problems,'merchants',merchants,'evidence',evidence,
  'embedding_model','intfloat/multilingual-e5-small','semantic_dimensions',384);
end $$;

create or replace function sm_intel.claim_embeddings(p_worker text,p_limit integer default 16)
returns table(doc_id uuid,doc_text text,doc_hash text) language sql volatile security invoker set search_path='' as $$
 with picked as (
  select id from sm_intel.search_documents
  where embedding_status in ('pending','failed','stale')
   or (embedding_status='processing' and claimed_at<now()-interval '20 minutes')
  order by case when entity_type='problem' then 0 when entity_type='product' then 1 else 2 end,
      synced_at asc,id
  for update skip locked
  limit greatest(1,least(coalesce(p_limit,16),64))
 ), updated as (
  update sm_intel.search_documents d set embedding_status='processing',
    embedding_attempts=d.embedding_attempts+1,claimed_by=left(p_worker,120),claimed_at=now(),embedding_error=null
  from picked where d.id=picked.id
  returning d.id,d.title,d.content,d.content_sha256
 )
 select id,left(concat_ws(' ',title,content),1200),content_sha256 from updated
$$;
create or replace function sm_intel.ack_embedding(
 p_doc_id uuid,p_worker text,p_content_sha text,p_embedding text,
 p_error text default null
) returns boolean language plpgsql volatile security invoker set search_path='' as $$
declare n integer;
begin
 if p_error is null then
  update sm_intel.search_documents
    set embedding=p_embedding::extensions.vector(384),
      embedding_model='intfloat/multilingual-e5-small',embedding_status='ready',
      embedded_at=now(),claimed_at=null,claimed_by=null,embedding_error=null
  where id=p_doc_id and embedding_status='processing'
    and claimed_by=p_worker and content_sha256=p_content_sha
    and p_embedding is not null;
 else
  update sm_intel.search_documents
  set embedding_status='failed',embedding_error=left(p_error,300),
      claimed_by=null,claimed_at=null
  where id=p_doc_id and embedding_status='processing'
    and claimed_by=p_worker and content_sha256=p_content_sha;
 end if;
 get diagnostics n=row_count;
 return n=1;
end $$;

create or replace function sm_intel.hybrid_retrieve(
 p_query text,p_embedding_text text default null,p_limit integer default 12,
 p_entity_types text[] default null,p_include_candidates boolean default true
) returns table(doc_id uuid,entity_type text,entity_pk text,source_table text,
 title text,content text,source_state text,rrf_score double precision,
 lexical_rank bigint,semantic_rank bigint,graph_node_id uuid,metadata jsonb)
language sql stable security invoker
set search_path='' as $$
 with params as (
  select websearch_to_tsquery('simple',left(trim(p_query),400)) qts,
   lower(left(trim(p_query),400)) qstr,
   case when p_embedding_text is null or p_embedding_text='' then null::extensions.vector(384)
      else p_embedding_text::extensions.vector(384) end qvec
 ),
 lexical as (
  select d.id,row_number() over (
     order by ts_rank_cd(d.fts,p.qts) desc,
              similarity(lower(d.title),p.qstr) desc,d.id) lex_rank
  from sm_intel.search_documents d cross join params p
  where d.tenant_key='socialmarket' and d.market_code='GR'
    and (p_entity_types is null or d.entity_type=any(p_entity_types))
    and (p_include_candidates or d.source_state='verified')
    and d.source_state not in ('removed','quarantined')
    and (d.fts @@ p.qts or similarity(lower(d.title),p.qstr)>0.19
       or lower(d.title) like '%'||p.qstr||'%')
  order by lex_rank limit 80
 ),
 semantic as (
  select d.id,row_number() over (
    order by d.embedding operator(extensions.<=>) p.qvec asc,d.id) sem_rank
  from sm_intel.search_documents d cross join params p
  where p.qvec is not null and d.tenant_key='socialmarket' and d.market_code='GR'
   and d.embedding_status='ready' and d.embedding is not null
   and (p_entity_types is null or d.entity_type=any(p_entity_types))
   and (p_include_candidates or d.source_state='verified')
   and d.source_state not in ('removed','quarantined')
  order by sem_rank limit 80
 ), fusion as (
  select coalesce(l.id,s.id) id,l.lex_rank,s.sem_rank,
   coalesce(1.0/(60+l.lex_rank),0)+coalesce(1.0/(60+s.sem_rank),0) score
  from lexical l full join semantic s on s.id=l.id
 )
 select d.id,d.entity_type,d.entity_pk,d.source_table,d.title,d.content,d.source_state,
    f.score,f.lex_rank,f.sem_rank,g.id,d.metadata
 from fusion f join sm_intel.search_documents d on d.id=f.id
 left join sm_intel.graph_nodes g on g.tenant_key='socialmarket'
  and g.source_table=d.source_table and g.source_pk=d.entity_pk and g.node_type=d.entity_type
 order by f.score desc,d.id
 limit greatest(1,least(coalesce(p_limit,12),30))
$$;

revoke all on table sm_intel.search_documents from public,anon,authenticated;
alter table sm_intel.search_documents enable row level security;
revoke all on function sm_intel.sync_search_documents() from public,anon,authenticated;
revoke all on function sm_intel.claim_embeddings(text,integer) from public,anon,authenticated;
revoke all on function sm_intel.ack_embedding(uuid,text,text,text,text) from public,anon,authenticated;
revoke all on function sm_intel.hybrid_retrieve(text,text,integer,text[],boolean) from public,anon,authenticated;
grant select,insert,update,delete on sm_intel.search_documents to service_role;
grant execute on function sm_intel.sync_search_documents() to service_role;
grant execute on function sm_intel.claim_embeddings(text,integer) to service_role;
grant execute on function sm_intel.ack_embedding(uuid,text,text,text,text) to service_role;
grant execute on function sm_intel.hybrid_retrieve(text,text,integer,text[],boolean) to service_role;
