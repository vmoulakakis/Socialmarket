create table if not exists ops.product_intelligence_config (
  id smallint primary key default 1 check (id = 1),
  version integer not null default 1,
  config jsonb not null,
  updated_by text,
  updated_at timestamptz not null default now()
);
alter table ops.product_intelligence_config enable row level security;

create or replace function public.product_intelligence_default_config()
returns jsonb language sql immutable security definer set search_path=''
as $$ select jsonb_build_object(
  'schema_version',1,'profile_name','Balanced','min_expected_commission_eur',10,'min_merchant_trust',30,
  'min_validated_pain_clusters',1,'min_audit_overall',70,'min_pain_fit',60,'min_product_evidence',60,
  'min_pain_evidence_count',1,'min_pain_source_diversity',1,'min_pain_severity',0,'min_commercial_intent',0,
  'min_greek_demand',0,'max_competition',100,'pain_rag_limit',8,'theme_rag_limit',5,'ai_batch',1,
  'ai_max_candidates',4,'ai_offers_per_product',1,'max_ai_batch_failure_rate',0.25,'ai_thinking_mode','auto',
  'preliminary_weights',jsonb_build_object('commission',45,'merchant_whitespace',35,'demand',20),
  'score_weights',jsonb_build_object('pain_gap_fit',25,'merchant_opportunity',20,'greek_demand',15,'commission',12,
    'inverse_competition',10,'seasonal',8,'merchant_trust',5,'discount',3,'evidence_confidence',2)
) $$;
revoke all on function public.product_intelligence_default_config() from public;
grant execute on function public.product_intelligence_default_config() to authenticated;

insert into ops.product_intelligence_config(id,config,updated_by)
values(1,public.product_intelligence_default_config(),'system') on conflict(id) do nothing;

create or replace function public.validate_product_intelligence_config(p jsonb)
returns boolean language plpgsql immutable security definer set search_path=''
as $$ declare sw numeric; pw numeric; begin
  if p is null or jsonb_typeof(p)<>'object' then raise exception 'config_must_be_object'; end if;
  if coalesce((p->>'min_expected_commission_eur')::numeric,-1) not between 10 and 500 then raise exception 'min_expected_commission_eur_out_of_range'; end if;
  if coalesce((p->>'min_merchant_trust')::numeric,-1) not between 0 and 100 then raise exception 'min_merchant_trust_out_of_range'; end if;
  if coalesce((p->>'min_validated_pain_clusters')::numeric,-1) not between 1 and 100 then raise exception 'min_validated_pain_clusters_out_of_range'; end if;
  if coalesce((p->>'min_audit_overall')::numeric,-1) not between 0 and 100 then raise exception 'min_audit_overall_out_of_range'; end if;
  if coalesce((p->>'min_pain_fit')::numeric,-1) not between 0 and 100 then raise exception 'min_pain_fit_out_of_range'; end if;
  if coalesce((p->>'min_product_evidence')::numeric,-1) not between 0 and 100 then raise exception 'min_product_evidence_out_of_range'; end if;
  if coalesce((p->>'min_pain_evidence_count')::numeric,-1) not between 1 and 1000 then raise exception 'min_pain_evidence_count_out_of_range'; end if;
  if coalesce((p->>'min_pain_source_diversity')::numeric,-1) not between 1 and 100 then raise exception 'min_pain_source_diversity_out_of_range'; end if;
  if coalesce((p->>'min_pain_severity')::numeric,-1) not between 0 and 100 then raise exception 'min_pain_severity_out_of_range'; end if;
  if coalesce((p->>'min_commercial_intent')::numeric,-1) not between 0 and 100 then raise exception 'min_commercial_intent_out_of_range'; end if;
  if coalesce((p->>'min_greek_demand')::numeric,-1) not between 0 and 100 then raise exception 'min_greek_demand_out_of_range'; end if;
  if coalesce((p->>'max_competition')::numeric,-1) not between 0 and 100 then raise exception 'max_competition_out_of_range'; end if;
  if coalesce((p->>'pain_rag_limit')::numeric,-1) not between 1 and 20 then raise exception 'pain_rag_limit_out_of_range'; end if;
  if coalesce((p->>'theme_rag_limit')::numeric,-1) not between 0 and 10 then raise exception 'theme_rag_limit_out_of_range'; end if;
  if coalesce((p->>'ai_batch')::numeric,-1) not between 1 and 12 then raise exception 'ai_batch_out_of_range'; end if;
  if coalesce((p->>'ai_max_candidates')::numeric,-1) not between 1 and 500 then raise exception 'ai_max_candidates_out_of_range'; end if;
  if coalesce((p->>'ai_offers_per_product')::numeric,-1) not between 1 and 3 then raise exception 'ai_offers_per_product_out_of_range'; end if;
  if coalesce((p->>'max_ai_batch_failure_rate')::numeric,-1) not between 0 and 1 then raise exception 'max_ai_batch_failure_rate_out_of_range'; end if;
  if coalesce(p->>'ai_thinking_mode','') not in ('auto','on','off') then raise exception 'invalid_ai_thinking_mode'; end if;
  if jsonb_typeof(p->'score_weights')<>'object' or jsonb_typeof(p->'preliminary_weights')<>'object' then raise exception 'weights_required'; end if;
  select coalesce(sum(value::numeric),-1) into sw from jsonb_each_text(p->'score_weights');
  select coalesce(sum(value::numeric),-1) into pw from jsonb_each_text(p->'preliminary_weights');
  if sw<>100 then raise exception 'score_weights_must_sum_100'; end if;
  if pw<>100 then raise exception 'preliminary_weights_must_sum_100'; end if;
  if not ((p->'score_weights') ?& array['pain_gap_fit','merchant_opportunity','greek_demand','commission','inverse_competition','seasonal','merchant_trust','discount','evidence_confidence']) then raise exception 'missing_score_weight'; end if;
  if not ((p->'preliminary_weights') ?& array['commission','merchant_whitespace','demand']) then raise exception 'missing_preliminary_weight'; end if;
  if exists(select 1 from jsonb_each_text(p->'score_weights') where value::numeric<0 or value::numeric>100) then raise exception 'score_weight_out_of_range'; end if;
  if exists(select 1 from jsonb_each_text(p->'preliminary_weights') where value::numeric<0 or value::numeric>100) then raise exception 'preliminary_weight_out_of_range'; end if;
  return true;
