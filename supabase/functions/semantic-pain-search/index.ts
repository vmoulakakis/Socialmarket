import 'jsr:@supabase/functions-js/edge-runtime.d.ts'
import postgres from 'https://deno.land/x/postgresjs@v3.4.5/mod.js'

const sql = postgres(Deno.env.get('SUPABASE_DB_URL')!, { prepare: false })
const embedder = new Supabase.ai.Session('gte-small')

Deno.serve(async (req: Request) => {
  if (req.method !== 'POST') return new Response('POST only', { status: 405 })
  const body = await req.json().catch(() => ({}))
  const query = String(body.query || '').trim()
  if (query.length < 3) return Response.json({ error: 'query_required' }, { status: 400 })

  const entityType = body.entity_type ? String(body.entity_type) : null
  const clusterTypes = Array.isArray(body.cluster_types) && body.cluster_types.length
    ? body.cluster_types.map((x: unknown) => String(x)).slice(0, 8)
    : ['pain','unmet_need','alternative_request','complaint']
  const limit = Math.max(1, Math.min(Number(body.limit || 20), 50))
  const minConfidence = Math.max(0, Math.min(Number(body.min_confidence ?? 0.55), 1))

  const vector = await embedder.run(query.slice(0, 5000), { mean_pool: true, normalize: true })
  const rows = await sql`select * from evidence.search_semantic_clusters(
    ${JSON.stringify(vector)}, ${entityType}, ${clusterTypes}, ${limit}, ${minConfidence}
  )`

  return Response.json({ ok: true, query, count: rows.length, results: rows })
})
