import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "npm:@supabase/supabase-js@2.53.0";
import { createRemoteJWKSet, jwtVerify } from "npm:jose@5.9.6";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL") ?? "";
const SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "";
const EXPECTED_REPOSITORY = Deno.env.get("SOCIALSCHEDULER_GITHUB_REPOSITORY") ?? "vmoulakakis/socialscheduler";
const OIDC_AUDIENCE = Deno.env.get("SOCIALSCHEDULER_OIDC_AUDIENCE") ?? "socialmarket-ai";

const supabase = createClient(SUPABASE_URL, SERVICE_ROLE_KEY, {
  auth: { persistSession: false, autoRefreshToken: false },
});
const githubJwks = createRemoteJWKSet(new URL("https://token.actions.githubusercontent.com/.well-known/jwks"));

const BRAND_ALIASES: Record<string, string> = {
  "CabinPilot Travel": "cabinpilot-travel",
  "CabinPilot Smart Savings": "cabinpilot-smart-savings",
  "Lyseis / Biz Box Solver": "lyseis-pou-axizoun",
  "Λύσεις που Αξίζουν / Biz Box Solver": "lyseis-pou-axizoun",
  "CoffeeGo / Coffee Anywhere AI": "coffeego-ai",
  "CoffeeGo AI": "coffeego-ai",
  "Travel AI / GreekVibes": "travel-ai",
  "Travel AI": "travel-ai",
  "Red Raven Eyewear": "red-raven-eyewear",
};

function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" },
  });
}

async function authorizeGithubAction(req: Request) {
  const auth = req.headers.get("authorization") ?? "";
  const token = auth.startsWith("Bearer ") ? auth.slice(7).trim() : "";
  if (!token) throw new Error("missing_github_oidc_token");

  const { payload } = await jwtVerify(token, githubJwks, {
    issuer: "https://token.actions.githubusercontent.com",
    audience: OIDC_AUDIENCE,
  });
  if (payload.repository !== EXPECTED_REPOSITORY) throw new Error("repository_not_allowed");
  const ref = String(payload.ref ?? "");
  if (ref && ref !== "refs/heads/main") throw new Error("only_main_branch_is_allowed");
  return payload;
}

