import 'jsr:@supabase/functions-js/edge-runtime.d.ts'
import { createRemoteJWKSet, jwtVerify } from 'npm:jose@6.1.0'
import postgres from 'https://deno.land/x/postgresjs@v3.4.5/mod.js'

const sql = postgres(Deno.env.get('SUPABASE_DB_URL')!, { prepare: false, max: 1 })
const ISSUER = 'https://token.actions.githubusercontent.com'
const AUDIENCE = 'socialmarket-ai-runtime'
const REPOSITORY_ID = '1329707883'
const REPOSITORY = 'vmoulakakis/Socialmarket'
const ALLOWED = new Set([
  'vmoulakakis/Socialmarket/.github/workflows/generic-evidence-intelligence.yml@refs/heads/main',
  'vmoulakakis/Socialmarket/.github/workflows/product-intelligence-v1.yml@refs/heads/main',
])
const JWKS = createRemoteJWKSet(new URL(`${ISSUER}/.well-known/jwks`))
const HASH = /^[0-9a-f]{64}$/
const STATUS = new Set(['ok', 'not_applicable', 'invalid', 'unavailable', 'error', 'safe_hold', 'cache_hit'])

const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), {
  status,
  headers: { 'content-type': 'application/json', 'cache-control': 'no-store' },
})

function text(value: unknown, max: number): string | null {
  const out = String(value ?? '').trim()
  return out ? out.slice(0, max) : null
}

function hash(value: unknown, name: string): string {
  const out = String(value ?? '').trim().toLowerCase()
  if (!HASH.test(out)) throw new Error(`invalid_${name}`)
  return out
}

function tier(value: unknown): number {
  const out = Number(value ?? 0)
  if (!Number.isInteger(out) || out < 0 || out > 9) throw new Error('invalid_tier')
  return out
}

function boundedObject(value: unknown, name: string, maxBytes = 200_000): Record<string, unknown> {
  if (!value || Array.isArray(value) || typeof value !== 'object') throw new Error(`${name}_must_be_object`)
  const encoded = JSON.stringify(value)
  if (new TextEncoder().encode(encoded).byteLength > maxBytes) throw new Error(`${name}_too_large`)
  return value as Record<string, unknown>
}

async function auth(req: Request) {
  const header = req.headers.get('authorization') || ''
  if (!header.startsWith('Bearer ')) throw new Error('missing_oidc')
  const { payload } = await jwtVerify(header.slice(7), JWKS, { issuer: ISSUER, audience: AUDIENCE })
  if (
    String(payload.repository_id || '') !== REPOSITORY_ID
    || String(payload.repository || '') !== REPOSITORY
    || String(payload.ref || '') !== 'refs/heads/main'
    || !ALLOWED.has(String(payload.workflow_ref || ''))
  ) throw new Error('oidc_not_allowed')
  return payload
}

async function cacheGet(body: Record<string, unknown>) {
  const cacheKey = hash(body.cache_key, 'cache_key')
  const taskType = text(body.task_type, 120)
  const inputHash = hash(body.input_hash, 'input_hash')
  const contractHash = hash(body.contract_hash, 'contract_hash')
  if (!taskType) throw new Error('task_type_required')

  const rows = await sql`
    select cache_key, task_type, input_hash, contract_hash, output, output_hash,
           executor, tier, route, model, created_at, last_used_at, hit_count
    from ops.ai_task_cache
    where cache_key=${cacheKey}
      and task_type=${taskType}
      and input_hash=${inputHash}
      and contract_hash=${contractHash}
    limit 1
  `
  const row = rows[0]
  if (!row) return { hit: false }
  await sql`
    update ops.ai_task_cache
    set last_used_at=now(), hit_count=hit_count+1
    where cache_key=${cacheKey}
  `
  return {
    hit: true,
    output: row.output,
    provenance: {
      output_hash: row.output_hash,
      executor: row.executor,
      tier: row.tier,
      route: row.route,
      model: row.model,
      created_at: row.created_at,
      hit_count: Number(row.hit_count || 0) + 1,
    },
  }
}

async function cachePut(body: Record<string, unknown>) {
  const cacheKey = hash(body.cache_key, 'cache_key')
  const taskType = text(body.task_type, 120)
  const inputHash = hash(body.input_hash, 'input_hash')
  const contractHash = hash(body.contract_hash, 'contract_hash')
  const outputHash = hash(body.output_hash, 'output_hash')
  const output = boundedObject(body.output, 'output')
  const executor = text(body.executor, 120)
  const route = text(body.route, 120)
  const model = text(body.model, 200)
  const taskTier = tier(body.tier)
  if (!taskType || !executor) throw new Error('task_type_and_executor_required')

  await sql`
    insert into ops.ai_task_cache(
      cache_key,task_type,input_hash,contract_hash,output,output_hash,
      executor,tier,route,model,created_at,last_used_at,hit_count
    ) values(
      ${cacheKey},${taskType},${inputHash},${contractHash},${sql.json(output)},${outputHash},
      ${executor},${taskTier},${route},${model},now(),now(),0
    )
    on conflict(cache_key) do update set
      last_used_at=now(),
      output=case
        when ops.ai_task_cache.input_hash=excluded.input_hash
         and ops.ai_task_cache.contract_hash=excluded.contract_hash
        then ops.ai_task_cache.output else excluded.output end,
      output_hash=case
        when ops.ai_task_cache.input_hash=excluded.input_hash
         and ops.ai_task_cache.contract_hash=excluded.contract_hash
        then ops.ai_task_cache.output_hash else excluded.output_hash end,
      task_type=excluded.task_type,
      input_hash=excluded.input_hash,
      contract_hash=excluded.contract_hash,
      executor=excluded.executor,
      tier=excluded.tier,
      route=excluded.route,
      model=excluded.model
  `
  return { stored: true }
}

