import "jsr:@supabase/functions-js/edge-runtime.d.ts";

const BUFFER_API_URL = "https://api.buffer.com";
const SUPPORTED = new Set(["facebook", "instagram", "tiktok"]);

function corsHeaders(req: Request) {
  const origin = req.headers.get("origin") || "*";
  return {
    "access-control-allow-origin": origin,
    "access-control-allow-methods": "GET,POST,OPTIONS",
    "access-control-allow-headers": "authorization, x-client-info, apikey, content-type",
    "vary": "origin",
  };
}

function json(req: Request, data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      ...corsHeaders(req),
      "content-type": "application/json",
      "cache-control": "no-store",
    },
  });
}

function env(name: string) {
  return Deno.env.get(name) || "";
}

async function gql<T>(query: string, variables: Record<string, unknown> = {}) {
  const apiKey = env("BUFFER_API_KEY");
  if (!apiKey) throw new Error("BUFFER_API_KEY_missing");

  const response = await fetch(BUFFER_API_URL, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({ query, variables }),
  });

  const text = await response.text();
  let payload: any;
  try {
    payload = text ? JSON.parse(text) : {};
  } catch {
    throw new Error(`Buffer returned non-JSON HTTP ${response.status}`);
  }

  if (!response.ok) {
    throw new Error(`Buffer HTTP ${response.status}: ${JSON.stringify(payload).slice(0, 600)}`);
  }
  if (payload?.errors?.length) {
    throw new Error(`Buffer GraphQL: ${payload.errors.map((x: any) => x?.message || "unknown error").join("; ")}`);
  }
  return payload.data as T;
}

type BufferOrg = { id: string; name: string };
type BufferChannel = {
  id: string;
  name: string;
  displayName?: string | null;
  descriptor?: string | null;
  service: string;
  avatar?: string | null;
  externalLink?: string | null;
  isQueuePaused?: boolean;
  isDisconnected?: boolean;
  isLocked?: boolean;
  organizationId?: string;
};

async function fetchBufferChannels() {
  const accountData = await gql<{ account: { id: string; organizations: BufferOrg[] } }>(`
    query SocialmarketBufferAccount {
      account {
        id
        organizations {
          id
          name
        }
      }
    }
  `);

  const organizations = accountData?.account?.organizations || [];
  const groups = await Promise.all(
    organizations.map(async (organization) => {
      const data = await gql<{ channels: BufferChannel[] }>(
        `query SocialmarketBufferChannels($organizationId: OrganizationId!) {
          channels(input: { organizationId: $organizationId }) {
            id
            name
            displayName
            descriptor
            service
            avatar
            externalLink
            isQueuePaused
            isDisconnected
            isLocked
            organizationId
          }
        }`,
        { organizationId: organization.id },
      );
      return (data?.channels || []).map((channel) => ({
        ...channel,
        organizationName: organization.name,
      }));
    }),
  );

  const allChannels = groups.flat();
  const channels = allChannels
    .filter((channel) => SUPPORTED.has(String(channel.service || "").toLowerCase()))
    .sort((a, b) => String(a.service).localeCompare(String(b.service)) || String(a.displayName || a.name).localeCompare(String(b.displayName || b.name)));

  return {
    accountId: accountData?.account?.id || null,
    organizationCount: organizations.length,
    totalChannelCount: allChannels.length,
    channels,
  };
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: corsHeaders(req) });

  try {
    const url = new URL(req.url);
    const action = url.pathname.split("/").filter(Boolean).pop() || "";

    if (req.method === "GET" && action === "health") {
      return json(req, {
        ok: true,
        service: "buffer-sync",
        configured: Boolean(env("BUFFER_API_KEY")),
        missing: env("BUFFER_API_KEY") ? [] : ["BUFFER_API_KEY"],
        supportedPlatforms: [...SUPPORTED],
      });
    }

    if ((req.method === "POST" || req.method === "GET") && ["sync", "channels"].includes(action)) {
      if (!env("BUFFER_API_KEY")) {
        return json(req, { error: "buffer_not_configured", missing: ["BUFFER_API_KEY"] }, 503);
      }
      const result = await fetchBufferChannels();
      return json(req, { ok: true, syncedAt: new Date().toISOString(), ...result });
    }

    return json(req, { error: "not_found" }, 404);
  } catch (error) {
    console.error(error);
    return json(req, { error: String(error instanceof Error ? error.message : error) }, 500);
  }
});
