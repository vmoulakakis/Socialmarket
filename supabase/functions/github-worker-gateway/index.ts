import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createRemoteJWKSet, jwtVerify } from "npm:jose@6.1.0";

const ISSUER = "https://token.actions.githubusercontent.com";
const AUDIENCE = "socialmarket-supabase-worker";
const REPOSITORY_ID = "1329707883";
const REPOSITORY = "vmoulakakis/Socialmarket";
const ALLOWED_WORKFLOWS = new Set([
  "vmoulakakis/Socialmarket/.github/workflows/import-products.yml@refs/heads/main",
  "vmoulakakis/Socialmarket/.github/workflows/market-intelligence.yml@refs/heads/main",
]);
const ALLOWED_TABLES = new Set([
  "sources","import_jobs","products","product_media","taxonomy","product_classifications","product_embeddings",
  "market_research_runs","market_signals","forecast_runs","forecasts","opportunity_scores","evidence_audits",
  "creative_jobs","creative_assets","approvals","agent_runs","app_settings"
]);
const ALLOWED_RPCS = new Set(["category_universe"]);
const JWKS = createRemoteJWKSet(new URL(`${ISSUER}/.well-known/jwks`));

function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), { status, headers: { "content-type": "application/json" } });
}

async function authorize(req: Request) {
  const auth = req.headers.get("authorization") || "";
  if (!auth.startsWith("Bearer ")) throw new Error("missing_bearer_token");
  const token = auth.slice(7);
  const { payload } = await jwtVerify(token, JWKS, { issuer: ISSUER, audience: AUDIENCE });
  if (String(payload.repository_id || "") !== REPOSITORY_ID) throw new Error("repository_id_not_allowed");
  if (String(payload.repository || "") !== REPOSITORY) throw new Error("repository_not_allowed");
  if (String(payload.ref || "") !== "refs/heads/main") throw new Error("ref_not_allowed");
  if (!ALLOWED_WORKFLOWS.has(String(payload.workflow_ref || ""))) throw new Error("workflow_not_allowed");
  return payload;
}

function validateResource(resource: string) {
  if (resource.startsWith("rpc/")) {
    const rpc = resource.slice(4);
    if (!ALLOWED_RPCS.has(rpc)) throw new Error("rpc_not_allowed");
    return;
  }
  if (!ALLOWED_TABLES.has(resource)) throw new Error("table_not_allowed");
}

Deno.serve(async (req: Request) => {
  if (req.method === "GET") return json({ ok: true, service: "github-worker-gateway" });
  if (req.method !== "POST") return json({ error: "method_not_allowed" }, 405);
  try {
    const claims = await authorize(req);
    const body = await req.json();
    const method = String(body.method || "GET").toUpperCase();
    if (!["GET", "POST", "PATCH"].includes(method)) throw new Error("db_method_not_allowed");
    const resource = String(body.resource || "");
    validateResource(resource);

    const supabaseUrl = Deno.env.get("SUPABASE_URL");
    const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
    if (!supabaseUrl || !serviceKey) throw new Error("supabase_runtime_credentials_missing");

    const url = new URL(`${supabaseUrl}/rest/v1/${resource}`);
    for (const [k, v] of Object.entries(body.params || {})) {
      if (v !== undefined && v !== null) url.searchParams.set(k, String(v));
    }
    const headers: Record<string,string> = {
      "apikey": serviceKey,
      "authorization": `Bearer ${serviceKey}`,
      "content-type": "application/json",
    };
    if (body.prefer) headers["prefer"] = String(body.prefer).slice(0, 200);
    const upstream = await fetch(url, {
      method,
      headers,
      body: method === "GET" ? undefined : JSON.stringify(body.data ?? {}),
    });
    const text = await upstream.text();
    const result = text ? (() => { try { return JSON.parse(text); } catch { return text; } })() : null;
    if (!upstream.ok) return json({ error: "upstream_error", status: upstream.status, detail: result }, upstream.status);
    return json({ ok: true, result, repository: claims.repository, workflow_ref: claims.workflow_ref }, upstream.status);
  } catch (e) {
    console.error(e);
    return json({ error: String(e instanceof Error ? e.message : e) }, 401);
  }
});
