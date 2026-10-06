# AliExpress Affiliate Gateway

Central server-side gateway for all Socialmarket and standalone affiliate funnels.

Required Supabase secrets:
- `ALIEXPRESS_APP_KEY`
- `ALIEXPRESS_APP_SECRET`
- `ALIEXPRESS_TRACKING_ID`

Never commit secret values to GitHub or expose them to a browser bundle.

Actions:
- `search`: AliExpress affiliate product discovery, defaults to EUR / Greece.
  Omit `sort` for the API's native relevance order; pass
  `LAST_VOLUME_DESC` for an independent popularity pass.
- `hotproducts`: hot-product discovery.
- `details`: refreshes up to 40 product IDs before deterministic scoring.
- `generate_link`: converts a verified AliExpress product URL to the account's affiliate promotion link.

The gateway intentionally reads credentials only through `Deno.env` so future Vercel sites can use one centralized integration without duplicating AliExpress credentials.

Gap Solver V2 uses this gateway only after a Greek problem passes demand and
market-gap evidence gates. See [`docs/ALIEXPRESS_GAP_SOLVER_V2.md`](../../../docs/ALIEXPRESS_GAP_SOLVER_V2.md).
