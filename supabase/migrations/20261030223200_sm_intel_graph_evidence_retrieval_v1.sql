-- SocialMarket GraphRAG v1.0: typed relations, evidence-gated review and bounded 1-2-hop traversal.
create or replace function sm_intel.validate_graph_edge()
returns trigger language plpgsql security invoker set search_path='' as $$
declare src text; dst text;
begin
 select node_type into src from sm_intel.graph_nodes where id=new.source_node_id and tenant_key=new.tenant_key;
 select node_type into dst from sm_intel.graph_nodes where id=new.target_node_id and tenant_key=new.tenant_key;
 if src is null or dst is null then raise exception 'graph_node_missing'; end if;
 if new.relation_type='OFFERED_BY' and (src not in ('product','offer') or dst<>'merchant') then
  raise exception 'invalid_offered_by_node_types';
 end if;
 if new.relation_type='SOLVES' and (src<>'problem' or dst<>'product') then
  raise exception 'invalid_solves_node_types';
 end if;
 if new.relation_type='SUPPORTED_BY' and (src not in ('problem','product','merchant','offer','program') or dst<>'evidence') then
  raise exception 'invalid_supported_by_node_types';
 end if;
 if new.review_status='verified' and not exists (
  select 1 from sm_intel.graph_edge_evidence ee
  where ee.edge_id=new.id and ee.polarity='supports'
 ) then raise exception 'verified_relationship_requires_positive_provenance'; end if;
 return new;
end $$;
drop trigger if exists sm_graph_edge_gate on sm_intel.graph_edges;
create trigger sm_graph_edge_gate before insert or update on sm_intel.graph_edges
 for each row execute function sm_intel.validate_graph_edge();
revoke all on function sm_intel.validate_graph_edge() from public,anon,authenticated;
grant execute on function sm_intel.validate_graph_edge() to service_role;

create or replace function sm_intel.graph_context(
 p_start_node_id uuid,
 p_max_hops integer default 2,
 p_include_candidates boolean default false
) returns table(
 hop integer,edge_id uuid,source_node_id uuid,source_label text,
 relation_type text,target_node_id uuid,target_label text,
 review_status text,evidence_confidence numeric,provenance_count bigint
)
language sql stable security invoker set search_path='' as $$
with recursive walk as (
 select 1 as hop,e.id as edge_id,e.source_node_id,e.target_node_id,e.relation_type,
        e.review_status,e.evidence_confidence,array[p_start_node_id,e.target_node_id]::uuid[] as trail
 from sm_intel.graph_nodes seed
 cross join lateral (
  select g.* from sm_intel.graph_edges g
  where g.tenant_key='socialmarket' and g.source_node_id=seed.id
    and g.review_status=any(case when p_include_candidates then array['verified','candidate']::text[] else array['verified']::text[] end)
    and (g.expires_at is null or g.expires_at>now())
    and (g.review_status<>'verified' or exists (select 1 from sm_intel.graph_edge_evidence z
          where z.edge_id=g.id and z.polarity='supports'))
  order by g.evidence_confidence desc,g.id limit 25
 ) e
 where seed.tenant_key='socialmarket' and seed.id=p_start_node_id
 union all
 select w.hop+1,e.id,e.source_node_id,e.target_node_id,e.relation_type,
        e.review_status,e.evidence_confidence,w.trail||e.target_node_id
 from walk w
 cross join lateral (
  select g.* from sm_intel.graph_edges g
  where g.tenant_key='socialmarket' and g.source_node_id=w.target_node_id
    and g.review_status=any(case when p_include_candidates then array['verified','candidate']::text[] else array['verified']::text[] end)
    and (g.expires_at is null or g.expires_at>now())
    and (g.review_status<>'verified' or exists (select 1 from sm_intel.graph_edge_evidence z
          where z.edge_id=g.id and z.polarity='supports'))
  order by g.evidence_confidence desc,g.id limit 25
 ) e
 where w.hop<least(2,greatest(1,coalesce(p_max_hops,2))) and not e.target_node_id=any(w.trail)
)
select w.hop,w.edge_id,w.source_node_id,s.display_label,w.relation_type,
       w.target_node_id,t.display_label,w.review_status,w.evidence_confidence,
       (select count(*) from sm_intel.graph_edge_evidence z where z.edge_id=w.edge_id)
from walk w join sm_intel.graph_nodes s on s.id=w.source_node_id
            join sm_intel.graph_nodes t on t.id=w.target_node_id
order by w.hop,w.evidence_confidence desc,w.edge_id limit 200;
$$;
revoke all on function sm_intel.graph_context(uuid,integer,boolean) from public,anon,authenticated;
grant execute on function sm_intel.graph_context(uuid,integer,boolean) to service_role;
