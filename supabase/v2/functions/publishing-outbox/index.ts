import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createRemoteJWKSet, jwtVerify } from "npm:jose@6.1.0";

const ISSUER = "https://token.actions.githubusercontent.com";
const AUDIENCE = "socialmarket-v2-publishing";
const REPOSITORY = "vmoulakakis/socialscheduler";
const REPOSITORY_ID = "1334464183";
const ALLOWED_REFS = new Set([
  "refs/heads/main",
  "refs/heads/feat/socialmarket-outbox-executor",
]);
const ALLOWED_WORKFLOWS = new Set([
  "vmoulakakis/socialscheduler/.github/workflows/social-scheduler.yml@refs/heads/main",
  "vmoulakakis/socialscheduler/.github/workflows/social-scheduler.yml@refs/heads/feat/socialmarket-outbox-executor",
  "vmoulakakis/socialscheduler/.github/workflows/migrate-legacy-backlog.yml@refs/heads/main",
  "vmoulakakis/socialscheduler/.github/workflows/migrate-legacy-backlog.yml@refs/heads/feat/socialmarket-outbox-executor",
  "vmoulakakis/socialscheduler/.github/workflows/ci.yml@refs/heads/main",
  "vmoulakakis/socialscheduler/.github/workflows/ci.yml@refs/heads/feat/socialmarket-outbox-executor",
]);
const JWKS = createRemoteJWKSet(new URL(`${ISSUER}/.well-known/jwks`));

function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" },
  });
}

async function authorize(req: Request) {
  const auth = req.headers.get("authorization") || "";
  if (!auth.startsWith("Bearer ")) throw new Error("missing_github_oidc_token");
  const { payload } = await jwtVerify(auth.slice(7), JWKS, { issuer: ISSUER, audience: AUDIENCE });
  if (String(payload.repository_id || "") !== REPOSITORY_ID) throw new Error("repository_id_not_allowed");
  if (String(payload.repository || "") !== REPOSITORY) throw new Error("repository_not_allowed");
  if (!ALLOWED_REFS.has(String(payload.ref || ""))) throw new Error("ref_not_allowed");
  if (!ALLOWED_WORKFLOWS.has(String(payload.workflow_ref || ""))) throw new Error("workflow_not_allowed");
  return payload;
}

async function rpc(name: string, params: Record<string, unknown> = {}) {
  const supabaseUrl = Deno.env.get("SUPABASE_URL");
  const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
  if (!supabaseUrl || !serviceKey) throw new Error("supabase_runtime_credentials_missing");
  const response = await fetch(`${supabaseUrl}/rest/v1/rpc/${name}`, {
    method: "POST",
    headers: { apikey: serviceKey, authorization: `Bearer ${serviceKey}`, "content-type": "application/json" },
    body: JSON.stringify(params),
  });
  const text = await response.text();
  let result: unknown = null;
  if (text) { try { result = JSON.parse(text); } catch { result = text; } }
  if (!response.ok) throw new Error(`rpc_${name}_${response.status}:${JSON.stringify(result)}`);
  return result;
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response(null, { status: 204 });
  if (req.method === "GET") return json({ ok: true, service: "publishing-outbox", auth: "github-oidc", audience: AUDIENCE, version: 2 });
  if (req.method !== "POST") return json({ ok: false, error: "method_not_allowed" }, 405);
  try {
    const claims = await authorize(req);
    const body = await req.json().catch(() => ({}));
    const action = String(body?.action || "health");

    if (action === "health") {
      const result = await rpc("worker_v2_outbox_health");
      return json({ ok: true, repository: claims.repository, ...(result as object) });
    }
    if (action === "peek") {
      const jobs = await rpc("worker_v2_outbox_peek", { p_limit: Math.max(1, Math.min(Number(body?.limit || 10), 50)) });
      return json({ ok: true, jobs: jobs || [] });
    }
    if (action === "claim") {
      const jobs = await rpc("worker_v2_outbox_claim", {
        p_executor: String(body?.executor || "socialscheduler"),
        p_limit: Math.max(1, Math.min(Number(body?.limit || 10), 50)),
        p_lease_minutes: Math.max(5, Math.min(Number(body?.lease_minutes || 30), 120)),
      });
      return json({ ok: true, jobs: jobs || [] });
    }
    if (action === "ack") {
      const job = await rpc("worker_v2_outbox_ack", { p_payload: {
        job_id: body?.job_id,
        status: body?.status,
        external_post_id: body?.external_post_id ?? null,
        external_permalink: body?.external_permalink ?? null,
        scheduled_at: body?.scheduled_at ?? null,
        published_at: body?.published_at ?? null,
        error: body?.error ?? null,
        metadata: body?.metadata ?? {},
      }});
      return json({ ok: true, job });
    }
    if (action === "reconcile") {
      const jobs = await rpc("worker_v2_outbox_reconcile", { p_limit: Math.max(1, Math.min(Number(body?.limit || 200), 500)) });
      return json({ ok: true, jobs: jobs || [] });
    }
    if (action === "import_legacy") {
      if (!Array.isArray(body?.campaigns)) return json({ ok: false, error: "campaigns_array_required" }, 400);
      const result = await rpc("worker_v2_outbox_import_legacy", { p_campaigns: body.campaigns });
      return json({ ok: true, ...(result as object) });
    }
    return json({ ok: false, error: "unknown_action" }, 400);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    const unauthorized = ["github_oidc", "repository_", "ref_not_allowed", "workflow_not_allowed", "JWTClaimValidationFailed", "JWSSignatureVerificationFailed"].some((x) => message.includes(x));
    console.error(message);
    return json({ ok: false, error: message }, unauthorized ? 401 : 503);
  }
});