function sanitizedMetadata(value: unknown): Record<string, unknown> {
  const data = boundedObject(value || {}, 'metadata', 30_000)
  const blocked = new Set(['prompt', 'instructions', 'payload', 'evidence', 'raw_input', 'raw_output'])
  return Object.fromEntries(Object.entries(data).filter(([key]) => !blocked.has(key.toLowerCase())))
}

async function recordResult(body: Record<string, unknown>) {
  const taskType = text(body.task_type, 120)
  const inputHash = hash(body.input_hash, 'input_hash')
  const contractHash = hash(body.contract_hash, 'contract_hash')
  const finalStatus = String(body.status || '')
  if (!taskType || !['ok', 'safe_hold'].includes(finalStatus)) throw new Error('invalid_final_result')
  const attempts = Array.isArray(body.attempts) ? body.attempts.slice(0, 30) : []

  for (const raw of attempts) {
    const a = boundedObject(raw, 'attempt', 40_000)
    const attemptStatus = String(a.status || '')
    if (!STATUS.has(attemptStatus)) throw new Error('invalid_attempt_status')
    const executor = text(a.executor, 120)
    if (!executor) throw new Error('attempt_executor_required')
    const attemptInput = hash(a.input_hash, 'attempt_input_hash')
    const attemptContract = hash(a.contract_hash, 'attempt_contract_hash')
    if (attemptInput !== inputHash || attemptContract !== contractHash) throw new Error('attempt_hash_mismatch')
    const latency = Math.max(0, Math.min(3_600_000, Number(a.latency_ms || 0)))
    const outputHash = a.output_hash ? hash(a.output_hash, 'attempt_output_hash') : null
    await sql`
      insert into ops.ai_task_attempts(
        task_type,input_hash,contract_hash,executor,tier,status,route,model,
        latency_ms,output_hash,error,metadata
      ) values(
        ${taskType},${inputHash},${contractHash},${executor},${tier(a.tier)},${attemptStatus},
        ${text(a.route,120)},${text(a.model,200)},${Math.round(latency)},${outputHash},
        ${text(a.error,1000)},${sql.json(sanitizedMetadata(a.metadata || {}))}
      )
    `
  }

  const selected = [...attempts].reverse().find((raw) => {
    const a = raw as Record<string, unknown>
    return a.status === 'ok' || a.status === 'cache_hit'
  }) as Record<string, unknown> | undefined
  const outputHash = body.output_hash ? hash(body.output_hash, 'output_hash') : null
  await sql`
    insert into ops.ai_task_results(
      task_type,input_hash,contract_hash,status,from_cache,reason,attempt_count,
      selected_executor,selected_tier,selected_route,selected_model,output_hash
    ) values(
      ${taskType},${inputHash},${contractHash},${finalStatus},${Boolean(body.from_cache)},
      ${text(body.reason,1000)},${attempts.length},${selected ? text(selected.executor,120) : null},
      ${selected ? tier(selected.tier) : null},${selected ? text(selected.route,120) : null},
      ${selected ? text(selected.model,200) : null},${outputHash}
    )
  `
  return { recorded: true, attempts: attempts.length }
}

Deno.serve(async (req) => {
  if (req.method === 'GET') return json({
    ok: true,
    service: 'ai-task-runtime-gateway',
    version: '1.0',
    contract: 'autopilot-ai-task-v1',
    stores_raw_prompts: false,
    stores_raw_evidence: false,
  })
  if (req.method !== 'POST') return json({ error: 'method_not_allowed' }, 405)
  try {
    await auth(req)
    const body = boundedObject(await req.json(), 'request', 300_000)
    const action = String(body.action || '')
    if (action === 'cache_get') return json({ ok: true, ...(await cacheGet(body)) })
    if (action === 'cache_put') return json({ ok: true, ...(await cachePut(body)) })
    if (action === 'record_result') return json({ ok: true, ...(await recordResult(body)) })
    throw new Error('action_not_allowed')
  } catch (error) {
    console.error(error)
    const message = String(error instanceof Error ? error.message : error)
    const status = message.includes('oidc') ? 401 : message.includes('too_large') ? 413 : 400
    return json({ error: message }, status)
  }
})
