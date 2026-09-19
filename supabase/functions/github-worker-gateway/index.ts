import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createRemoteJWKSet, jwtVerify } from "npm:jose@6.1.0";

const ISSUER = "https://token.actions.githubusercontent.com";
const AUDIENCE = "socialmarket-supabase-worker";
const REPOSITORY_ID = "1329707883";
const REPOSITORY = "vmoulakakis/Socialmarket";

const ALLOWED_WORKFLOWS = new Set([
  "vmoulakakis/Socialmarket/.github/workflows/import-products.yml@refs/heads/main",
  "vmoulakakis/Socialmarket/.github/workflows/product-intelligence-v1.yml@refs/heads/main",
  "vmoulakakis/Socialmarket/.github/workflows/merchant-resolution.yml@refs/heads/main",
  "vmoulakakis/Socialmarket/.github/workflows/merchant-trust-research.yml@refs/heads/main",
  "vmoulakakis/Socialmarket/.github/workflows/niche-discovery.yml@refs/heads/main",
  "vmoulakakis/Socialmarket/.github/workflows/market-intelligence.yml@refs/heads/main",
  "vmoulakakis/Socialmarket/.github/workflows/merchant-demand-intelligence.yml@refs/heads/main",
  "vmoulakakis/Socialmarket/.github/workflows/agent-tool-executor.yml@refs/heads/main",
  "vmoulakakis/Socialmarket/.github/workflows/linkwise-product-discovery.yml@refs/heads/main",
  "vmoulakakis/Socialmarket/.github/workflows/linkwise-top100-commission.yml@refs/heads/main",
  "vmoulakakis/Socialmarket/.github/workflows/direct-aliexpress-agentic.yml@refs/heads/main",
  "vmoulakakis/Socialmarket/.github/workflows/agentic-commerce-backend.yml@refs/heads/main",
]);

const ALLOWED_TABLES = new Set([
  "sources","import_jobs","products","product_media","taxonomy","product_classifications","product_embeddings",
  "market_research_runs","market_signals","forecast_runs","forecasts","opportunity_scores","evidence_audits",
  "creative_jobs","creative_assets","approvals","agent_runs","app_settings","agent_tool_tasks","agent_budget_policies","agent_usage_ledger",
  "merchant_profiles","merchant_category_memberships","merchant_evidence","merchant_research_runs","merchant_demand_assessments","merchant_rankings",
  "merchant_selection_policies","merchant_latest_360","merchant_product_discovery_eligible","merchant_product_bootstrap_eligible",
  "product_discovery_runs","merchant_product_candidates",
  "market_problem_clusters","problem_demand_assessments","merchant_problem_fits",
  "commerce_raw_evidence","commerce_semantic_documents","commerce_taxonomy_nodes","commerce_problem_product_matches",
  "commerce_feed_runs","commerce_feed_eligible_offers","commerce_pipeline_checkpoints","commerce_pipeline_policies",
  "commerce_agent_runs","commerce_learning_calibrations","commerce_performance_events",
  "product_selection_policies","product_selection_funnel","product_selection_1000",
  "social_presentation_intelligence","social_distribution_metrics","linkwise_program_commissions",
  "ai_source_queries","ai_product_candidates","ai_product_offers","ai_demand_signals","ai_demand_forecasts","ai_product_evaluations","ai_promotion_candidates_v",
]);

const ALLOWED_RPCS = new Set([
  "category_universe","eligible_products_for_niche_discovery","apply_product_identity_updates","apply_final_offer_updates",
  "reserve_agent_budget","finalize_agent_budget","release_agent_budget","claim_agent_tool_task","finish_agent_tool_task","fail_agent_tool_task",
  "vmdb_refresh_semantic_memory","vmdb_semantic_embedding_claim","vmdb_semantic_embedding_ack","vmdb_semantic_search","vmdb_ai_backend_health",
  "vmdb_product_bootstrap_health",
]);

const JWKS = createRemoteJWKSet(new URL(`${ISSUER}/.well-known/jwks`));

function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), { status, headers: { "content-type": "application/json" } });
}

async function authorize(req: Request) {
  const auth = req.headers.get("authorization") || "";
  if (!auth.startsWith("Bearer ")) throw new Error("missing_bearer_token");
  const { payload } = await jwtVerify(auth.slice(7), JWKS, { issuer: ISSUER, audience: AUDIENCE });
  if (String(payload.repository_id || "") !== REPOSITORY_ID) throw new Error("repository_id_not_allowed");
  if (String(payload.repository || "") !== REPOSITORY) throw new Error("repository_not_allowed");
  if (String(payload.ref || "") !== "refs/heads/main") throw new Error("ref_not_allowed");
  if (!ALLOWED_WORKFLOWS.has(String(payload.workflow_ref || ""))) throw new Error("workflow_not_allowed");
  return payload;
}

function validateResource(resource: string) {
  if (resource.startsWith("rpc/")) {
    if (!ALLOWED_RPCS.has(resource.slice(4))) throw new Error("rpc_not_allowed");
    return;
  }
  if (!ALLOWED_TABLES.has(resource)) throw new Error("table_not_allowed");
}

Deno.serve(async (req: Request) => {
  if (req.method === "GET") {
    return json({
      ok: true,
      service: "github-worker-gateway",
      database: "vmdb",
      queue: true,
      budgets: true,
      merchant360: true,
      productAdmission: true,
      productBootstrap: true,
      semanticMemory: true,
      aiBackendHealth: true,
      directPublishingOutboxAccess: false,
      version: 6,
    });
  }
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

    const headers: Record<string, string> = {
      apikey: serviceKey,
      authorization: `Bearer ${serviceKey}`,
      "content-type": "application/json",
    };
    if (body.prefer) headers.prefer = String(body.prefer).slice(0, 200);

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