end $$;
revoke all on function public.validate_product_intelligence_config(jsonb) from public;
grant execute on function public.validate_product_intelligence_config(jsonb) to authenticated;

create or replace function public.admin_get_product_config() returns jsonb
language plpgsql stable security definer set search_path=''
as $$ declare r ops.product_intelligence_config%rowtype; begin
  if not public.socialmarket_is_admin() then raise exception 'admin_only'; end if;
  select * into r from ops.product_intelligence_config where id=1;
  return jsonb_build_object('config',r.config,'version',r.version,'updated_by',r.updated_by,'updated_at',r.updated_at);
end $$;
revoke all on function public.admin_get_product_config() from public;
grant execute on function public.admin_get_product_config() to authenticated;

create or replace function public.admin_update_product_config(p_config jsonb) returns jsonb
language plpgsql security definer set search_path=''
as $$ declare r ops.product_intelligence_config%rowtype; begin
  if not public.socialmarket_is_admin() then raise exception 'admin_only'; end if;
  perform public.validate_product_intelligence_config(p_config);
  update ops.product_intelligence_config set config=p_config,version=version+1,updated_by=lower(auth.jwt()->>'email'),updated_at=now() where id=1 returning * into r;
  insert into ops.admin_action_log(actor_email,action_type,entity_type,entity_id,metadata)
  values(lower(auth.jwt()->>'email'),'product_config_update','product_intelligence','singleton',jsonb_build_object('version',r.version,'config',r.config));
  return jsonb_build_object('config',r.config,'version',r.version,'updated_by',r.updated_by,'updated_at',r.updated_at);
end $$;
revoke all on function public.admin_update_product_config(jsonb) from public;
grant execute on function public.admin_update_product_config(jsonb) to authenticated;

create or replace function public.admin_reset_product_config() returns jsonb
language plpgsql security definer set search_path=''
as $$ declare d jsonb:=public.product_intelligence_default_config(); r ops.product_intelligence_config%rowtype; begin
  if not public.socialmarket_is_admin() then raise exception 'admin_only'; end if;
  update ops.product_intelligence_config set config=d,version=version+1,updated_by=lower(auth.jwt()->>'email'),updated_at=now() where id=1 returning * into r;
  insert into ops.admin_action_log(actor_email,action_type,entity_type,entity_id,metadata)
  values(lower(auth.jwt()->>'email'),'product_config_reset','product_intelligence','singleton',jsonb_build_object('version',r.version));
  return jsonb_build_object('config',r.config,'version',r.version,'updated_by',r.updated_by,'updated_at',r.updated_at);
end $$;
revoke all on function public.admin_reset_product_config() from public;
grant execute on function public.admin_reset_product_config() to authenticated;