function hashtagsFromCaption(caption: string): string[] {
  return Array.from(caption.matchAll(/(^|\s)(#[\p{L}\p{N}_]+)/gu)).map((m) => m[2]);
}

function rawAssetUrl(filename?: string | null): string | null {
  if (!filename) return null;
  return `https://raw.githubusercontent.com/vmoulakakis/socialscheduler/main/assets/${encodeURIComponent(filename)}`;
}

async function importLegacyCampaigns(campaigns: any[]) {
  let contentItems = 0;
  let jobs = 0;
  const warnings: string[] = [];

  for (const campaign of campaigns ?? []) {
    const sourceKey = String(campaign?.id ?? "").trim();
    const brandName = String(campaign?.brand ?? "").trim();
    const brandSlug = BRAND_ALIASES[brandName];
    if (!sourceKey || !brandSlug) {
      warnings.push(`Skipped ${sourceKey || "unknown"}: unmapped brand ${brandName || "unknown"}`);
      continue;
    }
    if (campaign?.requires_verification === true) {
      warnings.push(`Held ${sourceKey}: fresh verification is required before SocialMarket approval`);
      continue;
    }

    const { data: brand, error: brandError } = await supabase
      .from("brand_sites").select("id,slug,name").eq("slug", brandSlug).single();
    if (brandError || !brand) throw brandError ?? new Error(`brand_not_found:${brandSlug}`);

    const platformText = campaign?.platform_text ?? {};
    const services: string[] = Array.isArray(campaign?.services) ? campaign.services : [];
    const firstCopy = services.map((x) => platformText?.[x]).find((x) => typeof x === "string" && x.trim()) ?? campaign?.text ?? "";
    const mediaUrl = campaign?.media_url || rawAssetUrl(campaign?.asset_filename);
    const metadata = {
      source: "socialscheduler_legacy_backlog",
      idea_id: campaign?.idea_id ?? null,
      idea_title: campaign?.idea_title ?? null,
      alt_text: campaign?.alt_text ?? null,
      imported_at: new Date().toISOString(),
    };

    const { data: item, error: itemError } = await supabase
      .from("content_items")
      .upsert({
        source_key: sourceKey,
        brand_site_id: brand.id,
        title: campaign?.topic || campaign?.idea_title || sourceKey,
        angle: campaign?.topic ?? null,
        core_copy: firstCopy || null,
        media_url: mediaUrl,
        status: "approved",
        scheduled_from: campaign?.target_at ?? null,
        approved_at: new Date().toISOString(),
        metadata,
        updated_at: new Date().toISOString(),
      }, { onConflict: "source_key" })
      .select("id").single();
    if (itemError || !item) throw itemError ?? new Error(`content_item_upsert_failed:${sourceKey}`);
    contentItems += 1;

    for (const platform of services) {
      if (!["facebook", "instagram", "tiktok"].includes(platform)) continue;
      if (campaign?.hold_services?.[platform] === true) {
        warnings.push(`Held ${sourceKey}/${platform}: preserved as non-executable legacy hold`);
        continue;
      }
      const caption = String(platformText?.[platform] ?? campaign?.text ?? "").trim();
      if (!caption) {
        warnings.push(`Skipped ${sourceKey}/${platform}: empty caption`);
        continue;
      }
      const format = campaign?.format?.[platform] || "post";
      const outboxRow = {
        content_item_id: item.id,
        platform,
        caption,
        hashtags: hashtagsFromCaption(caption),
        format,
        media_url: mediaUrl,
        tracking_url: campaign?.tracking_url ?? null,
        scheduled_for: campaign?.target_at ?? null,
        status: "approved",
        executor_metadata: {
          source: "socialscheduler_legacy_backlog",
          legacy_idea_id: campaign?.idea_id ?? null,
        },
        updated_at: new Date().toISOString(),
      };
      const { error: outboxError } = await supabase
        .from("publishing_outbox")
        .upsert(outboxRow, { onConflict: "content_item_id,platform" });
      if (outboxError) throw outboxError;
      jobs += 1;
    }
  }
  return { content_items: contentItems, jobs, warnings };
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { status: 204 });
  try {
    const claims = await authorizeGithubAction(req);
    const body = req.method === "POST" ? await req.json().catch(() => ({})) : {};
    const action = String(body?.action ?? new URL(req.url).searchParams.get("action") ?? "health");

    if (action === "health") {
      const { count, error } = await supabase.from("publishing_outbox").select("id", { count: "exact", head: true });
      if (error) throw error;
      return json({ ok: true, repository: claims.repository, outbox_jobs: count ?? 0 });
    }

    if (action === "peek") {
      const limit = Math.max(1, Math.min(Number(body?.limit ?? 10), 50));
      const { data, error } = await supabase
        .from("publishing_outbox")
        .select("id,content_item_id,platform,caption,hashtags,format,media_url,tracking_url,scheduled_for,priority,content_items(title,brand_sites(slug,name))")
        .eq("status", "approved")
        .not("scheduled_for", "is", null)
        .order("scheduled_for", { ascending: true })
        .order("priority", { ascending: false })
        .limit(limit);
      if (error) throw error;
      const jobs = (data ?? []).map((row: any) => ({
        ...row,
        title: row.content_items?.title ?? null,
        brand_slug: row.content_items?.brand_sites?.slug ?? null,
        brand_name: row.content_items?.brand_sites?.name ?? null,
        content_items: undefined,
      }));
      return json({ ok: true, jobs });
    }

    if (action === "claim") {
      const limit = Math.max(1, Math.min(Number(body?.limit ?? 10), 50));
      const { data, error } = await supabase.rpc("claim_publishing_jobs", {
        p_executor: String(body?.executor ?? "socialscheduler"),
        p_limit: limit,
        p_lease_minutes: Math.max(5, Math.min(Number(body?.lease_minutes ?? 30), 120)),
      });
      if (error) throw error;
      return json({ ok: true, jobs: data ?? [] });
    }

    if (action === "ack") {
      const { data, error } = await supabase.rpc("ack_publishing_job", {
        p_job_id: body?.job_id,
        p_status: body?.status,
        p_external_post_id: body?.external_post_id ?? null,
        p_external_permalink: body?.external_permalink ?? null,
        p_scheduled_at: body?.scheduled_at ?? null,
        p_published_at: body?.published_at ?? null,
        p_error: body?.error ?? null,
        p_executor_metadata: body?.metadata ?? {},
      });
      if (error) throw error;
      return json({ ok: true, job: data });
    }

    if (action === "reconcile") {
      const { data, error } = await supabase.rpc("list_publishing_reconcile_jobs", {
        p_limit: Math.max(1, Math.min(Number(body?.limit ?? 200), 500)),
      });
      if (error) throw error;
      return json({ ok: true, jobs: data ?? [] });
    }

    if (action === "import_legacy") {
      if (!Array.isArray(body?.campaigns)) return json({ ok: false, error: "campaigns_array_required" }, 400);
      const result = await importLegacyCampaigns(body.campaigns);
      return json({ ok: true, ...result });
    }

    return json({ ok: false, error: "unknown_action" }, 400);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    const unauthorized = ["missing_github_oidc_token", "repository_not_allowed", "only_main_branch_is_allowed", "JWTClaimValidationFailed", "JWSSignatureVerificationFailed"].some((x) => message.includes(x));
    return json({ ok: false, error: message }, unauthorized ? 401 : 503);
  }
});
