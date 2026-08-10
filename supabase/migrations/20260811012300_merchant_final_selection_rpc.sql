create or replace function public.apply_final_offer_updates(updates jsonb)
returns integer
language plpgsql
set search_path to 'public'
as $$
declare affected integer;
begin
  with u as (
    select * from jsonb_to_recordset(updates) as x(
      id uuid,
      merchant_trust_score numeric,
      is_preferred_offer boolean,
      offer_selection_reason jsonb,
      market_eligible boolean,
      market_exclusion_reason text
    )
  )
  update public.products p set
    merchant_trust_score = coalesce(u.merchant_trust_score,p.merchant_trust_score),
    is_preferred_offer = coalesce(u.is_preferred_offer,false),
    offer_selection_reason = coalesce(u.offer_selection_reason,p.offer_selection_reason,'{}'::jsonb),
    market_eligible = coalesce(u.market_eligible,p.market_eligible),
    market_exclusion_reason = u.market_exclusion_reason,
    updated_at = now()
  from u where p.id=u.id;
  get diagnostics affected = row_count;
  return affected;
end;
$$;
revoke all on function public.apply_final_offer_updates(jsonb) from public, anon, authenticated;
grant execute on function public.apply_final_offer_updates(jsonb) to service_role;
