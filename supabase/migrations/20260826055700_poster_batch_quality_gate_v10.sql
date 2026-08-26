create table if not exists ops.product_batch_quality_gates (
 run_id uuid primary key references intel.product_ranking_runs(id) on delete cascade,
 status text not null check(status in ('PASS','FAIL')),
 checks jsonb not null,
 evaluated_at timestamptz not null default now()
);
alter table ops.product_batch_quality_gates enable row level security;
revoke all on ops.product_batch_quality_gates from public,anon,authenticated;

create or replace function publish.validate_poster_batch_v10(p_run_id uuid)
returns jsonb language plpgsql security definer set search_path='' as $$
declare c jsonb; passed boolean;
begin
 with ranked as (select * from intel.product_rankings where run_id=p_run_id),
 variants as (
   select r.*,v.value variant from ranked r
   cross join lateral jsonb_array_elements(coalesce(r.creative_pack->'variants','[]'::jsonb)) v
   where r.creative_status='ready'
 ), facts as (
 select
   (select count(*) from ranked) rankings,
   (select count(*) from ranked where lower(coalesce(product_name,'')||' '||coalesce(category,'')||' '||coalesce(subcategory,'')||' '||coalesce(merchant_name,'')) ~ '(hotel|hostel|resort|accommodation|lodging|ξενοδοχ|κατάλυμ|διαμον)') excluded,
   (select count(*) from ranked where creative_status='ready' and upper(coalesce(creative_audit->>'verdict',''))='READY') ready_products,
   (select count(*) from variants) variants,
   (select count(distinct lower(regexp_replace(coalesce(variant->>'hook',''),'\s+',' ','g'))) from variants) unique_hooks,
   (select count(distinct lower(regexp_replace(coalesce(variant->>'caption',''),'\s+',' ','g'))) from variants) unique_captions,
   (select count(distinct (variant->'hashtags')::text) from variants) unique_tagsets,
   (select count(*) from variants where coalesce(variant->>'asset_url','') ~ '^https://.*[.]png$') png_assets,
   (select count(*) from variants where variant->'qr_spec'->>'payload_rule'='exact_tracking_url' and variant->'qr_spec'->>'payload_url'=creative_pack->>'affiliate_short_url') exact_qr,
   (select count(*) from publish.affiliate_short_links l where l.run_id=p_run_id and l.active and l.destination_url ~ '^https://go[.]linkwi[.]se/') short_links,
   (select count(*) from content.items i where i.metadata->>'creative_run_id'=p_run_id::text and i.metadata->>'creative_contract_version'='v10' and i.tracking_url ~ '/socialscheduler-go/r-') content_items,
   (select count(*) from intel.demand_themes d where d.status='active' and current_date between d.active_from and d.active_to and d.confidence is not null and d.base_demand_score is not null) fresh_seasonal
 )
 select jsonb_build_object('rankings',rankings,'excluded_verticals',excluded,'ready_products',ready_products,'variants',variants,'unique_hooks',unique_hooks,'unique_captions',unique_captions,'unique_tagsets',unique_tagsets,'png_assets',png_assets,'exact_qr',exact_qr,'short_links',short_links,'content_items',content_items,'fresh_seasonal_themes',fresh_seasonal) into c from facts;
 passed := (c->>'rankings')::int=100 and (c->>'excluded_verticals')::int=0 and (c->>'ready_products')::int=20 and
 (c->>'variants')::int=60 and (c->>'unique_hooks')::int=60 and (c->>'unique_captions')::int=60 and
 (c->>'unique_tagsets')::int=60 and (c->>'png_assets')::int=60 and (c->>'exact_qr')::int=60 and
 (c->>'short_links')::int=20 and (c->>'content_items')::int=60 and (c->>'fresh_seasonal_themes')::int>=1;
 insert into ops.product_batch_quality_gates(run_id,status,checks,evaluated_at)
 values(p_run_id,case when passed then 'PASS' else 'FAIL' end,c,now())
 on conflict(run_id) do update set status=excluded.status,checks=excluded.checks,evaluated_at=now();
 return jsonb_build_object('passed',passed,'run_id',p_run_id,'checks',c);
end $$;
revoke all on function publish.validate_poster_batch_v10(uuid) from public,anon,authenticated;
grant execute on function publish.validate_poster_batch_v10(uuid) to service_role;

create or replace function public.worker_v10_poster_outbox_refill(p_hours integer default 72,p_dry_run boolean default false)
returns jsonb language plpgsql security definer set search_path='' as $$
declare rid uuid; gate jsonb;
begin
 select id into rid from intel.product_ranking_runs where status='completed' order by completed_at desc nulls last limit 1;
 if rid is null then raise exception 'v10_no_completed_batch'; end if;
 gate:=publish.validate_poster_batch_v10(rid);
 if not coalesce((gate->>'passed')::boolean,false) then raise exception 'v10_hard_gate_closed:%',gate::text; end if;
 return publish.refill_poster_outbox_v9(p_hours,p_dry_run);
end $$;
revoke all on function public.worker_v10_poster_outbox_refill(integer,boolean) from public,anon,authenticated;
grant execute on function public.worker_v10_poster_outbox_refill(integer,boolean) to service_role;
select cron.alter_job(25,command:='select public.worker_v10_poster_outbox_refill(72,false);',active:=false);
select cron.alter_job(26,command:='select public.worker_v10_poster_outbox_refill(168,false); select public.socialscheduler_rebalance_frequency_v6(168);',active:=false);
