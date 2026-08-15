create or replace function public.admin_ingest_affiliate_performance(p jsonb)
returns uuid
language plpgsql
security definer
set search_path=''
as $$
declare rid uuid; v_date date; v_channel text; v_platform text; v_variant text; v_offer uuid; v_outbox uuid; v_source text; begin
  if not public.socialmarket_is_admin() then raise exception 'admin_only'; end if;
  if p is null or jsonb_typeof(p)<>'object' then raise exception 'payload_required'; end if;
  v_date=(p->>'metric_date')::date;
  v_channel=coalesce(nullif(p->>'channel',''),'other');
  v_platform=coalesce(nullif(p->>'platform',''),'other');
  v_variant=coalesce(nullif(p->>'variant_key',''),'control');
  v_offer=nullif(p->>'offer_id','')::uuid;
  v_outbox=nullif(p->>'publishing_outbox_id','')::uuid;
  v_source=coalesce(nullif(p->>'source',''),'manual');
  if v_channel not in ('organic_social','paid_social','paid_search','seo_content','email','direct','other') then raise exception 'invalid_channel'; end if;
  delete from ops.affiliate_performance_daily
   where metric_date=v_date and channel=v_channel and platform=v_platform and variant_key=v_variant
     and coalesce(offer_id,'00000000-0000-0000-0000-000000000000'::uuid)=coalesce(v_offer,'00000000-0000-0000-0000-000000000000'::uuid)
     and coalesce(publishing_outbox_id,'00000000-0000-0000-0000-000000000000'::uuid)=coalesce(v_outbox,'00000000-0000-0000-0000-000000000000'::uuid)
     and source=v_source;
  insert into ops.affiliate_performance_daily(
    metric_date,product_id,offer_id,merchant_id,program_id,content_item_id,publishing_outbox_id,channel,platform,variant_key,
    impressions,views,sessions,outbound_clicks,conversions_pending,conversions_approved,conversions_rejected,
    commission_pending_eur,commission_approved_eur,media_spend_eur,content_cost_eur,source,source_ref,metadata
  ) values(
    v_date,nullif(p->>'product_id','')::uuid,v_offer,nullif(p->>'merchant_id','')::uuid,nullif(p->>'program_id','')::uuid,
    nullif(p->>'content_item_id','')::uuid,v_outbox,v_channel,v_platform,v_variant,
    greatest(coalesce((p->>'impressions')::bigint,0),0),greatest(coalesce((p->>'views')::bigint,0),0),greatest(coalesce((p->>'sessions')::bigint,0),0),greatest(coalesce((p->>'outbound_clicks')::bigint,0),0),
    greatest(coalesce((p->>'conversions_pending')::integer,0),0),greatest(coalesce((p->>'conversions_approved')::integer,0),0),greatest(coalesce((p->>'conversions_rejected')::integer,0),0),
    coalesce((p->>'commission_pending_eur')::numeric,0),coalesce((p->>'commission_approved_eur')::numeric,0),coalesce((p->>'media_spend_eur')::numeric,0),coalesce((p->>'content_cost_eur')::numeric,0),
    v_source,p->>'source_ref',coalesce(p->'metadata','{}'::jsonb)
  ) returning id into rid;
  return rid;
end $$;
revoke all on function public.admin_ingest_affiliate_performance(jsonb) from public;
grant execute on function public.admin_ingest_affiliate_performance(jsonb) to authenticated;

create or replace function public.admin_affiliate_ab_results()
returns jsonb
language plpgsql
security definer
set search_path=''
as $$ begin
  if not public.socialmarket_is_admin() then raise exception 'admin_only'; end if;
  return jsonb_build_object(
    'generated_at',now(),
    'variants',coalesce((select jsonb_agg(to_jsonb(x) order by x.commission_approved_eur desc,x.outbound_clicks desc) from (
      select channel,platform,variant_key,
        sum(impressions) impressions,sum(views) views,sum(sessions) sessions,sum(outbound_clicks) outbound_clicks,
        sum(conversions_pending) conversions_pending,sum(conversions_approved) conversions_approved,sum(conversions_rejected) conversions_rejected,
        round(sum(commission_approved_eur)::numeric,2) commission_approved_eur,round(sum(media_spend_eur)::numeric,2) media_spend_eur,round(sum(content_cost_eur)::numeric,2) content_cost_eur,
        case when sum(impressions)>0 then round(sum(outbound_clicks)::numeric/sum(impressions)*100,3) end outbound_ctr_pct,
        case when sum(outbound_clicks)>0 then round(sum(conversions_approved)::numeric/sum(outbound_clicks)*100,3) end approved_cvr_pct,
        case when sum(outbound_clicks)>0 then round(sum(commission_approved_eur)::numeric/sum(outbound_clicks),4) end own_epc_eur,
        case when sum(impressions)>0 then round(sum(commission_approved_eur)::numeric/sum(impressions)*1000,2) end revenue_per_1000_impressions_eur,
        case when sum(conversions_approved)+sum(conversions_rejected)>0 then round(sum(conversions_rejected)::numeric/(sum(conversions_approved)+sum(conversions_rejected))*100,2) end rejection_rate_pct,
        case when sum(media_spend_eur)+sum(content_cost_eur)>0 then round((sum(commission_approved_eur)-sum(media_spend_eur)-sum(content_cost_eur))::numeric/(sum(media_spend_eur)+sum(content_cost_eur))*100,2) end roi_pct,
        min(metric_date) first_day,max(metric_date) last_day
      from ops.affiliate_performance_daily where metric_date>=current_date-29 group by channel,platform,variant_key
    )x),'[]'::jsonb),
    'note','These are first-party observed metrics only. No statistical winner is declared automatically without sufficient experiment design and sample size.'
  );
end $$;
revoke all on function public.admin_affiliate_ab_results() from public;
grant execute on function public.admin_affiliate_ab_results() to authenticated;
