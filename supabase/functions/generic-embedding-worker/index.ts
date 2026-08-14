import 'jsr:@supabase/functions-js/edge-runtime.d.ts'
import postgres from 'https://deno.land/x/postgresjs@v3.4.5/mod.js'

const sql = postgres(Deno.env.get('SUPABASE_DB_URL')!, { prepare: false })
const embedder = new Supabase.ai.Session('gte-small')

Deno.serve(async (req: Request) => {
  if (req.method !== 'POST') return new Response('POST only', { status: 405 })
  const body = await req.json().catch(() => ({}))
  const limit = Math.max(1, Math.min(Number(body.limit || 10), 30))
  const worker = `edge-generic-embedding-${crypto.randomUUID()}`

  await sql`update ops.collection_jobs
    set status='queued', lease_owner=null, lease_expires_at=null,
        not_before=now()+interval '2 minutes', last_error=coalesce(last_error,'lease_expired')
    where collection_type='semantic_embedding' and status='running' and lease_expires_at < now()`

  const jobs = await sql`select * from ops.claim_generic_embedding_jobs(${worker}, ${limit}, 20)`
  const results: unknown[] = []

  for (const job of jobs) {
    try {
      const vector = await embedder.run(String(job.semantic_text).slice(0, 5000), {
        mean_pool: true,
        normalize: true,
      })
      await sql`select ops.complete_generic_embedding_job(${job.job_id}, ${JSON.stringify(vector)}, 'gte-small')`
      results.push({ ok: true, job_id: job.job_id, cluster_id: job.cluster_id, entity_type: job.entity_type })
    } catch (err) {
      const message = String((err as Error)?.message || err).slice(0, 1200)
      await sql`select ops.fail_generic_embedding_job(${job.job_id}, ${message})`
      results.push({ ok: false, job_id: job.job_id, error: message })
    }
  }

  return Response.json({ ok: true, claimed: jobs.length, results })
})
