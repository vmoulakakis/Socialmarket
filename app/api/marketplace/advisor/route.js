import { NextResponse } from 'next/server';
import { getLuxeTop100 } from '@/lib/luxecorner';
import { selectForNeed } from '@/lib/shopper-agent.mjs';

// Public read-only research endpoint. No model call, credentials, writes or publishing.
// Live AI reasoning remains disabled until validated source views and owner-approved budget are available.
export async function POST(request) {
  const declared = Number(request.headers.get('content-length') || '0');
  if (declared > 2048) return NextResponse.json({ error: 'request_too_large' }, { status: 413 });
  let payload;
  try { payload = await request.json(); }
  catch { return NextResponse.json({ error: 'invalid_json' }, { status: 400 }); }
  if (typeof payload?.query !== 'string' || payload.query.length < 3 || payload.query.length > 180)
    return NextResponse.json({ error: 'query_requires_3_to_180_characters' }, { status: 400 });
  if (payload.budget != null && (!Number.isFinite(Number(payload.budget)) || Number(payload.budget) <= 0 || Number(payload.budget) > 100000))
    return NextResponse.json({ error: 'invalid_budget' }, { status: 400 });
  try {
    const rows = await getLuxeTop100();
    const result = selectForNeed({ rows, query: payload.query, budget: payload.budget });
    return NextResponse.json({
      ...result, source: 'VMDB / luxecorner_top100_public_v',
      mode: 'bounded_read_only_retrieval',
      coverage: 'premium-home collection; not the entire Greek market',
      ai_model_executed: false,
    }, { headers: { 'Cache-Control': 'no-store' } });
  } catch {
    return NextResponse.json({ error: 'source_unavailable', detail: 'Ο κατάλογος δεν είναι προσωρινά διαθέσιμος.' }, { status: 503 });
  }
}
