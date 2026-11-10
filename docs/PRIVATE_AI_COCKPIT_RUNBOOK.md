# SocialMarket AI — Private Control Cockpit

**Version:** 1.0.0 (2026-10-31)  
**Repository:** `vmoulakakis/Socialmarket` · protected preview branch `feat/socialmarket-vmdb-intelligence-v1-20261030`  
**VMDB:** `gqpbskssrvpfjtujwezc`, isolated `sm_intel` private schema.

## Purpose
Single, desktop-first, responsive personal workstation to **inspect and control** the SocialMarket backend and AI database. Accurate decision support for affiliate eligibility, full-feed ingestion, merchant identity, demand/supply research, AI retrieval, agents, budget and audit.

The private cockpit is NOT an affiliate storefront, public API, nor proof that upstream AI/embedding/Linkwise workers are running.

## Personal access and deployment
- Route: `/ai-cockpit` on the EXISTING Next.js SocialMarket app. Do not change default public sites or main branch.
- Vercel preview requires Vercel Deployment Protection SSO (confirmed enabled on the SocialMarket project for preview deployments). Production custom domains are not the requested target.
- The in-app AuthGate uses Supabase Auth restricted to an approved administrator account. Every cockpit Next.js API request independently validates its Supabase JWT using `adminAuth`, then PostgreSQL independently checks `auth.uid()` and `private.is_admin()`.
- `sm_intel` tables stay private; anon and authenticated direct SQL table access not granted. No service_role, database password, Vault secret, raw third-party feed URL or privileged cookie appears in browser data.
- `Cache-Control: private, no-store`, no arbitrary SQL, no unsafe shell/remote fetch.
- Deployment must target a tested Git commit and **preview only**, not `main`/production.
- 2026-10-31 current blocker: Vercel `POST /v13/deployments` responded `402 api-deployments-free-per-day` (>100 free API deployments/24h); existing 2026-10-30 latest READY preview commit predates cockpit. Do not misrepresent it as deployed.

## Screens / modules
1. **Mission Control**: catalog, programs, indexed docs, affiliate-ready count, agent queue; pipeline stages; priority alerts; shared AI budget consumption; task distribution bar chart.
2. **Catalog & Merchants**: fresh vs stale, unknown program IDs and valid-to, active source data, product category distribution, merchant mapping states, feed run history with stored/rejected counts.
3. **AI Intelligence**: vector/GraphRAG readiness (E5 384D), graph nodes and verified edges, keyword/SQL hybrid retrieval with candidate evidence disclosure, Greek market research backlog.
4. **Operations & Audit**: audited safe backend commands, objective pause/resume, recorded agent-run traces, real legacy cron/stale run watchdog, audit trail, descriptive read-only configuration.

## API contracts
`GET /api/ai-cockpit` -> auth-verified RPCs:
- `public.socialmarket_cockpit_snapshot()`
- `public.socialmarket_cockpit_runtime_health()`

`GET /api/ai-cockpit?q=...` -> admin-verified `public.socialmarket_cockpit_search(p_query, p_limit)`, bounded SQL + RRF candidate retrieval, **not verified commercial recommendations**.

`POST /api/ai-cockpit` only accepts `{action, target?}`:
- `sync_search_docs`: reindex existing text source docs only (no paid embeddings).
- `queue_research`: add missing research tasks idempotently.
- `pause_objective`/`resume_objective`: enforce specialist dispatch status via `sm_intel.claim_architect_tasks`.

Actions are server-allowlisted, bounded, admin-only, persisted in `sm_intel.cockpit_audit`. No feed import, publishing, commission override, refund, Awin application or remote LLM invocation button.

## Monitoring terminology (do not mix)
- `raw_products` = historical catalog rows; not number of available or commercially valid products.
- `merchant_program_rows` = source program entries; not approved merchant profiles.
- `qualified_offers` = verified, calculated minimum affiliate commission ≥€10, not automatically promotional.
- `promotion_ready_offers` = approved, verified tracking, in-stock, current source and approval, fail-closed.
- `searchable_docs` = indexed SQL/FTS text; `vector_docs` = E5 actually embedded documents.
- `graph_edges` = candidate links; `graph_verified_edges` = supported, verified evidence edges.
- `agent_tasks` = queued work, not completed research.
- `budgets` from `public.agent_budget_policies` and `public.agent_usage_ledger` are currently **shared VMDB governance budgets**, not exclusively per SocialMarket. Show them as shared.
- `legacy_linkwise_cron.active` reports scheduler configuration, not a successful job; stalled runs are separately counted.
- The user previously explicitly forbade a full JSON upload/import during this stage; leave legacy background job untouched and never trigger new feed import from cockpit.

## Verification / release checklist
- [x] SQL migration applied and admin-claim simulation fetched actual snapshot.
- [x] Non-admin simulated JWT rejected for snapshot and command.
- [x] Admin SQL/FTS search returned product matches.
- [x] API route checks admin session on every GET/POST; private tables never exposed to client.
- [x] Safe-control audit table and pause-aware agent claim SQL created.
- [ ] Latest Vercel preview deployment READY at the cockpit source commit (blocked by free API deployment quota).
- [ ] Authenticated browser QA on actual preview desktop and mobile.
- [ ] Full-feed streaming import remains disabled by request.
- [ ] Vector embeddings from multilingual E5 remain pending; no false AI readiness status.

**Future enhancements after safe deployment:** independent evidence quality benchmark dashboard, merchant identity remediation wizard, double-confirmation for high-impact system tasks, conversion/refund KPI normalization, and semantic embedding runtime once E5 worker is provisioned.
