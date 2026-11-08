import { NextResponse } from 'next/server';
import { adminAuth } from '@/lib/admin-auth';
import { agentCompletion } from '@/lib/model-router';
import { getShopCatalog,shopBuyerRows } from '@/lib/shop-catalog';
import {searchShopCatalog,enrichTerms} from '@/lib/shop-search.mjs';
import { evidencePacket, runBuyerCrew } from '@/lib/shopper-crew.mjs';

export const maxDuration = 60;
const enabled = () => process.env.SHOPPER_BUYER_CREW_ENABLED === 'true' &&
  process.env.ENABLE_PAID_REMOTE === '1';

function reply(body,status=200) {
  return NextResponse.json(body,{status,headers:{'Cache-Control':'no-store','X-Robots-Tag':'noindex, nofollow'}});
}

/**
 * Admin-only MyAgenticTeam lab.
 * GET is deliberately unsupported; evidence and model calls require a signed-in
 * administrator. Any remote model spending is disabled unless both owner gates
 * are enabled, then existing DB budget reservations still apply.
 */
export async function POST(req) {
  const auth = await adminAuth(req);
  if (!auth) return reply({error:'admin_session_required'},401);
  let input;
  try {
    const raw = await req.text();
    if (raw.length > 2048) return reply({error:'request_too_large'},413);
    input = JSON.parse(raw);
  } catch { return reply({error:'invalid_json'},400); }

  const question = input?.query;
  if (typeof question !== 'string' || question.trim().length < 3 || question.length > 180)
    return reply({error:'query_requires_3_to_180_characters'},400);
  const budget = input?.budget == null || input?.budget === '' ? null : Number(input.budget);
  if (budget !== null && (!Number.isFinite(budget) || budget <= 0 || budget > 100000))
    return reply({error:'invalid_budget'},400);
  if (input?.run_model !== undefined && typeof input.run_model !== 'boolean')
    return reply({error:'run_model_must_be_boolean'},400);
  try {
    const {products}=await getShopCatalog();
    const matched=searchShopCatalog(products,{query:question,budget,perPage:30});
    const rows=shopBuyerRows(matched.results);
    const context={rows,question:question+' '+enrichTerms(question).join(' '),budget};
    if (!input.run_model || !enabled()) {
      const {result,products} = evidencePacket(context);
      return reply({
        ...result, products_considered:products.length,
        crew_status: input.run_model ? 'MODEL_DISABLED_BY_OWNER_POLICY' : 'DETERMINISTIC_PREFLIGHT',
        ai_model_executed:false, research:[],critic:[],publication_approved:false,
        model_enabled:enabled(), source:'VMDB / ai_product_offers + Linkwise research',
        note:'Πραγματικός πολυκατηγορικός κατάλογος. Η διαθεσιμότητα και ο εξωτερικός Skeptic παραμένουν προς επαλήθευση.',
      });
    }
    const result = await runBuyerCrew({...context,complete:agentCompletion,accessToken:auth.accessToken});
    return reply({...result,model_enabled:true,source:'VMDB / ai_product_offers + Linkwise research'});
  } catch {
    return reply({error:'buyer_crew_unavailable',detail:'Δεν ήταν δυνατή η ανάκτηση των στοιχείων.'},503);
  }
}
