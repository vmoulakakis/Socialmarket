# CarCare Greece — Awin marketplace MVP
Isolated Next.js app under the existing SocialMarket control plane. The existing main SocialMarket application, its routes, content, Buffer pipeline and shared data remain unchanged.

## Current capabilities
- Interactive Greek tyre-size assistant with AJAX offer lookup, exact dimensions and up to three matching offers.
- Zero invented products or prices. Empty results include a useful safety checklist.
- Supabase RLS public visibility only for joined and approved advertisers, eligible stocked offers, commission at least EUR 10, tracked HTTPS Awin URLs and freshness under 72 hours.
- The app defaults to non-commercial mode; API returns no offers and outbound Awin redirect is disabled until an authorized commercial hosting environment is configured.
- Awin MCP connected in ChatGPT to publisher 3060863, Back Market GR currently pending; actual feed/commission secrets not yet configured.
- No automatic advertiser join API exists in the currently connected MCP; merchant approval is controlled by Awin/advertisers.

## Run / test
Run npm install then npm test and npm run build from apps/carcare.
Configure SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY for REST read from existing isolated carcare tables.
Do not commit any Awin feed URLs, Supabase secret keys or tokens.
The commercial site MUST NOT be deployed to Vercel Hobby, whose terms require personal/non-commercial use.
## Acceptance
Test actual feed integration after joined merchant, verified commission and approved feed URL. Keep paid publishing, tracking, feed refresh and automation disabled until credentials and policy are reviewed.
